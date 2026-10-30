from xml.etree import ElementTree as ET
from test_phase4e_workflow import workflow, create, request, event, xml

def fixture():
    def note(octave=4, sign=""):
        return f"<note><pitch><step>B</step><octave>{octave}</octave></pitch><duration>1</duration><voice>1</voice><type>quarter</type>{sign}</note>"
    return ('<score-partwise version="4.0"><part-list><score-part id="P1"><part-name>Test</part-name></score-part></part-list><part id="P1"><measure number="1"><attributes><divisions>1</divisions><key><fifths>0</fifths></key><time><beats>5</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes>'+note()+note()+note(5)+note(sign="<accidental>natural</accidental>")+note()+'</measure><measure number="2">'+note()+'</measure></part></score-partwise>').encode()

def test_scope_boundaries_history_roundtrip(workflow):
    client,_=workflow
    before=create(client,fixture())
    response=request(client,before,'events/e-1',dict(pitch=dict(step="B",octave=4,alter="1"),written_accidental="sharp",accidental_scope_measure=True),'PATCH')
    assert response.status_code==200,response.text
    after=response.json()
    assert event(after,'e-1')['pitch']['alter']=='1'
    assert event(after,'e-2')['pitch']['alter']=='1'
    assert event(after,'e-2')['accidental']['text'] is None
    for i in range(3,7):
        assert event(after,f'e-{i}')==event(before,f'e-{i}')
    root=ET.fromstring(xml(after))
    assert root.findall('.//note')[1].findtext('pitch/alter')=='1'
    reopened=create(client,xml(after))
    assert event(reopened,'e-2')['pitch']['alter']=='1'
    undone=request(client,after,'undo').json()
    assert xml(undone)==xml(before)
    redone=request(client,undone,'redo').json()
    assert xml(redone)==xml(after)
    cleared=request(client,redone,'events/e-1',dict(written_accidental=None,accidental_scope_measure=True),'PATCH')
    assert cleared.status_code==200,cleared.text
    assert event(cleared.json(),'e-2')['pitch']['alter']=='0'

def test_flat_scope_and_tie_safeguard(workflow):
    client,_=workflow
    before=create(client,fixture())
    response=request(client,before,'events/e-1',dict(pitch=dict(step="B",octave=4,alter="-1"),written_accidental="flat",accidental_scope_measure=True),'PATCH')
    assert response.status_code==200,response.text
    assert event(response.json(),'e-2')['pitch']['alter']=='-1'
    tied=create(client,fixture().replace(b'<type>quarter</type>',b'<type>quarter</type><tie type="start"/>',1))
    failed=request(client,tied,'events/e-1',dict(pitch=dict(step="B",octave=4,alter="1"),written_accidental="sharp",accidental_scope_measure=True),'PATCH')
    assert failed.status_code==422

def test_staff_boundary_and_shared_voice_scope(workflow):
    client,_=workflow
    source=fixture().replace(b'<clef>',b'<staves>2</staves><clef>',1)
    source=source.replace(b'</measure>',b'<backup><duration>5</duration></backup><note><pitch><step>B</step><octave>4</octave></pitch><duration>1</duration><voice>2</voice><type>quarter</type><staff>2</staff></note></measure>',1)
    before=create(client,source)
    after=request(client,before,'events/e-1',dict(pitch=dict(step="B",octave=4,alter="1"),written_accidental="sharp",accidental_scope_measure=True),'PATCH').json()
    assert event(after,'e-6')==event(before,'e-6')

def tied_fixture():
    def n(kind, duration=4):
        sound="".join(f'<tie type="{k}"/>' for k in kind)
        visual="".join(f'<tied type="{k}" orientation="under"/>' for k in kind)
        return f'<note><pitch><step>B</step><octave>4</octave></pitch><duration>{duration}</duration>{sound}<voice>1</voice><type>{"whole" if duration==4 else "quarter"}</type><notations>{visual}</notations></note>'
    return ('<score-partwise version="4.0"><part-list><score-part id="P1"><part-name>Test</part-name></score-part></part-list><part id="P1"><measure number="1"><attributes><divisions>1</divisions><key><fifths>0</fifths></key><time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes>'+n(["start"])+'</measure><measure number="2">'+n(["stop","start"])+'</measure><measure number="3">'+n(["stop"],1)+n([],1)+'</measure></part></score-partwise>').encode()

def test_tie_chain_accidental_from_either_endpoint(workflow):
    client,_=workflow
    for selected in ["e-1","e-3"]:
        before=create(client,tied_fixture())
        after=request(client,before,"events/"+selected,dict(pitch=dict(step="B",octave=4,alter="1"),written_accidental="sharp",accidental_scope_measure=True),"PATCH")
        assert after.status_code==200,after.text
        after=after.json()
        for identifier in ["e-1","e-2","e-3"]:
            assert event(after,identifier)["pitch"]["alter"]=="1"
        # Forward accidental scope is restricted to the selected measure.
        assert event(after,"e-4")["pitch"]["alter"]==("1" if selected=="e-3" else "0")
        def ties(data):
            root=ET.fromstring(xml(data))
            return [ET.tostring(e) for e in root.iter() if e.tag in ("tie","tied")]
        assert ties(after)==ties(before)
        assert [event(after,i)["duration"] for i in ["e-1","e-2","e-3"]]==["4","4","1"]
        reopened=create(client,xml(after))
        assert event(reopened,"e-2")["pitch"]["alter"]=="1"
        assert ties(reopened)==ties(before)
        undo=request(client,after,"undo").json()
        assert xml(undo)==xml(before)
        assert xml(request(client,undo,"redo").json())==xml(after)
