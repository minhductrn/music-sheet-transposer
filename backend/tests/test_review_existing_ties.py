"""Tie-only human correction preserves the two original rhythmic events."""
from xml.etree import ElementTree as ET
import pytest
from test_phase4e_workflow import workflow, create, request, event, xml, verify, patch

XML = b'''<score-partwise version="4.0"><work><work-title>Unrelated title</work-title></work><part-list><score-part id="P"><part-name>Voice</part-name></score-part></part-list><part id="P"><measure number="5"><attributes><divisions>4</divisions><time><beats>5</beats><beat-type>8</beat-type></time><staves>2</staves></attributes><direction><direction-type><words>Keep</words></direction-type></direction><harmony><root><root-step>C</root-step></root><kind>major</kind></harmony><note><pitch><step>A</step><octave>4</octave></pitch><duration>8</duration><voice>1</voice><type>half</type><staff>1</staff><notations><slur type="start" number="1"/><ornaments><trill-mark/></ornaments></notations><lyric><text>one</text></lyric></note><note><!-- keep comment --><pitch><step>A</step><octave>4</octave></pitch><duration>2</duration><voice>1</voice><type>eighth</type><staff>1</staff><notations><slur type="stop" number="1"/><articulations><accent/></articulations></notations><lyric><text>two</text></lyric></note><barline><bar-style>light-heavy</bar-style></barline></measure></part></score-partwise>'''


def tie(client, review, target='e-2'):
    return request(client, review, 'events/e-1', {'tie_to_event_id': target}, 'PATCH')


def strip_tie(data):
    root = ET.fromstring(data, parser=ET.XMLParser(target=ET.TreeBuilder(insert_comments=True)))
    for note in root.findall('.//note'):
        for node in note.findall('tie'):
            note.remove(node)
        parent = note.find('notations')
        if parent is not None:
            for node in parent.findall('tied'):
                parent.remove(node)
    return ET.tostring(root)


@pytest.mark.parametrize('semitones', [0, 2, -2])
def test_existing_tie_preserves_events_history_and_transpose(workflow, monkeypatch, semitones):
    client, _ = workflow
    original = verify(client, create(client, XML))
    assert event(original, 'e-1')['tie_target_ids'] == ['e-2']
    response = tie(client, original)
    assert response.status_code == 200, response.text
    corrected = response.json()
    assert corrected['revision'] == original['revision'] + 1 and corrected['state'] == 'REVIEW_REQUIRED'
    assert event(corrected, 'e-1')['tie_target_id'] == 'e-2'
    assert event(corrected, 'e-1')['ties'] == ['start'] and event(corrected)['ties'] == ['stop']
    for key in ('e-1', 'e-2'):
        for field in ('pitch', 'duration', 'duration_units', 'onset', 'voice', 'staff', 'grace', 'display_size', 'lyric_ids'):
            assert event(corrected, key)[field] == event(original, key)[field]
    assert event(corrected, 'e-1')['duration'] == '2' and event(corrected)['duration'] == '1/2'
    assert event(corrected, 'e-1')['onset'] == '0' and event(corrected)['onset'] == '2'
    assert strip_tie(xml(corrected)) == strip_tie(XML)
    assert corrected['validation'] == original['validation']
    root = ET.fromstring(xml(corrected))
    notes = root.findall('.//note')
    assert [n.find('tie').get('type') for n in notes] == ['start', 'stop']
    assert [n.find('notations/tied').get('type') for n in notes] == ['start', 'stop']
    assert 'tie_start' in event(corrected, 'e-1')['provenance']['manual_fields']
    assert 'tie_stop' in event(corrected)['provenance']['manual_fields']
    assert request(client, corrected, 'transpose', {'semitones': semitones}).status_code == 409
    undo = request(client, corrected, 'undo').json()
    assert xml(undo) == XML and event(undo, 'e-1')['tie_target_id'] is None
    redo = request(client, undo, 'redo').json()
    assert xml(redo) == xml(corrected)
    removed = tie(client, redo, None).json()
    assert strip_tie(xml(removed)) == strip_tie(XML)
    assert not ET.fromstring(xml(removed)).findall('.//tie')
    assert not ET.fromstring(xml(removed)).findall('.//tied')
    restored = request(client, removed, 'undo').json()
    assert xml(restored) == xml(corrected)
    verified = verify(client, restored)
    import app.music.musicxml.transposer as module
    real = module.transpose_musicxml_document
    captured = []
    def capture(contents, *args, **kwargs):
        captured.append(contents)
        return real(contents, *args, **kwargs)
    monkeypatch.setattr(module, 'transpose_musicxml_document', capture)
    result = request(client, verified, 'transpose', {'semitones': semitones})
    assert result.status_code == 200, result.text
    assert captured == [xml(verified)] and captured[0] != XML
    output = ET.fromstring(result.content).findall('.//note')
    for note, duration, kind in zip(output, ['8', '2'], ['start', 'stop']):
        assert note.findtext('pitch/step') == {0: 'A', 2: 'B', -2: 'G'}[semitones]
        assert note.findtext('duration') == duration
        assert note.find('tie').get('type') == note.find('notations/tied').get('type') == kind
    invalidated = tie(client, verified, None).json()
    assert invalidated['state'] == 'REVIEW_REQUIRED'
    assert request(client, invalidated, 'transpose', {'semitones': 0}).status_code == 409


