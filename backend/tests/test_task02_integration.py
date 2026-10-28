"""Task02: real XML round trips, explicit slurs and independent written Sax outputs."""
import os
from pathlib import Path
from fractions import Fraction
from xml.etree import ElementTree as ET
import pytest
from app.core.config import Settings
from app.music.review.service import ReviewService
from app.music.review.storage import MemoryReviewStore
from app.music.review.document import ReviewError, Document
from app.music.review.models import SlurEdit, EventPatch, PitchInput, TextPatch, LyricAdd
from app.music.musicxml.instruments import instrument_score, INSTRUMENTS
from app.music.musicxml.concert_key import transpose_concert_key
from app.music.musicxml.transposer import MusicXMLTranspositionError
from test_review_api import setup_review

XML = '''<score-partwise version="4.0"><work><work-title>Pilot</work-title></work><identification><rights>Preserve rights</rights></identification><part-list><score-part id="P1"><part-name>Concert</part-name></score-part></part-list><part id="P1"><measure number="1"><attributes><divisions>6</divisions><key><fifths>-1</fifths><mode>major</mode></key><time><beats>2</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes><note><pitch><step>F</step><octave>4</octave></pitch><duration>6</duration><voice>1</voice><type>quarter</type><lyric number="1"><text>Niềm</text></lyric></note><note><pitch><step>G</step><octave>4</octave></pitch><duration>6</duration><voice>1</voice><type>quarter</type></note><backup><duration>12</duration></backup><note><pitch><step>C</step><octave>4</octave></pitch><duration>12</duration><voice>2</voice><type>half</type></note></measure><measure number="2"><note><pitch><step>G</step><octave>4</octave></pitch><duration>6</duration><voice>1</voice><type>quarter</type></note><note><rest/><duration>6</duration><voice>1</voice><type>quarter</type></note></measure></part></score-partwise>'''.encode('utf-8')


def service():
    c=Settings(); return ReviewService(MemoryReviewStore(c,lambda:1000),c,lambda:1000)


def midi(xml):
    d=Document.parse(xml);return [(int(d.text(p,'octave'))+1)*12+dict(C=0,D=2,E=4,F=5,G=7,A=9,B=11)[d.text(p,'step')]+Fraction(d.text(p,'alter','0')) for p in d.root.iter(d.namespace+'pitch')]


def test_slur_roundtrip_undo_direction_remove_and_unrelated_xml():
    s=service();r=s.create(XML)
    r=s.slur_edit(r['id'],r['revision'],SlurEdit(source_event_id='e-1',target_event_id='e-2'))
    assert len(r['slurs'])==1
    before=s.musicxml(r['id'])
    r=s.slur_edit(r['id'],r['revision'],SlurEdit(source_event_id='e-1',target_event_id='e-2',direction='down'))
    assert r['slurs'][0]['direction']=='down'
    duplicate=s.slur_edit(r['id'],r['revision'],SlurEdit(source_event_id='e-1',target_event_id='e-2'))
    assert duplicate['revision']==r['revision'] and duplicate['slurs'][0]['direction']=='down'
    reopened=s.create(s.musicxml(r['id']));assert reopened['slurs'][0]['direction']=='down'
    r=s.history(r['id'],r['revision'],'undo');assert s.musicxml(r['id'])==before
    r=s.history(r['id'],r['revision'],'redo');assert r['slurs'][0]['direction']=='down'
    r=s.slur_edit(r['id'],r['revision'],SlurEdit(source_event_id='e-1',target_event_id='e-2',remove=True))
    assert not r['slurs'];assert midi(s.musicxml(r['id']))==midi(XML)
    assert ET.fromstring(s.musicxml(r['id'])).findtext('.//rights')=='Preserve rights'


@pytest.mark.parametrize('target',['e-1','e-3','e-5'])
def test_invalid_slur_is_atomic(target):
    s=service();r=s.create(XML)
    with pytest.raises(ReviewError):s.slur_edit(r['id'],r['revision'],SlurEdit(source_event_id='e-1',target_event_id=target))
    assert s.musicxml(r['id'])==XML


def test_slur_delete_removes_both_ends_and_undo_restores():
    s=service();r=s.create(XML);r=s.slur_edit(r['id'],r['revision'],SlurEdit(source_event_id='e-1',target_event_id='e-4'))
    r=s.event_delete(r['id'],r['revision'],'e-1',True)
    assert not r['slurs'];assert not list(ET.fromstring(s.musicxml(r['id'])).iter('slur'))
    r=s.history(r['id'],r['revision'],'undo');assert len(r['slurs'])==1


