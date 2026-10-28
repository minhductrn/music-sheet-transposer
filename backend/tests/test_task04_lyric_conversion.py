from xml.etree import ElementTree as ET
import pytest
from test_phase4e_workflow import workflow,create,request,xml

SOURCE=b'<score-partwise><part-list><score-part id="P1"><part-name>Voice</part-name></score-part></part-list><part id="P1"><measure number="1"><attributes><divisions>4</divisions><key><fifths>0</fifths></key><time><beats>2</beats><beat-type>4</beat-type></time></attributes><direction><direction-type><words>old OCR text</words><dynamics><mf/></dynamics></direction-type></direction><note><pitch><step>F</step><alter>1</alter><octave>4</octave></pitch><duration>4</duration><voice>1</voice><type>quarter</type><accidental>sharp</accidental></note><note><pitch><step>C</step><alter>0</alter><octave>5</octave></pitch><duration>4</duration><voice>2</voice><type>quarter</type><accidental>natural</accidental></note></measure><measure number="2"><attributes><key><fifths>3</fifths></key></attributes></measure></part></score-partwise>'

def unchanged_notes(data):
 root=ET.fromstring(xml(data));return [(ET.tostring(n.find('pitch')),ET.tostring(n.find('accidental')),n.findtext('duration'),n.findtext('voice')) for n in root.findall('.//note')]

def test_confirmed_text_mapping_preserves_pitch_accidentals_voices_keys_and_roundtrip(workflow):
 client,_=workflow;before=create(client,SOURCE)
 after=request(client,before,'texts/w-1/to-lyrics',{'mappings':[{'event_id':'e-1','number':'1','text':'Tiến'},{'event_id':'e-2','number':'2','text':'bước'}],'remove_source':True})
 assert after.status_code==200,after.text
 after=after.json();assert unchanged_notes(after)==unchanged_notes(before)
 root=ET.fromstring(xml(after));assert [n.text for n in root.findall('.//fifths')]==['0','3'];assert root.find('.//words') is None;assert root.find('.//dynamics/mf') is not None
 assert [(l['event_id'],l['number'],l['text']) for l in after['score']['lyrics']]==[('e-1','1','Tiến'),('e-2','2','bước')]
 undo=request(client,after,'undo').json();assert xml(undo)==xml(before)
 redo=request(client,undo,'redo').json();assert xml(redo)==xml(after)
 reopened=create(client,xml(redo));assert [(l['number'],l['text']) for l in reopened['score']['lyrics']]==[('1','Tiến'),('2','bước')]

@pytest.mark.parametrize('mappings',[[{'event_id':'e-1','number':'1','text':'A'},{'event_id':'e-1','number':'1','text':'B'}],[{'event_id':'does-not-exist','number':'1','text':'A'}]])
def test_invalid_mapping_is_atomic(workflow,mappings):
 client,_=workflow;before=create(client,SOURCE);response=request(client,before,'texts/w-1/to-lyrics',{'mappings':mappings,'remove_source':True});assert response.status_code in (404,422)
 current=client.get('/api/v1/reviews/'+before['id']).json();assert current['revision']==before['revision'];assert xml(current)==xml(before)


def test_missing_dot_repairs_e7_two_beat_measure_for_single_note_and_chord(workflow):
 client,_=workflow
 for chord in (False,True):
  head='<note><pitch><step>B</step><octave>4</octave></pitch><duration>4</duration><voice>1</voice><type>quarter</type></note>'
  member='<note><chord/><pitch><step>D</step><octave>5</octave></pitch><duration>4</duration><voice>1</voice><type>quarter</type></note>' if chord else ''
  tail='<note><pitch><step>B</step><octave>4</octave></pitch><duration>2</duration><voice>1</voice><type>eighth</type></note>'
  body=SOURCE.decode();a=body.index('<direction>');b=body.index('</measure>',a);body=body[:a]+head+member+tail+body[b:]
  before=create(client,body.encode());after=request(client,before,'events/e-1',{'duration':'3/2','preserve_onsets':False},'PATCH')
  assert after.status_code==200,after.text
  after=after.json();measure=after['score']['parts'][0]['measures'][0];events=[e for v in measure['voices'] for e in v['events']]
  assert measure['actual_duration']=='2'
  assert events[0]['duration']=='3/2' and events[0]['notated_duration']['dots']==1
  if chord:assert events[1]['duration']=='3/2' and events[1]['notated_duration']['dots']==1
  assert events[-1]['onset']=='3/2' and events[-1]['duration']=='1/2'
  assert [e['pitch'] for e in events]==[e['pitch'] for v in before['score']['parts'][0]['measures'][0]['voices'] for e in v['events']]
  undo=request(client,after,'undo').json();assert xml(undo)==xml(before)


