"""Mixed quarter/eighth triplets: chords are rhythmic positions, not advances."""
from fractions import Fraction
from xml.etree import ElementTree as ET
import pytest
from test_phase4e_workflow import workflow, create, request, xml, verify
from test_delete_preserve_timing import events


def note(step, octave, units, kind, chord=False, extra=''):
    return f'<note>{"<chord/>" if chord else ""}<pitch><step>{step}</step><octave>{octave}</octave></pitch><duration>{units}</duration><voice>1</voice><type>{kind}</type><staff>1</staff>{extra}</note>'


def source():
    body = note('F', 4, 6, 'quarter', extra='<lyric number="1"><text>Ngài</text></lyric><lyric number="2"><text>yêu</text></lyric>') + note('A', 4, 6, 'quarter', True)
    body += note('G', 4, 3, 'eighth') + note('C', 5, 3, 'eighth', True)
    # Unrelated following tie, explicit orientation, text and rest must survive.
    body += note('D', 4, 6, 'quarter').replace('<voice>', '<tie type="start"/><voice>').replace('<staff>1</staff>', '<staff>1</staff><notations><tied type="start" orientation="over"/></notations>')
    body += note('D', 4, 6, 'quarter').replace('<voice>', '<tie type="stop"/><voice>').replace('<staff>1</staff>', '<staff>1</staff><notations><tied type="stop" orientation="over"/></notations>')
    body += '<note><rest/><duration>3</duration><voice>1</voice><type>eighth</type><staff>1</staff></note>'
    return ('<score-partwise version="4.0"><work><work-title>Mixed chord test</work-title></work><part-list><score-part id="P"><part-name>Voice</part-name></score-part></part-list><part id="P"><measure number="1"><attributes><divisions>6</divisions><time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes><direction><direction-type><words>Giữ nguyên</words></direction-type></direction>' + body + '</measure></part></score-partwise>').encode()


def payload(insert=False):
    result = dict(measure_id='m-1', staff=1, voice='1', pattern='quarter-eighth', base_duration='1')
    result.update(dict(onset='0', pitches=[dict(step=s, octave=o, alter='0') for s, o in [('F',4),('A',4),('G',4),('C',5)]]) if insert else dict(event_ids=['e-1','e-2','e-3','e-4']))
    return result


def nodes(review):
    return ET.fromstring(xml(review)).findall('.//note')


def structure(review):
    return [(e['pitch'],e['kind'],e['onset'],e['duration'],e['chord_member'],e['voice'],e['staff'],e['ties']) for e in events(review).values()]


def assert_mixed(review):
    group = [e for e in events(review).values() if e['notated_duration']['time_modification']]
    assert len(group) == 4
    assert [e['onset'] for e in group] == ['0','0','2/3','2/3']
    assert [e['duration'] for e in group] == ['2/3','2/3','1/3','1/3']
    assert [e['chord_member'] for e in group] == [False,True,False,True]
    assert group[0]['chord_id'] == group[1]['chord_id']
    assert group[2]['chord_id'] == group[3]['chord_id'] != group[0]['chord_id']
    ns = [n for n in nodes(review) if n.find('time-modification') is not None]
    assert [n.findtext('type') for n in ns] == ['quarter','quarter','eighth','eighth']
    assert [n.findtext('time-modification/actual-notes') for n in ns] == ['3'] * 4
    assert [n.findtext('time-modification/normal-notes') for n in ns] == ['2'] * 4
    assert [[n.get('type') for n in note.findall('notations/tuplet')] for note in ns] == [['start'],[],['stop'],[]]
    assert Fraction(group[-1]['onset']) + Fraction(group[-1]['duration']) == 1


def roundtrip(client, after):
    saved = verify(client, after)
    exported = client.get(f'/api/v1/reviews/{saved["id"]}/musicxml?verified_only=true')
    assert exported.status_code == 200, exported.text
    reopened = create(client, exported.content)
    assert_mixed(reopened)
    assert structure(reopened) == structure(saved)
    assert [ET.tostring(n) for n in nodes(reopened)] == [ET.tostring(n) for n in nodes(saved)]
    return reopened