@pytest.mark.parametrize('instrument',list(INSTRUMENTS))
def test_instrument_offsets_metadata_concert_identity_and_reopen(instrument):
    source=XML;written=instrument_score(source,instrument);offset,diatonic,chromatic,octave,name,program=INSTRUMENTS[instrument]
    assert midi(written)==[n+offset for n in midi(source)]
    tree=ET.fromstring(written);t=tree.find('.//transpose')
    assert int(t.findtext('diatonic'))==diatonic
    assert int(t.findtext('chromatic'))+12*int(t.findtext('octave-change','0'))==-offset
    assert tree.findtext('.//midi-program')==str(program)
    assert tree.findtext('.//part-name')==name
    assert tree.findtext('.//lyric/text')=='Niềm'
    assert tree.findtext('.//time/beats')=='2'
    assert service().create(written)['score']['parts'][0]['measures'][0]['voices']
    with pytest.raises(MusicXMLTranspositionError):instrument_score(written,instrument)
    assert source==XML


def test_concert_then_sax_does_not_double_apply_concert_interval():
    concert=transpose_concert_key(XML,1,'up',source_fifths=-1,source_mode='major')
    assert midi(concert)==[p+2 for p in midi(XML)]
    assert midi(instrument_score(concert,'tenor'))==[p+16 for p in midi(XML)]


def test_slur_api_revision_and_instrument_endpoint(setup_review):
    client,_,_=setup_review
    r=client.post('/api/v1/reviews',files={'musicxml':('test.musicxml',XML)}).json()
    body={'source_event_id':'e-1','target_event_id':'e-2'}
    assert client.post(f"/api/v1/reviews/{r['id']}/slurs",json=body).status_code==428
    response=client.post(f"/api/v1/reviews/{r['id']}/slurs",json=body,headers={'If-Match':str(r['revision'])})
    assert response.status_code==200 and len(response.json()['slurs'])==1
    assert client.post(f"/api/v1/reviews/{r['id']}/slurs",json=body,headers={'If-Match':str(r['revision'])}).status_code==409
    response=client.post('/api/v1/transpose/instrument',data={'instrument':'alto'},files={'file':('concert.musicxml',XML)})
    assert response.status_code==200 and midi(response.content)==[p+9 for p in midi(XML)]


def test_real_local_po_sample_roundtrip_and_three_saxes(tmp_path):
    path=os.environ.get('AI_SDF_TASK02_SAMPLE')
    if not path:pytest.skip('PO sample is local-only; set AI_SDF_TASK02_SAMPLE to exercise it')
    original=Path(path).read_bytes();s=service();r=s.create(original)
    assert s.musicxml(r['id'])==original
    assert len(r['score']['parts'])==1 and len(r['score']['parts'][0]['measures'])==17
    assert r['score']['parts'][0]['measures'][0]['time_signature'][0]['pairs']==[{'beats':'2','beat_type':'4'}]
    notes=[e for p in r['score']['parts'] for m in p['measures'] for v in m['voices'] for e in v['events']]
    assert len(notes)==63 and {e['voice'] for e in notes}=={'1','2'}
    first=next(e for e in notes if e['pitch']);old=first['pitch'];target={**old,'octave':old['octave']+1}
    r=s.event_patch(r['id'],r['revision'],first['id'],EventPatch(pitch=PitchInput(**target)))
    lyric=r['score']['lyrics'][0];r=s.lyric_patch(r['id'],r['revision'],lyric['id'],TextPatch(text='Niềm tin Unicode'))
    changed=s.musicxml(r['id']);saved=tmp_path/'concert.musicxml';saved.write_bytes(changed)
    reopened=s.create(saved.read_bytes());assert reopened['score']['lyrics'][0]['text']=='Niềm tin Unicode'
    before=ET.fromstring(original);after=ET.fromstring(changed)
    for tag in ['duration','voice','staff','tie','tied','chord','time','backup']:
        assert [ET.tostring(n) for n in before.iter(tag)]==[ET.tostring(n) for n in after.iter(tag)]
    concert=transpose_concert_key(changed,1,'up',source_fifths=-1,source_mode='major')
    for instrument,(offset,*_) in INSTRUMENTS.items():
        output=instrument_score(concert,instrument);assert midi(output)==[p+offset for p in midi(concert)]
        s.create(output)
    assert Path(path).read_bytes()==original


