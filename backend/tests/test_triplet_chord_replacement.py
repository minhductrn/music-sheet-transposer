"""Whole-chord replacement from any one bound head; shared interval, explicit scope."""
from fractions import Fraction
from xml.etree import ElementTree as ET
import pytest
from test_phase4e_workflow import workflow, create, request, xml, verify
from test_delete_preserve_timing import events
from test_triplet_replacement import note, payload, post, unchanged


def chord_source(divisions=6, protected=''):
    d=divisions
    two=note('E',4,d)+note('C',5,d,chord=True,extra=protected)
    three=note('F',4,d)+note('A',4,d,chord=True)+note('D',5,d,chord=True)
    first=two+note('D',4,d)+three+note('G',4,d)
    first+=f'<backup><duration>{4*d}</duration></backup>'+note('B',3,4*d,'whole',voice='2',staff=2)
    lyrics=note('A',4,d)+note('C',5,d,chord=True,extra='<lyric number="1"><text>Ngài</text></lyric>')
    def tied(step,octave,chord,kind):
        return note(step,octave,d,chord=chord,extra=f'<notations><tied type="{kind}" orientation="over"/></notations>').replace('<voice>',f'<tie type="{kind}"/><voice>')
    ties=''.join(tied(s,o,ch,t) for t in ['start','stop'] for s,o,ch in [('B',4,False),('D',5,True)])
    return (f'<score-partwise version="4.0"><work><work-title>Whole chord replacement</work-title></work><part-list><score-part id="P"><part-name>Voice</part-name></score-part></part-list><part id="P"><measure number="1"><attributes><divisions>{d}</divisions><time><beats>4</beats><beat-type>4</beat-type></time><staves>2</staves><clef number="1"><sign>G</sign><line>2</line></clef><clef number="2"><sign>F</sign><line>4</line></clef></attributes><direction><direction-type><words>Giữ nguyên</words></direction-type></direction>{first}</measure><measure number="2">{lyrics}{ties}{note("E",5,d)}</measure></part></score-partwise>').encode()


def confirmed(body,ids):
    return dict(body,original_member_ids=ids)


@pytest.mark.parametrize('target,ids,start', [('e-1',['e-1','e-2'],'0'),('e-2',['e-1','e-2'],'0'),('e-4',['e-4','e-5','e-6'],'2'),('e-5',['e-4','e-5','e-6'],'2'),('e-6',['e-4','e-5','e-6'],'2')])
@pytest.mark.parametrize('pattern,counts',[('equal',(1,1)),('quarter-eighth',(1,1)),('quarter-eighth',(1,2)),('quarter-eighth',(2,1)),('quarter-eighth',(2,2))])
def test_any_head_resolves_and_replaces_whole_shared_interval(workflow,target,ids,start,pattern,counts):
    client,_=workflow;before=create(client,chord_source())
    options=post(client,before,'triplet-replacement/options',target=target).json()
    assert options['eligible'] is True
    original=options['original']
    assert [m['id'] for m in original['members']]==ids
    assert original['member_count']==len(ids) and original['duration']=='1'
    assert original['start']==start and Fraction(original['end'])==Fraction(start)+1
    body=confirmed(payload(pattern,counts),ids)
    preview=post(client,before,'triplet-replacement/preview',body,target=target).json()
    assert preview['valid'] is True and preview['fits_exactly'] is True
    assert preview['original']==original and preview['proposed_duration']=='1'
    assert preview['noteheads_per_position']==([1,1,1] if pattern=='equal' else list(counts))
    assert preview['replacement_pitches']==body['pitches'];unchanged(client,before)
    response=post(client,before,'replace-triplet',body,target=target)
    assert response.status_code==200,response.text
    after=response.json();old=events(before);new=events(after)
    added=[e for k,e in new.items() if k not in old]
    assert set(new)==(set(old)-set(ids))|{e['id'] for e in added}
    assert len(added)==len(body['pitches']) and [e['pitch'] for e in added]==body['pitches']
    assert min(Fraction(e['onset']) for e in added)==Fraction(start)
    assert max(Fraction(e['onset'])+Fraction(e['duration']) for e in added)==Fraction(start)+1
    assert sum((Fraction(e['duration']) for e in added if not e['chord_member']),Fraction(0))==1
    for key,event in old.items():
        if key not in ids:
            # Candidate choices are derived UI metadata, not existing tie links.
            assert {k:v for k,v in new[key].items() if k!='tie_target_ids'}=={k:v for k,v in event.items() if k!='tie_target_ids'}
            assert not set(new[key]['tie_target_ids']).intersection(ids)
            assert set(new[key]['tie_target_ids']).issubset(new)
    for field in ['lyrics','texts','harmonies']:assert after['score'][field]==before['score'][field]
    oldxml=ET.fromstring(xml(before));newxml=ET.fromstring(xml(after))
    for tag in ['backup','forward']:assert len(newxml.findall('.//'+tag))==len(oldxml.findall('.//'+tag))
    untouched=[n for i,n in enumerate(oldxml.findall('.//note'),1) if f'e-{i}' not in ids]
    # Exclude newly inserted group by preserved chronological position, compare every surviving XML node.
    notes=newxml.findall('.//note');index=int(ids[0].split('-')[1])-1
    assert [ET.tostring(n) for n in notes[:index]+notes[index+len(added):]]==[ET.tostring(n) for n in untouched]
    assert [t.get('type') for t in newxml.findall('.//tuplet')]==['start','stop']
    undo=request(client,after,'undo').json();assert xml(undo)==xml(before) and not undo['can_undo']
    redo=request(client,undo,'redo').json();assert xml(redo)==xml(after)
    saved=verify(client,redo);exported=client.get(f'/api/v1/reviews/{saved["id"]}/musicxml?verified_only=true')
    assert exported.status_code==200
    reopened=create(client,exported.content)
    assert [ET.tostring(n) for n in ET.fromstring(xml(reopened)).findall('.//note')]==[ET.tostring(n) for n in newxml.findall('.//note')]


