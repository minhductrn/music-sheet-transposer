"""Synthetic palette requests use existing canonical commands, never OMR."""
from fractions import Fraction
from xml.etree import ElementTree as ET

import pytest

from test_phase4e_workflow import workflow, create, request, xml, verify, event

BASES = ('4', '2', '1', '1/2', '1/4', '1/8', '1/16')
FACTORS = (Fraction(1), Fraction(3, 2), Fraction(7, 4))


def source(kind='note', modification=''):
    head = '<rest/>' if kind == 'rest' else '<pitch><step>C</step><octave>4</octave></pitch>'
    return f'''<score-partwise><part-list><score-part id="P1"><part-name>Voice</part-name></score-part></part-list><part id="P1"><measure number="1"><attributes><divisions>192</divisions><time><beats>4</beats><beat-type>4</beat-type></time><staves>2</staves></attributes>
    <note>{head}<duration>192</duration><voice>1</voice><type>quarter</type>{modification}<staff>1</staff></note>
    <note><pitch><step>D</step><octave>4</octave></pitch><duration>192</duration><tie type="start"/><voice>1</voice><type>quarter</type><staff>1</staff><notations><tied type="start"/></notations><lyric number="2"><syllabic>single</syllabic><text>Ngài</text></lyric></note>
    <note><pitch><step>D</step><octave>4</octave></pitch><duration>192</duration><tie type="stop"/><voice>1</voice><type>quarter</type><staff>1</staff><notations><tied type="stop"/></notations></note>
    <backup><duration>576</duration></backup><note><rest/><duration>768</duration><voice>2</voice><type>whole</type><staff>2</staff></note></measure></part></score-partwise>'''.encode()


def untouched(data):
    root = ET.fromstring(xml(data))
    return [ET.tostring(n) for n in root.findall('.//note')[1:]]


@pytest.mark.parametrize('kind', ['note', 'rest'])
@pytest.mark.parametrize('base', BASES)
@pytest.mark.parametrize('dots', range(3))
def test_all_palette_values_edit_insert_history_and_roundtrip(workflow, kind, base, dots):
    client, _ = workflow
    before = create(client, source(kind))
    written = str(Fraction(base) * FACTORS[dots])
    assert event(before, 'e-1')['palette_duration_options'][written] == written
    response = request(client, before, 'events/e-1', dict(duration=written, duration_scope='note', preserve_onsets=True), 'PATCH')
    assert response.status_code == 200, response.text
    after = response.json()
    assert untouched(after) == untouched(before)
    assert event(after, 'e-2')['onset'] == event(before, 'e-2')['onset']
    assert event(after, 'e-1')['duration'] == written
    assert event(after, 'e-1')['notated_duration']['dots'] == dots
    undo = request(client, after, 'undo').json()
    assert xml(undo) == xml(before)
    redo = request(client, undo, 'redo').json()
    assert xml(redo) == xml(after)
    # New content intentionally differs from source; independent explicit voice.
    payload = dict(measure_id='m-1', onset='0', voice='new', staff=2, kind=kind, duration=written)
    if kind == 'note':
        payload['pitch'] = dict(step='F', octave=5, alter='1')
    inserted = request(client, redo, 'events', payload)
    assert inserted.status_code == 200, inserted.text
    saved = verify(client, inserted.json())
    exported = client.get(f'/api/v1/reviews/{saved["id"]}/musicxml?verified_only=true')
    assert exported.status_code == 200
    reopened = create(client, exported.content)
    signature = lambda r: [(e['kind'], e['pitch'], e['duration'], e['onset'], e['voice'], e['staff'], e['notated_duration'], e['ties']) for p in r['score']['parts'] for m in p['measures'] for v in m['voices'] for e in v['events']]
    assert signature(reopened) == signature(saved)
    assert [(l['number'], l['segments']) for l in reopened['score']['lyrics']] == [('2', ['Ngài'])]


def test_tuplet_written_mapping_and_ratio_preservation(workflow):
    client, _ = workflow
    modification = '<time-modification><actual-notes>3</actual-notes><normal-notes>2</normal-notes></time-modification>'
    before = create(client, source(modification=modification))
    assert event(before, 'e-1')['palette_duration_options']['1/2'] == '1/3'
    result = request(client, before, 'events/e-1', dict(duration='1/3', duration_scope='note', preserve_onsets=True), 'PATCH')
    assert result.status_code == 200
    after = result.json()
    node = ET.fromstring(xml(after)).find('.//note')
    assert node.findtext('type') == 'eighth'
    assert node.findtext('time-modification/actual-notes') == '3'
    assert node.findtext('time-modification/normal-notes') == '2'
    assert event(after, 'e-2')['onset'] == event(before, 'e-2')['onset']
    assert untouched(after) == untouched(before)


def test_unsupported_normal_type_rejects_and_low_divisions_refine_without_moving_other_notes(workflow):
    client, _ = workflow
    modification = '<time-modification><actual-notes>3</actual-notes><normal-notes>2</normal-notes><normal-type>quarter</normal-type></time-modification>'
    before = create(client, source(modification=modification))
    assert event(before, 'e-1')['palette_duration_options'] == {}
    result = request(client, before, 'events/e-1', dict(duration='1/3', duration_scope='note', preserve_onsets=True), 'PATCH')
    assert result.status_code == 422
    current = client.get(f'/api/v1/reviews/{before["id"]}').json()
    assert current['revision'] == before['revision'] and xml(current) == xml(before)
    low = create(client, source().replace(b'<divisions>192</divisions>', b'<divisions>1</divisions>'))
    assert event(low, 'e-1')['palette_duration_options']['1/16'] == '1/16'
    result = request(client, low, 'events/e-1', dict(duration='1/16', duration_scope='note', preserve_onsets=True), 'PATCH')
    assert result.status_code == 200, result.text
    after = result.json()
    assert event(after, 'e-1')['duration'] == '1/16'
    for key in ('e-2','e-3','e-4'):
        for field in ('onset','duration','pitch','voice','staff','lyric_ids'):
            assert event(after,key)[field] == event(low,key)[field]
    undo = request(client,after,'undo').json()
    assert xml(undo) == xml(low)
