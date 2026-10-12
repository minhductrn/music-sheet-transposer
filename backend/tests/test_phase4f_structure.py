"""Synthetic source-fidelity contracts. No real-song diagnosis or recognition runs."""
from dataclasses import asdict
from xml.etree import ElementTree as ET
import pytest
from test_phase4e_workflow import workflow, create, request, xml
from test_semantic_recovery import archive, SHEET, BOOK
from app.music.recovery.omr import parse_omr
from app.music.review.document import Document
from app.music.review.importer import import_score


def draft(beats='2', denominator='4', units=8, extra=''):
    return f'''<score-partwise version="4.0"><part-list><score-part id="P1"><part-name>Voice</part-name></score-part></part-list><part id="P1"><measure number="1"><attributes><divisions>4</divisions><key><fifths>-1</fifths></key><time><beats>{beats}</beats><beat-type>{denominator}</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes><note><pitch><step>A</step><octave>4</octave></pitch><duration>{units}</duration><voice>1</voice><type>half</type><staff>1</staff><lyric><text>đây</text></lyric></note>{extra}</measure><measure number="2"><note><rest/><duration>8</duration><voice>1</voice><type>half</type><staff>1</staff></note><barline><bar-style>light-heavy</bar-style></barline></measure></part></score-partwise>'''.encode()


@pytest.mark.parametrize('beats,denominator,units,capacity,compound', [('2','4',8,'2',False), ('3','4',12,'3',False), ('4','4',16,'4',False), ('6','8',12,'3',True)])
def test_import_preserves_meter_and_exact_content(workflow, beats, denominator, units, capacity, compound):
    client, _ = workflow
    original = draft(beats, denominator, units)
    review = create(client, original)
    measure = review['score']['parts'][0]['measures'][0]
    assert xml(review) == original
    assert measure['time_signature'][0]['pairs'] == [{'beats': beats, 'beat_type': denominator}]
    assert measure['expected_duration'] == capacity
    assert measure['meter_context'][0]['groups'][0]['compound'] is compound
    event = measure['voices'][0]['events'][0]
    assert event['measure_id'] == measure['id'] and event['duration_units'] == str(units)
    assert event['clef']['fields'][0]['text'] == 'G'
    assert event['ties'] == [] and review['score']['lyrics'][0]['text'] == 'đây'
    assert review['score']['layout']['mode'] == 'RESPONSIVE'
    assert review['score']['systems'] == review['score']['pages'] == review['source_evidence'] == []


@pytest.mark.parametrize('units,state,blocking', [(14,'OVERFILLED',False), (4,'UNDERFILLED',False)])
def test_invalid_recognition_is_visible_and_never_repaired(workflow, units, state, blocking):
    client, _ = workflow
    original = draft(units=units)
    review = create(client, original)
    measure = review['score']['parts'][0]['measures'][0]
    assert measure['rhythm_status'] == state and measure['conflict_state'] == 'CONFLICT'
    assert (review['validation']['error_count'] > 0) is blocking
    assert xml(review) == original
    validated = request(client, review, 'validate').json()
    assert xml(validated) == original
    root = ET.fromstring(xml(validated))
    assert len(root.findall('.//note')) == 2
    assert root.findall('.//measure')[0].findtext('note/duration') == str(units)
    assert not root.findall('.//tie')
    assert request(client, validated, 'verify', {'confirmed_source_comparison': True}).status_code == 200


def test_partial_requires_explicit_xml_and_context_is_inherited():
    raw = draft(units=4)
    score, _ = import_score(Document.parse(raw))
    assert score.parts[0].measures[0].rhythm_status == 'UNDERFILLED'
    partial, _ = import_score(Document.parse(raw.replace(b'<measure number="1">', b'<measure number="1" implicit="yes">')))
    assert partial.parts[0].measures[0].rhythm_status == 'PARTIAL'
    assert partial.parts[0].measures[1].voices[0].events[0].clef['fields'][0]['text'] == 'G'
    assert partial.parts[0].measures[1].barlines[0]['style'] == 'light-heavy'


def test_explicit_breaks_group_measures_without_changing_xml(workflow):
    client, _ = workflow
    original = draft().replace(b'<measure number="2">', b'<measure number="2"><print new-system="yes" new-page="yes"/>')
    review = create(client, original)
    layout = review['score']['layout']
    assert layout['origin'] == 'MUSICXML_PRINT'
    assert [s['measure_ids'] for s in layout['systems']] == [['m-1'], ['m-2']]
    assert len(review['score']['pages']) == 2
    assert xml(review) == original


