"""User-driven 3:2 edits through revisioned history and saved canonical XML."""
from fractions import Fraction
from xml.etree import ElementTree as ET
import pytest
from test_phase4e_workflow import workflow, create, request, xml, verify
from test_delete_preserve_timing import score, note, remove, events


def insert_payload(**extra):
    return dict(measure_id='m-1', voice='1', staff=1, base_duration='1/2', onset='1',
                pitches=[dict(step=p, alter='0', octave=5) for p in 'DFE'], **extra)


def assert_triplet(review):
    root = ET.fromstring(xml(review))
    nodes = [n for n in root.findall('.//note') if n.find('time-modification') is not None]
    assert len(nodes) == 3
    assert [n.findtext('time-modification/actual-notes') for n in nodes] == ['3'] * 3
    assert [n.findtext('time-modification/normal-notes') for n in nodes] == ['2'] * 3
    assert [n.findtext('type') for n in nodes] == ['eighth'] * 3
    assert [[t.attrib for t in n.findall('notations/tuplet')] for n in nodes] == [
        [{'type': 'start', 'number': '1', 'bracket': 'yes', 'show-number': 'actual'}], [], [{'type': 'stop', 'number': '1'}]]


def musical(review):
    return [(e['kind'], e['pitch'], e['onset'], e['duration'], e['voice'], e['staff'], e['ties']) for e in events(review).values()]


def test_delete_replace_triplet_history_save_export_reimport(workflow):
    client, _ = workflow
    original = create(client, score(note('C') + note('D') + note('G', 2)))
    before = remove(client, original, 'e-2')
    result = request(client, before, 'triplets', insert_payload())
    assert result.status_code == 200, result.text
    after = result.json()
    assert_triplet(after)
    added = [e for key, e in events(after).items() if key not in events(before)]
    assert [e['pitch']['step'] for e in added] == list('DFE')
    assert [e['onset'] for e in added] == ['1', '4/3', '5/3']
    assert [e['duration'] for e in added] == ['1/3'] * 3
    for key in events(before):
        old, new = events(before)[key], events(after)[key]
        for field in ('kind', 'pitch', 'onset', 'duration', 'voice', 'staff', 'lyric_ids', 'ties'):
            assert new[field] == old[field]
    assert before['score']['lyrics'] == after['score']['lyrics']
    assert request(client, before, 'triplets', insert_payload()).status_code == 409
    undone = request(client, after, 'undo').json()
    assert xml(undone) == xml(before)
    redone = request(client, undone, 'redo').json()
    assert xml(redone) == xml(after)
    saved = verify(client, redone)
    exported = client.get(f'/api/v1/reviews/{saved["id"]}/musicxml?verified_only=true')
    assert exported.status_code == 200
    reopened = create(client, exported.content)
    assert_triplet(reopened)
    assert musical(reopened) == musical(saved)
    assert [n.findtext('lyric/text') for n in ET.fromstring(exported.content).findall('.//note')] == [n.findtext('lyric/text') for n in ET.fromstring(xml(reopened)).findall('.//note')]


def test_convert_explicit_existing_notes_preserves_following_onsets(workflow):
    client, _ = workflow
    before = create(client, score(note('C') + note('D') + note('E') + note('F')))
    payload = dict(measure_id='m-1', voice='1', staff=1, base_duration='1/2', event_ids=['e-1', 'e-2', 'e-3'])
    result = request(client, before, 'triplets', payload)
    assert result.status_code == 200, result.text
    after = result.json()
    assert_triplet(after)
    assert [events(after)[f'e-{i}']['pitch'] for i in (1, 2, 3)] == [events(before)[f'e-{i}']['pitch'] for i in (1, 2, 3)]
    assert events(after)['e-4']['onset'] == events(before)['e-4']['onset'] == '3'
    assert after['score']['lyrics'] == before['score']['lyrics']
    assert [events(after)[f'e-{i}']['onset'] for i in (1, 2, 3)] == ['0', '1/3', '2/3']
    assert request(client, after, 'triplets', payload).status_code == 422


@pytest.mark.parametrize('base', ['4', '2', '1', '1/2', '1/4', '1/8', '1/16'])
def test_all_supported_written_values_refine_divisions_exactly(workflow, base):
    client, _ = workflow
    before = create(client, score(''))
    payload = insert_payload(); payload.update(base_duration=base, onset='0')
    result = request(client, before, 'triplets', payload)
    assert result.status_code == 200, result.text
    after = result.json()
    added = [e for k, e in events(after).items() if k not in events(before)]
    assert len(added) == 3
    assert [Fraction(e['duration']) for e in added] == [Fraction(base) * Fraction(2, 3)] * 3
    assert events(after)['e-1']['duration'] == '4'  # Later inherited divisions remain musically unchanged.


