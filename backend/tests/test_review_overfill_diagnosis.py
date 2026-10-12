"""Synthetic reproduction of browser diagnostics, not an assertion about the PDF."""
from fractions import Fraction
from xml.etree import ElementTree as ET

from test_phase4e_workflow import workflow, create, request, xml

XML = b'''<score-partwise version="4.0"><part-list><score-part id="P"><part-name>Voice</part-name></score-part></part-list><part id="P">
<measure number="1"><attributes><divisions>4</divisions><time><beats>2</beats><beat-type>4</beat-type></time></attributes><note><rest/><duration>6</duration><voice>1</voice><type>quarter</type><dot/><staff>1</staff></note><backup><duration>6</duration></backup><note><rest/><duration>6</duration><voice>2</voice><type>quarter</type><dot/><staff>1</staff></note></measure>
<measure number="4"><direction><direction-type><words>Unrelated empty measure marking</words></direction-type></direction></measure>
<measure number="5"><note><pitch><step>A</step><octave>4</octave></pitch><duration>2</duration><voice>1</voice><type>eighth</type><staff>1</staff><lyric><text>synthetic</text></lyric></note><note><rest/><duration>4</duration><voice>1</voice><type>quarter</type><staff>1</staff></note><barline><bar-style>regular</bar-style></barline></measure>
<measure number="17"><note><rest/><duration>2</duration><voice>1</voice><type>eighth</type><staff>1</staff></note></measure>
</part></score-partwise>'''


def measure(review, number='5'):
    return next(m for p in review['score']['parts'] for m in p['measures'] if m['number'] == number)


def events(review):
    return [e for v in measure(review)['voices'] for e in v['events']]


def add(client, review, **fields):
    anchor = events(review)[0]
    body = dict(measure_id=measure(review)['id'], before_event_id=anchor['id'], kind='note',
                pitch=dict(step='A', alter='0', octave=4), duration='2', voice='1', staff=1, grace=False)
    body.update(fields)
    response = request(client, review, 'events', body)
    assert response.status_code == 200, response.text
    return response.json()


def measure_nodes(review):
    return {m.get('number'): ET.tostring(m) for m in ET.fromstring(xml(review)).findall('.//measure')}


def test_two_beat_insertion_can_reproduce_exact_browser_overfill_and_warnings(workflow):
    client, _ = workflow
    original = create(client, XML)
    assert measure(original)['actual_duration'] == '3/2'
    corrected = add(client, original)
    source, target, remaining = events(corrected)
    assert [(e['onset'], e['duration']) for e in (source, target, remaining)] == [('0', '2'), ('2', '1/2'), ('5/2', '1')]
    extent = max(Fraction(e['onset']) + Fraction(e['duration']) for e in events(corrected))
    assert extent == Fraction(7, 2) and measure(corrected)['actual_duration'] == '7/2'
    assert measure(corrected)['expected_duration'] == '2'
    assert source['provenance']['origin'] == 'manual_addition'
    assert target['provenance']['origin'] == remaining['provenance']['origin'] == 'musicxml_import'
    assert corrected['validation']['error_count'] == 0 and corrected['validation']['warning_count'] == 8
    assert any(d['code'] == 'measure_overfilled' and d['severity'] == 'WARNING' and not d['blocking'] for d in corrected['validation']['diagnostics'])
    assert corrected['validation']['can_verify']
    # Existing-note tie edit retains both notes and their independent durations.
    response = request(client, corrected, f'events/{source["id"]}', {'tie_to_event_id': target['id']}, 'PATCH')
    assert response.status_code == 200, response.text
    tied = response.json()
    assert [(e['onset'], e['duration']) for e in events(tied)] == [('0', '2'), ('2', '1/2'), ('5/2', '1')]
    assert events(tied)[0]['ties'] == ['start'] and events(tied)[1]['ties'] == ['stop']
    assert tied['validation'] == corrected['validation']
    assert tied['validation']['can_verify']
    for number in ('1', '4', '17'):
        assert measure_nodes(tied)[number] == measure_nodes(original)[number]
    undone_tie = request(client, tied, 'undo').json()
    assert measure(undone_tie)['actual_duration'] == '7/2'
    undone_insertion = request(client, undone_tie, 'undo').json()
    assert measure(undone_insertion)['actual_duration'] == '3/2' and xml(undone_insertion) == XML
    redone_insertion = request(client, undone_insertion, 'redo').json()
    assert measure(redone_insertion)['actual_duration'] == '7/2'
    redone_tie = request(client, redone_insertion, 'redo').json()
    assert xml(redone_tie) == xml(tied)


def test_chord_insertion_does_not_double_count_duration(workflow):
    client, _ = workflow
    original = create(client, XML)
    anchor = events(original)[0]
    corrected = add(client, original, before_event_id=None, chord_with_id=anchor['id'], duration=anchor['duration'],
                    pitch=dict(step='C', alter='0', octave=4))
    assert measure(corrected)['actual_duration'] == '3/2'
    assert [(e['onset'], e['duration']) for e in events(corrected)] == [('0', '1/2'), ('0', '1/2'), ('1/2', '1')]
    assert events(corrected)[1]['chord_member']
    assert corrected['validation']['error_count'] == 0
    assert measure_nodes(corrected)['17'] == measure_nodes(original)['17']


def test_sequential_insertion_preserves_backup_forward_and_next_measure(workflow):
    client, _ = workflow
    # Each baseline voice occupies two beats, with a retained silent forward.
    original_xml = XML.replace(b'<note><rest/><duration>6</duration><voice>1</voice>',
                               b'<forward><duration>2</duration><voice>1</voice></forward><note><rest/><duration>6</duration><voice>1</voice>').replace(
                                   b'<backup><duration>6</duration>', b'<backup><duration>8</duration>')
    original = create(client, original_xml)
    first = measure(original, '1')
    anchor = first['voices'][0]['events'][0]
    response = request(client, original, 'events', dict(measure_id=first['id'], before_event_id=anchor['id'],
                       kind='note', pitch=dict(step='D', octave=4), duration='1', voice='1', staff=1))
    assert response.status_code == 200, response.text
    corrected = response.json()
    first_after = measure(corrected, '1')
    assert first_after['actual_duration'] == '3'
    # Retaining backup 2 shifts the subsequent voice's cursor to 1; this is exposed,
    # never compensated automatically or normalized into the following measure.
    assert first_after['voices'][1]['events'][0]['onset'] == '1'
    before = ET.fromstring(xml(original)).find('.//measure')
    after = ET.fromstring(xml(corrected)).find('.//measure')
    for tag in ('backup', 'forward'):
        assert ET.tostring(after.find(tag)) == ET.tostring(before.find(tag))
    for number in ('4', '5', '17'):
        assert measure_nodes(corrected)[number] == measure_nodes(original)[number]
    assert any(d['code'] == 'measure_overfilled' and d['severity'] == 'WARNING' and not d['blocking'] for d in corrected['validation']['diagnostics'])
    assert corrected['validation']['can_verify']
