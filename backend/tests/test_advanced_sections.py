from copy import deepcopy
from xml.etree import ElementTree as ET
from test_phase4e_workflow import workflow, create, request, xml, event
from test_measure_accidental_scope import tied_fixture
from pathlib import Path

def body(start="m-1",end="m-2",**extra):
    return dict(start_measure_id=start,end_measure_id=end,source_fifths=-1,target_fifths=0,mode="major",semitones=7,**extra)

def test_preview_append_atomic_history_and_roundtrip(workflow):
    client,_=workflow
    original=Path("../frontend-v2/tests/fixtures/task02.musicxml").read_bytes()
    before=create(client,original)
    preview=request(client,before,"sections/preview",body())
    assert preview.status_code==200,preview.text
    assert preview.json()["section"]["count"]==2
    assert client.get("/api/v1/reviews/"+before["id"]).json()["revision"]==before["revision"]
    after=request(client,before,"sections/append",body())
    assert after.status_code==200,after.text
    after=after.json()
    a=ET.fromstring(xml(after));b=ET.fromstring(original)
    for old,new in zip(b.findall(".//part/measure"),a.findall(".//part/measure")):
        assert ET.tostring(old)==ET.tostring(new)
    assert len(a.findall(".//part/measure"))==5
    assert a.findall(".//part/measure")[3].findtext("attributes/key/fifths")=="0"
    assert a.findall(".//part/measure")[3].findtext("barline/bar-style")=="light-light"
    oldpitch=event(before,"e-1")["pitch"]
    copied=after["score"]["parts"][0]["measures"][3]["voices"][0]["events"][0]
    assert copied["pitch"]!=oldpitch
    imported=create(client,xml(after));assert len(imported["score"]["parts"][0]["measures"])==5
    undo=request(client,after,"undo").json();assert xml(undo)==xml(before)
    assert xml(request(client,undo,"redo").json())==xml(after)
    assert request(client,before,"sections/append",body()).status_code==409

def test_tie_boundary_and_full_chain_copy(workflow):
    client,_=workflow
    before=create(client,tied_fixture())
    bad=body("m-1","m-1");bad.update(source_fifths=0,target_fifths=2,semitones=2)
    response=request(client,before,"sections/append",bad)
    assert response.status_code==422,response.text
    good={**bad,"end_measure_id":"m-3"}
    response=request(client,before,"sections/append",good)
    assert response.status_code==200,response.text
    after=response.json();assert len(after["score"]["parts"][0]["measures"])==6
    reopened=create(client,xml(after))
    copied=reopened["score"]["parts"][0]["measures"][3]["voices"][0]["events"][0]
    assert copied["tie_target_id"]
    assert copied["pitch"]["step"]=="C"

def test_chords_source_override_and_half_tone(workflow):
    client,_=workflow
    raw=b'<score-partwise version="4.0"><part-list><score-part id="P1"><part-name>Test</part-name></score-part></part-list><part id="P1"><measure number="1"><attributes><divisions>1</divisions><key><fifths>0</fifths><mode>minor</mode></key><time><beats>1</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes><harmony><root><root-step>A</root-step></root><kind>minor</kind><bass><bass-step>E</bass-step></bass></harmony><note><pitch><step>A</step><octave>4</octave></pitch><duration>1</duration><type>quarter</type><lyric number="2"><text>Love</text></lyric></note></measure></part></score-partwise>'
    before=create(client,raw);b=body("m-1","m-1");b.update(source_fifths=0,target_fifths=-5,mode="minor",semitones=1)
    response=request(client,before,"sections/append",b);assert response.status_code==200,response.text
    m=ET.fromstring(xml(response.json())).findall(".//part/measure")[1]
    assert m.findtext("harmony/root/root-step")=="B"
    assert m.findtext("harmony/root/root-alter")=="-1"
    assert m.findtext("note/pitch/alter")=="-1"
    assert m.findtext("note/lyric/text")=="Love"