@pytest.mark.parametrize('update', [dict(onset='bad'), dict(voice=''), dict(pitches=[]), dict(staff=3), dict(onset='-1')])
def test_invalid_requests_are_atomic(workflow, update):
    client, _ = workflow
    before = create(client, score(''))
    payload = insert_payload(); payload.update(update)
    response = request(client, before, 'triplets', payload)
    assert response.status_code == 422, response.text
    current = client.get(f'/api/v1/reviews/{before["id"]}').json()
    assert current['revision'] == before['revision']
    assert xml(current) == xml(before)


def test_overlap_is_not_silently_replaced(workflow):
    client, _ = workflow
    before = create(client, score(note('C', 4)))
    result = request(client, before, 'triplets', insert_payload())
    assert result.status_code == 422
    assert xml(client.get(f'/api/v1/reviews/{before["id"]}').json()) == xml(before)


def test_unrelated_chord_rest_lyrics_ties_text_and_checks_are_preserved(workflow):
    client, _ = workflow
    tied = note('F', 2).replace('<voice>', '<tie type="start"/><voice>').replace('<lyric>', '<notations><tied type="start" orientation="over"/></notations><lyric>')
    rest = '<note><rest/><duration>1</duration><voice>1</voice><type>quarter</type><staff>1</staff></note>'
    body = '<direction><direction-type><words>Ngài yêu thương</words></direction-type></direction>' + note('C') + note('E', chord=True) + rest + tied
    source = score(body).replace(note('G', 4).encode(), note('F', 4).replace('<voice>', '<tie type="stop"/><voice>').replace('<lyric>', '<notations><tied type="stop" orientation="over"/></notations><lyric>').encode())
    source = source.replace(b'<lyric><text>C</text></lyric>', '<lyric number="1"><text>Đấng</text></lyric><lyric number="2"><text>Ngài</text></lyric>'.encode())
    before = create(client, source)
    payload = insert_payload(); payload.update(onset='4')  # Explicit overfull correction is permitted; never repair meter.
    response = request(client, before, 'triplets', payload)
    assert response.status_code == 200, response.text
    after = response.json()
    for key, old in events(before).items():
        new = events(after)[key]
        for field in ('kind', 'pitch', 'duration', 'onset', 'chord_id', 'chord_member', 'voice', 'staff', 'ties', 'lyric_ids', 'notated_duration'):
            assert new[field] == old[field]
    assert before['score']['lyrics'] == after['score']['lyrics']
    assert before['score']['texts'] == after['score']['texts']
    checked = request(client, after, 'validate').json()
    assert xml(checked) == xml(after)  # Validation never regenerates/corrects the user's notes.
    assert_triplet(checked)
    saved = verify(client, checked)
    exported = client.get(f'/api/v1/reviews/{saved["id"]}/musicxml?verified_only=true')
    reopened = create(client, exported.content)
    assert musical(reopened) == musical(saved)
    assert_triplet(reopened)
    # Approved Stage 2 preservation transposer reads saved corrected XML, no OMR.
    from app.music.musicxml.transposer import transpose_musicxml_document
    transposed = transpose_musicxml_document(exported.content, 2)
    root = ET.fromstring(transposed)
    assert len(root.findall('.//time-modification/actual-notes')) == 3
    assert len(root.findall('.//tuplet')) == 2


@pytest.mark.parametrize('ids', [['e-2', 'e-1', 'e-3'], ['e-1', 'e-1', 'e-3'], ['e-1', 'e-3', 'e-4']])
def test_ambiguous_conversion_never_changes_any_note(workflow, ids):
    client, _ = workflow
    before = create(client, score(note('C') + note('D') + note('E') + note('F')))
    response = request(client, before, 'triplets', dict(measure_id='m-1', voice='1', staff=1, base_duration='1/2', event_ids=ids))
    assert response.status_code == 422
    assert xml(client.get(f'/api/v1/reviews/{before["id"]}').json()) == xml(before)


def test_divisions_refinement_preserves_decimal_direction_offsets(workflow):
    client, _ = workflow
    before = create(client, score('<direction><direction-type><words>Keep</words></direction-type><offset>0.25</offset></direction>'))
    payload = insert_payload(); payload['onset'] = '0'
    response = request(client, before, 'triplets', payload)
    assert response.status_code == 200, response.text
    root = ET.fromstring(xml(response.json()))
    assert root.findtext('.//offset') == '1.5'
    assert Fraction(root.findtext('.//offset')) / Fraction(root.findtext('.//divisions')) == Fraction(1, 4)


def test_refinement_preserves_note_playback_and_figured_bass_units(workflow):
    client, _ = workflow
    body = '<figured-bass><figure><figure-number>6</figure-number></figure><duration>1</duration></figured-bass>' + note('C').replace('<note>', '<note attack="0.25" release="0.125">')
    before = create(client, score(body))
    payload = insert_payload(); payload['onset'] = '1'
    response = request(client, before, 'triplets', payload)
    assert response.status_code == 200, response.text
    root = ET.fromstring(xml(response.json()))
    assert root.find('.//note').get('attack') == '1.5'
    assert root.find('.//note').get('release') == '0.75'
    assert Fraction(root.findtext('.//figured-bass/duration')) / Fraction(root.findtext('.//divisions')) == 1
