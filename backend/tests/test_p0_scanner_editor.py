from xml.etree import ElementTree as ET
import pytest
from test_phase4e_workflow import workflow, create, request, xml, event, patch, verify
from test_phase4f_structure import draft


def empty():
    root = ET.fromstring(draft())
    m1, m2 = root.findall('part/measure')
    m1.remove(m1.find('note'))
    note = m2.find('note'); note.remove(note.find('rest'))
    pitch = ET.Element('pitch'); note.insert(0, pitch)
    ET.SubElement(pitch, 'step').text = 'A'
    ET.SubElement(pitch, 'octave').text = '4'
    return ET.tostring(root)


def add(client, review, **fields):
    body = dict(measure_id='m-1', onset='0', voice='1', staff=1, kind='note', pitch={'step':'A','octave':4}, duration='2')
    body.update(fields)
    response = request(client, review, 'events', body)
    assert response.status_code == 200, response.text
    return response.json()


def test_generalized_small_half_tie_verify_transpose(workflow):
    client, _ = workflow
    review = add(client, create(client, empty()))
    review = add(client, review, voice='2', pitch={'step':'C','octave':5}, display_size='small')
    c = event(review, 'new-2')
    assert (c['duration'],c['display_size'],c['grace'],c['onset'],c['voice']) == ('2','small',False,'0','2')
    review = patch(client, review, 'new-1', tie_to_event_id='e-1')
    root = ET.fromstring(xml(review))
    assert len(root.findall('.//tie')) == len(root.findall('.//tied')) == 2
    review = verify(client, review)
    for offset, step in [(2,'D'),(3,'E')]:
        response = request(client, review, 'transpose', {'semitones':offset})
        assert response.status_code == 200, response.text
        small = next(n for n in ET.fromstring(response.content).findall('.//note') if n.find('type').get('size') == 'cue')
        assert small.findtext('pitch/step') == step and small.findtext('duration') == '8' and small.find('grace') is None
    reparsed = create(client, xml(review))
    small = next(e for p in reparsed['score']['parts'] for m in p['measures'] for v in m['voices'] for e in v['events'] if e['display_size'] == 'small')
    assert small['duration'] == '2' and not small['grace']
    review = patch(client, review, 'new-1', tie_to_event_id=None)
    assert not ET.fromstring(xml(review)).findall('.//tie')
    assert request(client, review, 'transpose', {'semitones':2}).status_code == 409


@pytest.mark.parametrize('fields', [dict(onset='1'),dict(onset='1/3',voice='2'),dict(staff=2),dict(voice=None),dict(after_event_id='e-1')])
def test_ambiguous_insertion_atomic(workflow, fields):
    client, _ = workflow
    review = create(client, draft())
    body = dict(measure_id='m-1',onset='0',voice='1',staff=1,kind='note',pitch={'step':'C','octave':5},duration='2'); body.update(fields)
    assert request(client, review, 'events', body).status_code == 422
    current = client.get(f'/api/v1/reviews/{review["id"]}').json()
    assert current['revision'] == review['revision'] and xml(current) == xml(review)


def test_no_spill_duration_delete_preserve_cursor(workflow):
    client, _ = workflow
    review = add(client, create(client, draft()), onset='4',voice='2')
    assert event(review,'new-1')['measure_id'] == 'm-1' and event(review,'e-2')['measure_id'] == 'm-2'
    review = patch(client, review, 'new-1',duration='1')
    assert event(review,'new-1')['onset'] == '4' and event(review,'e-1')['onset'] == '0'
    response = request(client, review,'events/new-1',method='DELETE'); assert response.status_code == 200, response.text
    review = response.json()
    assert not any(i['severity']=='ERROR' and not i['can_confirm_source'] for i in review['validation']['diagnostics'])


def test_size_timing_ownership_independent(workflow):
    client, _ = workflow
    review = add(client, create(client, empty()),display_size='small')
    review = patch(client, review,'new-1',grace=True)
    assert event(review,'new-1')['grace'] and event(review,'new-1')['display_size']=='small'
    review = patch(client, review,'new-1',grace=False,duration='2')
    response = request(client, review,'events/new-1/ownership',dict(measure_id='m-2',onset='0',voice='2',staff=1))
    assert response.status_code == 200, response.text
    review=response.json(); e=event(review,'new-1')
    assert (e['measure_id'],e['voice'],e['onset'],e['duration'],e['display_size'],e['grace'])==('m-2','2','0','2','small',False)
    assert event(review,'e-1')['onset']=='0'
    assert not any(i['severity']=='ERROR' for i in review['validation']['diagnostics'])


