"""Single-note exact-interval replacement; no intermediate history or compensation."""
from fractions import Fraction
from xml.etree import ElementTree as ET
import pytest
from test_phase4e_workflow import workflow, create, request, xml, verify
from test_delete_preserve_timing import events


def note(step, octave, duration, kind='quarter', *, chord=False, voice='1', staff=1, extra=''):
    return f'<note>{"<chord/>" if chord else ""}<pitch><step>{step}</step><octave>{octave}</octave></pitch><duration>{duration}</duration><voice>{voice}</voice><type>{kind}</type><staff>{staff}</staff>{extra}</note>'


def source(divisions=6, extra_target='', second_voice=True):
    d=divisions
    first=note('F',4,d,extra=extra_target)+note('D',4,d)+note('E',4,d)+note('G',4,d,chord=True)
    first+=note('A',4,d,extra='<lyric number="1"><text>Ngài</text></lyric><lyric number="2"><text>yêu</text></lyric>')
    if second_voice:first+=f'<backup><duration>{4*d}</duration></backup>'+note('B',3,4*d,'whole',voice='2',staff=2)
    tied=note('C',5,2*d,'half',extra='<notations><tied type="start" orientation="over"/></notations>').replace('<voice>', '<tie type="start"/><voice>')
    tied+=note('C',5,d,extra='<notations><tied type="stop" orientation="over"/></notations>').replace('<voice>', '<tie type="stop"/><voice>')
    tied+=f'<note><rest/><duration>{d}</duration><voice>1</voice><type>quarter</type><staff>1</staff></note>'
    invalid=note('E',5,3*d,'half').replace('<staff>', '<dot/><staff>')+note('B',4,d)
    return (f'<score-partwise version="4.0"><work><work-title>Single-note replacement</work-title></work><part-list><score-part id="P"><part-name>Voice</part-name></score-part></part-list><part id="P"><measure number="1"><attributes><divisions>{d}</divisions><time><beats>4</beats><beat-type>4</beat-type></time><staves>{2 if second_voice else 1}</staves><clef><sign>G</sign><line>2</line></clef></attributes><direction><direction-type><words>Giữ nguyên</words></direction-type></direction>{first}</measure><measure number="2">{tied}</measure><measure number="3">{invalid}</measure></part></score-partwise>').encode()


def payload(pattern='equal',counts=(1,1)):
    values=[('C',5),('D',5),('E',5)] if pattern=='equal' else [('F',4),('A',4),('G',4),('C',5)][:sum(counts)]
    pitches=[dict(step=s,octave=o,alter='0') for s,o in values]
    return dict(pattern=pattern,member_counts=list(counts),pitches=pitches)


def post(client,before,suffix,body=None,target='e-1'):
    return request(client,before,f'events/{target}/{suffix}',body)


def unchanged(client,before):
    assert client.get(f'/api/v1/reviews/{before["id"]}').json()==before


