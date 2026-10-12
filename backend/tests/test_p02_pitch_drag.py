"""Direct drag uses existing single-event pitch PATCH and preservation/history lifecycle."""
from copy import deepcopy
from xml.etree import ElementTree as ET
import pytest
from test_phase4e_workflow import workflow, create, request, event, xml, verify
from test_review_existing_ties import XML as BASE, tie


def fixture_xml(small=False, grace=False, sign=None):
    data = BASE.replace(b'<step>A</step>', b'<step>C</step>')
    data = data.replace(b'<staves>2</staves>', b'<staves>2</staves><clef><sign>G</sign><line>2</line></clef>')
    data = data.replace(b'<lyric><text>one</text></lyric>', b'<lyric number="2"><syllabic>single</syllabic><text>one</text></lyric>')
    if small:
        data = data.replace(b'<type>half</type>', b'<type size="cue">half</type>')
    if grace:
        data = data.replace(b'<note><pitch>', b'<note><grace slash="yes"/><pitch>', 1).replace(b'<duration>8</duration>', b'', 1)
    if sign:
        data = data.replace(b'<staff>1</staff>', f'<accidental cautionary="yes">{sign}</accidental><staff>1</staff>'.encode(), 1)
    return data


@pytest.mark.parametrize('small,grace,sign', [(False,False,None),(True,False,None),(True,True,None),(False,False,'natural')])
def test_single_pitch_patch_same_event_preserves_xml_properties_and_history(workflow, small, grace, sign):
    client, _ = workflow
    before = create(client, fixture_xml(small, grace, sign))
    original = deepcopy(event(before, 'e-1'))
    response = request(client, before, 'events/e-1', {'pitch': {'step':'C','octave':5,'alter':'0'}}, 'PATCH')
    assert response.status_code == 200, response.text
    after = response.json()
    changed = event(after, 'e-1')
    assert changed['pitch'] == {'step':'C','octave':5,'alter':'0'}
    for field in ('id','measure_id','onset','duration','duration_units','notated_duration','voice','staff','display_size','grace','lyric_ids','accidental'):
        assert changed[field] == original[field], field
    assert changed['provenance']['evidence_ids'] == original['provenance']['evidence_ids']
    assert after['score']['lyrics'] == before['score']['lyrics']
    assert event(after,'e-2') == event(before,'e-2')
    def without_pitch(data):
        root = ET.fromstring(data, parser=ET.XMLParser(target=ET.TreeBuilder(insert_comments=True)))
        node = root.find('.//note')
        node.remove(node.find('pitch'))
        return ET.tostring(root)
    assert without_pitch(xml(after)) == without_pitch(xml(before))
    assert after['revision'] == before['revision'] + 1
    undo = request(client, after, 'undo').json()
    assert xml(undo) == xml(before)
    redo = request(client, undo, 'redo').json()
    assert xml(redo) == xml(after)


def test_pitch_change_retains_tie_and_slur_and_surfaces_conflict(workflow):
    client, _ = workflow
    before = tie(client, create(client, fixture_xml())).json()
    response = request(client, before, 'events/e-1', {'pitch':{'step':'C','octave':5,'alter':'0'}}, 'PATCH')
    assert response.status_code == 200, response.text
    after = response.json()
    assert event(after,'e-1')['ties'] == ['start']
    assert event(after,'e-2')['ties'] == ['stop']
    assert any('tie' in d['code'] for d in after['validation']['diagnostics'])
    assert b'<slur type="stop" number="1"' in xml(after)


def test_verified_pitch_edit_invalidates_verification_and_blocks_transpose(workflow):
    client, _ = workflow
    before = verify(client, create(client, fixture_xml()))
    response = request(client, before, 'events/e-1', {'pitch': {'step':'C','octave':5,'alter':'0'}}, 'PATCH')
    assert response.status_code == 200, response.text
    after = response.json()
    assert after['state'] == 'REVIEW_REQUIRED'
    assert request(client, after, 'transpose', {'semitones':2}).status_code == 409
