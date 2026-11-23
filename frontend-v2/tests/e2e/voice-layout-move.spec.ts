import {test,expect} from '@playwright/test';
const head=(step:string,octave:number,duration:number,voice:number,type:string)=>`<note><pitch><step>${step}</step><octave>${octave}</octave></pitch><duration>${duration}</duration><voice>${voice}</voice><type>${type}</type></note>`;
const wrap=(content:string)=>`<score-partwise version="4.0"><part-list><score-part id="P"><part-name>Voice</part-name></score-part></part-list><part id="P"><measure number="1"><attributes><divisions>8</divisions><time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes>${content}</measure></part></score-partwise>`;

test('Longer second voice stays inside the stave at 100, 70 and 50 percent without rewriting XML',async({page})=>{
 const ids=new Set<string>();let initial='';page.on('response',async r=>{if(r.request().method()==='POST'&&r.url().endsWith('/reviews')&&r.ok()){const b=await r.json();ids.add(b.id);initial=b.musicxml_base64;}});
 try{
  const xml=wrap(head('C',5,16,1,'half')+'<backup><duration>16</duration></backup><forward><duration>21</duration><voice>2</voice></forward>'+['C','B','A','G'].map(s=>head(s,s==='C'?5:4,4,2,'eighth')).join('')+head('F',4,8,2,'quarter')+head('E',4,8,2,'quarter'));
  await page.goto('/');await page.locator('input[type=file]').setInputFiles({name:'polyphonic-layout.musicxml',mimeType:'application/xml',buffer:Buffer.from(xml)});
  for(const zoom of [100,70,50]){
   if(zoom<100)for(let n=zoom===70?100:70;n>zoom;n-=10)await page.getByRole('button',{name:'Working score zoom out',exact:true}).click();
   await expect.poll(async()=>page.locator('.working-scroll [data-event-id]').count()).toBe(7);await page.waitForTimeout(250);
   const outside=await page.locator('.working-scroll svg g.vf-measure').first().evaluate(g=>{const lines=[...g.children].filter(n=>n.tagName==='path').slice(0,5).map(n=>n.getBoundingClientRect());const right=Math.max(...lines.map(b=>b.right));return [...g.querySelectorAll('[data-event-id]')].filter(n=>n.getBoundingClientRect().right>right+2).map(n=>n.getAttribute('data-event-id'));});expect(outside).toEqual([]);
  }
  const current=await(await page.request.get('/api/v1/reviews/'+[...ids][0])).json();expect(current.musicxml_base64).toBe(initial);
 }finally{for(const id of ids)await page.request.delete('/api/v1/reviews/'+id,{timeout:3000}).catch(()=>{});}
});

test('Horizontal drag changes onset in voice 1, retains voice 2, and supports Undo',async({page})=>{
 const ids=new Set<string>();page.on('response',async r=>{if(r.request().method()==='POST'&&r.url().endsWith('/reviews')&&r.ok())ids.add((await r.json()).id);});
 try{
  const xml=wrap(head('C',5,8,1,'quarter')+'<forward><duration>16</duration></forward>'+head('C',5,8,1,'quarter')+'<backup><duration>32</duration></backup>'+head('E',4,32,2,'whole'));
  await page.goto('/');await page.locator('input[type=file]').setInputFiles({name:'move-in-voice.musicxml',mimeType:'application/xml',buffer:Buffer.from(xml)});
  const first=page.getByRole('button',{name:'Note e-1, voice 1',exact:true}),last=page.getByRole('button',{name:'Note e-2, voice 1',exact:true});await expect(first).toBeVisible();
  await page.locator('.working-pane').evaluate(el=>window.scrollBy(0,el.getBoundingClientRect().top-100));await page.waitForTimeout(200);
  const a=(await first.boundingBox())!,b=(await last.boundingBox())!;await page.mouse.move(a.x+a.width/2,a.y+a.height/2);await page.mouse.down();await page.mouse.move((a.x+b.x)/2,a.y+a.height/2,{steps:12});await expect(page.locator('.note-drop-preview')).toContainText('Voice 1');
  const pending=page.waitForResponse(r=>r.url().endsWith('/events/e-1/ownership'));await page.mouse.up();const response=await pending;expect(response.ok()).toBeTruthy();const result=await response.json();const events=result.score.parts[0].measures[0].voices.flatMap((v:{events:unknown[]})=>v.events);
  expect(events.find((e:{id:string})=>e.id==='e-1')).toMatchObject({voice:'1',pitch:{step:'C',octave:5},duration:'1'});expect(events.find((e:{id:string})=>e.id==='e-1').onset).not.toBe('0');expect(events.find((e:{id:string})=>e.id==='e-2').onset).toBe('3');expect(events.find((e:{id:string})=>e.id==='e-3')).toMatchObject({voice:'2',onset:'0',duration:'4'});
  const undo=page.waitForResponse(r=>r.url().endsWith('/undo'));await page.getByRole('button',{name:/Undo/}).click();const restored=await(await undo).json();expect(restored.score.parts[0].measures[0].voices[0].events[0].onset).toBe('0');
 }finally{for(const id of ids)await page.request.delete('/api/v1/reviews/'+id,{timeout:3000}).catch(()=>{});}
});


