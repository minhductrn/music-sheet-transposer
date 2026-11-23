from test_phase4e_workflow import workflow, create, request, xml

XML=b'''<score-partwise version="4.0"><part-list><score-part id="P"><part-name>Voice</part-name></score-part></part-list><part id="P"><measure number="1"><attributes><divisions>2</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes><note><pitch><step>C</step><octave>5</octave></pitch><duration>2</duration><voice>1</voice><type>quarter</type><tie type="start"/><notations><tied type="start"/><articulations><accent/></articulations></notations><lyric><text>Keep</text></lyric></note><forward><duration>4</duration></forward><note><pitch><step>C</step><octave>5</octave></pitch><duration>2</duration><voice>1</voice><type>quarter</type><tie type="stop"/><notations><tied type="stop"/></notations></note><backup><duration>8</duration></backup><note><pitch><step>E</step><octave>4</octave></pitch><duration>8</duration><voice>2</voice><type>whole</type></note></measure></part></score-partwise>'''

def events(review):return {e['id']:e for v in review['score']['parts'][0]['measures'][0]['voices'] for e in v['events']}

def test_move_in_voice_preserves_other_voice_ties_lyrics_history_and_roundtrip(workflow):
    client,_=workflow;before=create(client,XML)
    result=request(client,before,'events/e-1/ownership',dict(measure_id='m-1',onset='1/16',voice='1',staff=1))
    assert result.status_code==200,result.text
    after=result.json();old,new=events(before),events(after)
    assert new['e-1']['onset']=='1/16'
    for field in ('pitch','duration','voice','staff','ties','lyric_ids'):assert new['e-1'][field]==old['e-1'][field]
    for id in ('e-2','e-3'):
        for field in ('onset','duration','voice','staff','pitch','ties'):assert new[id][field]==old[id][field]
    data=xml(after);assert b'accent' in data and b'Keep' in data
    reopened=create(client,data)
    assert sorted((e['voice'],e['onset'],e['duration']) for e in events(reopened).values())==sorted((e['voice'],e['onset'],e['duration']) for e in new.values())
    undo=request(client,after,'undo').json();assert xml(undo)==XML
    redo=request(client,undo,'redo').json();assert xml(redo)==data

def test_collision_rejects_atomically_without_switching_voice(workflow):
    client,_=workflow;before=create(client,XML)
    result=request(client,before,'events/e-1/ownership',dict(measure_id='m-1',onset='3',voice='1',staff=1))
    assert result.status_code==422
    current=client.get('/api/v1/reviews/'+before['id']).json()
    assert current['revision']==before['revision'] and xml(current)==XML


def test_explicit_beam_detach_moves_one_note_and_undo_restores_group(workflow):
    client,_=workflow
    source=XML.replace(b'<type>quarter</type><tie type="start"/>',b'<type>quarter</type><beam number="1">begin</beam><tie type="start"/>').replace(b'<type>quarter</type><tie type="stop"/>',b'<type>quarter</type><beam number="1">end</beam><tie type="stop"/>')
    before=create(client,source)
    body=dict(measure_id='m-1',onset='1',voice='1',staff=1)
    blocked=request(client,before,'events/e-1/ownership',body)
    assert blocked.status_code==422 and 'beam group' in blocked.text
    assert xml(client.get('/api/v1/reviews/'+before['id']).json())==source
    moved=request(client,before,'events/e-1/ownership',{**body,'detach_beam':True})
    assert moved.status_code==200,moved.text
    after=moved.json();assert events(after)['e-1']['onset']=='1'
    assert events(after)['e-2']['onset']=='3' and events(after)['e-3']['onset']=='0'
    assert b'<beam' not in xml(after) and b'Keep' in xml(after) and b'accent' in xml(after)
    assert events(after)['e-1']['ties']==events(before)['e-1']['ties']
    undo=request(client,after,'undo').json();assert xml(undo)==source


def test_split_chord_leader_into_another_voice_keeps_both_onsets(workflow):
    client,_=workflow
    source=b'''<score-partwise version="4.0"><part-list><score-part id="P"><part-name>Voice</part-name></score-part></part-list><part id="P"><measure number="1"><attributes><divisions>2</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes><forward><duration>6</duration></forward><note><pitch><step>G</step><octave>4</octave></pitch><duration>2</duration><voice>1</voice><type>quarter</type></note><note><chord/><pitch><step>C</step><octave>5</octave></pitch><duration>2</duration><voice>1</voice><type>quarter</type></note></measure></part></score-partwise>'''
    before=create(client,source)
    result=request(client,before,'events/e-1/ownership',dict(measure_id='m-1',onset='3',voice='2',staff=1))
    assert result.status_code==200,result.text
    after=result.json();notes=events(after)
    assert (notes['e-1']['voice'],notes['e-1']['onset'],notes['e-1']['pitch']['step'])==('2','3','G')
    assert (notes['e-2']['voice'],notes['e-2']['onset'],notes['e-2']['pitch']['step'])==('1','3','C')
    assert notes['e-1']['duration']==notes['e-2']['duration']=='1'
    assert all(e['chord_id'] is None for e in notes.values())
    reopened=create(client,xml(after))
    assert sorted((e['voice'],e['onset'],e['pitch']['step']) for e in events(reopened).values())==[('1','3','C'),('2','3','G')]
    undo=request(client,after,'undo').json();assert xml(undo)==source


def test_draft_move_accepts_temporary_rhythm_collision_and_preserves_other_notes(workflow):
    client,_=workflow;before=create(client,XML)
    response=request(client,before,'events/e-1/ownership',dict(measure_id='m-1',onset='5/2',voice='1',staff=1,draft_edit=True))
    assert response.status_code==200,response.text
    after=response.json();old,new=events(before),events(after)
    assert new['e-1']['onset']=='5/2' and new['e-1']['voice']=='1'
    for id in ('e-2','e-3'):
        for field in ('onset','duration','voice','pitch'):assert new[id][field]==old[id][field]
    assert xml(request(client,after,'undo').json())==XML


def test_draft_move_preserves_tuplet_instrument_and_beam_markup(workflow):
    client,_=workflow
    source=XML.replace(b'<type>quarter</type><tie type="start"/>',b'<type>quarter</type><beam number="1">begin</beam><instrument id="I1"/><time-modification><actual-notes>3</actual-notes><normal-notes>2</normal-notes></time-modification><tie type="start"/>')
    before=create(client,source)
    result=request(client,before,'events/e-1/ownership',dict(measure_id='m-1',onset='3',voice='2',staff=1,draft_edit=True))
    assert result.status_code==200,result.text
    after=result.json()
    assert events(after)['e-1']['voice']=='2' and events(after)['e-1']['onset']=='3'
    for markup in [b'<beam number="1">begin</beam>',b'<instrument id="I1"',b'<time-modification>',b'Keep']:
        assert markup in xml(after)
    assert events(after)['e-2']['onset']==events(before)['e-2']['onset']
    assert xml(request(client,after,'undo').json())==source
