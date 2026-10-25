"""Explicit per-head size uses existing chord command and canonical size patch."""
from xml.etree import ElementTree as ET
import pytest
from test_phase4e_workflow import workflow,create,request,xml,verify
from test_delete_preserve_timing import events
from test_chord_edit_01 import source,triplet_source


@pytest.mark.parametrize('kind,target',[('quarter','e-2'),('chord','e-3'),('lyrics','e-2'),('tied','e-2'),('triplet','e-1')])
@pytest.mark.parametrize('sizes',[['normal','normal'],['small','normal'],['normal','small']])
def test_explicit_sizes_add_independently_preserve_and_roundtrip(workflow,kind,target,sizes):
    client,_=workflow;before=create(client,triplet_source() if kind=='triplet' else source(kind));current=before;stages=[before]
    for step,size in zip(['C','D'],sizes):
        response=request(client,current,'events',{'measure_id':'m-1','chord_with_id':target,'pitch':{'step':step,'octave':5},'display_size':size})
        assert response.status_code==200,response.text
        after=response.json();added=next(e for id,e in events(after).items() if id not in events(current))
        assert added['display_size']==size
        leader=events(current)[target]['chord_id'] or target
        for key in ['duration','onset','voice','staff']:assert added[key]==events(current)[leader][key]
        assert after['score']['lyrics']==before['score']['lyrics']
        for id,old in events(before).items():
            for key in ['pitch','duration','onset','voice','staff','display_size','ties','lyric_ids']:assert events(after)[id][key]==old[key]
        assert after['score']['parts'][0]['measures'][0]['actual_duration']==before['score']['parts'][0]['measures'][0]['actual_duration']
        current=after;stages.append(current)
    # Existing notehead size changes are individual, never whole-chord edits.
    for size in ['small','normal']:
        response=client.patch(f'/api/v1/reviews/{current["id"]}/events/{target}',headers={'If-Match':str(current['revision'])},json={'display_size':size})
        assert response.status_code==200,response.text
        changed=response.json();assert events(changed)[target]['display_size']==size
        for id,old in events(current).items():
            if id!=target:
                for key in ['pitch','duration','onset','voice','staff','display_size','ties','lyric_ids']:assert events(changed)[id][key]==old[key]
        for key in ['pitch','duration','onset','voice','staff','chord_id','ties','lyric_ids']:assert events(changed)[target][key]==events(current)[target][key]
        undo=request(client,changed,'undo').json();assert xml(undo)==xml(current)
        redo=request(client,undo,'redo').json();assert xml(redo)==xml(changed)
        current=redo
    saved=verify(client,current);exported=client.get(f'/api/v1/reviews/{saved["id"]}/musicxml?verified_only=true');assert exported.status_code==200
    reopened=create(client,exported.content)
    assert [ET.tostring(n) for n in ET.fromstring(xml(reopened)).findall('.//note')]==[ET.tostring(n) for n in ET.fromstring(xml(saved)).findall('.//note')]
    assert [e['display_size'] for e in events(reopened).values()]==[e['display_size'] for e in events(saved).values()]
    current=saved  # Verification updates the review revision.
    # Both size changes and additions remain separate existing history steps.
    for expected in [stages[2],stages[1],stages[0]]:
        # The first two undo operations remove the two explicit size edits.
        if expected is stages[2]:
            current=request(client,current,'undo').json();current=request(client,current,'undo').json()
        else:current=request(client,current,'undo').json()
        assert xml(current)==xml(expected)


def test_bad_size_and_stale_requests_leave_original_score_untouched(workflow):
    client,_=workflow;before=create(client,source())
    for body in [{'display_size':'automatic'},{'display_size':'SMALL'}]:
        response=client.patch(f'/api/v1/reviews/{before["id"]}/events/e-2',headers={'If-Match':str(before['revision'])},json=body)
        assert response.status_code==422
    assert client.get(f'/api/v1/reviews/{before["id"]}').json()==before
    after=request(client,before,'events',{'measure_id':'m-1','chord_with_id':'e-2','pitch':{'step':'C','octave':5},'display_size':'small'}).json()
    assert request(client,before,'events',{'measure_id':'m-1','chord_with_id':'e-2','pitch':{'step':'D','octave':5},'display_size':'normal'}).status_code==409
    assert xml(client.get(f'/api/v1/reviews/{before["id"]}').json())==xml(after)


def test_type_omitted_small_uses_notehead_notation_without_inventing_written_duration(workflow):
    client,_=workflow;before=create(client,source().replace(b'<type>quarter</type>',b''))
    after=request(client,before,'events/e-2',{'display_size':'small'},method='PATCH').json()
    assert events(after)['e-2']['display_size']=='small'
    notes=ET.fromstring(xml(after)).findall('.//note')
    assert notes[1].find('type') is None
    assert notes[1].find('notehead').get('font-size')=='small'
    for id,old in events(before).items():
        for key in ['pitch','duration','onset','voice','staff','ties','lyric_ids']:assert events(after)[id][key]==old[key]
    added=request(client,after,'events',{'measure_id':'m-1','chord_with_id':'e-2','pitch':{'step':'C','octave':5},'display_size':'small'}).json()
    assert events(added)['new-2']['display_size']=='small'
    saved=verify(client,added);exported=client.get(f'/api/v1/reviews/{saved["id"]}/musicxml?verified_only=true');assert exported.status_code==200
    reopened=create(client,exported.content)
    assert [ET.tostring(n) for n in ET.fromstring(xml(reopened)).findall('.//note')]==[ET.tostring(n) for n in ET.fromstring(xml(saved)).findall('.//note')]