test('Draft beam movement is one gesture and Undo restores note and beam',async({page})=>{
 const ids=new Set<string>();page.on('response',async r=>{if(r.request().method()==='POST'&&r.url().endsWith('/reviews')&&r.ok())ids.add((await r.json()).id);});
 try{
  const first=head('C',5,4,1,'eighth').replace('</note>','<beam number="1">begin</beam></note>'),second=head('B',4,4,1,'eighth').replace('</note>','<beam number="1">end</beam></note>');
  const xml=wrap(first+second+'<forward><duration>16</duration></forward>'+head('C',5,8,1,'quarter')+'<backup><duration>32</duration></backup>'+head('E',4,32,2,'whole'));
  await page.goto('/');await page.locator('input[type=file]').setInputFiles({name:'beam-move.musicxml',mimeType:'application/xml',buffer:Buffer.from(xml)});const source=page.getByRole('button',{name:'Note e-1, voice 1',exact:true});await expect(source).toBeVisible();await page.locator('.working-pane').evaluate(el=>window.scrollBy(0,el.getBoundingClientRect().top-100));await page.waitForTimeout(200);
  const a=(await source.boundingBox())!,b=(await page.getByRole('button',{name:'Note e-3, voice 1',exact:true}).boundingBox())!;await page.mouse.move(a.x+a.width/2,a.y+a.height/2);await page.mouse.down();await page.mouse.move((a.x+b.x)/2,a.y+a.height/2,{steps:12});const pending=page.waitForResponse(r=>r.url().endsWith('/events/e-1/ownership'));await page.mouse.up();const response=await pending;expect(response.ok()).toBeTruthy();await expect(page.getByRole('dialog',{name:'Move beamed note'})).toHaveCount(0);const result=await response.json();const notes=result.score.parts[0].measures[0].voices.flatMap((v:{events:unknown[]})=>v.events);expect(notes.find((e:{id:string})=>e.id==='e-1').onset).not.toBe('0');expect(notes.find((e:{id:string})=>e.id==='e-2').onset).toBe('1/2');expect(notes.find((e:{id:string})=>e.id==='e-4').voice).toBe('2');
  const undo=page.waitForResponse(r=>r.url().endsWith('/undo'));await page.getByRole('button',{name:/Undo/}).click();const restored=await(await undo).json();expect(Buffer.from(restored.musicxml_base64,'base64').toString()).toContain('<beam');
 }finally{for(const id of ids)await page.request.delete('/api/v1/reviews/'+id,{timeout:3000}).catch(()=>{});}
});