def test_pedal_harmony_add_move_delete_leave_notes_and_source_words_unchanged(workflow):
 client,_=workflow
 source=SOURCE.replace(b'<words>old OCR text</words>',b'<words>old OCR text</words><pedal type="start" line="no"/>')
 before=create(client,source);marks=[m for m in before['score']['omr_marks'] if m['kind']=='pedal'];assert len(marks)==1
 removed=request(client,before,'marks/'+marks[0]['id'],None,'DELETE');assert removed.status_code==200,removed.text
 after=removed.json();assert unchanged_notes(after)==unchanged_notes(before);assert ET.fromstring(xml(after)).find('.//words').text=='old OCR text';assert ET.fromstring(xml(after)).find('.//pedal') is None
 after=request(client,after,'harmonies',{'measure_id':'m-1','before_event_id':'e-1','root_step':'B','root_alter':'0','kind':'diminished','text':'m(b5)'}).json()
 harmony=after['score']['harmonies'][0];assert harmony['root_step']=='B' and harmony['text']=='m(b5)'
 after=request(client,after,'harmonies/'+harmony['id']+'/move',{'measure_id':'m-1','before_event_id':'e-2'}).json()
 assert after['score']['harmonies'][0]['onset']=='1'
 after=request(client,after,'harmonies/'+harmony['id'],None,'DELETE').json();assert after['score']['harmonies']==[];assert unchanged_notes(after)==unchanged_notes(before)
 restored=request(client,after,'undo').json();assert restored['score']['harmonies'][0]['text']=='m(b5)'


def test_old_pedal_selection_cannot_delete_a_mark_after_an_unrelated_edit(workflow):
 client,_=workflow;source=SOURCE.replace(b'<words>old OCR text</words>',b'<words>old OCR text</words><pedal type="start"/>');before=create(client,source);old=before['score']['omr_marks'][0]['id']
 after=request(client,before,'texts/w-1',{'text':'explicit edit'},'PATCH').json()
 response=request(client,after,'marks/'+old,None,'DELETE');assert response.status_code==409
 current=client.get('/api/v1/reviews/'+before['id']).json();assert xml(current)==xml(after) and len([m for m in current['score']['omr_marks'] if m['kind']=='pedal'])==1


def test_delete_selection_atomic_undo_and_unselected_timing(workflow):
 client,_=workflow;before=create(client,SOURCE)
 response=request(client,before,'events/delete-selection',{'event_ids':['e-1','e-2']})
 assert response.status_code==200,response.text
 after=response.json();assert not ET.fromstring(xml(after)).findall('.//note')
 restored=request(client,after,'undo').json();assert unchanged_notes(restored)==unchanged_notes(before)
 invalid=request(client,restored,'events/delete-selection',{'event_ids':['e-1','missing']})
 assert invalid.status_code!=200
 current=client.get('/api/v1/reviews/'+before['id']).json();assert unchanged_notes(current)==unchanged_notes(before)


def test_user_can_delete_false_dynamic_without_removing_shared_words(workflow):
 client,_=workflow;before=create(client,SOURCE)
 mark=next(m for m in before['score']['omr_marks'] if m['kind']=='dynamics')
 after=request(client,before,'marks/'+mark['id'],method='DELETE');assert after.status_code==200,after.text
 after=after.json();root=ET.fromstring(xml(after));assert root.find('.//dynamics') is None
 assert root.findtext('.//words')=='old OCR text';assert unchanged_notes(after)==unchanged_notes(before)
 restored=request(client,after,'undo').json();assert ET.fromstring(xml(restored)).find('.//dynamics/mf') is not None


def test_composer_printed_credit_edit_syncs_exact_pair_and_undo(workflow):
 client,_=workflow
 source=SOURCE.replace(b'<part-list>', '<identification><creator type="composer">Héi Nguyén</creator></identification><credit><credit-type>composer</credit-type><credit-words>Héi Nguyén</credit-words></credit><part-list>'.encode())
 before=create(client,source);credit=next(x for x in before['score']['texts'] if x['role']=='printed_composer')
 response=request(client,before,'texts/'+credit['id'],{'text':'Hải Nguyễn'},'PATCH');assert response.status_code==200,response.text
 after=response.json();root=ET.fromstring(xml(after));assert root.findtext('.//creator')==root.findtext('.//credit-words')=='Hải Nguyễn';assert unchanged_notes(after)==unchanged_notes(before)
 assert xml(request(client,after,'undo').json())==source


