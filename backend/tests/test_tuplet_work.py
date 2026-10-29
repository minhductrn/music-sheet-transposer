from xml.etree import ElementTree as ET
from fractions import Fraction
import pytest
from test_phase4e_workflow import workflow,create,request,xml,event


def source(rest=False,mixed=False):
    first='<rest/>' if rest else '<pitch><step>C</step><octave>4</octave></pitch>'
    middle='<note><rest/><duration>2</duration><voice>1</voice><type>eighth</type></note>' if mixed else ''
    return ('<score-partwise><part-list><score-part id="P1"><part-name>Voice</part-name></score-part></part-list><part id="P1"><measure number="1"><attributes><divisions>4</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes><note>'+first+'<duration>4</duration><voice>1</voice><type>quarter</type><lyric number="1"><text>Keep</text></lyric></note>'+middle+'<forward><duration>8</duration></forward><note><pitch><step>G</step><octave>4</octave></pitch><duration>4</duration><voice>1</voice><type>quarter</type></note></measure></part></score-partwise>').encode()


def events(value):return [e for p in value['score']['parts'] for m in p['measures'] for v in m['voices'] for e in v['events']]


@pytest.mark.parametrize('actual,normal',[(3,2),(2,3),(4,3),(5,4),(6,4),(7,4),(8,6),(9,8)])
def test_supported_ratios_preserve_outside_and_history(workflow,actual,normal):
    client,_=workflow
    original=source().replace(b'</note><forward>',b'</note>'+b'<note><rest/><duration>4</duration><voice>1</voice><type>quarter</type></note>'*(actual-1)+b'<forward>',1)
    before=create(client,original);outside=event(before,'e-'+str(actual+1))
    ids=['e-'+str(i+1) for i in range(actual)]
    response=request(client,before,'tuplets',{'event_ids':ids,'actual_notes':actual,'normal_notes':normal,'show_number':'both','placement':'below','bracket':'no'})
    assert response.status_code==200,response.text
    after=response.json();assert event(after,'e-'+str(actual+1))['onset']==outside['onset']
    assert Fraction(event(after,'e-1')['duration'])==Fraction(normal,actual)
    assert Fraction(event(after,'e-2')['duration'])==Fraction(normal,actual)
    root=ET.fromstring(xml(after));mark=root.find('.//tuplet');assert mark.attrib['placement']=='below' and mark.attrib['bracket']=='no' and mark.attrib['show-number']=='both'
    assert root.findtext('.//lyric/text')=='Keep'
    reopened=create(client,xml(after));assert len(ET.fromstring(xml(reopened)).findall('.//time-modification'))==actual
    undo=request(client,after,'undo').json();assert xml(undo)==xml(before)
    redo=request(client,undo,'redo').json();assert xml(redo)==xml(after)


@pytest.mark.parametrize('rest',[False,True])
def test_split_single_duration_then_edit_complete_group_and_remove(workflow,rest):
    client,_=workflow;before=create(client,source(rest=rest))
    response=request(client,before,'tuplets',{'event_ids':['e-1'],'action':'split','actual_notes':3,'normal_notes':2})
    assert response.status_code==200,response.text
    after=response.json();members=[e for e in events(after) if Fraction(e['onset'])<1]
    assert len(members)==3 and all(Fraction(e['duration'])==Fraction(1,3) for e in members)
    assert all(e['kind']==('rest' if rest else 'note') for e in members)
    ids=[e['id'] for e in members]
    updated=request(client,after,'tuplets',{'event_ids':ids,'actual_notes':6,'normal_notes':4})
    assert updated.status_code==200,updated.text
    removed=request(client,updated.json(),'tuplets',{'event_ids':ids,'action':'remove'})
    assert removed.status_code==200,removed.text
    assert not ET.fromstring(xml(removed.json())).findall('.//time-modification')
    assert Fraction(event(removed.json(),'e-2')['onset'])==3


def test_partial_tuplet_is_rejected_without_changing_revision(workflow):
    client,_=workflow;before=create(client,source())
    after=request(client,before,'tuplets',{'event_ids':['e-1'],'action':'split'}).json()
    failed=request(client,after,'tuplets',{'event_ids':['e-1'],'action':'remove'})
    assert failed.status_code==422,failed.text
    assert request(client,after,'undo').status_code==200