@pytest.mark.parametrize('replacement', [
    (b'<step>A</step>', b'<step>B</step>'),
    (b'<voice>1</voice>', b'<voice>2</voice>'),
    (b'<staff>1</staff>', b'<staff>2</staff>'),
    (b'<octave>4</octave>', b'<octave>5</octave>'),
    (b'<octave>4</octave>', b'<alter>1</alter><octave>4</octave>'),
    (b'<duration>2</duration>', b'<grace/>'),
])
def test_unusual_target_is_user_correctable_without_changing_notes(workflow, replacement):
    client, _ = workflow
    # Replace only the second event's musical property.
    head, tail = XML.split(b'<note><!-- keep comment -->')
    original = create(client, head + b'<note><!-- keep comment -->' + tail.replace(*replacement))
    result = tie(client, original)
    assert result.status_code == 200, result.text
    after = result.json()
    assert event(after, 'e-1')['tie_target_id'] == 'e-2'
    assert 'e-2' in event(original, 'e-1')['tie_target_ids']
    assert strip_tie(xml(after)) == strip_tie(xml(original))
    assert any(d['category'] == 'MUSIC_WARNING' and not d['blocking'] for d in after['validation']['diagnostics'])



@pytest.mark.parametrize('target,status', [('e-1', 422), ('missing', 404), ('m-1', 404), ('', 422)])
def test_invalid_ids_are_atomic(workflow, target, status):
    client, _ = workflow
    original = create(client, XML)
    result = tie(client, original, target)
    assert result.status_code == status and 'detail' in result.json()
    loaded = client.get('/api/v1/reviews/' + original['id']).json()
    assert loaded['revision'] == original['revision'] and xml(loaded) == XML


def test_earlier_target_is_advisory_and_stale_revision_rejected(workflow):
    client, _ = workflow
    original = create(client, XML)
    earlier = request(client, original, 'events/e-2', {'tie_to_event_id': 'e-1'}, 'PATCH')
    assert earlier.status_code == 200
    assert any(d['code'] == 'tie_timing' and not d['blocking'] for d in earlier.json()['validation']['diagnostics'])
    updated = tie(client, earlier.json()).json()
    assert tie(client, original, None).status_code == 409
    assert request(client, updated, 'events/missing', {'tie_to_event_id': 'e-2'}, 'PATCH').status_code == 404


def test_unrelated_musical_warnings_remain_advisory(workflow):
    client, _ = workflow
    # Forward extends the measure: error survives a tie-only repair in that same measure.
    broken = XML.replace(b'<barline>', b'<forward><duration>4</duration></forward><barline>').replace(
        b'</part>', b'<measure number="6"/><measure number="7"/><measure number="8"/><measure number="9"/><measure number="10"/><measure number="11"/></part>')
    original = create(client, broken)
    # Existing policy marks overfill as blocking for recognition reviews. Mark this
    # as a review-edited measure through an ordinary insertion/deletion history marker.
    service = workflow[1]
    service.store.get(original['id']).document.manual_changes['m-1'] = ['events']
    original = client.get('/api/v1/reviews/' + original['id']).json()
    assert original['validation']['error_count'] == 0
    assert original['validation']['warning_count'] == 8
    corrected = tie(client, original).json()
    assert corrected['validation'] == original['validation']
    assert request(client, corrected, 'verify', {'confirmed_source_comparison': True}).status_code == 200