def test_title_metadata_and_single_printed_credit_edit_and_undo(workflow):
 client,_=workflow
 source=SOURCE.replace(b'<part-list>', '<movement-title>Tiến Bước Véo Nhé Chlia</movement-title><credit><credit-words>Tiến Bước Véo Nhé Chlia</credit-words></credit><part-list>'.encode())
 before=create(client,source);credit=next(x for x in before['score']['texts'] if x['role']=='credit')
 response=request(client,before,'texts/'+credit['id'],{'text':'Tiến Bước Vào Nhà Chúa'},'PATCH');assert response.status_code==200,response.text
 after=response.json();root=ET.fromstring(xml(after));assert root.findtext('movement-title')==root.findtext('.//credit-words')=='Tiến Bước Vào Nhà Chúa';assert unchanged_notes(after)==unchanged_notes(before)
 assert xml(request(client,after,'undo').json())==source


def test_delete_false_pedal_preserves_independent_sound_and_undo(workflow):
 client,_=workflow;source=SOURCE.replace(b'<words>old OCR text</words><dynamics><mf/></dynamics>',b'<pedal type="start"/>').replace(b'</direction-type></direction>',b'</direction-type><sound tempo="96" dynamics="70"/></direction>');before=create(client,source)
 mark=next(m for m in before['score']['omr_marks'] if m['kind']=='pedal');response=request(client,before,'marks/'+mark['id'],method='DELETE');assert response.status_code==200,response.text
 after=response.json();root=ET.fromstring(xml(after));assert root.find('.//pedal') is None;assert root.find('.//sound').attrib=={'tempo':'96','dynamics':'70'};assert root.find('.//direction-type/words') is not None and not root.findtext('.//direction-type/words');assert unchanged_notes(after)==unchanged_notes(before)
 assert xml(request(client,after,'undo').json())==source


def test_user_places_harmony_without_note_and_edits_moves_it(workflow):
 client,_=workflow;before=create(client,SOURCE)
 response=request(client,before,'harmonies',{'measure_id':'m-2','onset':'1/3','root_step':'G','kind':'major'});assert response.status_code==200,response.text
 after=response.json();h=after['score']['harmonies'][0];assert h['root_step']=='G' and h['onset']=='1/3'
 response=request(client,after,'harmonies/'+h['id'],{'root_step':'E','kind':'minor','text':'m'},'PATCH');assert response.status_code==200,response.text
 response=request(client,response.json(),'harmonies/'+h['id']+'/move',{'measure_id':'m-1','onset':'1/2'});assert response.status_code==200,response.text
 moved=response.json();assert moved['score']['harmonies'][0]['onset']=='1/2'
 def musical_events(data):return [(e['id'],e['pitch'],e['onset'],e['duration'],e['voice'],e['staff']) for p in data['score']['parts'] for m in p['measures'] for v in m['voices'] for e in v['events']]
 assert musical_events(moved)==musical_events(before)


def test_delete_text_keeps_independent_sound(workflow):
 client,_=workflow;source=SOURCE.replace(b'<dynamics><mf/></dynamics>',b'').replace(b'</direction-type></direction>',b'</direction-type><sound tempo="96"/></direction>');before=create(client,source)
 response=request(client,before,'texts/w-1',method='DELETE');assert response.status_code==200,response.text
 after=response.json();assert b'old OCR text' not in xml(after);assert ET.fromstring(xml(after)).find('.//sound').get('tempo')=='96';assert unchanged_notes(after)==unchanged_notes(before)
 assert xml(request(client,after,'undo').json())==source


def test_delete_pedal_removes_its_playback_flag_but_keeps_tempo(workflow):
 client,_=workflow;source=SOURCE.replace(b'<words>old OCR text</words><dynamics><mf/></dynamics>',b'<pedal type="start"/>').replace(b'</direction-type></direction>',b'</direction-type><sound damper-pedal="yes" tempo="96"/></direction>');before=create(client,source);mark=next(m for m in before['score']['omr_marks'] if m['kind']=='pedal');after=request(client,before,'marks/'+mark['id'],method='DELETE').json();root=ET.fromstring(xml(after));assert root.find('.//pedal') is None;assert root.find('.//sound').attrib=={'tempo':'96'};assert unchanged_notes(after)==unchanged_notes(before);assert xml(request(client,after,'undo').json())==source