def test_instrument_written_section_preserves_transpose_metadata(workflow):
    client,_=workflow
    raw=Path("../frontend-v2/tests/fixtures/task02.musicxml").read_bytes()
    response=client.post("/api/v1/transpose/instrument",files={"file":("score.musicxml",raw)},data={"instrument":"alto","direction":"down"})
    assert response.status_code==200,response.text
    before=create(client,response.content)
    b=body();b.update(source_fifths=2,target_fifths=-3,semitones=1)
    response=request(client,before,"sections/append",b)
    assert response.status_code==200,response.text
    after=ET.fromstring(xml(response.json()));original=ET.fromstring(xml(before))
    assert [ET.tostring(n) for n in after.findall(".//measure")[3].findall("attributes/transpose")]==[ET.tostring(n) for n in original.findall(".//measure")[0].findall("attributes/transpose")]
    assert ET.tostring(after.findall(".//measure")[0])==ET.tostring(original.findall(".//measure")[0])

def test_explicit_concert_interval_source_override_and_octaves(workflow):
    client,_=workflow
    raw=Path("../frontend-v2/tests/fixtures/task02.musicxml").read_bytes()
    for semitones in [-12,12]:
        response=client.post("/api/v1/transpose/concert-key",files={"file":("score.musicxml",raw)},data={"source_fifths":-1,"source_mode":"major","source_confirmed":"true","target_fifths":-1,"direction":"up" if semitones>0 else "down","semitones":semitones})
        assert response.status_code==200,response.text
        original=ET.fromstring(raw).find(".//note/pitch");new=ET.fromstring(response.content).find(".//note/pitch")
        assert new.findtext("step")==original.findtext("step")
        assert int(new.findtext("octave"))==int(original.findtext("octave"))+semitones//12

def test_copied_tie_can_be_edited_and_removed_independently(workflow):
    client,_=workflow;before=create(client,tied_fixture());b=body("m-1","m-3");b.update(source_fifths=0,target_fifths=2,semitones=2)
    after=request(client,before,"sections/append",b).json()
    source=after["score"]["parts"][0]["measures"][3]["voices"][0]["events"][0]["id"]
    response=request(client,after,"events/"+source,{"tie_to_event_id":None},"PATCH")
    assert response.status_code==200,response.text
    result=response.json()
    assert event(result,source)["tie_target_id"] is None
    assert event(result,"e-1")["tie_target_id"]=="e-2"

def test_failed_boundaries_and_intervals_leave_revision_unchanged(workflow):
    client,_=workflow;raw=Path("../frontend-v2/tests/fixtures/task02.musicxml").read_bytes()
    for replacement in [b'<notations><slur type="start"/></notations>',b'<notations><tuplet type="start"/></notations>']:
        before=create(client,raw.replace(b'</note>',replacement+b'</note>',1))
        response=request(client,before,"sections/append",body())
        assert response.status_code==422,response.text
        assert client.get("/api/v1/reviews/"+before["id"]).json()["revision"]==before["revision"]
    before=create(client,raw);b=body();b["semitones"]=1
    assert request(client,before,"sections/append",b).status_code==422

def test_repeated_copy_has_unique_xml_ids_and_preserved_original_nodes(workflow):
    client,_=workflow;before=create(client,tied_fixture());b=body("m-1","m-3");b.update(source_fifths=0,target_fifths=2,semitones=2)
    one=request(client,before,"sections/append",b).json()
    two=request(client,one,"sections/append",b)
    assert two.status_code==200,two.text
    root=ET.fromstring(xml(two.json()));ids=[n.get("id") for n in root.iter() if n.get("id") and n.tag.rsplit("}",1)[-1] not in {"part","instrument"}]
    assert len(ids)==len(set(ids))
    assert len(root.findall(".//part/measure"))==9
    restored=create(client,xml(two.json()))
    for index in [0,3,6]:
        assert restored["score"]["parts"][0]["measures"][index]["voices"][0]["events"][0]["tie_target_id"]