def test_reused_slur_lane_resolves_pairs_without_duplicate_and_preserves_neighbor():
    xml=XML.replace(b'<note><pitch><step>F',b'<note><notations><slur type="start" number="1"/></notations><pitch><step>F',1).replace(b'<note><pitch><step>G',b'<note><notations><slur type="stop" number="1"/></notations><pitch><step>G',1)
    xml=xml.replace(b'<measure number="2"><note>',b'<measure number="2"><note><notations><slur type="start" number="1"/></notations>').replace(b'<note><rest/>',b'<note><notations><slur type="stop" number="1"/></notations><rest/>')
    # Stop on a pitched note in this synthetic slur case.
    xml=xml.replace(b'<rest/>',b'<pitch><step>A</step><octave>4</octave></pitch>')
    s=service();r=s.create(xml);assert len(r['slurs'])==2
    r=s.slur_edit(r['id'],r['revision'],SlurEdit(source_event_id='e-1',target_event_id='e-2'))
    assert len(r['slurs'])==2 and len(list(ET.fromstring(s.musicxml(r['id'])).iter('slur')))==4
    r=s.slur_edit(r['id'],r['revision'],SlurEdit(source_event_id='e-1',target_event_id='e-2',remove=True))
    assert len(r['slurs'])==1 and r['slurs'][0]['source_event_id']=='e-4'


def test_instrument_harmony_and_explicit_display_and_note_instrument_refs():
    xml=XML.replace(b'<part-name>Concert</part-name>',b'<part-name>Concert</part-name><part-name-display><display-text>OLD CONCERT</display-text></part-name-display><part-abbreviation-display><display-text>OLD</display-text></part-abbreviation-display><score-instrument id="old"><instrument-name>Voice</instrument-name></score-instrument>')
    xml=xml.replace(b'<note><pitch><step>F',b'<harmony><root><root-step>F</root-step></root><kind>major</kind></harmony><note><instrument id="old"/><pitch><step>F',1)
    output=ET.fromstring(instrument_score(xml,'alto'))
    assert output.findtext('.//root-step')=='D'
    assert output.find('.//part-name-display') is None and output.find('.//part-abbreviation-display') is None
    assert output.find('.//note/instrument').get('id')==output.find('.//score-instrument').get('id')


def test_imported_slur_orientation_and_explicit_direction_remain_consistent():
    s=service();r=s.create(XML);r=s.slur_edit(r['id'],r['revision'],SlurEdit(source_event_id='e-1',target_event_id='e-2'))
    raw=s.musicxml(r['id']).replace(b'placement="above"',b'orientation="under"')
    r=s.create(raw);assert r['slurs'][0]['direction']=='down'
    r=s.slur_edit(r['id'],r['revision'],SlurEdit(source_event_id='e-1',target_event_id='e-2',direction='up'))
    for node in ET.fromstring(s.musicxml(r['id'])).iter('slur'):
        assert node.get('placement')=='above' and node.get('orientation')=='over'


@pytest.mark.parametrize('instrument',list(INSTRUMENTS))
def test_instrument_down_is_equivalent_key_lower_register_without_changing_concert(instrument):
    offset=INSTRUMENTS[instrument][0];up=instrument_score(XML,instrument);down=instrument_score(XML,instrument,'down')
    assert midi(down)==[p+{'alto':-3,'soprano':-10,'tenor':2}[instrument] for p in midi(XML)]
    assert ET.fromstring(up).findtext('.//key/fifths')==ET.fromstring(down).findtext('.//key/fifths')
    assert ET.tostring(ET.fromstring(up).find('.//transpose'))==ET.tostring(ET.fromstring(down).find('.//transpose'))
    assert XML.find(b'<transpose>')==-1


