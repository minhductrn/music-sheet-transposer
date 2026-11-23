import {test,expect} from '@playwright/test';

for (const placement of ['before','after']) test('Insert C5 quarter '+placement+' a dotted half, undo and redo',async({page})=>{
 const ids=new Set<string>();
 page.on('response',async r=>{if(r.request().method()==='POST'&&r.url().endsWith('/reviews')&&r.ok())ids.add((await r.json()).id);});
 const xml='<score-partwise version="4.0"><part-list><score-part id="P1"><part-name>Voice</part-name></score-part></part-list><part id="P1"><measure number="1"><attributes><divisions>2</divisions><key><fifths>0</fifths></key><time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes><note><pitch><step>C</step><octave>5</octave></pitch><duration>6</duration><voice>1</voice><type>half</type><dot/><lyric><text>Keep</text></lyric></note></measure></part></score-partwise>';
 try {
  await page.goto('/');await page.locator('input[type=file]').setInputFiles({name:'sequential.musicxml',mimeType:'application/xml',buffer:Buffer.from(xml)});
  const head=page.getByRole('button',{name:'Note e-1, voice 1',exact:true});await expect(head).toBeVisible();await head.focus();await head.press('Enter');
  await page.getByRole('button',{name:'Add note '+placement,exact:true}).click();
  await page.getByLabel('New note duration',{exact:true}).selectOption('1');
  const pending=page.waitForResponse(r=>r.request().method()==='POST'&&/\/reviews\/[^/]+\/events$/.test(r.url()));
  await page.getByRole('button',{name:'Insert note',exact:true}).click();const response=await pending;expect(response.ok()).toBeTruthy();
  const result=await response.json();const notes=result.score.parts[0].measures[0].voices[0].events;
  expect(notes.map((e:{duration:string})=>e.duration)).toEqual(placement==='after'?['3','1']:['1','3']);
  expect(notes.map((e:{onset:string})=>e.onset)).toEqual(placement==='after'?['0','3']:['0','1']);
  expect(notes.every((e:{pitch:{step:string;octave:number}})=>e.pitch.step==='C'&&e.pitch.octave===5)).toBeTruthy();
  const undo=page.waitForResponse(r=>r.url().endsWith('/undo'));await page.getByRole('button',{name:/Undo/}).click();expect((await(await undo).json()).score.parts[0].measures[0].voices[0].events).toHaveLength(1);
  const redo=page.waitForResponse(r=>r.url().endsWith('/redo'));await page.getByRole('button',{name:/Redo/}).click();expect((await(await redo).json()).score.parts[0].measures[0].voices[0].events).toHaveLength(2);
  const exported=await page.request.get('/api/v1/reviews/'+result.id+'/musicxml?verified_only=false');expect(exported.ok()).toBeTruthy();
  const saved=await exported.body();const form={musicxml:{name:'roundtrip.musicxml',mimeType:'application/xml',buffer:saved}};
  const reopened=await page.request.post('/api/v1/reviews',{multipart:form});expect(reopened.ok()).toBeTruthy();const roundtrip=await reopened.json();ids.add(roundtrip.id);
  expect(roundtrip.score.parts[0].measures[0].voices[0].events.map((e:{duration:string})=>e.duration)).toEqual(notes.map((e:{duration:string})=>e.duration));
  expect(roundtrip.score.lyrics[0].segments).toContain('Keep');
 } finally {for(const id of ids)await page.request.delete('/api/v1/reviews/'+id,{timeout:3000}).catch(()=>{});}
});

test('A full OMR measure warns but permits sequential correction',async({page})=>{
 const ids=new Set<string>();page.on('response',async r=>{if(r.request().method()==='POST'&&r.url().endsWith('/reviews')&&r.ok())ids.add((await r.json()).id);});
 try {
  const xml='<score-partwise version="4.0"><part-list><score-part id="P"><part-name>Voice</part-name></score-part></part-list><part id="P"><measure number="1"><attributes><divisions>1</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes><note><pitch><step>C</step><octave>5</octave></pitch><duration>1</duration><voice>1</voice><type>quarter</type></note><note><pitch><step>C</step><octave>5</octave></pitch><duration>3</duration><voice>1</voice><type>half</type><dot/></note></measure></part></score-partwise>';
  await page.goto('/');await page.locator('input[type=file]').setInputFiles({name:'omr-full.musicxml',mimeType:'application/xml',buffer:Buffer.from(xml)});
  const head=page.getByRole('button',{name:'Note e-2, voice 1',exact:true});await expect(head).toBeVisible();await head.focus();await head.press('Enter');
  await page.getByRole('button',{name:'Add note after',exact:true}).click();
  await expect(page.getByText('This insertion exceeds the measure duration.',{exact:false})).toBeVisible();
  const pending=page.waitForResponse(r=>r.request().method()==='POST'&&/\/reviews\/[^/]+\/events$/.test(r.url()));
  await page.getByRole('button',{name:'Insert note',exact:true}).click();const response=await pending;expect(response.ok()).toBeTruthy();
  const result=await response.json();expect(result.score.parts[0].measures[0].voices[0].events.map((e:{duration:string})=>e.duration)).toEqual(['1','3','1']);
 } finally {for(const id of ids)await page.request.delete('/api/v1/reviews/'+id,{timeout:3000}).catch(()=>{});}
});
