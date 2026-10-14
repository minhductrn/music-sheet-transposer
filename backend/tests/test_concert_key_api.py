"""Saved-file → concert transpose → independent Save As → editable Open."""
from xml.etree import ElementTree as ET

import pytest

from music.test_concert_key import score, invariant
from test_phase4e_workflow import workflow, create, event, patch, verify, xml


def test_saved_concert_roundtrip_preserves_corrections_and_original(workflow, tmp_path):
    client, _ = workflow
    saved_path = tmp_path / 'source.musicxml'
    saved_path.write_bytes(score())
    original = saved_path.read_bytes()
    files = {'file': ('source.musicxml', original)}
    inspected = client.post('/api/v1/concert-key', files=files)
    assert inspected.status_code == 200, inspected.text
    assert inspected.json()['suggested'] == {'fifths': 0, 'mode': 'major'}
    response = client.post('/api/v1/transpose/concert-key', files=files,
                           data={'target_fifths': '-2', 'direction': 'down', 'source_fifths': '0', 'source_mode': 'major', 'source_confirmed': 'true'})
    assert response.status_code == 200, response.text
    output_path = tmp_path / 'new-concert.musicxml'
    output_path.write_bytes(response.content)
    assert saved_path.read_bytes() == original
    assert invariant(output_path.read_bytes()) == invariant(original)
    reopened = create(client, output_path.read_bytes())
    assert xml(reopened) == response.content
    assert event(reopened, 'e-1')['tie_target_id'] == 'e-4'
    assert event(reopened, 'e-2')['tie_target_id'] == 'e-5'
    assert event(reopened, 'e-1')['tie_direction'] == 'up'
    assert event(reopened, 'e-2')['tie_direction'] == 'down'
    assert event(reopened, 'e-1')['display_size'] == 'small'
    assert event(reopened, 'e-2')['display_size'] == 'normal'
    assert event(reopened, 'e-1')['pitch']['step'] == 'B'
    assert event(reopened, 'e-1')['pitch']['alter'] == '-1'
    assert reopened['semantic_recovery'] is None
    confirmed = verify(client, reopened)
    exported = client.get(f'/api/v1/reviews/{confirmed["id"]}/musicxml?verified_only=true')
    assert exported.status_code == 200
    assert exported.content == response.content
    # Output is still editable and history works without touching the saved file.
    changed = patch(client, confirmed, 'e-1', tie_direction='down')
    assert event(changed, 'e-1')['tie_direction'] == 'down'
    assert output_path.read_bytes() == response.content
    root = ET.fromstring(exported.content)
    assert len(root.findall('.//lyric')) == 4
    assert len(root.findall('.//chord')) == 2


@pytest.mark.parametrize('data', [{'target_fifths': '8'}, {'direction': 'sideways'}, {'target_fifths': '1.5'}])
def test_invalid_target_contract(workflow, data):
    client, _ = workflow
    response = client.post('/api/v1/transpose/concert-key', files={'file': ('saved.musicxml', score())}, data={'source_fifths': '0', 'source_mode': 'major', 'source_confirmed': 'true', **data})
    assert response.status_code == 422


def test_missing_mode_returns_candidates_without_a_suggestion(workflow):
    client, _ = workflow
    response = client.post('/api/v1/concert-key', files={'file': ('saved.musicxml', score().replace(b'<mode>major</mode>', b''))})
    assert response.status_code == 200
    assert response.json() == {'fifths': 0, 'mode': None, 'suggested': None,
                               'candidates': [{'fifths': 0, 'mode': 'major'}, {'fifths': 0, 'mode': 'minor'}]}


@pytest.mark.parametrize('mode', ['major', 'minor'])
def test_confirmed_one_flat_save_open_export_roundtrip(workflow, tmp_path, mode):
    client, _ = workflow
    original = score(-1, 'major', 'F' if mode == 'major' else 'D').replace(b'<mode>major</mode>', b'')
    source_file = tmp_path / 'concert.musicxml'
    source_file.write_bytes(original)
    response = client.post('/api/v1/transpose/concert-key', files={'file': ('concert.musicxml', source_file.read_bytes())},
                           data={'source_fifths': '-1', 'source_mode': mode, 'source_confirmed': 'true',
                                 'target_fifths': '1', 'direction': 'up'})
    assert response.status_code == 200, response.text
    saved_file = tmp_path / 'independent.musicxml'
    saved_file.write_bytes(response.content)
    assert source_file.read_bytes() == original
    assert invariant(response.content) == invariant(original)
    reopened = create(client, saved_file.read_bytes())
    assert event(reopened, 'e-1')['tie_target_id'] == 'e-4'
    assert event(reopened, 'e-2')['tie_target_id'] == 'e-5'
    assert event(reopened, 'e-1')['tie_direction'] == 'up'
    assert event(reopened, 'e-2')['tie_direction'] == 'down'
    assert event(reopened, 'e-1')['display_size'] == 'small'
    confirmed = verify(client, reopened)
    exported = client.get(f'/api/v1/reviews/{confirmed["id"]}/musicxml?verified_only=true')
    assert exported.status_code == 200 and exported.content == saved_file.read_bytes()
    assert ET.fromstring(exported.content).findtext('.//key/mode') == mode


@pytest.mark.parametrize('fields,expected', [
    ({'source_confirmed': 'false'}, 'Confirm the Source Key'),
    ({'source_fifths': '0'}, 'incompatible'),
    ({'source_mode': 'dorian'}, None),
])
def test_confirmation_and_signature_are_validated_by_api(workflow, fields, expected):
    client, _ = workflow
    original = score(-1).replace(b'<mode>major</mode>', b'')
    data = {'source_fifths': '-1', 'source_mode': 'major', 'source_confirmed': 'true', 'target_fifths': '1', **fields}
    response = client.post('/api/v1/transpose/concert-key', files={'file': ('source.musicxml', original)}, data=data)
    assert response.status_code == 422
    if expected:
        assert expected in response.json()['detail']


def test_confirmation_fields_are_required_even_with_explicit_mode(workflow):
    client, _ = workflow
    response = client.post('/api/v1/transpose/concert-key', files={'file': ('source.musicxml', score(-1))}, data={'target_fifths': '1'})
    assert response.status_code == 422
    assert {i['loc'][-1] for i in response.json()['detail']} == {'source_fifths', 'source_mode', 'source_confirmed'}


@pytest.mark.parametrize('replacement,expected', [
    ((b'<key><fifths>0</fifths><mode>major</mode></key>', b''), 'source key is missing'),
    ((b'<mode>major</mode>', b'<mode>dorian</mode>'), 'unsupported modes'),
])
def test_missing_or_unsupported_key_information_is_actionable(workflow, replacement, expected):
    client, _ = workflow
    response = client.post('/api/v1/concert-key', files={'file': ('source.musicxml', score().replace(*replacement))})
    assert response.status_code == 422
    assert expected in response.json()['detail']