def test_preserved_triplet_keeps_ids_lyrics_manual_tie_slur_and_history():
    from app.music.review.models import TripletReplacement
    s=service();r=s.create(XML.replace(b'<note><pitch><step>F',b'<note id="original-note"><pitch><step>F',1))
    r=s.event_patch(r['id'],r['revision'],'e-1',EventPatch(tie_to_event_id='e-4'))
    r=s.slur_edit(r['id'],r['revision'],SlurEdit(source_event_id='e-1',target_event_id='e-2',direction='down'))
    before=s.musicxml(r['id']);original_lyrics=r['score']['lyrics'];before_events={e['id']:e for p in r['score']['parts'] for m in p['measures'] for v in m['voices'] for e in v['events']}
    body=TripletReplacement(preserve_associations=True,pattern='quarter-eighth',original_member_ids=['e-1'],member_counts=(1,1),pitches=[PitchInput(step='F',octave=4),PitchInput(step='F',octave=4)])
    preview=s.replacement_preview(r['id'],r['revision'],'e-1',body);assert preview['valid'] and s.musicxml(r['id'])==before
    r=s.triplet_replace(r['id'],r['revision'],'e-1',body)
    after_events={e['id']:e for p in r['score']['parts'] for m in p['measures'] for v in m['voices'] for e in v['events']}
    assert set(before_events)<=set(after_events) and after_events['e-1']['duration']=='2/3'
    assert after_events['e-1']['tie_target_id']=='e-4'
    assert r['score']['lyrics']==original_lyrics and r['slurs'][0]['source_event_id']=='e-1' and r['slurs'][0]['direction']=='down'
    for key in set(before_events)-{'e-1'}:
        assert (after_events[key]['onset'],after_events[key]['duration'],after_events[key]['pitch'])==(before_events[key]['onset'],before_events[key]['duration'],before_events[key]['pitch'])
    xml=s.musicxml(r['id']);assert ET.fromstring(xml).find('.//note').get('id')=='original-note'
    reopened=s.create(xml);assert reopened['score']['lyrics'][0]['text']=='Niềm' and len(reopened['slurs'])==1
    assert any(e.get('tie_target_id') for p in reopened['score']['parts'] for m in p['measures'] for v in m['voices'] for e in v['events'])
    r=s.history(r['id'],r['revision'],'undo');assert s.musicxml(r['id'])==before
    r=s.history(r['id'],r['revision'],'redo');assert s.musicxml(r['id'])==xml


def test_preserved_triplet_rejects_implicit_first_pitch_reassignment_atomically():
    from app.music.review.models import TripletReplacement
    s=service();r=s.create(XML)
    body=TripletReplacement(preserve_associations=True,pattern='quarter-eighth',original_member_ids=['e-1'],pitches=[PitchInput(step='A',octave=4),PitchInput(step='F',octave=4)])
    with pytest.raises(ReviewError):s.triplet_replace(r['id'],r['revision'],'e-1',body)
    assert s.musicxml(r['id'])==XML


def test_po_sample_preserving_quarter_keeps_all_original_ids_and_54_lyrics():
    from app.music.review.models import TripletReplacement
    path=os.environ.get('AI_SDF_TASK02_SAMPLE')
    if not path:pytest.skip('Private local sample only')
    raw=Path(path).read_bytes();s=service();r=s.create(raw)
    original={e['id']:e for p in r['score']['parts'] for m in p['measures'] for v in m['voices'] for e in v['events']}
    target=next(e for e in original.values() if e['duration']=='1' and e['lyric_ids'] and e['kind']=='note' and not e['grace'])
    members=[e for e in original.values() if e['chord_id']==target['chord_id']] if target['chord_id'] else [target]
    lyrics=r['score']['lyrics']
    body=TripletReplacement(preserve_associations=True,pattern='quarter-eighth',original_member_ids=[e['id'] for e in members],member_counts=(len(members),1),pitches=[PitchInput(**e['pitch']) for e in members]+[PitchInput(**members[0]['pitch'])])
    r=s.triplet_replace(r['id'],r['revision'],target['id'],body)
    actual={e['id']:e for p in r['score']['parts'] for m in p['measures'] for v in m['voices'] for e in v['events']}
    assert set(original)<set(actual) and len(actual)==64
    assert r['score']['lyrics']==lyrics and len(lyrics)==54
    assert all(actual[e['id']]['duration']=='2/3' for e in members)
    assert Path(path).read_bytes()==raw


def test_instrument_down_refuses_out_of_range_pitch_without_mutation():
    xml=XML.replace(b'<step>F</step><octave>4',b'<step>C</step><octave>0',1)
    with pytest.raises(MusicXMLTranspositionError,match='octave range'):instrument_score(xml,'alto','down')
    assert b'<step>C</step><octave>0' in xml


