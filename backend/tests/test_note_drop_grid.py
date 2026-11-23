from test_phase4e_workflow import workflow, create, request, xml

XML=b'''<score-partwise version="4.0"><part-list><score-part id="P"><part-name>Voice</part-name></score-part></part-list><part id="P"><measure number="1"><attributes><divisions>2</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes><note><pitch><step>C</step><octave>5</octave></pitch><duration>6</duration><voice>1</voice><type>half</type><dot/></note></measure></part></score-partwise>'''

def test_binary_drop_grid_refines_divisions_preserving_original_and_roundtrip(workflow):
    client,_=workflow
    before=create(client,XML)
    response=request(client,before,'events',dict(measure_id='m-1',onset='1/16',voice='2',staff=1,kind='note',pitch=dict(step='C',octave=5),duration='1'))
    assert response.status_code==200,response.text
    after=response.json()
    events=[e for v in after['score']['parts'][0]['measures'][0]['voices'] for e in v['events']]
    assert [(e['onset'],e['duration']) for e in events]==[('0','3'),('1/16','1')]
    again=create(client,xml(after))
    assert [(e['onset'],e['duration']) for v in again['score']['parts'][0]['measures'][0]['voices'] for e in v['events']]==[('0','3'),('1/16','1')]
    undo=request(client,after,'undo').json()
    assert xml(undo)==XML


def test_draft_add_preserves_negative_imported_cursor_and_existing_notes(workflow):
    client, _ = workflow
    broken = XML.replace(b'</measure>', b'<backup><duration>8</duration></backup></measure>')
    before = create(client, broken)
    assert any(d['code'] == 'negative_onset' for d in before['validation']['diagnostics'])
    response = request(client, before, 'events', dict(measure_id='m-1', onset='3', voice='2', staff=1, kind='note', pitch=dict(step='C', octave=5), duration='1', draft_edit=True))
    assert response.status_code == 200, response.text
    after = response.json()
    events = [e for v in after['score']['parts'][0]['measures'][0]['voices'] for e in v['events']]
    assert [(e['onset'], e['duration']) for e in events] == [('0', '3'), ('3', '1')]
    assert b'<backup><duration>8</duration></backup>' in xml(after)
    assert any(d['code'] == 'negative_onset' for d in after['validation']['diagnostics'])
    assert xml(request(client, after, 'undo').json()) == broken


def test_draft_add_and_delete_with_negative_cursor(workflow):
    client, _ = workflow
    source = XML.replace(b'</measure>', b'<backup><duration>8</duration></backup></measure>')
    before = create(client, source)
    response = request(client, before, 'events/e-1', None, 'DELETE')
    assert response.status_code == 200, response.text


def test_draft_tuplet_changes_selected_values_without_moving_interleaved_voice(workflow):
    client,_=workflow
    def note(step,voice):return f'<note><pitch><step>{step}</step><octave>5</octave></pitch><duration>2</duration><voice>{voice}</voice><type>quarter</type></note>'.encode()
    body=b''.join(note(step,1)+b'<backup><duration>2</duration></backup>'+note('G',2) for step in ['C','D','E'])
    source=XML[:XML.index(b'<note>')]+body+b'</measure></part></score-partwise>'
    before=create(client,source)
    response=request(client,before,'tuplets',dict(event_ids=['e-1','e-3','e-5'],action='apply',actual_notes=3,normal_notes=2,draft_edit=True))
    assert response.status_code==200,response.text
    after=response.json()
    original={e['id']:e for v in before['score']['parts'][0]['measures'][0]['voices'] for e in v['events']}
    for v in after['score']['parts'][0]['measures'][0]['voices']:
        for e in v['events']:
            assert e['onset']==original[e['id']]['onset']
            assert e['duration']==('2/3' if e['voice']=='1' else '1')
    assert xml(request(client,after,'undo').json())==source
