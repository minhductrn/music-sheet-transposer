from fractions import Fraction
from xml.etree import ElementTree as ET
import pytest
from test_phase4e_workflow import workflow, create, request, xml, verify
from test_delete_preserve_timing import events
from test_triplet_replacement import note


def source(kind='quarter', placement='middle'):
    ratio='<time-modification><actual-notes>3</actual-notes><normal-notes>2</normal-notes></time-modification>'
    type_,duration={'quarter':('quarter',6),'chord':('quarter',6),'multi':('quarter',6),'dotted':('quarter',9),'beamed':('eighth',3),'sixteenth':('16th', '1.5'),'lyrics':('quarter',6),'tied':('quarter',6),'triplet':('eighth',2),'mixed-quarter':('quarter',4),'mixed-eighth':('eighth',2),'short-member':('quarter',6)}[kind]
    extra=ratio if 'triplet' in kind or 'mixed' in kind else '<beam number="1">begin</beam>' if kind=='beamed' else '<lyric number="1"><text>Ngài</text></lyric>' if kind=='lyrics' else '<tie type="start"/><notations><tied type="start" orientation="under"/></notations>' if kind=='tied' else ''
    target=note('E',4,duration,type_,extra=extra)
    if kind=='dotted':target=target.replace('<staff>','<dot/><staff>')
    if kind in ['chord','multi','short-member']:
        target+=note('G',4,3 if kind=='short-member' else duration,'eighth' if kind=='short-member' else type_,chord=True)
    if kind=='multi':target+=note('B',4,duration,type_,chord=True)
    before=note('D',4,6) if placement!='beginning' else ''
    after=note('E',4,6,extra='<tie type="stop"/><notations><tied type="stop" orientation="under"/></notations>' if kind=='tied' else '') if placement!='end' else ''
    extent=Fraction(duration)+ (6 if before else 0)+(6 if after else 0)
    return (f'<score-partwise version="4.0"><part-list><score-part id="P"><part-name>Voice</part-name></score-part></part-list><part id="P"><measure number="1"><attributes><divisions>6</divisions><staves>2</staves><clef><sign>G</sign><line>2</line></clef></attributes>{before}{target}{after}<backup><duration>{float(extent):g}</duration></backup>{note("A",3,float(extent),voice="2",staff=2)}</measure></part></score-partwise>').encode()


@pytest.mark.parametrize('kind',['quarter','chord','multi','dotted','beamed','sixteenth','lyrics','tied','triplet','mixed-quarter','mixed-eighth','short-member'])
@pytest.mark.parametrize('placement',['beginning','middle','end'])
def test_inherit_selected_position_without_insertion_slot(workflow,kind,placement):
    client,_=workflow;before=create(client,source(kind,placement))
    target='e-1' if placement=='beginning' else 'e-2'
    # Selecting any chord member must inherit the leader's complete interval.
    if kind in ['chord','multi','short-member']:target=f'e-{int(target.split("-")[1])+1}'
    leader=events(before)[target]['chord_id'] or target
    response=request(client,before,'events',{'measure_id':'m-1','chord_with_id':target,'pitch':{'step':'C','octave':5,'alter':'0'}})
    assert response.status_code==200,response.text
    after=response.json();old=events(before);new=events(after)
    added=next(e for k,e in new.items() if k not in old)
    assert added['pitch']==dict(step='C',alter='0',octave=5)
    for field in ['onset','duration','voice','staff']:assert added[field]==old[leader][field]
    assert added['chord_member'] and added['chord_id']==leader
    assert added['notated_duration']==old[leader]['notated_duration']
    for key,event in old.items():
        for field,value in event.items():
            if field not in ['chord_id','tie_target_ids']:assert new[key][field]==value
    assert after['score']['lyrics']==before['score']['lyrics']
    assert after['score']['parts'][0]['measures'][0]['actual_duration']==before['score']['parts'][0]['measures'][0]['actual_duration']
    oldnotes=ET.fromstring(xml(before)).findall('.//note');newnotes=ET.fromstring(xml(after)).findall('.//note')
    index=int(leader.split('-')[1])-1+{'chord':2,'multi':3}.get(kind,1)
    assert [ET.tostring(n) for n in newnotes[:index]+newnotes[index+1:]]==[ET.tostring(n) for n in oldnotes]
    assert not newnotes[index].findall('lyric') and not newnotes[index].findall('tie')
    undo=request(client,after,'undo').json();assert xml(undo)==xml(before) and not undo['can_undo']
    redo=request(client,undo,'redo').json();assert xml(redo)==xml(after)
    saved=verify(client,redo);exported=client.get(f'/api/v1/reviews/{saved["id"]}/musicxml?verified_only=true')
    assert exported.status_code==200
    reopened=create(client,exported.content)
    assert [ET.tostring(n) for n in ET.fromstring(xml(reopened)).findall('.//note')]==[ET.tostring(n) for n in newnotes]
    assert request(client,before,'events',{'measure_id':'m-1','chord_with_id':target,'pitch':{'step':'D','octave':5}}).status_code==409


def triplet_source():
    ratio='<time-modification><actual-notes>3</actual-notes><normal-notes>2</normal-notes></time-modification>'
    notes=''.join(note(s,4,2,'eighth',extra=ratio+('<notations><tuplet type="start" bracket="yes"/></notations>' if i==0 else '<notations><tuplet type="stop"/></notations>' if i==2 else '')) for i,s in enumerate(['E','F','G']))
    return source().replace((note('D',4,6)+note('E',4,6)+note('E',4,6)).encode(),(notes+note('A',4,12,'half')).encode())


def test_owner_triplet_two_additions_each_independently_undoable(workflow):
    client,_=workflow;before=create(client,triplet_source());current=before;stages=[before]
    for target,step in [('e-1','C'),('e-2','D'),('e-3','B')]:
        current=request(client,current,'events',{'measure_id':'m-1','chord_with_id':target,'pitch':{'step':step,'octave':5}}).json();stages.append(current)
        for id,event in events(before).items():
            for field in ['onset','duration','pitch','voice','staff','notated_duration']:assert events(current)[id][field]==event[field]
    for expected in reversed(stages[:-1]):current=request(client,current,'undo').json();assert xml(current)==xml(expected)
    for expected in stages[1:]:current=request(client,current,'redo').json();assert xml(current)==xml(expected)


def test_duplicate_pitch_retains_existing_canonical_unison_convention(workflow):
    client,_=workflow;before=create(client,source(placement='beginning'))
    after=request(client,before,'events',{'measure_id':'m-1','chord_with_id':'e-1','pitch':{'step':'E','octave':4}}).json()
    assert len(events(after))==len(events(before))+1
    assert events(after)['new-1']['pitch']==events(before)['e-1']['pitch']


def test_selected_overlapping_voice_is_preserved_without_guessing(workflow):
    client,_=workflow;before=create(client,source())
    target=next(e for e in events(before).values() if e['voice']=='2')
    response=request(client,before,'events',{'measure_id':'m-1','chord_with_id':target['id'],'pitch':{'step':'G','octave':3}})
    assert response.status_code==200,response.text
    after=response.json();added=events(after)['new-1']
    for field in ['onset','duration','voice','staff']:assert added[field]==target[field]
    assert added['voice']=='2' and added['staff']==2
    for id,old in events(before).items():
        for field in ['pitch','onset','duration','voice','staff','notated_duration','lyric_ids','ties']:assert events(after)[id][field]==old[field]