def test_explicit_insert_preserves_ownership_history_and_unrelated_xml(workflow):
    client, _ = workflow
    before = create(client, draft())
    after = request(client, before, 'events', {'measure_id':'m-1', 'after_event_id':'e-1', 'kind':'note',
                    'pitch':{'step':'C','octave':5}, 'duration':'1', 'grace':False}).json()
    m1, m2 = after['score']['parts'][0]['measures']
    added = m1['voices'][0]['events'][-1]
    assert added['measure_id'] == 'm-1' and added['provenance']['origin'] == 'manual_addition'
    assert m1['rhythm_status'] == 'OVERFILLED' and m2 == before['score']['parts'][0]['measures'][1]
    assert ET.tostring(ET.fromstring(xml(after)).findall('.//measure')[1]) == ET.tostring(ET.fromstring(xml(before)).findall('.//measure')[1])
    undo = request(client, after, 'undo').json()
    assert xml(undo) == xml(before)
    assert xml(request(client, undo, 'redo').json()) == xml(after)


def test_omr_retains_pages_staff_lines_slots_and_structural_inters():
    sheet = ET.fromstring(SHEET)
    inters = sheet.find('.//inters')
    for kind in ('time-whole', 'key', 'barline'):
        ET.SubElement(inters, kind, {'id':kind, 'staff':'7', 'grade':'0.8'})
    evidence = parse_omr(archive(ET.tostring(sheet)))
    system = evidence.sheets[0].systems[0]
    assert system.page_id == '1'
    assert len(system.structure['staffs'][0]['lines']) == 5
    assert system.structure['staffs'][0]['lines'][0][0] == {'x':100.0,'y':60.0}
    assert system.structure['stacks'][0]['slots'][0]['x_offset'] == 112
    assert {'clef','key','barline','time-whole','stem','beam'}.issubset({i['kind'] for i in system.structure['inters']})
    assert system.measures[0].candidates[0].bounds is not None
    assert '/private' not in str(asdict(evidence))


def test_sidecar_survives_disabled_recovery_and_unsafe_binding_is_not_layout(workflow):
    client, service = workflow
    service.config.audiveris_semantic_recovery_enabled = False
    original = draft()
    review = create(client, original, archive())
    assert xml(review) == original
    assert review['source_evidence'][0]['sheets'][0]['systems'][0]['page_id'] == '1'
    assert review['score']['layout']['mode'] == 'RESPONSIVE'  # Two XML measures, one observed.
    assert review['source_evidence'][0]['sheets'][0]['systems'][0]['structure']['origin'] == 'SOURCE_OBSERVATION'


def test_complete_omr_measure_order_supplies_review_group_only(workflow):
    client, service = workflow
    service.config.audiveris_semantic_recovery_enabled = False
    original = draft()
    root = ET.fromstring(original)
    root.find('part').remove(root.findall('.//measure')[1])
    original = ET.tostring(root)
    review = create(client, original, archive())
    assert review['score']['layout']['origin'] == 'OMR_ORDERED_MEASURES'
    assert review['score']['layout']['systems'][0]['measure_ids'] == ['m-1']
    assert xml(review) == original and ET.fromstring(xml(review)).find('.//print') is None


def test_two_omr_systems_retain_grouping_and_history(workflow):
    from copy import deepcopy
    client, service = workflow
    service.config.audiveris_semantic_recovery_enabled = False
    sheet, book = ET.fromstring(SHEET), ET.fromstring(BOOK)
    second = deepcopy(sheet.find('.//system'))
    second.set('id', '2')
    second.find('stack').set('id', '2')
    second.find('part/measure').set('id', '2')
    sheet.find('page').append(second)
    book.find('sheet/page').append(deepcopy(book.find('sheet/page/system')))
    original = draft()
    before = create(client, original, archive(ET.tostring(sheet), ET.tostring(book)))
    assert [g['measure_ids'] for g in before['score']['systems']] == [['m-1'], ['m-2']]
    assert len(before['score']['pages']) == 1
    assert before['score']['layout']['mode'] == 'SOURCE_REVIEW'
    corrected = request(client, before, 'events/e-1', {'pitch': {'step':'B','octave':4}}, 'PATCH').json()
    assert corrected['score']['parts'][0]['measures'][0]['voices'][0]['events'][0]['provenance']['layer'] == 'USER_CORRECTION'
    assert corrected['source_evidence'] == before['source_evidence']
    assert corrected['score']['layout'] == before['score']['layout']
    undo = request(client, corrected, 'undo').json()
    assert xml(undo) == original and undo['source_evidence'] == before['source_evidence']
    assert request(client, undo, 'redo').json()['score']['layout'] == before['score']['layout']


def test_ambiguous_meter_and_effective_clef_do_not_reinterpret_pitch():
    raw = draft(extra='<attributes><clef><sign>F</sign><line>4</line></clef></attributes>')
    doc = Document.parse(raw)
    score, _ = import_score(doc)
    first, second = score.parts[0].measures
    assert first.voices[0].events[0].clef['fields'][0]['text'] == 'G'
    assert second.voices[0].events[0].clef['fields'][0]['text'] == 'F'
    assert first.voices[0].events[0].pitch.step == 'A'
    assert doc.xml() == raw
    unknown, _ = import_score(Document.parse(raw.replace(b'<beats>2</beats><beat-type>4</beat-type>', b'<senza-misura/>')))
    assert unknown.parts[0].measures[0].rhythm_status == 'STRUCTURALLY_AMBIGUOUS'