def test_tenor_lower_written_register_matches_soprano_but_keeps_tenor_sound_identity():
    source=XML.replace(b'<note><pitch><step>F', b'<harmony><root><root-step>F</root-step></root><kind>major</kind><bass><bass-step>C</bass-step></bass></harmony><note id="keep-note"><pitch><step>F',1)
    soprano=instrument_score(source,'soprano','up')
    tenor=instrument_score(source,'tenor','down')
    standard=instrument_score(source,'tenor','up')
    assert midi(tenor)==midi(soprano)==[p+2 for p in midi(source)]
    assert midi(standard)==[p+12 for p in midi(tenor)]
    st,tt=ET.fromstring(soprano),ET.fromstring(tenor)
    for tag in ['pitch','key','harmony','duration','voice','staff','lyric','time','backup']:
        assert [ET.tostring(n) for n in tt.iter(tag)]==[ET.tostring(n) for n in st.iter(tag)]
    assert tt.findtext('.//part-name')=='Tenor Saxophone'
    assert tt.findtext('.//midi-program')=='67'
    assert tt.findtext('.//transpose/chromatic')=='-2'
    assert tt.findtext('.//transpose/octave-change')=='-1'
    assert st.find('.//transpose/octave-change') is None
    assert tt.find('.//note').get('id')=='keep-note'
    # Same written pitches, but the real Tenor sounds an octave below Concert.
    assert [p-14 for p in midi(tenor)]==[p-12 for p in midi(source)]
    assert b'<transpose>' not in source
    reopened=service().create(tenor)
    assert reopened['score']['parts'][0]['name']=='Tenor Saxophone'


def test_tenor_down_endpoint_is_major_second_written_with_major_ninth_metadata(setup_review):
    client,_,_=setup_review
    response=client.post('/api/v1/transpose/instrument',data={'instrument':'tenor','direction':'down'},files={'file':('concert.musicxml',XML)})
    assert response.status_code==200
    assert midi(response.content)==[p+2 for p in midi(XML)]
    assert ET.fromstring(response.content).findtext('.//transpose/octave-change')=='-1'


def test_po_sample_tenor_readable_register_preserves_every_lyric_tie_and_note_identity():
    path=os.environ.get('AI_SDF_TASK02_SAMPLE')
    if not path:pytest.skip('Private local sample only')
    raw=Path(path).read_bytes();tenor=instrument_score(raw,'tenor','down');soprano=instrument_score(raw,'soprano','up')
    assert midi(tenor)==midi(soprano)==[p+2 for p in midi(raw)]
    before,after=ET.fromstring(raw),ET.fromstring(tenor)
    for tag in ['duration','voice','staff','tie','tied','slur','lyric','time','backup','forward','time-modification']:
        assert [ET.tostring(n) for n in before.iter(tag)]==[ET.tostring(n) for n in after.iter(tag)]
    assert [n.get('id') for n in before.iter('note')]==[n.get('id') for n in after.iter('note')]
    assert Path(path).read_bytes()==raw


@pytest.mark.parametrize('instrument,direction,offset,fifths',[('alto','up',9,3),('alto','down',-3,3),('soprano','up',2,2),('tenor','down',2,2)])
def test_missing_initial_key_requires_user_declaration_before_sax(instrument,direction,offset,fifths):
    initial=b'<key><fifths>-1</fifths><mode>major</mode></key>'
    original=XML.replace(initial,b'')
    with pytest.raises(MusicXMLTranspositionError,match='Confirm the original Concert key'):
        instrument_score(original,instrument,direction)
    saved=original.replace(b'<divisions>6</divisions>',b'<divisions>6</divisions><key><fifths>0</fifths><mode>minor</mode></key>',1)
    output=instrument_score(saved,instrument,direction)
    root=ET.fromstring(output)
    assert root.findtext('.//measure/attributes/key/fifths')==str(fifths)
    assert root.findtext('.//measure/attributes/key/mode')=='minor'
    assert midi(output)==[pitch+offset for pitch in midi(saved)]
    assert ET.fromstring(original).find('.//key') is None


@pytest.mark.parametrize('direction,shift,octave',[('up',9,5),('down',-3,4)])
def test_alto_a_major_section_is_f_sharp_major_with_matching_note_spellings(direction,shift,octave):
    original=XML.replace(b'<fifths>-1</fifths>',b'<fifths>3</fifths>').replace(b'<step>F</step>',b'<step>A</step>').replace(b'<step>G</step>',b'<step>C</step><alter>1</alter>')
    output=instrument_score(original,'alto',direction)
    root=ET.fromstring(output)
    assert root.findtext('.//key/fifths')=='6'
    assert root.findtext('.//key/mode')=='major'
    notes=root.findall('.//note/pitch')
    assert (notes[0].findtext('step'),notes[0].findtext('alter'),notes[0].findtext('octave'))==('F','1',str(octave))
    assert (notes[1].findtext('step'),notes[1].findtext('alter'))==('A','1')
    assert midi(output)==[value+shift for value in midi(original)]
