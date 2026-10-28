from fractions import Fraction
from xml.etree import ElementTree as ET
import pytest
from test_phase4e_workflow import workflow,create,request,xml,event

BASE=b'<score-partwise><part-list><score-part id="P1"><part-name>Voice</part-name></score-part></part-list><part id="P1"><measure number="1"><attributes><divisions>48</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes><forward><duration>192</duration><voice>1</voice><staff>1</staff></forward></measure></part></score-partwise>'

@pytest.mark.parametrize('actual,normal',[(3,2),(2,3),(5,4),(6,4),(7,4),(9,8)])
def test_explicit_tuplet_ratios_pitch_correction_history_export(workflow,actual,normal):
 client,_=workflow;before=create(client,BASE)
 response=request(client,before,'triplets',{'measure_id':'m-1','voice':'1','staff':1,'base_duration':'1/4','actual_notes':actual,'normal_notes':normal,'onset':'0','pitches':[{'step':'C','alter':'0','octave':4}]*actual})
 assert response.status_code==200,response.text
 after=response.json();notes=ET.fromstring(xml(after)).findall('.//note');assert len(notes)==actual
 assert all(n.findtext('time-modification/actual-notes')==str(actual) and n.findtext('time-modification/normal-notes')==str(normal) for n in notes)
 ev=next(e for p in after['score']['parts'] for m in p['measures'] for v in m['voices'] for e in v['events'])
 changed=request(client,after,'events/'+ev['id'],{'pitch':{'step':'G','alter':'1','octave':5}},'PATCH');assert changed.status_code==200,changed.text
 result=changed.json();assert event(result,ev['id'])['duration']==str(Fraction(normal,actual*4))
 undo=request(client,result,'undo').json();assert xml(undo)==xml(after)
 reopened=create(client,xml(result));assert len(ET.fromstring(xml(reopened)).findall('.//time-modification'))==actual

def test_grace_slash_is_explicit_and_does_not_change_main_note_timing(workflow):
 client,_=workflow
 from test_duration_palette import source
 before=create(client,source());main=event(before,'e-1')
 response=request(client,before,'events',{'measure_id':'m-1','before_event_id':'e-1','voice':'1','staff':1,'kind':'note','pitch':{'step':'B','alter':'0','octave':3},'duration':'1/2','grace':True,'grace_slash':True})
 assert response.status_code==200,response.text
 after=response.json();assert ET.fromstring(xml(after)).find('.//grace').get('slash')=='yes'
 assert event(after,'e-1')['onset']==main['onset']
 assert event(after,'e-1')['duration']==main['duration']
