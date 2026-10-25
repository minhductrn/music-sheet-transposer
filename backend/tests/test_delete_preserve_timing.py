"""Synthetic timing-preserving deletion through the canonical review API."""
from xml.etree import ElementTree as ET

import pytest

from test_phase4e_workflow import workflow, create, request, xml, verify


def note(step, duration=1, chord=False, voice='1', staff=1):
    return f'<note>{"<chord/>" if chord else ""}<pitch><step>{step}</step><octave>4</octave></pitch><duration>{duration}</duration><voice>{voice}</voice><type>quarter</type><staff>{staff}</staff><lyric><text>{step}</text></lyric></note>'


def score(notes):
    return ('<score-partwise version="4.0"><part-list><score-part id="P1"><part-name>Test</part-name></score-part></part-list><part id="P1"><measure number="1"><attributes><divisions>1</divisions><time><beats>4</beats><beat-type>4</beat-type></time><staves>2</staves></attributes>' + notes + '</measure><measure number="2">' + note('G', 4) + '</measure></part></score-partwise>').encode()


def events(review):
    return {e['id']: e for p in review['score']['parts'] for m in p['measures'] for v in m['voices'] for e in v['events']}


def remove(client, before, identifier):
    result = request(client, before, f'events/{identifier}/delete-preserve-timing')
    assert result.status_code == 200, result.text
    return result.json()


def unchanged_survivors(before, after, removed):
    for key, old in events(before).items():
        if key == removed:
            continue
        new = events(after)[key]
        for field in ('onset', 'duration', 'pitch', 'voice', 'staff', 'grace', 'lyric_ids'):
            assert new[field] == old[field], (key, field)


@pytest.mark.parametrize('identifier', ['e-1', 'e-2', 'e-3'])
def test_first_middle_final_and_canonical_export_reimport(workflow, identifier):
    client, _ = workflow
    before = create(client, score(note('C') + note('D') + note('E', 2)))
    after = remove(client, before, identifier)
    unchanged_survivors(before, after, identifier)
    root = ET.fromstring(xml(after))
    forward = root.find('.//forward')
    assert forward.findtext('duration') == ('2' if identifier == 'e-3' else '1')
    assert forward.findtext('voice') == '1' and forward.findtext('staff') == '1'
    assert root.find('.//rest') is None
    assert ET.tostring(root.findall('.//measure')[1]) == ET.tostring(ET.fromstring(xml(before)).findall('.//measure')[1])
    saved = verify(client, after)
    exported = client.get(f'/api/v1/reviews/{saved["id"]}/musicxml?verified_only=true')
    assert exported.status_code == 200, exported.text
    assert exported.content == xml(after)
    reopened = create(client, exported.content)
    semantic = lambda r: [(e['pitch'], e['onset'], e['duration'], e['voice'], e['staff']) for e in events(r).values()]
    assert semantic(reopened) == semantic(after)
    undone = request(client, saved, 'undo').json()
    assert xml(undone) == xml(before)
    redone = request(client, undone, 'redo').json()
    assert xml(redone) == xml(after)


@pytest.mark.parametrize('identifier', ['e-1', 'e-2'])
def test_chord_pitch_and_last_member(workflow, identifier):
    client, _ = workflow
    before = create(client, score(note('C') + note('E', chord=True) + note('D', 3)))
    after = remove(client, before, identifier)
    unchanged_survivors(before, after, identifier)
    assert ET.fromstring(xml(after)).find('.//forward') is None
    survivor = 'e-2' if identifier == 'e-1' else 'e-1'
    final = remove(client, after, survivor)
    unchanged_survivors(after, final, survivor)
    assert ET.fromstring(xml(final)).findtext('.//forward/duration') == '1'


def test_multiple_voices_staff_and_existing_backup_unchanged(workflow):
    client, _ = workflow
    before = create(client, score(note('C') + note('D', 3) + '<backup><duration>4</duration></backup>' + note('A', 4, voice='2', staff=2)))
    after = remove(client, before, 'e-1')
    unchanged_survivors(before, after, 'e-1')
    assert ET.fromstring(xml(after)).findtext('.//backup/duration') == '4'
    after2 = remove(client, after, 'e-3')
    unchanged_survivors(after, after2, 'e-3')
    forwards = ET.fromstring(xml(after2)).findall('.//forward')
    assert [(f.findtext('duration'), f.findtext('voice'), f.findtext('staff')) for f in forwards] == [('1', '1', '1'), ('4', '2', '2')]


def test_legacy_delete_still_shifts_imported_notes(workflow):
    client, _ = workflow
    before = create(client, score(note('C') + note('D', 3)))
    result = request(client, before, 'events/e-1', method='DELETE')
    assert result.status_code == 200
    assert events(result.json())['e-2']['onset'] == '0'
    assert ET.fromstring(xml(result.json())).find('.//forward') is None