def test_full_measure_rest_can_be_divided(workflow):
    client,_=workflow
    original=source(rest=True).replace(b'<rest/>',b'<rest measure="yes"/>',1).replace(b'<type>quarter</type>',b'',1)
    before=create(client,original)
    response=request(client,before,'tuplets',{'event_ids':['e-1'],'action':'split'})
    assert response.status_code==200,response.text
    rests=ET.fromstring(xml(response.json())).findall('.//rest')
    assert len(rests)==3 and all('measure' not in n.attrib for n in rests)


def test_chord_split_preserves_original_ids_lyrics_and_distinct_pitches(workflow):
    client,_=workflow
    chord=b'<note><chord/><pitch><step>E</step><octave>4</octave></pitch><duration>4</duration><voice>1</voice><type>quarter</type></note>'
    original=source().replace(b'</note><forward>',b'</note>'+chord+b'<forward>',1)
    before=create(client,original)
    response=request(client,before,'tuplets',{'event_ids':['e-1','e-2'],'action':'split','actual_notes':4,'normal_notes':3})
    # A quarter span / 3 requires an unsupported written value; fail atomically.
    assert response.status_code==422
    response=request(client,before,'tuplets',{'event_ids':['e-1','e-2'],'action':'split'})
    assert response.status_code==200,response.text
    after=response.json();assert event(after,'e-1')['pitch']['step']=='C' and event(after,'e-2')['pitch']['step']=='E'
    root=ET.fromstring(xml(after));assert len(root.findall('.//chord'))==3 and len(root.findall('.//lyric'))==1


def test_ratio_expansion_cannot_overlap_unselected_notes(workflow):
    client,_=workflow
    before=create(client,source(mixed=True).replace(b'<forward><duration>8</duration></forward>',b''))
    failed=request(client,before,'tuplets',{'event_ids':['e-1','e-2'],'actual_notes':2,'normal_notes':3})
    assert failed.status_code==422
    assert 'overlap' in failed.json()['detail'].lower()


def test_mixed_triplet_uses_explicit_base_unit_and_keeps_pitch_editable(workflow):
    client,_=workflow;before=create(client,source(mixed=True))
    after=request(client,before,'tuplets',{'event_ids':['e-1','e-2']}).json()
    root=ET.fromstring(xml(after));assert [n.text for n in root.findall('.//normal-type')]==['eighth','eighth']
    changed=request(client,after,'events/e-1',{'pitch':{'step':'D','alter':'1','octave':5}},'PATCH')
    assert changed.status_code==200,changed.text
    assert event(changed.json(),'e-1')['duration']=='2/3'


def test_ratio_without_representable_written_unit_is_rejected(workflow):
    client,_=workflow;before=create(client,source(mixed=True))
    response=request(client,before,'tuplets',{'event_ids':['e-1','e-2'],'actual_notes':5,'normal_notes':4})
    assert response.status_code==422 and 'units' in response.json()['detail']


@pytest.mark.parametrize('actual,normal',[(3,2),(2,3),(4,3),(5,4),(6,4),(7,4),(8,6),(9,8)])
def test_split_all_ratios_preserves_total_span_and_pitch_editability(workflow,actual,normal):
    client,_=workflow
    root=ET.fromstring(source());first=root.find('.//note')
    first.find('duration').text=str(normal*2)
    first.find('type').text={2:'quarter',3:'quarter',4:'half',6:'half',8:'whole'}[normal]
    if normal in (3,6): ET.SubElement(first,'dot')
    before=create(client,ET.tostring(root));span=Fraction(normal,2)
    response=request(client,before,'tuplets',{'event_ids':['e-1'],'action':'split','actual_notes':actual,'normal_notes':normal})
    assert response.status_code==200,response.text
    after=response.json();members=[e for e in events(after) if Fraction(e['onset'])<span]
    assert len(members)==actual
    assert sum((Fraction(e['duration']) for e in members),Fraction(0))==span
    assert all(Fraction(e['duration'])==span/actual for e in members)
    last=members[-1]['id'];changed=request(client,after,'events/'+last,{'pitch':{'step':'D','alter':'1','octave':5}},'PATCH')
    assert changed.status_code==200,changed.text
    assert event(changed.json(),last)['duration']==members[-1]['duration']
    assert len(ET.fromstring(xml(changed.json())).findall('.//time-modification'))==actual