def test_imported_tie_shows_target_and_can_be_removed(workflow):
    client, _ = workflow
    original = create(client, XML)
    tied = tie(client, original).json()
    imported = create(client, xml(tied))
    assert event(imported, 'e-1')['tie_target_id'] == 'e-2'
    removed = tie(client, imported, None)
    assert removed.status_code == 200, removed.text
    assert strip_tie(xml(removed.json())) == strip_tie(XML)
    assert not ET.fromstring(xml(removed.json())).findall('.//tie')


def test_change_target_between_adjacent_matching_chord_notes(workflow):
    client, _ = workflow
    # Two possible next notes at the same onset, not a skipped/intervening note.
    root = ET.fromstring(XML)
    from copy import deepcopy
    notes = root.findall('.//note')
    extra = deepcopy(notes[1])
    extra.insert(0, ET.Element('chord'))
    root.find('.//measure').insert(5, extra)
    original = create(client, ET.tostring(root))
    assert event(original, 'e-1')['tie_target_ids'] == ['e-2', 'e-3']
    tied = tie(client, original).json()
    changed = tie(client, tied, 'e-3')
    assert changed.status_code == 200, changed.text
    changed = changed.json()
    assert event(changed, 'e-1')['tie_target_id'] == 'e-3'
    assert event(changed, 'e-2')['ties'] == [] and event(changed, 'e-3')['ties'] == ['stop']
    assert xml(request(client, changed, 'undo').json()) == xml(tied)


@pytest.mark.parametrize('namespace', ['', 'http://www.musicxml.org/ns/musicxml'])
def test_remove_preserves_incoming_and_outgoing_continuations(workflow, namespace):
    client, _ = workflow
    original = XML.replace(b'<score-partwise version="4.0">', f'<score-partwise version="4.0" xmlns="{namespace}">'.encode()) if namespace else XML
    # Other sides of a continuation remain distinct relationships.
    original = original.replace(b'<duration>8</duration>', b'<duration>8</duration><tie type="stop"/>').replace(b'<duration>2</duration>', b'<duration>2</duration><tie type="start"/>').replace(b'<notations><slur type="start"', b'<notations><tied type="stop"/><slur type="start"').replace(b'<notations><slur type="stop"', b'<notations><tied type="start"/><slur type="stop"')
    baseline = create(client, original)
    added = tie(client, baseline)
    assert added.status_code == 200, added.text
    removed = tie(client, added.json(), None)
    assert removed.status_code == 200, removed.text
    ns = '{' + namespace + '}' if namespace else ''
    notes = ET.fromstring(xml(removed.json())).findall('.//' + ns + 'note')
    assert [[n.get('type') for n in note.findall(ns + 'tie')] for note in notes] == [['stop'], ['start']]
    assert [[n.get('type') for n in note.findall(ns + 'notations/' + ns + 'tied')] for note in notes] == [['stop'], ['start']]
    assert len(ET.fromstring(xml(removed.json())).findall('.//' + ns + 'slur')) == 2


@pytest.mark.parametrize('alter', ['bad', '1/0'])
def test_malformed_pitch_projects_diagnostic_without_crashing_discovery(workflow, alter):
    client, _ = workflow
    original = create(client, XML.replace(b'<octave>4</octave>', f'<alter>{alter}</alter><octave>4</octave>'.encode()))
    assert original['validation']['error_count'] > 0
    assert event(original, 'e-1')['tie_target_ids'] == []
    result = tie(client, original)
    assert result.status_code == 422


def test_combined_invalid_tie_and_pitch_patch_is_atomic(workflow):
    client, _ = workflow
    original = create(client, XML)
    result = request(client, original, 'events/e-1', {'pitch': {'step': 'B', 'octave': 4}, 'tie_to_event_id': 'missing'}, 'PATCH')
    assert result.status_code == 404
    loaded = client.get('/api/v1/reviews/' + original['id']).json()
    assert xml(loaded) == XML and loaded['revision'] == original['revision']
