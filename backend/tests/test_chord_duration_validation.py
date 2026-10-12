"""Duration edits must preserve every ordered chord adjacency."""
import pytest

from test_phase4e_workflow import workflow, create, request, event, xml


XML = b'''<score-partwise version="4.0">
<part-list><score-part id="P1"><part-name>Voice</part-name></score-part></part-list>
<part id="P1"><measure number="1"><attributes><divisions>8</divisions>
<time><beats>2</beats><beat-type>4</beat-type></time></attributes>
<note><pitch><step>C</step><octave>4</octave></pitch><duration>8</duration>
<tie type="start"/><voice>1</voice><type>quarter</type><staff>1</staff>
<notations><tied type="start"/></notations><lyric number="2"><text>word</text></lyric></note>
<note><chord/><pitch><step>E</step><octave>4</octave></pitch><duration>4</duration>
<voice>1</voice><type size="cue">eighth</type><notehead font-size="small">normal</notehead><staff>1</staff></note>
<note><chord/><pitch><step>G</step><octave>4</octave></pitch><duration>2</duration>
<voice>1</voice><type>16th</type><staff>1</staff></note>
<note><pitch><step>C</step><octave>4</octave></pitch><duration>8</duration>
<tie type="stop"/><voice>1</voice><type>quarter</type><staff>1</staff>
<notations><tied type="stop"/></notations></note>
<note><grace/><pitch><step>D</step><octave>4</octave></pitch><voice>1</voice><type>eighth</type></note>
</measure></part></score-partwise>'''


@pytest.mark.parametrize('identifier,duration', [
    ('e-3', '3/4'),  # Below the leader, but above the preceding member.
    ('e-2', '1/8'),  # Below the following member.
    ('e-1', '1/4'),  # Below the first member.
])
def test_invalid_note_duration_rejected_atomically(workflow, identifier, duration):
    client, _ = workflow
    before = create(client, XML)
    assert before['validation']['error_count'] == 0
    assert not any(d['code'] == 'chord_duration' for d in before['validation']['diagnostics'])
    response = request(client, before, 'events/' + identifier,
                       dict(duration=duration, duration_scope='note'), 'PATCH')
    assert response.status_code == 422, response.text
    assert client.get('/api/v1/reviews/' + before['id']).json() == before


@pytest.mark.parametrize('preserve_onsets', [False, True])
@pytest.mark.parametrize('identifier,duration,scope', [
    ('e-3', '1/2', 'note'), ('e-2', '1/4', 'note'), ('e-2', '1/2', 'chord'),
])
def test_valid_duration_edit_preserves_semantics_and_chord_time(workflow, identifier, duration, scope, preserve_onsets):
    client, _ = workflow
    before = create(client, XML)
    response = request(client, before, 'events/' + identifier,
                       dict(duration=duration, duration_scope=scope, preserve_onsets=preserve_onsets), 'PATCH')
    assert response.status_code == 200, response.text
    after = response.json()
    assert after['validation']['error_count'] == 0
    assert not any(d['code'] == 'chord_duration' for d in after['validation']['diagnostics'])
    for eid in ['e-1', 'e-2', 'e-3', 'e-4', 'e-5']:
        original, updated = event(before, eid), event(after, eid)
        for field in ['voice', 'staff', 'pitch', 'lyric_ids', 'display_size', 'grace', 'cue', 'ties', 'chord_id', 'chord_member']:
            assert updated[field] == original[field]
        expected = duration if (scope == 'chord' and eid in ['e-1', 'e-2', 'e-3']) or eid == identifier else original['duration']
        assert updated['duration'] == expected
    next_onset = '1/2' if scope == 'chord' and not preserve_onsets else '1'
    assert [event(after, eid)['onset'] for eid in ['e-1', 'e-2', 'e-3', 'e-4']] == ['0', '0', '0', next_onset]
    undone = request(client, after, 'undo').json()
    assert xml(undone) == xml(before)
    assert xml(request(client, undone, 'redo').json()) == xml(after)
