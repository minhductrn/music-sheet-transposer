"""Human insertion into preserved MusicXML, independent of recognition providers."""
from xml.etree import ElementTree as ET
import pytest
from test_phase4e_workflow import workflow, create, request, event, xml, verify, patch

XML = b'''<score-partwise version="4.0"><work><work-title>Preserve me</work-title></work><part-list><score-part id="P"><part-name>Voice</part-name></score-part></part-list><part id="P"><measure number="1"><attributes><divisions>4</divisions><time><beats>4</beats><beat-type>4</beat-type></time><staves>2</staves></attributes><direction><direction-type><words>Unrelated marking</words></direction-type></direction><note><rest/><duration>4</duration><voice>2</voice><type>quarter</type><staff>2</staff></note><note default-x="123"><!-- preserved comment --><pitch><step>A</step><octave>4</octave></pitch><duration>4</duration><voice>2</voice><type>quarter</type><staff>2</staff><notations><articulations><accent/></articulations></notations><lyric><text>word</text></lyric></note><barline><bar-style>light-heavy</bar-style></barline></measure></part></score-partwise>'''


def insert(client, review, **fields):
    data = dict(measure_id='m-1', before_event_id='e-2', kind='note', pitch=dict(step='A', alter='0', octave=4), duration='2', voice='2', staff=2, grace=False, tie_to_event_id='e-2')
    data.update(fields)
    return request(client, review, 'events', data)


def inserted(review):
    return next(e for p in review['score']['parts'] for m in p['measures'] for v in m['voices'] for e in v['events'] if e['id'].startswith('new-'))


@pytest.mark.parametrize('semitones', [0, 2, -2])
def test_tied_insertion_preservation_history_and_transpose(workflow, monkeypatch, semitones):
    client, _ = workflow
    baseline = verify(client, create(client, XML))
    response = insert(client, baseline)
    assert response.status_code == 200, response.text
    corrected = response.json()
    added = inserted(corrected)
    assert added['pitch'] == dict(step='A', alter='0', octave=4)
    assert added['duration'] == '2' and added['duration_units'] == '8' and not added['grace']
    assert added['voice'] == '2' and added['staff'] == 2 and added['ties'] == ['start']
    assert event(corrected)['ties'] == ['stop']
    assert corrected['state'] == 'REVIEW_REQUIRED' and corrected['validation']['error_count'] == 0
    assert added['provenance']['origin'] == 'manual_addition'
    assert 'tie_stop' in event(corrected)['provenance']['manual_fields']
    tree, original = ET.fromstring(xml(corrected)), ET.fromstring(XML)
    notes = tree.findall('.//note')
    assert notes[1].find('tie').get('type') == 'start'
    assert notes[1].find('notations/tied').get('type') == 'start'
    assert notes[2].find('tie').get('type') == 'stop'
    assert notes[2].find('notations/tied').get('type') == 'stop'
    for path in ('work', './/attributes', './/direction', './/barline', './/lyric', './/articulations'):
        assert ET.tostring(tree.find(path)) == ET.tostring(original.find(path))
    assert ET.tostring(notes[0]) == ET.tostring(original.findall('.//note')[0])
    undo = request(client, corrected, 'undo').json()
    assert xml(undo) == XML and event(undo)['ties'] == []
    redo = request(client, undo, 'redo').json()
    assert xml(redo) == xml(corrected)
    blocked = request(client, redo, 'transpose', {'semitones': semitones})
    assert blocked.status_code == 409
    verified = verify(client, redo)
    import app.music.musicxml.transposer as module
    original_transpose = module.transpose_musicxml_document
    captured = []
    def capture(contents, *args, **kwargs):
        captured.append(contents)
        return original_transpose(contents, *args, **kwargs)
    monkeypatch.setattr(module, 'transpose_musicxml_document', capture)
    result = request(client, verified, 'transpose', {'semitones': semitones})
    assert result.status_code == 200, result.text
    assert captured == [xml(verified)] and captured[0] != XML
    exported = client.get(f'/api/v1/reviews/{verified["id"]}/musicxml?verified_only=true')
    assert exported.status_code == 200 and exported.content == xml(verified)
    output = ET.fromstring(result.content).findall('.//note')
    assert output[1].findtext('pitch/step') == output[2].findtext('pitch/step') == {0: 'A', 2: 'B', -2: 'G'}[semitones]
    assert output[1].find('tie').get('type') == 'start' and output[2].find('tie').get('type') == 'stop'
    assert output[1].find('notations/tied').get('type') == 'start'
    assert output[2].find('notations/tied').get('type') == 'stop'
    edited = patch(client, verified, added['id'], duration='1')
    assert edited['state'] == 'REVIEW_REQUIRED'
    assert request(client, edited, 'transpose', {'semitones': 0}).status_code == 409


@pytest.mark.parametrize('fields', [dict(kind='rest', pitch=None), dict(tie_to_event_id='e-1')])
def test_unsafe_ties_are_rejected_atomically(workflow, fields):
    client, _ = workflow
    baseline = create(client, XML)
    result = insert(client, baseline, **fields)
    assert result.status_code == 422, result.text
    loaded = client.get('/api/v1/reviews/' + baseline['id']).json()
    assert loaded['revision'] == baseline['revision'] and xml(loaded) == XML


def test_later_pitch_edit_is_advisory_and_undo_restores(workflow):
    client, _ = workflow
    corrected = insert(client, create(client, XML)).json()
    changed = patch(client, corrected, pitch=dict(step='B', octave=4))
    assert any(d['code'] == 'tie_pitch_mismatch' and not d['blocking'] for d in changed['validation']['diagnostics'])
    verified = verify(client, changed)
    undo = request(client, verified, 'undo').json()
    assert undo['validation']['error_count'] == 0 and xml(undo) == xml(corrected)