@pytest.mark.parametrize('notes', [note('C', 0) + note('D', 4), note('C', 2) + note('E', 1, chord=True) + note('D', 2)])
def test_ambiguous_or_duration_changing_deletion_rejected_atomically(workflow, notes):
    client, _ = workflow
    before = create(client, score(notes))
    result = request(client, before, 'events/e-1/delete-preserve-timing')
    assert result.status_code == 422
    assert client.get(f'/api/v1/reviews/{before["id"]}').json() == before


def test_positioned_note_has_one_compensation_and_stale_revision_rejected(workflow):
    client, _ = workflow
    before = create(client, score(note('C', 4)))
    added = request(client, before, 'events', dict(measure_id='m-1', onset='0', voice='2', staff=2, pitch=dict(step='E', octave=4), duration='1')).json()
    after = remove(client, added, 'new-1')
    unchanged_survivors(added, after, 'new-1')
    assert len(ET.fromstring(xml(after)).findall('.//forward')) == 2  # one existing cursor return + one replacement
    assert request(client, added, 'events/e-1/delete-preserve-timing').status_code == 409


def test_grace_deletion_needs_no_forward(workflow):
    client, _ = workflow
    grace = note('C').replace('<pitch>', '<grace/><pitch>').replace('<duration>1</duration>', '')
    before = create(client, score(grace + note('D', 4)))
    after = remove(client, before, 'e-1')
    unchanged_survivors(before, after, 'e-1')
    assert ET.fromstring(xml(after)).find('.//forward') is None


def test_namespace_and_mid_measure_divisions_preserved(workflow):
    client, _ = workflow
    raw = score(note('C') + '<attributes><divisions>2</divisions></attributes>' + note('D', 6))
    raw = raw.replace(b'<score-partwise version="4.0">', b'<score-partwise xmlns="urn:test:musicxml" version="4.0">')
    before = create(client, raw)
    after = remove(client, before, 'e-1')
    unchanged_survivors(before, after, 'e-1')
    forward = ET.fromstring(xml(after)).find('.//{urn:test:musicxml}forward')
    assert forward.findtext('{urn:test:musicxml}duration') == '1'
    assert forward.findtext('{urn:test:musicxml}voice') == '1'


def test_shorter_nonleading_chord_member_can_be_removed(workflow):
    client, _ = workflow
    before = create(client, score(note('C', 2) + note('E', chord=True) + note('D', 2)))
    after = remove(client, before, 'e-2')
    unchanged_survivors(before, after, 'e-2')


def test_deleted_lyrics_and_ties_cleanup_and_unrelated_relationships(workflow):
    client, _ = workflow
    before = create(client, score(note('C') + note('E', chord=True) + note('C', 3)))
    connected = request(client, before, 'events/e-1', dict(tie_to_event_id='e-3'), 'PATCH')
    assert connected.status_code == 200, connected.text
    before = connected.json()
    direction = request(client, before, 'events/e-1', dict(tie_direction='down'), 'PATCH')
    assert direction.status_code == 200, direction.text
    before = direction.json()
    # Delete the other chord pitch: the accepted tie and lyric owner survive.
    after = remove(client, before, 'e-2')
    unchanged_survivors(before, after, 'e-2')
    assert events(after)['e-1']['tie_relationship'] == events(before)['e-1']['tie_relationship']
    assert events(after)['e-1']['tie_direction'] == 'down'
    # Deleting the tie owner removes its lyric and the corresponding tie endpoint.
    final = remove(client, after, 'e-1')
    legacy = request(client, after, 'events/e-1', method='DELETE')
    assert legacy.status_code == 409  # stale request cannot overwrite the atomic edit
    assert not any(l['event_id'] == 'e-1' for l in final['score']['lyrics'])
    assert ET.fromstring(xml(final)).find('.//tie') is None
    assert ET.fromstring(xml(final)).find('.//tied') is None
    undone = request(client, final, 'undo').json()
    assert xml(undone) == xml(after)
    assert events(undone)['e-1']['tie_direction'] == 'down'


@pytest.mark.parametrize('notes', [
    note('C') + note('D'),  # Temporarily incomplete measure.
    note('C', 4) + note('D', 4),  # Overfilled measure.
    note('C') + note('D') + note('E', 2, chord=True),  # Unrelated advisory chord-duration mismatch.
    note('C', 2) + '<backup><duration>1</duration></backup>' + note('D', 2),  # Overlapping voice events.
])
def test_musician_controls_incomplete_or_theoretically_inconsistent_content(workflow, notes):
    client, _ = workflow
    before = create(client, score(notes))
    after = remove(client, before, 'e-1')
    unchanged_survivors(before, after, 'e-1')
    assert after['validation']['can_verify']
    saved = verify(client, after)
    exported = client.get(f'/api/v1/reviews/{saved["id"]}/musicxml?verified_only=true')
    assert exported.status_code == 200
    assert exported.content == xml(after)
    reopened = create(client, exported.content)
    assert reopened['validation']['can_verify']
    assert ET.fromstring(exported.content).find('.//rest') is None
