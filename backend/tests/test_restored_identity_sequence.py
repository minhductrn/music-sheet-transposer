from dataclasses import replace
from test_phase4e_workflow import workflow,create,request,xml

XML=b'<score-partwise><part-list><score-part id="P"><part-name>Test</part-name></score-part></part-list><part id="P"><measure number="1"><attributes><divisions>1</divisions></attributes><note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><type>quarter</type><lyric number="1"><text>Existing one</text></lyric><lyric number="3"><text>Existing three</text></lyric></note></measure></part></score-partwise>'


def test_restored_low_counter_does_not_overwrite_existing_lyrics(workflow):
    client,service=workflow
    before=create(client,XML);session=service.store.get(before['id']);doc=session.document.clone()
    doc.refs['new-106']=doc.refs.pop('l-1');doc.refs['new-108']=doc.refs.pop('l-2')
    service.store.put(replace(session,document=doc,sequence=105))
    before=client.get('/api/v1/reviews/'+before['id']).json()
    response=request(client,before,'events/e-1/lyrics',{'number':'2','text':'su'})
    assert response.status_code==200,response.text
    after=response.json();lyrics={l['id']:l['text'] for l in after['score']['lyrics']}
    assert lyrics=={'new-106':'Existing one','new-108':'Existing three','new-109':'su'}
    assert xml(request(client,after,'undo').json())==XML
    undone=client.get('/api/v1/reviews/'+after['id']).json()
    redone=request(client,undone,'redo').json()
    assert xml(redone)==xml(after)


def test_allocator_reserves_suffix_ids_and_history_references(workflow):
    client,service=workflow
    before=create(client,XML);session=service.store.get(before['id']);past=session.document.clone()
    past.refs['new-500-split-1']=past.refs.pop('l-1')
    service.store.put(replace(session,sequence=0,undo=[past]))
    response=request(client,before,'events/e-1/lyrics',{'number':'2','text':'su'})
    assert response.status_code==200,response.text
    assert any(l['id']=='new-501' and l['text']=='su' for l in response.json()['score']['lyrics'])
