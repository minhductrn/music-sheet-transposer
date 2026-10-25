"""Read-only canonical selection preview and existing atomic conversion."""
from xml.etree import ElementTree as ET
import pytest
from test_phase4e_workflow import workflow, create, request, xml, verify
from test_tuplet_02 import source, assert_mixed, structure
from test_delete_preserve_timing import score, note, events


def preview(client, review, ids):
    response = request(client, review, 'triplets/preview', {'event_ids': ids})
    assert response.status_code == 200, response.text
    return response.json()


def test_reverse_selected_chords_preview_is_readonly_and_command_roundtrips(workflow):
    client, _ = workflow
    original = create(client, source())
    forward = preview(client, original, ['e-1','e-2','e-3','e-4'])
    reverse = preview(client, original, ['e-4','e-3','e-2','e-1'])
    assert reverse == forward
    assert reverse['valid'] is True
    assert (reverse['positions'],reverse['noteheads'],reverse['pattern'],reverse['ratio']) == (2,4,'Quarter + eighth','3:2')
    before = client.get(f'/api/v1/reviews/{original["id"]}').json()
    assert before == original  # revision, XML, history and lifecycle untouched
    result = request(client, original, 'triplets', reverse['command'])
    assert result.status_code == 200, result.text
    after = result.json(); assert_mixed(after)
    assert after['revision'] == original['revision'] + 1
    assert after['score']['lyrics'] == original['score']['lyrics']
    assert after['score']['texts'] == original['score']['texts']
    for key in ['e-5','e-6','e-7']: assert events(after)[key] == events(original)[key]
    undone = request(client, after, 'undo').json(); assert xml(undone) == xml(original)
    redone = request(client, undone, 'redo').json(); assert xml(redone) == xml(after)
    assert request(client, original, 'triplets/preview', {'event_ids':['e-1','e-2']}).status_code == 409
    assert request(client, original, 'triplets', forward['command']).status_code == 409
    saved = verify(client, redone)
    exported = client.get(f'/api/v1/reviews/{saved["id"]}/musicxml?verified_only=true')
    reopened = create(client, exported.content); assert_mixed(reopened)
    assert structure(reopened) == structure(saved)
    assert [(n.findtext('time-modification/actual-notes'), [t.attrib for t in n.findall('notations/tuplet')]) for n in ET.fromstring(exported.content).findall('.//note')] == [(n.findtext('time-modification/actual-notes'), [t.attrib for t in n.findall('notations/tuplet')]) for n in ET.fromstring(xml(reopened)).findall('.//note')]


def test_three_equal_notes_reverse_order_uses_canonical_rhythm(workflow):
    client, _ = workflow
    before = create(client, score(note('C')+note('D')+note('E')+note('F')))
    data = preview(client,before,['e-3','e-1','e-2'])
    assert data['valid'] is True
    assert data['command']['event_ids'] == ['e-1','e-2','e-3']
    assert data['command']['base_duration'] == '1'
    after = request(client,before,'triplets',data['command']).json()
    assert [events(after)[f'e-{i}']['duration'] for i in (1,2,3)] == ['2/3']*3
    assert events(after)['e-4']['onset'] == '3'


@pytest.mark.parametrize('ids,reason', [
    (['e-1','e-3','e-4'],'all notes belonging'),
    (['e-2'],'all notes belonging'),
    (['e-5','e-7'],'pitched notes'),
    (['e-1','e-1'],'only once'),
    (['missing'],'no longer available'),
    ([], 'Select three consecutive'),
])
def test_invalid_preview_never_mutates(workflow,ids,reason):
    client,_=workflow; before=create(client,source())
    result=preview(client,before,ids)
    assert result['valid'] is False and result['command'] is None
    assert reason in result['explanation']
    assert client.get(f'/api/v1/reviews/{before["id"]}').json() == before


def test_nonconsecutive_notes_have_useful_error(workflow):
    client,_=workflow
    before=create(client,score(note('C')+note('D')+note('E')+note('F')))
    result=preview(client,before,['e-1','e-3','e-4'])
    assert result['valid'] is False
    assert 'not consecutive' in result['explanation']
    assert 'e-1' not in result['explanation']


@pytest.mark.parametrize('variant,reason', [('measure','same measure'),('voice','same voice and staff'),('staff','same voice and staff')])
def test_cross_scope_selection_is_rejected(workflow,variant,reason):
    client,_=workflow
    body=score(note('C')+note('D')+note('E'))
    if variant=='voice':body=body.replace(note('E').encode(),note('E',voice='2').encode())
    if variant=='staff':body=body.replace(note('E').encode(),note('E',staff=2).encode())
    before=create(client,body)
    ids=['e-1','e-2','e-4'] if variant=='measure' else ['e-1','e-2','e-3']
    result=preview(client,before,ids)
    assert result['valid'] is False and reason in result['explanation']
    assert xml(client.get(f'/api/v1/reviews/{before["id"]}').json()) == xml(before)


def test_existing_tuplet_preview_is_rejected_without_normalization(workflow):
    client,_=workflow; before=create(client,source())
    command=preview(client,before,['e-1','e-2','e-3','e-4'])['command']
    converted=request(client,before,'triplets',command).json()
    result=preview(client,converted,['e-1','e-2','e-3','e-4'])
    assert result['valid'] is False and 'existing tuplet' in result['explanation']
    assert xml(client.get(f'/api/v1/reviews/{converted["id"]}').json()) == xml(converted)


def test_inconsistent_written_durations_are_not_advertised_as_valid(workflow):
    client,_=workflow
    before=create(client,score(note('C')+note('D')+note('E',2)))
    result=preview(client,before,['e-1','e-2','e-3'])
    assert result['valid'] is False and 'unsupported durations' in result['explanation']
    assert xml(client.get(f'/api/v1/reviews/{before["id"]}').json()) == xml(before)