@pytest.mark.parametrize('pattern,counts', [('equal',(1,1)),('quarter-eighth',(1,1)),('quarter-eighth',(2,2)),('quarter-eighth',(1,2)),('quarter-eighth',(2,1))])
def test_replace_exactly_preserves_survivors_local_structure_history_and_saved_xml(workflow,pattern,counts):
    client,_=workflow; before=create(client,source())
    options=post(client,before,'triplet-replacement/options').json()
    assert options['eligible'] is True and {p['id'] for p in options['patterns']}=={'equal','quarter-eighth'}
    assert options['original']['duration']=='1'
    body=payload(pattern,counts)
    checked=post(client,before,'triplet-replacement/preview',body)
    assert checked.status_code==200,checked.text
    assert checked.json()['fits_exactly'] is True;unchanged(client,before)
    response=post(client,before,'replace-triplet',body)
    assert response.status_code==200,response.text
    after=response.json(); assert after['revision']==before['revision']+1
    assert 'e-1' not in events(after)
    new=[e for key,e in events(after).items() if key not in events(before)]
    assert len(new)==len(body['pitches'])
    assert [e['pitch'] for e in new]==body['pitches']
    expected=[('0','1/3'),('1/3','1/3'),('2/3','1/3')] if pattern=='equal' else [('0','2/3')]*counts[0]+[('2/3','1/3')]*counts[1]
    assert [(e['onset'],e['duration']) for e in new]==expected
    assert sum((Fraction(e['duration']) for e in new if not e['chord_member']),Fraction(0))==1
    for key,event in events(before).items():
        if key!='e-1':
            assert {k:v for k,v in events(after)[key].items() if k!='tie_target_ids'}=={k:v for k,v in event.items() if k!='tie_target_ids'}
    assert after['score']['lyrics']==before['score']['lyrics']
    assert after['score']['texts']==before['score']['texts']
    old=ET.fromstring(xml(before)); newxml=ET.fromstring(xml(after))
    for tag in ['backup','forward']:assert len(newxml.findall('.//'+tag))==len(old.findall('.//'+tag))
    ns=newxml.findall('.//note');oldns=old.findall('.//note')
    assert [ET.tostring(n) for n in ns[len(new):]]==[ET.tostring(n) for n in oldns[1:]]
    assert [t.get('type') for n in ns for t in n.findall('notations/tuplet')]==['start','stop']
    assert len(newxml.findall('.//time-modification'))==len(new)
    undo=request(client,after,'undo').json(); assert xml(undo)==xml(before)
    assert undo['can_undo'] is False  # No separate deletion/insertion history entry.
    redo=request(client,undo,'redo').json(); assert xml(redo)==xml(after)
    saved=verify(client,redo)
    exported=client.get(f'/api/v1/reviews/{saved["id"]}/musicxml?verified_only=true')
    assert exported.status_code==200
    reopened=create(client,exported.content)
    assert [ET.tostring(n) for n in ET.fromstring(xml(reopened)).findall('.//note')]==[ET.tostring(n) for n in ET.fromstring(xml(saved)).findall('.//note')]
    assert [(e['pitch'],e['onset'],e['duration'],e['chord_member']) for e in events(reopened).values()]==[(e['pitch'],e['onset'],e['duration'],e['chord_member']) for e in events(saved).values()]


@pytest.mark.parametrize('extra', ['<lyric><text>Ngài</text></lyric>','<notations><slur type="start" number="1"/></notations>','<notations><articulations><accent/></articulations></notations>','<beam number="1">begin</beam>','<play><mute>on</mute></play>'])
def test_target_associations_are_rejected_without_discard_or_reassignment(workflow,extra):
    client,_=workflow;before=create(client,source(extra_target=extra))
    options=post(client,before,'triplet-replacement/options').json()
    assert options['eligible'] is False and 'associations' in options['explanation']
    checked=post(client,before,'triplet-replacement/preview',payload()).json()
    assert checked['valid'] is False
    assert post(client,before,'replace-triplet',payload()).status_code==422
    unchanged(client,before)


def test_chord_rest_tie_and_incompatible_interval_rejections(workflow):
    client,_=workflow;before=create(client,source(second_voice=False))
    targets={e['id']:e for e in events(before).values()}
    for target in ['e-3', 'e-4']:
        options=post(client,before,'triplet-replacement/options',target=target).json()
        assert options['eligible'] is True
        assert [m['id'] for m in options['original']['members']]==['e-3','e-4']
        # An old client cannot silently expand a single-note destructive command.
        assert post(client,before,'replace-triplet',payload(),target=target).status_code==422
        unchanged(client,before)
    for target,reason in [('e-5','associations'),('e-6','associations'),('e-7','associations'),('e-8','pitched'),('e-9','Rhythmic Range')]:
        options=post(client,before,'triplet-replacement/options',target=target).json()
        assert options['eligible'] is False,(target,targets.get(target),options)
        assert reason in options['explanation']
        assert post(client,before,'replace-triplet',payload(),target=target).status_code==422
        unchanged(client,before)


