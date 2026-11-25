"""PC-09: explicit corrections are not vetoed by musical diagnostics."""
from xml.etree import ElementTree as ET
import pytest
from test_phase4e_workflow import workflow,create,request,xml
from test_delete_preserve_timing import note,score,events,unchanged_survivors

@pytest.mark.parametrize('action',['apply','split','mixed','remove'])
def test_tuplet_partial_chord_and_cross_voice_preserves_unselected(workflow,action):
    client,_=workflow
    before=create(client,score(note('C',2)+note('E',1,chord=True)+note('D',2,voice='2')))
    body=dict(event_ids=['e-2','e-3'],action=action,actual_notes=3,normal_notes=2,draft_edit=True)
    response=request(client,before,'tuplets',body)
    assert response.status_code==200,response.text
    after=response.json()
    for key in ['e-1','e-4']:
        for field in ['pitch','voice','staff','onset','duration','lyric_ids']:
            assert events(after)[key][field]==events(before)[key][field]
    for key in ['e-2','e-3']:
        for field in ['pitch','voice','staff','onset','lyric_ids']:
            assert events(after)[key][field]==events(before)[key][field]
    reopened=create(client,xml(after))
    semantic=lambda r:sorted((e['pitch']['step'],e['voice'],e['onset'],e['duration']) for e in events(r).values())
    assert semantic(after)==semantic(reopened)
    assert xml(request(client,after,'undo').json())==xml(before)


def test_cross_voice_slur_is_explicit_and_undoable(workflow):
    client,_=workflow
    before=create(client,score(note('C')+note('D',3,voice='2')))
    response=request(client,before,'slurs',dict(source_event_id='e-1',target_event_id='e-2',draft_edit=True))
    assert response.status_code==200,response.text
    after=response.json()
    assert len(ET.fromstring(xml(after)).findall('.//slur'))==2
    unchanged_survivors(before,after,None)
    assert xml(request(client,after,'undo').json())==xml(before)


def test_duration_can_refine_divisions_without_moving_unrelated_content(workflow):
    client,_=workflow
    before=create(client,score(note('C')+note('D',3)))
    response=request(client,before,'events/e-1',dict(duration='1/3',draft_edit=True,preserve_onsets=True),'PATCH')
    assert response.status_code==200,response.text
    after=response.json()
    assert events(after)['e-1']['duration']=='1/3'
    assert events(after)['e-2']['onset']=='1'
    assert events(after)['e-2']['duration']=='3'


def test_reverse_timing_slur_can_be_removed_without_changing_notes(workflow):
    client,_=workflow
    before=create(client,score(note('C')+note('D',3,voice='2')))
    response=request(client,before,'slurs',dict(source_event_id='e-2',target_event_id='e-1',draft_edit=True))
    assert response.status_code==200,response.text
    added=response.json()
    response=request(client,added,'slurs',dict(source_event_id='e-2',target_event_id='e-1',draft_edit=True,remove=True))
    assert response.status_code==200,response.text
    assert ET.fromstring(xml(response.json())).find('.//slur') is None
    unchanged_survivors(before,response.json(),None)


@pytest.mark.parametrize('slash',[False,True])
def test_grace_before_has_slur_and_never_adds_beats(workflow,slash):
    client,_=workflow
    before=create(client,score(note('C',1)+note('D',3)))
    response=request(client,before,'events',dict(measure_id='m-1',before_event_id='e-1',kind='note',pitch=dict(step='B',octave=4),duration='1/2',voice='1',staff=1,grace=True,grace_slash=slash,grace_slur=True,draft_edit=True))
    assert response.status_code==200,response.text
    after=response.json()
    unchanged_survivors(before,after,None)
    grace=next(e for key,e in events(after).items() if key not in events(before))
    assert grace['grace'] and grace['duration'] is None
    assert any(s['source_event_id']==grace['id'] and s['target_event_id']=='e-1' for s in after['slurs'])
    root=ET.fromstring(xml(after));n=root.find('.//measure/note')
    assert n.find('duration') is None
    assert n.find('grace').get('slash')==('yes' if slash else 'no')
    assert n.find('.//slur').get('type')=='start'
    assert root.findall('.//measure/note')[1].find('.//slur').get('type')=='stop'
    reopened=create(client,xml(after))
    assert sum(e['grace'] for e in events(reopened).values())==1
    assert xml(request(client,after,'undo').json())==xml(before)
