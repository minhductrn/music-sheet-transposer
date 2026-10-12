"""P0.1 symbol commands preserve sounding pitch, explicit signs and XML history."""
from xml.etree import ElementTree as ET
import pytest
from test_phase4e_workflow import workflow, create, request, event, xml
from test_review_existing_ties import XML as BASE


def keyed_xml():
    return BASE.replace(b'<staves>2</staves>', b'<key><fifths>-1</fifths></key><staves>2</staves>')


@pytest.mark.parametrize('step,alter,sign', [
    ('A', '0', None), ('B', '-1', None), ('B', '0', 'natural'),
    ('A', '-1', 'flat'), ('A', '1', 'sharp'),
    ('A', '-2', 'flat-flat'), ('A', '2', 'double-sharp'),
])
def test_inserted_pitch_and_printed_accidental_are_independent(workflow, step, alter, sign):
    client, _ = workflow
    before = create(client, keyed_xml())
    response = request(client, before, 'events', dict(
        measure_id='m-1', onset='0', voice='3', staff=1,
        pitch=dict(step=step, octave=4, alter=alter), duration='1', written_accidental=sign))
    assert response.status_code == 200, response.text
    after = response.json()
    assert event(after, 'new-1')['pitch']['alter'] == alter
    note = ET.fromstring(xml(after)).findall('.//note')[-1]
    assert note.findtext('accidental') == sign
    assert note.findtext('pitch/alter', '0') == alter
    undo = request(client, after, 'undo').json()
    assert xml(undo) == xml(before)
    assert xml(request(client, undo, 'redo').json()) == xml(after)


def test_clear_explicit_natural_follows_key_and_preserves_other_xml(workflow):
    client, _ = workflow
    before = create(client, keyed_xml())
    added = request(client, before, 'events', dict(measure_id='m-1', onset='0', voice='3', staff=1,
        pitch=dict(step='B', octave=4, alter='0'), written_accidental='natural')).json()
    response = request(client, added, 'events/new-1', dict(
        pitch=dict(step='B', octave=4, alter='-1'), written_accidental=None), 'PATCH')
    assert response.status_code == 200, response.text
    after = response.json()
    assert event(after, 'new-1')['accidental']['text'] is None
    assert event(after, 'new-1')['pitch']['alter'] == '-1'
    assert event(after, 'e-1') == event(added, 'e-1')
    assert xml(request(client, after, 'undo').json()) == xml(added)


@pytest.mark.parametrize('duration,note_type,units', [('1/2','eighth','2'), ('1','quarter','4'), ('2','half','8'), ('4','whole','16')])
def test_note_value_changes_keep_neighbor_onsets_and_unrelated_properties(workflow, duration, note_type, units):
    client, _ = workflow
    before = create(client, BASE)
    response = request(client, before, 'events/e-1', dict(duration=duration, preserve_onsets=True), 'PATCH')
    assert response.status_code == 200, response.text
    after = response.json()
    assert event(after, 'e-1')['duration'] == duration
    assert event(after, 'e-2')['onset'] == event(before, 'e-2')['onset']
    note = ET.fromstring(xml(after)).find('.//note')
    assert note.findtext('type') == note_type and note.findtext('duration') == units
    for field in ('pitch','voice','staff','display_size','lyric_ids','grace'):
        assert event(after,'e-1')[field] == event(before,'e-1')[field]
    undo = request(client, after, 'undo').json()
    assert xml(undo) == xml(before)
    assert xml(request(client, undo, 'redo').json()) == xml(after)


@pytest.mark.parametrize('text', ['khắp', 'Chúa', 'Người', 'Mừng', 'Đem', 'Tin', 'Chu\u0301a'])
def test_unicode_lyric_edit_preserves_attributes_children_other_verses_and_history(workflow, text):
    client, _ = workflow
    data = BASE.replace(b'<lyric><text>one</text></lyric>',
        '<lyric number="1" placement="below" default-y="-40"><syllabic>begin</syllabic><text font-style="italic">one</text><extend type="start"/><end-line/></lyric><lyric number="2"><text>Người</text></lyric>'.encode())
    before = create(client, data)
    lyric = next(l for l in before['score']['lyrics'] if l['event_id'] == 'e-1' and l['number'] == '1')
    response = request(client, before, f'lyrics/{lyric["id"]}', {'text':text}, 'PATCH')
    assert response.status_code == 200, response.text
    after = response.json()
    original = ET.fromstring(xml(before)).find('.//lyric')
    edited = ET.fromstring(xml(after)).find('.//lyric')
    assert edited.findtext('text') == text
    edited.find('text').text = original.findtext('text')
    assert ET.tostring(edited) == ET.tostring(original)
    assert [l for l in after['score']['lyrics'] if l['number']=='2'] == [l for l in before['score']['lyrics'] if l['number']=='2']
    undo = request(client, after, 'undo').json()
    assert xml(undo) == xml(before)
    assert xml(request(client, undo, 'redo').json()) == xml(after)


@pytest.mark.parametrize('step,follow_alter', [('A','0'), ('B','-1')])
def test_existing_sharp_clear_removes_sign_and_history_restores_exact_xml(workflow, step, follow_alter):
    client, _ = workflow
    before = create(client, keyed_xml())
    response = request(client, before, 'events/e-1', dict(
        pitch=dict(step=step, octave=4, alter='1'), written_accidental='sharp'), 'PATCH')
    assert response.status_code == 200, response.text
    sharp = response.json()
    assert event(sharp,'e-1')['accidental']['text'] == 'sharp'
    response = request(client, sharp, 'events/e-1', dict(
        pitch=dict(step=step, octave=4, alter=follow_alter), written_accidental=None), 'PATCH')
    assert response.status_code == 200, response.text
    cleared = response.json()
    assert event(cleared,'e-1')['accidental']['text'] is None
    assert event(cleared,'e-1')['pitch']['alter'] == follow_alter
    node = ET.fromstring(xml(cleared)).find('.//note')
    assert node.find('accidental') is None  # NONE never means printed natural.
    assert node.findtext('pitch/alter','0') == follow_alter
    assert event(cleared,'e-2') == event(sharp,'e-2')
    undo = request(client, cleared, 'undo').json()
    assert xml(undo) == xml(sharp)
    assert event(undo,'e-1')['accidental']['text'] == 'sharp'
    redo = request(client, undo, 'redo').json()
    assert xml(redo) == xml(cleared)
    assert event(redo,'e-1')['accidental']['text'] is None
    if step == 'B':
        natural = request(client, redo, 'events/e-1', dict(
            pitch=dict(step='B', octave=4, alter='0'), written_accidental='natural'), 'PATCH').json()
        assert event(natural,'e-1')['accidental']['text'] == 'natural'
        assert ET.fromstring(xml(natural)).find('.//note').findtext('accidental') == 'natural'
