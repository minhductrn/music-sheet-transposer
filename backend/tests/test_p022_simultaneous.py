"""Exact anchored timing and independently owned parallel ties."""
from xml.etree import ElementTree as ET
import pytest
from test_phase4e_workflow import workflow, create, request, event, xml
from test_review_tied_insertion import XML


@pytest.mark.parametrize("size,duration,voice,chord", [
    ("small", "1/2", "2", True), ("normal", "1", "2", True),
    ("small", "2", "2", False), ("normal", "1/2", "3", False),
])
def test_exact_anchor_independent_duration_and_history(workflow, size, duration, voice, chord):
    client, _ = workflow
    before = create(client, XML)
    response = request(client, before, 'events', dict(
        measure_id='m-1', same_onset_id='e-2', voice=voice, staff=2,
        pitch=dict(step='D', octave=5, alter='1'), written_accidental='sharp',
        duration=duration, display_size=size))
    assert response.status_code == 200, response.text
    after = response.json()
    added = event(after, 'new-1')
    assert added['onset'] == event(before, 'e-2')['onset'] == '1'
    assert added['duration'] == duration and added['display_size'] == size
    assert added['voice'] == voice and added['chord_member'] == chord
    assert not added['grace'] and added['pitch']['step'] == 'D'
    assert added['accidental']['text'] == 'sharp'
    for identifier in ['e-1', 'e-2']:
        for field in ['id', 'onset', 'duration', 'voice', 'staff', 'pitch', 'grace', 'display_size', 'lyric_ids', 'accidental']:
            assert event(after, identifier)[field] == event(before, identifier)[field]
    assert b'preserved comment' in xml(after)
    assert ET.fromstring(xml(after)).findtext('.//lyric/text') == 'word'
    undone = request(client, after, 'undo').json()
    assert xml(undone) == xml(before)
    redone = request(client, undone, 'redo').json()
    assert xml(redone) == xml(after)
    assert event(redone, 'new-1')['id'] == added['id']


def test_two_simultaneous_pairs_replay_scoped_removal_check_and_history(workflow):
    client, _ = workflow
    raw = XML.replace(b'<rest/>', b'<pitch><step>A</step><octave>4</octave></pitch>')
    before = create(client, raw)
    current = before
    for anchor in ['e-1', 'e-2']:
        response = request(client, current, 'events', dict(measure_id='m-1',
            same_onset_id=anchor, pitch=dict(step='C', octave=5),
            duration='1/2', display_size='small'))
        assert response.status_code == 200, response.text
        current = response.json()
    for source, target in [('e-1', 'e-2'), ('new-1', 'new-2')]:
        response = request(client, current, 'events/' + source,
                           dict(tie_to_event_id=target), 'PATCH')
        assert response.status_code == 200, response.text
        current = response.json()
    root = ET.fromstring(xml(current))
    owned = [n for n in root.findall('.//tied') if n.get('id')]
    assert len(owned) == 4 and len({n.get('number') for n in owned}) == 2
    replay = request(client, current, 'events/new-1',
                     dict(tie_to_event_id='new-2'), 'PATCH').json()
    assert replay['revision'] == current['revision'] and xml(replay) == xml(current)
    checked = request(client, current, 'music-check')
    assert checked.status_code == 200
    assert client.get('/api/v1/reviews/' + current['id']).json() == current
    removed = request(client, current, 'events/new-1',
                      dict(tie_to_event_id=None), 'PATCH').json()
    assert event(removed, 'e-1')['tie_relationship'] == event(current, 'e-1')['tie_relationship']
    assert event(removed, 'new-1')['tie_relationship'] is None
    undo = request(client, removed, 'undo').json()
    assert xml(undo) == xml(current)
    assert xml(request(client, undo, 'redo').json()) == xml(removed)


def test_anchor_conflict_fails_atomically(workflow):
    client, _ = workflow
    before = create(client, XML)
    response = request(client, before, 'events', dict(measure_id='m-1',
        same_onset_id='e-2', onset='0', pitch=dict(step='C', octave=4)))
    assert response.status_code == 422
    assert client.get('/api/v1/reviews/' + before['id']).json() == before


def test_member_duration_correction_does_not_normalize_anchor(workflow):
    client, _ = workflow
    before = create(client, XML)
    added = request(client, before, 'events', dict(measure_id='m-1',
        same_onset_id='e-2', pitch=dict(step='C', octave=5),
        duration='1/2', display_size='small')).json()
    response = request(client, added, 'events/new-1',
                       dict(duration='1/4', duration_scope='note', preserve_onsets=True), 'PATCH')
    assert response.status_code == 200, response.text
    after = response.json()
    assert event(after, 'new-1')['duration'] == '1/4'
    assert event(after, 'new-1')['onset'] == event(added, 'new-1')['onset']
    assert event(after, 'e-2')['duration'] == '1'
    assert xml(request(client, after, 'undo').json()) == xml(added)