@pytest.mark.parametrize('extra,reason', [('<lyric><text>Giữ</text></lyric>','lyrics'),('<tie type="start"/>','ties'),('<notations><slur type="start" number="1"/></notations>','slurs'),('<notations><articulations><accent/></articulations></notations>','notation')])
def test_protected_unselected_member_blocks_entire_chord_without_loss(workflow,extra,reason):
    client,_=workflow;before=create(client,chord_source(protected=extra));body=confirmed(payload(),['e-1','e-2'])
    for target in ['e-1','e-2']:
        options=post(client,before,'triplet-replacement/options',target=target).json()
        assert options['eligible'] is False and reason in options['explanation']
        assert options['original']['member_count']==2
        assert not post(client,before,'triplet-replacement/preview',body,target=target).json()['valid']
        assert post(client,before,'replace-triplet',body,target=target).status_code==422
        unchanged(client,before)


def test_explicit_scope_confirmation_and_stale_revision_are_required(workflow):
    client,_=workflow;before=create(client,chord_source())
    for ids in [None,['e-1'],['e-2','e-1'],['e-1','e-3'],['e-1','e-2','e-3'],['e-1','e-1']]:
        body=payload() if ids is None else confirmed(payload(),ids)
        assert post(client,before,'replace-triplet',body).status_code==422
        assert not post(client,before,'triplet-replacement/preview',body).json()['valid'];unchanged(client,before)
    after=post(client,before,'replace-triplet',confirmed(payload(),['e-1','e-2'])).json()
    for suffix,body in [('replace-triplet',confirmed(payload(),['e-1','e-2'])),('triplet-replacement/preview',confirmed(payload(),['e-1','e-2'])),('triplet-replacement/options',None)]:
        assert post(client,before,suffix,body).status_code==409
    unchanged(client,after)


@pytest.mark.parametrize('case', ['orphan','four','different-duration','different-voice','different-staff','unison','tuplet'])
def test_unsupported_or_ambiguous_chord_is_rejected(workflow,case):
    data=chord_source()
    a=note('E',4,6);b=note('C',5,6,chord=True)
    replacement={'orphan':a.replace('<note>','<note><chord/>')+b,
                 'four':a+b+note('G',5,6,chord=True)+note('B',5,6,chord=True),
                 'different-duration':a+note('C',5,3,chord=True),
                 'different-voice':a+note('C',5,6,chord=True,voice='2'),
                 'different-staff':a+note('C',5,6,chord=True,staff=2),
                 'unison':a+note('E',4,6,chord=True),
                 'tuplet':a+b.replace('</note>','<time-modification><actual-notes>3</actual-notes><normal-notes>2</normal-notes></time-modification></note>')}[case]
    client,_=workflow;before=create(client,data.replace((a+b).encode(),replacement.encode(),1))
    options=post(client,before,'triplet-replacement/options').json()
    assert options['eligible'] is False,options
    assert post(client,before,'replace-triplet',confirmed(payload(),['e-1','e-2'])).status_code==422;unchanged(client,before)


def test_internal_builder_failure_rolls_back_all_removed_chord_members(workflow):
    client,_=workflow;before=create(client,chord_source())
    bad=confirmed(payload('quarter-eighth',(2,2)),['e-1','e-2']);bad['pitches'][1]=bad['pitches'][0]
    preview=post(client,before,'triplet-replacement/preview',bad).json()
    assert not preview['valid'] and 'unison' in preview['explanation']
    assert post(client,before,'replace-triplet',bad).status_code==422;unchanged(client,before)


def test_divisions_refinement_preserves_unrelated_chord_and_other_voice(workflow):
    client,_=workflow;before=create(client,chord_source(divisions=1))
    response=post(client,before,'replace-triplet',confirmed(payload(),['e-1','e-2']))
    assert response.status_code==200,response.text
    after=response.json()
    for key,old in events(before).items():
        if key in ['e-1','e-2']:continue
        for field in ['pitch','duration','onset','voice','staff','chord_id','chord_member','ties','lyric_ids']:assert events(after)[key][field]==old[field]
    old=ET.fromstring(xml(before));new=ET.fromstring(xml(after))
    for tag in ['backup','forward']:assert len(old.findall('.//'+tag))==len(new.findall('.//'+tag))