def test_source_confirmation_scope_and_invalidation(workflow):
    client, _=workflow
    raw=draft(units=12); review=create(client,raw)
    issue=next(i for i in review['validation']['diagnostics'] if i['code']=='measure_overfilled')
    response=request(client,review,'diagnostics/confirm-source',dict(diagnostic_id=issue['id'],note='Source contains this long measure.'))
    assert response.status_code==200,response.text
    review=response.json(); assert xml(review)==raw and review['validation']['can_verify']
    review=verify(client,review)
    review=patch(client,review,'e-2',display_size='small')
    assert next(i for i in review['validation']['diagnostics'] if i['id']==issue['id'])['source_confirmed']
    review=patch(client,review,'e-1',pitch={'step':'C','octave':5})
    assert not next(i for i in review['validation']['diagnostics'] if i['id']==issue['id'])['source_confirmed']
    assert review['state']=='REVIEW_REQUIRED'
    assert request(client,review,'verify',{'confirmed_source_comparison':True}).status_code==200


def test_technical_failures_not_confirmable(workflow):
    client,_=workflow
    review=create(client,draft().replace(b'<duration>8</duration>',b'<duration>bad</duration>',1))
    issue=next(i for i in review['validation']['diagnostics'] if i['severity']=='ERROR' and not i['can_confirm_source'])
    assert request(client,review,'diagnostics/confirm-source',dict(diagnostic_id=issue['id'],note='Matches source')).status_code==422
    assert request(client,review,'verify',{'confirmed_source_comparison':True}).status_code==409


def test_chord_insertion_and_owner_split_preserve_other_notes(workflow):
    client,_=workflow
    review=add(client,create(client,empty()))
    review=add(client,review,pitch={'step':'C','octave':5},display_size='small')
    assert event(review,'new-2')['chord_member']
    response=request(client,review,'events/new-2/ownership',dict(measure_id='m-2',onset='0',voice='2',staff=1))
    assert response.status_code==200,response.text
    review=response.json()
    assert not event(review,'new-2')['chord_member']
    assert event(review,'new-1')['duration']=='2' and event(review,'new-1')['measure_id']=='m-1'
    assert event(review,'e-1')['onset']=='0'


def test_move_with_tie_or_collision_fails_atomically(workflow):
    client,_=workflow
    review=add(client,create(client,empty()))
    response=request(client,review,'events/new-1/ownership',dict(measure_id='m-2',onset='1',voice='1',staff=1))
    assert response.status_code==422
    review=patch(client,review,'new-1',tie_to_event_id='e-1')
    response=request(client,review,'events/new-1/ownership',dict(measure_id='m-2',onset='0',voice='2',staff=1))
    assert response.status_code==422
    assert xml(client.get(f'/api/v1/reviews/{review["id"]}').json())==xml(review)


def test_missing_tie_endpoint_is_technical_but_pitch_mismatch_is_advisory(workflow):
    client,_=workflow
    review=add(client,create(client,empty()))
    assert request(client,review,'events/new-1',{'tie_to_event_id':'missing'},'PATCH').status_code==404
    review=patch(client,review,'new-1',tie_to_event_id='e-1')
    review=patch(client,review,'e-1',pitch={'step':'B','octave':4})
    issue=next(i for i in review['validation']['diagnostics'] if i['code']=='tie_pitch_mismatch')
    assert issue['can_confirm_source'] and not issue['blocking']
    confirmed=request(client,review,'diagnostics/confirm-source',dict(diagnostic_id=issue['id'],note='Source comparison'))
    assert confirmed.status_code==200 and xml(confirmed.json())==xml(review)
    assert request(client,confirmed.json(),'verify',{'confirmed_source_comparison':True}).status_code==200


def test_source_confirmation_no_silent_reactivation_and_history(workflow):
    client,_=workflow
    review=create(client,draft(units=12))
    issue=next(i for i in review['validation']['diagnostics'] if i['code']=='measure_overfilled')
    review=request(client,review,'diagnostics/confirm-source',dict(diagnostic_id=issue['id'],note='Confirmed printed notation')).json()
    before=review
    review=patch(client,review,'e-1',pitch={'step':'C','octave':5})
    review=patch(client,review,'e-1',pitch={'step':'A','octave':4})
    assert not next(i for i in review['validation']['diagnostics'] if i['id']==issue['id'])['source_confirmed']
    review=request(client,review,'undo').json(); review=request(client,review,'undo').json()
    assert review['state']=='REVIEW_REQUIRED'
    assert next(i for i in review['validation']['diagnostics'] if i['id']==issue['id'])['source_confirmed']
    assert xml(review)==xml(before)
    review=verify(client,review)
    assert request(client,review,'transpose',{'semitones':3}).status_code==200
    exported=client.get(f'/api/v1/reviews/{review["id"]}/musicxml?verified=true')
    assert exported.status_code==200
    assert ET.fromstring(exported.content).findtext('part/measure/note/duration')=='12'


def test_position_rejects_broken_existing_chord(workflow):
    client,_=workflow
    review=create(client,draft().replace(b'<note><pitch>',b'<note><chord/><pitch>',1))
    assert any(i['code']=='broken_chord' for i in review['validation']['diagnostics'])
    response=request(client,review,'events',dict(measure_id='m-1',onset='0',voice='2',staff=1,kind='note',duration='2',pitch={'step':'C','octave':5}))
    assert response.status_code==422
