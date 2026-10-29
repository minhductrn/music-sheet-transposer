"""Human lyric correction on preserved synthetic XML; no recognition invocation."""
from xml.etree import ElementTree as ET
import pytest
from test_phase4e_workflow import workflow, create, request, event, xml, verify
from test_review_existing_ties import XML as BASE

XML = BASE.replace(b'<lyric><text>one</text></lyric>',
    '<lyric number="1"><syllabic>begin</syllabic><text>khế“ịp</text><elision> </elision><text>đây</text><extend/></lyric><lyric number="2"><syllabic>single</syllabic><text>khác</text></lyric>'.encode())


def strip_lyrics(data):
    root = ET.fromstring(data, parser=ET.XMLParser(target=ET.TreeBuilder(insert_comments=True)))
    for note in root.findall('.//note'):
        for lyric in note.findall('lyric'):
            note.remove(lyric)
    return ET.tostring(root)


def corrected(client):
    review = create(client, XML)
    review = request(client, review, 'events/e-1', {'tie_to_event_id': 'e-2'}, 'PATCH').json()
    return verify(client, review)


@pytest.mark.parametrize('operation', ['add', 'edit', 'remove'])
@pytest.mark.parametrize('semitones', [0, 2, -2])
def test_lyrics_preserve_musical_state_history_and_corrected_transpose(workflow, monkeypatch, operation, semitones):
    client, _ = workflow
    before = corrected(client)
    verse = next(l for l in before['score']['lyrics'] if l['event_id'] == 'e-1' and l['number'] == '1')
    if operation == 'add':
        response = request(client, before, 'events/e-1/lyrics', {'text': 'Cùng đem tin mừng', 'number': '3'})
    elif operation == 'edit':
        response = request(client, before, f'lyrics/{verse["id"]}', {'text': 'khắp', 'segment_index': 0}, 'PATCH')
    else:
        response = request(client, before, f'lyrics/{verse["id"]}', method='DELETE')
    assert response.status_code == 200, response.text
    after = response.json()
    assert after['revision'] == before['revision'] + 1 and after['state'] == 'REVIEW_REQUIRED'
    assert 'lyrics' in event(after, 'e-1')['provenance']['manual_fields']
    for key in ('e-1', 'e-2'):
        for field in ('pitch', 'duration', 'onset', 'duration_units', 'voice', 'staff', 'ties', 'display_size', 'grace'):
            assert event(after, key)[field] == event(before, key)[field]
    assert strip_lyrics(xml(after)) == strip_lyrics(xml(before))
    assert after['validation'] == before['validation']
    verses = ET.fromstring(xml(after)).findall('.//note')[0].findall('lyric')
    assert next(l for l in verses if l.get('number') == '2').findtext('text') == 'khác'
    if operation == 'edit':
        lyric = next(l for l in verses if l.get('number') == '1')
        assert [t.text for t in lyric.findall('text')] == ['khắp', 'đây']
        assert lyric.findtext('syllabic') == 'begin' and lyric.find('extend') is not None
    if operation == 'add':
        assert next(l for l in verses if l.get('number') == '3').findtext('text') == 'Cùng đem tin mừng'
    if operation == 'remove':
        assert all(l.get('number') != '1' for l in verses)
    assert request(client, after, 'transpose', {'semitones': semitones}).status_code == 409
    undo = request(client, after, 'undo').json()
    assert xml(undo) == xml(before) and undo['state'] != 'VERIFIED'
    redo = request(client, undo, 'redo').json()
    assert xml(redo) == xml(after)
    verified = verify(client, redo)
    import app.music.musicxml.transposer as module
    original = module.transpose_musicxml_document
    captured = []
    def capture(contents, value):
        captured.append(contents)
        return original(contents, value)
    monkeypatch.setattr(module, 'transpose_musicxml_document', capture)
    transposed = request(client, verified, 'transpose', {'semitones': semitones})
    assert transposed.status_code == 200, transposed.text
    assert captured == [xml(verified)] and captured[0] != XML
    assert [ET.tostring(l) for l in ET.fromstring(transposed.content).findall('.//lyric')] == [ET.tostring(l) for l in ET.fromstring(xml(verified)).findall('.//lyric')]


def test_newly_inserted_note_can_receive_lyric_and_stale_delete_rolls_back(workflow):
    client, _ = workflow
    review = create(client, XML)
    inserted = request(client, review, 'events', {'measure_id': 'm-1', 'after_event_id': 'e-2', 'pitch': {'step': 'D', 'octave': 5}, 'duration': '1/2'}).json()
    note = next(e for p in inserted['score']['parts'] for m in p['measures'] for v in m['voices'] for e in v['events'] if e['id'].startswith('new-'))
    response = request(client, inserted, f'events/{note["id"]}/lyrics', {'text': 'đây', 'number': '1'})
    assert response.status_code == 200
    updated = response.json()
    lyric = next(l for l in updated['score']['lyrics'] if l['event_id'] == note['id'])
    assert lyric['segments'] == ['đây']
    assert request(client, inserted, f'lyrics/{lyric["id"]}', method='DELETE').status_code == 409
    assert xml(client.get(f'/api/v1/reviews/{review["id"]}').json()) == xml(updated)
    assert request(client, updated, 'lyrics/nonexistent', method='DELETE').status_code == 404