test('Changing the selected G4 voice splits it from C5 while preserving their common beat',async({page})=>{
 const ids=new Set<string>();page.on('response',async r=>{if(r.request().method()==='POST'&&r.url().endsWith('/reviews')&&r.ok())ids.add((await r.json()).id);});
 try{
  const xml=wrap('<forward><duration>24</duration></forward>'+head('G',4,8,1,'quarter')+head('C',5,8,1,'quarter').replace('<note>','<note><chord/>'));
  await page.goto('/');await page.locator('input[type=file]').setInputFiles({name:'split-voices.musicxml',mimeType:'application/xml',buffer:Buffer.from(xml)});
  const g=page.getByRole('button',{name:'Note e-1, voice 1',exact:true});await expect(g).toBeVisible();await g.focus();await g.press('Enter');
  const input=page.getByLabel('Selected event voice',{exact:true});await input.fill('2');const pending=page.waitForResponse(r=>r.url().endsWith('/events/e-1/ownership'));await input.press('Tab');const response=await pending;expect(response.ok()).toBeTruthy();const result=await response.json();const notes=result.score.parts[0].measures[0].voices.flatMap((v:{events:unknown[]})=>v.events);
  expect(notes.find((e:{id:string})=>e.id==='e-1')).toMatchObject({voice:'2',onset:'3',pitch:{step:'G',octave:4}});expect(notes.find((e:{id:string})=>e.id==='e-2')).toMatchObject({voice:'1',onset:'3',pitch:{step:'C',octave:5}});
  await page.waitForTimeout(200);const a=(await page.getByRole('button',{name:'Note e-1, voice 2',exact:true}).boundingBox())!,b=(await page.getByRole('button',{name:'Note e-2, voice 1',exact:true}).boundingBox())!;expect(Math.abs(a.x+a.width/2-b.x-b.width/2)).toBeLessThan(3);
  const undo=page.waitForResponse(r=>r.url().endsWith('/undo'));await page.getByRole('button',{name:/Undo/}).click();expect((await(await undo).json()).score.parts[0].measures[0].voices).toHaveLength(1);
 }finally{for(const id of ids)await page.request.delete('/api/v1/reviews/'+id,{timeout:3000}).catch(()=>{});}
});


test('Voice 2 snaps to a nearby D5 voice-1 column without colliding with its preceding note',async({page})=>{
 const ids=new Set<string>();page.on('response',async r=>{if(r.request().method()==='POST'&&r.url().endsWith('/reviews')&&r.ok())ids.add((await r.json()).id);});
 try{
  const xml=wrap('<forward><duration>24</duration></forward>'+head('D',5,8,1,'quarter')+'<backup><duration>32</duration></backup>'+head('E',4,24,2,'half').replace('</type>','</type><dot/>')+'<forward><duration>4</duration></forward>'+head('G',4,4,2,'eighth'));
  await page.goto('/');await page.locator('input[type=file]').setInputFiles({name:'align-other-voice.musicxml',mimeType:'application/xml',buffer:Buffer.from(xml)});await expect(page.getByRole('button',{name:'Note e-3, voice 2',exact:true})).toBeVisible();
  for(let n=0;n<3;n++)await page.getByRole('button',{name:'Working score zoom out',exact:true}).click();await page.waitForTimeout(300);await page.locator('.working-pane').evaluate(el=>window.scrollBy(0,el.getBoundingClientRect().top-100));
  const a=(await page.getByRole('button',{name:'Note e-3, voice 2',exact:true}).boundingBox())!,b=(await page.getByRole('button',{name:'Note e-1, voice 1',exact:true}).boundingBox())!;
  await page.mouse.move(a.x+a.width/2,a.y+a.height/2);await page.mouse.down();await page.mouse.move(b.x+b.width/2-3,a.y+a.height/2,{steps:12});await expect(page.locator('.note-drop-preview')).toContainText('beat 4');await expect(page.locator('.note-drop-preview')).toContainText('Voice 2');await expect(page.locator('.note-drop-preview')).toContainText('Aligned with Voice 1');const guide=page.locator('.note-column-guide');await expect(guide).toBeVisible();await expect(guide).toHaveAttribute('data-onset','3');const line=(await guide.boundingBox())!;expect(Math.abs(line.x+line.width/2-b.x-b.width/2)).toBeLessThan(3);
  const pending=page.waitForResponse(r=>r.url().endsWith('/events/e-3/ownership'));await page.mouse.up();const response=await pending;expect(response.ok()).toBeTruthy();const result=await response.json();const notes=result.score.parts[0].measures[0].voices.flatMap((v:{events:unknown[]})=>v.events);
  await expect(page.locator('.note-column-guide')).toHaveCount(0);expect(notes.find((e:{id:string})=>e.id==='e-3')).toMatchObject({voice:'2',onset:'3',duration:'1/2',pitch:{step:'G',octave:4}});expect(notes.find((e:{id:string})=>e.id==='e-1')).toMatchObject({voice:'1',onset:'3',pitch:{step:'D',octave:5}});expect(notes.find((e:{id:string})=>e.id==='e-2')).toMatchObject({voice:'2',onset:'0',duration:'3'});
 }finally{for(const id of ids)await page.request.delete('/api/v1/reviews/'+id,{timeout:3000}).catch(()=>{});}
});


