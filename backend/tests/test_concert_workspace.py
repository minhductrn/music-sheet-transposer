"""S2A-02 integration: editable result → independent Save As → reimport."""
from xml.etree import ElementTree as ET

from music.test_concert_key import score, invariant
from test_phase4e_workflow import workflow, create, event, patch, verify, xml


def test_edited_concert_result_save_as_reimport(workflow, tmp_path):
    client, _ = workflow
    original = score(-1, 'major', 'F').replace(b'<mode>major</mode>', b'')
    root = ET.fromstring(original)
    measure = root.find('.//measure')
    measure.remove(measure.find('harmony'))
    for step, kind in [('G', 'minor'), ('C', 'dominant'), ('F', 'major')]:
        harmony = ET.SubElement(measure, 'harmony')
        ET.SubElement(ET.SubElement(harmony, 'root'), 'root-step').text = step
        ET.SubElement(harmony, 'kind').text = kind
    original = ET.tostring(root)
    source = tmp_path / 'original.musicxml'
    source.write_bytes(original)
    response = client.post('/api/v1/transpose/concert-key', files={'file': (source.name, source.read_bytes())},
                           data={'source_fifths': '-1', 'source_mode': 'major', 'source_confirmed': 'true',
                                 'target_fifths': '-3', 'direction': 'down'})
    assert response.status_code == 200, response.text
    output = ET.fromstring(response.content)
    assert output.findtext('.//key/fifths') == '-3'
    assert [(h.findtext('root/root-step'), h.findtext('root/root-alter', '0'), h.findtext('kind'))
            for h in output.findall('.//harmony')] == [('F', '0', 'minor'), ('B', '-1', 'dominant'), ('E', '-1', 'major')]
    assert invariant(response.content) == invariant(original)
    review = create(client, response.content)
    # Exercise supported right-panel edits through the very same Stage 1 API.
    edited = patch(client, review, 'e-1', tie_direction='down')
    edited = patch(client, edited, 'e-2', display_size='small')
    confirmed = verify(client, edited)
    exported = client.get(f'/api/v1/reviews/{confirmed["id"]}/musicxml?verified_only=true')
    assert exported.status_code == 200
    saved = tmp_path / 'edited-result.musicxml'
    saved.write_bytes(exported.content)
    reopened = create(client, saved.read_bytes())
    assert xml(reopened) == exported.content
    assert event(reopened, 'e-1')['tie_direction'] == 'down'
    assert event(reopened, 'e-1')['tie_target_id'] == 'e-4'
    assert event(reopened, 'e-2')['display_size'] == 'small'
    assert event(reopened, 'e-2')['tie_direction'] == 'down'
    assert event(reopened, 'e-2')['tie_target_id'] == 'e-5'
    for field in ('pitch', 'duration', 'voice', 'staff', 'chord_id'):
        assert event(reopened, 'e-1')[field] == event(review, 'e-1')[field]
    reopened_tree = ET.fromstring(xml(reopened))
    for tag in ('lyric', 'harmony', 'chord'):
        assert [ET.tostring(n) for n in reopened_tree.findall(f'.//{tag}')] == [ET.tostring(n) for n in output.findall(f'.//{tag}')]
    assert source.read_bytes() == original