def test_convert_chords_and_independent_pitch_history_roundtrip(workflow):
    client, _ = workflow
    before = create(client, source())
    response = request(client, before, 'triplets', payload())
    assert response.status_code == 200, response.text
    converted = response.json(); assert_mixed(converted)
    assert set(events(converted)) == set(events(before))
    for key, event in events(before).items():
        for field in ('pitch','chord_id','chord_member','lyric_ids','ties','voice','staff'):
            assert events(converted)[key][field] == event[field]
        if key not in payload()['event_ids']:
            assert events(converted)[key] == event
    assert before['score']['lyrics'] == converted['score']['lyrics']
    assert before['score']['texts'] == converted['score']['texts']
    original_nodes = nodes(before)
    assert [ET.tostring(n) for n in nodes(converted)[4:]] == [ET.tostring(n) for n in original_nodes[4:]]
    undo = request(client, converted, 'undo').json(); assert xml(undo) == xml(before)
    redo = request(client, undo, 'redo').json(); assert xml(redo) == xml(converted)
    for step, octave in [('C',4),('C',5),('G',4)]:
        patch = request(client, redo, 'events/e-2', {'pitch':dict(step=step,octave=octave,alter='0')}, 'PATCH')
        assert patch.status_code == 200, patch.text
        edited = patch.json(); assert_mixed(edited)
        assert events(edited)['e-2']['pitch']['step'] == step
        assert events(edited)['e-2']['pitch']['octave'] == octave
        for key in events(redo):
            if key != 'e-2': assert events(edited)[key] == events(redo)[key]
        undone = request(client, edited, 'undo').json(); assert xml(undone) == xml(redo)
        redone = request(client, undone, 'redo').json(); assert xml(redone) == xml(edited)
        redo = redone
    roundtrip(client, redo)


def test_delete_add_chords_and_history_with_unrelated_preservation(workflow):
    client, _ = workflow
    before = create(client, source())
    for key in ['e-2','e-1','e-4','e-3']:
        response = request(client, before, f'events/{key}/delete-preserve-timing')
        assert response.status_code == 200, response.text
        before = response.json()
    result = request(client, before, 'triplets', payload(True))
    assert result.status_code == 200, result.text
    after = result.json(); assert_mixed(after)
    for key, e in events(before).items():
        assert {k:v for k,v in events(after)[key].items() if k != 'tie_target_ids'} == {k:v for k,v in e.items() if k != 'tie_target_ids'}
    # Candidate picker options can grow after insertion; established ties cannot.
    assert [ET.tostring(n) for n in nodes(after)[:len(nodes(before))]] == [ET.tostring(n) for n in nodes(before)]
    undone = request(client, after, 'undo').json(); assert xml(undone) == xml(before)
    redone = request(client, undone, 'redo').json(); assert xml(redone) == xml(after)
    roundtrip(client, redone)
    assert request(client, before, 'triplets', payload(True)).status_code == 409


@pytest.mark.parametrize('ids', [['e-1','e-3','e-4'], ['e-2','e-1','e-3','e-4'], ['e-1','e-2','e-3','e-3'], ['e-1','e-2'], ['e-3','e-4','e-5','e-6']])
def test_ambiguous_conversion_is_atomic(workflow, ids):
    client, _ = workflow
    before = create(client, source()); data = payload(); data['event_ids'] = ids
    response = request(client, before, 'triplets', data)
    assert response.status_code == 422, response.text
    current = client.get(f'/api/v1/reviews/{before["id"]}').json()
    assert current['revision'] == before['revision']; assert xml(current) == xml(before)


@pytest.mark.parametrize('changes', [dict(base_duration='1/2'), dict(pattern='5:4'), dict(staff=3), dict(pitches=[]), dict(onset='-1')])
def test_invalid_insertion_is_atomic(workflow, changes):
    client, _ = workflow
    before = create(client, source()); data = payload(True); data.update(changes)
    response = request(client, before, 'triplets', data)
    assert response.status_code == 422, response.text
    assert xml(client.get(f'/api/v1/reviews/{before["id"]}').json()) == xml(before)


def test_single_note_and_chord_mixed_group_conversion(workflow):
    client, _ = workflow
    # Remove the first chord's upper member explicitly before conversion.
    before = create(client, source())
    deleted = request(client, before, 'events/e-2/delete-preserve-timing').json()
    data = payload(); data['event_ids'] = ['e-1','e-3','e-4']
    response = request(client, deleted, 'triplets', data)
    assert response.status_code == 200, response.text
    after = response.json()
    ns = [n for n in nodes(after) if n.find('time-modification') is not None]
    assert len(ns) == 3
    assert [n.findtext('type') for n in ns] == ['quarter','eighth','eighth']


def test_mixed_refines_divisions_and_rejects_shared_unison(workflow):
    from test_delete_preserve_timing import score
    client, _ = workflow
    before = create(client, score(''))
    bad = payload(True); bad['pitches'][1] = bad['pitches'][0]
    response = request(client, before, 'triplets', bad)
    assert response.status_code == 422
    assert xml(client.get(f'/api/v1/reviews/{before["id"]}').json()) == xml(before)
    response = request(client, before, 'triplets', payload(True))
    assert response.status_code == 200, response.text
    after = response.json(); assert_mixed(after)
    assert events(after)['e-1']['duration'] == events(before)['e-1']['duration']
    assert request(client, before, 'triplets', payload(True)).status_code == 409