test('Equal-onset C5/G4 stay aligned even with preceding same-voice overlap, preserving original voices and XML',async({page})=>{
 const ids=new Set<string>();let original='';page.on('response',async r=>{if(r.request().method()==='POST'&&r.url().endsWith('/reviews')&&r.ok()){const b=await r.json();ids.add(b.id);original=b.musicxml_base64;}});
 const n=(step:string,octave:number,duration:number,voice:number,lyric='')=>`<note><pitch><step>${step}</step><octave>${octave}</octave></pitch><duration>${duration}</duration><voice>${voice}</voice><type>${duration===48?'half':'quarter'}</type>${duration===48?'<dot/>':''}<staff>1</staff>${lyric?`<lyric number="1"><text>${lyric}</text></lyric>`:''}</note>`;
 const shift=(kind:string,d:number)=>`<${kind}><duration>${d}</duration></${kind}>`;
 const body=n('C',5,16,2)+shift('forward',48)+shift('backup',64)+shift('forward',59)+n('C',5,16,1,'high')+shift('backup',75)+shift('forward',31)+n('B',4,16,2)+shift('backup',47)+shift('forward',47)+n('A',4,16,2)+shift('backup',63)+shift('forward',59)+n('G',4,16,2,'low')+shift('backup',75)+n('C',5,48,1)+shift('backup',48);
 const xml=wrap(body).replace('<divisions>8</divisions>','<divisions>16</divisions>');
 try{
  await page.goto('/');await page.locator('input[type=file]').setInputFiles({name:'overlap-align.musicxml',mimeType:'application/xml',buffer:Buffer.from(xml)});
  for(const zoom of [100,70,50]){
   if(zoom<100)for(let n=zoom===70?100:70;n>zoom;n-=10)await page.getByRole('button',{name:'Working score zoom out',exact:true}).click();
   const c=page.getByRole('button',{name:'Note e-2, voice 1',exact:true}),g=page.getByRole('button',{name:'Note e-5, voice 2',exact:true});await expect(g).toBeVisible();await page.waitForTimeout(250);
   const a=(await c.boundingBox())!,b=(await g.boundingBox())!;expect(Math.abs(a.x+a.width/2-b.x-b.width/2)).toBeLessThan(2);await expect(page.locator('.working-scroll [data-event-id]')).toHaveCount(6);
  }
  const current=await(await page.request.get('/api/v1/reviews/'+[...ids][0])).json();expect(current.musicxml_base64).toBe(original);
  const notes=current.score.parts[0].measures[0].voices.flatMap((v:{events:unknown[]})=>v.events);expect(notes.find((e:{id:string})=>e.id==='e-2')).toMatchObject({voice:'1',onset:'59/16'});expect(notes.find((e:{id:string})=>e.id==='e-5')).toMatchObject({voice:'2',onset:'59/16'});
  await page.getByTestId('real-lyric-e-5-1').click();await expect(page.getByTestId('inline-lyric-editor')).toHaveAttribute('data-event-id','e-5');await expect(page.getByTestId('inline-lyric-editor')).toHaveAttribute('data-verse','1');await expect(page.getByLabel('Lyric syllable',{exact:true})).toHaveValue('low');
 }finally{for(const id of ids)await page.request.delete('/api/v1/reviews/'+id,{timeout:3000}).catch(()=>{});}
});