@pytest.mark.parametrize('delete_source', [True, False])
def test_deleting_endpoint_cleans_owned_counterpart_and_is_undoable(workflow, delete_source):
    client, _ = workflow
    corrected = insert(client, create(client, XML)).json()
    identifier = inserted(corrected)['id'] if delete_source else 'e-2'
    deleted = request(client, corrected, f'events/{identifier}', method='DELETE').json()
    assert not ET.fromstring(xml(deleted)).findall('.//tie')
    assert not ET.fromstring(xml(deleted)).findall('.//tied')
    assert xml(request(client, deleted, 'undo').json()) == xml(corrected)


def test_overfilled_untied_insertion_is_source_authoritative(workflow):
    client, _ = workflow
    result = insert(client, create(client, XML), duration='4', tie_to_event_id=None).json()
    assert any(d['code'] == 'measure_overfilled' and d['severity'] == 'WARNING' and not d['blocking'] for d in result['validation']['diagnostics'])
    assert request(client, result, 'verify', {'confirmed_source_comparison': True}).status_code == 200


@pytest.mark.parametrize('namespace', ['', 'http://www.musicxml.org/ns/musicxml'])
def test_tie_across_barline_and_existing_continuation_preserved(workflow, namespace):
    client, _ = workflow
    original = XML.replace(b'<score-partwise version="4.0">', f'<score-partwise version="4.0" xmlns="{namespace}">'.encode()) if namespace else XML
    # First measure has two beats; insertion fills it, next measure starts at zero.
    original = original.replace(b'<duration>4</duration>', b'<duration>8</duration>', 1).replace(b'<type>quarter</type>', b'<type>half</type>', 1)
    tree = ET.fromstring(original)
    ns = '{' + namespace + '}' if namespace else ''
    first = tree.find('.//' + ns + 'measure')
    target = first.findall(ns + 'note')[1]
    first.remove(target)
    second = ET.SubElement(tree.find(ns + 'part'), ns + 'measure', {'number': '2'})
    target.find(ns + 'duration').text = '16'
    target.find(ns + 'type').text = 'whole'
    target.insert(2, ET.Element(ns + 'tie', {'type': 'start'}))
    ET.SubElement(target.find(ns + 'notations'), ns + 'tied', {'type': 'start'})
    second.append(target)
    baseline = create(client, ET.tostring(tree))
    corrected = insert(client, baseline, before_event_id=None, after_event_id='e-1').json()
    assert corrected['validation']['error_count'] == 0
    assert event(corrected)['ties'] == ['start', 'stop'] or event(corrected)['ties'] == ['stop', 'start']
    output = ET.fromstring(xml(corrected))
    continuation = output.findall('.//' + ns + 'note')[2]
    assert [n.get('type') for n in continuation.findall(ns + 'tie')] == ['stop', 'start']
    assert sorted(n.get('type') for n in continuation.findall(ns + 'notations/' + ns + 'tied')) == ['start', 'stop']
    assert verify(client, corrected)['state'] == 'VERIFIED'


def test_existing_target_stop_is_not_duplicated_or_removed_on_delete(workflow):
    client, _ = workflow
    original = XML.replace(b'<voice>2</voice><type>quarter</type><staff>2</staff><notations>', b'<tie type="stop"/><voice>2</voice><type>quarter</type><staff>2</staff><notations><tied type="stop"/>')
    corrected = insert(client, create(client, original)).json()
    target = ET.fromstring(xml(corrected)).findall('.//note')[2]
    assert len(target.findall('tie')) == 1
    assert len(target.findall('notations/tied')) == 2
    assert len([n for n in target.findall('notations/tied') if n.get('id')]) == 1
    deleted = request(client, corrected, f'events/{inserted(corrected)["id"]}', method='DELETE').json()
    assert ET.tostring(ET.fromstring(xml(deleted)).findall('.//note')[1]) == ET.tostring(ET.fromstring(original).findall('.//note')[1])


def test_simultaneous_insert_preserves_chord_onset_and_accidental(workflow):
    client, _ = workflow
    original = XML.replace(b'<rest/>', b'<pitch><step>C</step><octave>4</octave></pitch>').replace(b'<duration>4</duration>', b'<duration>8</duration>', 1).replace(b'<type>quarter</type>', b'<type>half</type>', 1).replace(b'<step>A</step>', b'<step>A</step><alter>1</alter>')
    result = insert(client, create(client, original), before_event_id=None, chord_with_id='e-1', duration='2', pitch=dict(step='A', alter='1', octave=4)).json()
    added = inserted(result)
    assert added['chord_member'] and added['onset'] == '0' and added['duration'] == '2'
    assert added['pitch']['alter'] == '1' and added['ties'] == ['start']
    assert result['validation']['error_count'] == 0


@pytest.mark.parametrize('fields', [dict(pitch=dict(step='B', octave=4)), dict(voice='1'), dict(staff=1), dict(grace=True), dict(duration='4')])
def test_musically_unusual_tied_insertion_is_advisory(workflow, fields):
    client, _ = workflow
    baseline = create(client, XML)
    result = insert(client, baseline, **fields)
    assert result.status_code == 200, result.text
    corrected = result.json()
    assert event(corrected)['pitch'] == event(baseline)['pitch']
    assert inserted(corrected)['tie_target_id'] == 'e-2'
    assert any(d['category'] == 'MUSIC_WARNING' and not d['blocking'] for d in corrected['validation']['diagnostics'])
    assert verify(client, corrected)['state'] == 'VERIFIED'
