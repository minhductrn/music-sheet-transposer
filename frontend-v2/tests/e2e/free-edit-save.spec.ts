import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('Save preserves bytes after optional Validate reports errors and never requires verification',async({page})=>{
 const ids=new Set<string>();let original='',verifyCalls=0;
 page.on('request',r=>{if(r.url().endsWith('/verify'))verifyCalls++;});
 page.on('response',async r=>{if(r.request().method()==='POST'&&r.url().endsWith('/reviews')&&r.ok()){const b=await r.json();ids.add(b.id);original=b.musicxml_base64;}});
 const xml='<score-partwise version="4.0"><part-list><score-part id="P"><part-name>Voice</part-name></score-part></part-list><part id="P"><measure number="1"><attributes><divisions>2</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes><note><pitch><step>C</step><octave>5</octave></pitch><duration>0</duration><voice>1</voice><type>quarter</type></note></measure></part></score-partwise>';
 try{
  await page.goto('/');const loaded=page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/reviews'));await page.locator('input[type=file]').setInputFiles({name:'user-score.musicxml',mimeType:'application/xml',buffer:Buffer.from(xml)});const initial=await(await loaded).json();expect(initial.validation.can_verify).toBe(false);
  await page.getByRole('button',{name:'Validate',exact:true}).click();
  const pending=page.waitForEvent('download');await page.getByRole('button',{name:'Save',exact:true}).click();const download=await pending;const saved=await readFile((await download.path())!);expect(saved).toEqual(Buffer.from(original,'base64'));expect(verifyCalls).toBe(0);
  const current=await(await page.request.get('/api/v1/reviews/'+initial.id)).json();expect(current.musicxml_base64).toBe(original);expect(current.revision).toBe(initial.revision);
 }finally{for(const id of ids)await page.request.delete('/api/v1/reviews/'+id,{timeout:3000}).catch(()=>{});}
});

test('Draft editing permits same-voice overlap and keeps the chosen voice',async({page})=>{
 const ids=new Set<string>();page.on('response',async r=>{if(r.request().method()==='POST'&&r.url().endsWith('/reviews')&&r.ok())ids.add((await r.json()).id);});
 const note=(step:string,d:number)=>`<note><pitch><step>${step}</step><octave>5</octave></pitch><duration>${d}</duration><voice>1</voice><type>quarter</type></note>`;
 const xml='<score-partwise version="4.0"><part-list><score-part id="P"><part-name>Voice</part-name></score-part></part-list><part id="P"><measure number="1"><attributes><divisions>4</divisions><time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes>'+note('C',4)+note('D',4)+note('E',4)+note('F',4)+'</measure></part></score-partwise>';
 try{
  await page.goto('/');await page.locator('input[type=file]').setInputFiles({name:'free-edit.musicxml',mimeType:'application/xml',buffer:Buffer.from(xml)});const aNote=page.getByRole('button',{name:'Note e-1, voice 1',exact:true}),bNote=page.getByRole('button',{name:'Note e-2, voice 1',exact:true});await expect(aNote).toBeVisible();await page.locator('.working-pane').evaluate(el=>window.scrollBy(0,el.getBoundingClientRect().top-100));await page.waitForTimeout(200);
  const a=(await aNote.boundingBox())!,b=(await bNote.boundingBox())!;await page.mouse.move(a.x+a.width/2,a.y+a.height/2);await page.mouse.down();await page.mouse.move((a.x+b.x)/2,a.y+a.height/2,{steps:12});const pending=page.waitForResponse(r=>r.url().endsWith('/events/e-1/ownership'));await page.mouse.up();const response=await pending;expect(response.ok()).toBeTruthy();const result=await response.json();const notes=result.score.parts[0].measures[0].voices.flatMap((v:{events:unknown[]})=>v.events);expect(notes.find((e:{id:string})=>e.id==='e-1').voice).toBe('1');expect(notes.find((e:{id:string})=>e.id==='e-1').onset).not.toBe('0');expect(notes.find((e:{id:string})=>e.id==='e-2').onset).toBe('1');
 }finally{for(const id of ids)await page.request.delete('/api/v1/reviews/'+id,{timeout:3000}).catch(()=>{});}
});