@pytest.mark.parametrize('semitones', [0, 2, -2])
def test_two_missing_adjacent_notes_can_be_added_then_tied(workflow, semitones):
    client, _ = workflow
    baseline = b'''<score-partwise version="4.0"><part-list><score-part id="P"><part-name>Voice</part-name></score-part></part-list><part id="P"><measure number="1"><attributes><divisions>4</divisions><time><beats>7</beats><beat-type>8</beat-type></time></attributes><note><pitch><step>G</step><octave>4</octave></pitch><duration>4</duration><voice>1</voice><type>quarter</type></note><barline><bar-style>light-heavy</bar-style></barline></measure></part></score-partwise>'''
    review = create(client, baseline)
    first_response = request(client, review, 'events', {'measure_id': 'm-1', 'after_event_id': 'e-1', 'pitch': {'step': 'A', 'octave': 4}, 'duration': '2'})
    assert first_response.status_code == 200
    first = first_response.json()
    second_response = request(client, first, 'events', {'measure_id': 'm-1', 'after_event_id': 'new-1', 'pitch': {'step': 'A', 'octave': 4}, 'duration': '1/2'})
    assert second_response.status_code == 200
    second = second_response.json()
    assert 'new-2' in event(second, 'new-1')['tie_target_ids']
    assert 'new-1' not in event(second, 'new-1')['tie_target_ids']
    tied_response = request(client, second, 'events/new-1', {'tie_to_event_id': 'new-2'}, 'PATCH')
    assert tied_response.status_code == 200
    tied = tied_response.json()
    assert event(tied, 'new-1')['duration'] == '2' and event(tied, 'new-2')['duration'] == '1/2'
    assert event(tied, 'new-1')['ties'] == ['start'] and event(tied, 'new-2')['ties'] == ['stop']
    assert tied['validation']['error_count'] == 0
    undo = tied
    for _ in range(3):
        undo = request(client, undo, 'undo').json()
    assert xml(undo) == baseline
    for _ in range(3):
        undo = request(client, undo, 'redo').json()
    assert xml(undo) == xml(tied)
    verified = verify(client, undo)
    output = request(client, verified, 'transpose', {'semitones': semitones})
    assert output.status_code == 200
    notes = ET.fromstring(output.content).findall('.//note')
    assert len(notes) == 3 and len(ET.fromstring(output.content).findall('.//measure')) == 1
    assert [n.findtext('duration') for n in notes] == ['4', '8', '2']
    assert notes[1].find('tie').get('type') == 'start' and notes[2].find('tie').get('type') == 'stop'


def test_duration_correction_overfill_is_advisory_without_omr(workflow):
    client, _ = workflow
    review = create(client, BASE)
    response = request(client, review, 'events/e-1', {'duration': '4'}, 'PATCH')
    assert response.status_code == 200
    corrected = response.json()
    assert any(d['code'] == 'measure_overfilled' and d['severity'] == 'WARNING' and not d['blocking'] for d in corrected['validation']['diagnostics'])
    assert corrected['validation']['can_verify']
    restored = request(client, corrected, 'undo').json()
    assert xml(restored) == xml(review)


def test_visual_pitch_context_tracks_mid_measure_key_changes(workflow):
    client, _ = workflow
    data = BASE.replace(b'<staves>2</staves>', b'<key><fifths>-1</fifths></key><staves>2</staves>').replace(
        b'<note><!-- keep comment -->', b'<attributes><key><fifths>1</fifths></key></attributes><note><!-- keep comment -->',
    )
    review = create(client, data)
    assert event(review, 'e-1')['key_signature'][0]['fifths'] == '-1'
    assert event(review, 'e-2')['key_signature'][0]['fifths'] == '1'
    assert xml(review) == data


def test_visual_duration_choices_use_existing_tuplet_and_divisions_rules(workflow):
    client, _ = workflow
    data = BASE.replace(b'<type>half</type>', b'<type>half</type><time-modification><actual-notes>3</actual-notes><normal-notes>2</normal-notes><normal-type>half</normal-type></time-modification>')
    review = create(client, data)
    assert event(review, 'e-1')['duration_options'] == ['1/4', '1/2', '1', '2', '4']
    assert event(review, 'e-2')['duration_options'] == ['1/4', '1/2', '1', '3/2', '2', '3', '4']
    assert xml(review) == data