def test_invalid_pattern_pitches_and_stale_requests_are_atomic(workflow):
    client,_=workflow; before=create(client,source())
    for bad in [dict(pattern='5:4',pitches=payload()['pitches']),dict(pattern='equal',pitches=[]),dict(pattern='quarter-eighth',member_counts=[3,1],pitches=payload()['pitches']),dict(**payload(),onset='0')]:
        assert post(client,before,'replace-triplet',bad).status_code==422
        unchanged(client,before)
    result=post(client,before,'replace-triplet',payload()).json()
    assert post(client,before,'replace-triplet',payload()).status_code==409
    assert post(client,before,'triplet-replacement/preview',payload()).status_code==409
    assert post(client,before,'triplet-replacement/options').status_code==409
    assert xml(client.get(f'/api/v1/reviews/{before["id"]}').json())==xml(result)


def test_wrong_interval_and_existing_tuplet_are_rejected(workflow):
    client,_=workflow;before=create(client,source())
    # A half note fits equal quarter triplets, but not the fixed quarter/eighth group.
    # This note also has a tie, so use an unassociated half-note fixture instead.
    xmlbody=source().replace(b'<duration>6</duration>',b'<duration>12</duration>',1).replace(b'<type>quarter</type>',b'<type>half</type>',1)
    half=create(client,xmlbody)
    options=post(client,half,'triplet-replacement/options').json()
    assert [p['id'] for p in options['patterns']]==['equal']
    bad=payload('quarter-eighth')
    checked=post(client,half,'triplet-replacement/preview',bad).json()
    assert checked['valid'] is False and 'does not fit' in checked['explanation']
    assert post(client,half,'replace-triplet',bad).status_code==422;unchanged(client,half)
    converted=post(client,before,'replace-triplet',payload()).json()
    member=next(key for key in events(converted) if key not in events(before))
    options=post(client,converted,'triplet-replacement/options',target=member).json()
    assert options['eligible'] is False and 'tuplet' in options['explanation']
    unchanged(client,converted)


def test_refinement_preserves_all_voice_staff_onsets_without_committed_compensation(workflow):
    client,_=workflow;before=create(client,source(divisions=1))
    result=post(client,before,'replace-triplet',payload())
    assert result.status_code==200,result.text
    after=result.json()
    for key,old in events(before).items():
        if key=='e-1':continue
        for field in ('pitch','duration','onset','voice','staff','chord_id','chord_member','ties','lyric_ids'):
            assert events(after)[key][field]==old[field]
    old=ET.fromstring(xml(before));new=ET.fromstring(xml(after))
    assert len(old.findall('.//backup'))==len(new.findall('.//backup'))
    assert len(old.findall('.//forward'))==len(new.findall('.//forward'))==0


def test_failure_after_internal_deletion_does_not_commit_any_partial_replacement(workflow):
    client,_=workflow;before=create(client,source())
    bad=payload('quarter-eighth',(2,2));bad['pitches'][1]=bad['pitches'][0]
    preview=post(client,before,'triplet-replacement/preview',bad).json()
    assert preview['valid'] is False and 'unison' in preview['explanation']
    assert post(client,before,'replace-triplet',bad).status_code==422
    unchanged(client,before)


@pytest.mark.parametrize('prefix,reason', [('<grace/>','Grace'),('<cue/>','cue'),('id="source-note"','associations')])
def test_unsupported_original_semantics_or_external_identity_are_not_discarded(workflow,prefix,reason):
    client,_=workflow;data=source()
    data=data.replace(b'<note>',('<note '+prefix+'>' if prefix.startswith('id=') else '<note>'+prefix).encode(),1)
    before=create(client,data)
    result=post(client,before,'triplet-replacement/options').json()
    assert result['eligible'] is False and reason in result['explanation']
    assert post(client,before,'replace-triplet',payload()).status_code==422
    unchanged(client,before)


def test_enclosing_tuplet_without_interior_ratio_markup_is_not_guessed(workflow):
    client,_=workflow
    data=source(extra_target='<notations><tuplet type="start" number="1"/></notations>')
    before=create(client,data)
    result=post(client,before,'triplet-replacement/options',target='e-2').json()
    assert result['eligible'] is False and 'inside an existing tuplet' in result['explanation']
    assert post(client,before,'replace-triplet',payload(),target='e-2').status_code==422
    unchanged(client,before)
