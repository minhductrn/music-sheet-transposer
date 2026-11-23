import {test,expect} from '@playwright/test';
const xml='<score-partwise version="4.0"><part-list><score-part id="P"><part-name>Voice</part-name></score-part></part-list><part id="P"><measure number="1"><attributes><divisions>2</divisions><time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes><note><pitch><step>C</step><octave>5</octave></pitch><duration>6</duration><voice>1</voice><type>half</type><dot/><lyric><text>Keep</text></lyric></note></measure></part></score-partwise>';
for(const scenario of ['same','space','cancel','same-70','same-50'])test('Drag a quarter note onto '+scenario,async({page})=>{
 const placement=scenario.split('-')[0];
 const ids=new Set<string>();page.on('response',async r=>{if(r.request().method()==='POST'&&r.url().endsWith('/reviews')&&r.ok())ids.add((await r.json()).id);});
 try{
  await page.goto('/');await page.locator('input[type=file]').setInputFiles({name:'drop.musicxml',mimeType:'application/xml',buffer:Buffer.from(xml)});
  const head=page.getByRole('button',{name:'Note e-1, voice 1',exact:true});await expect(head).toBeVisible();
  if(scenario.includes('-')){const zoom=Number(scenario.split('-')[1]);for(let n=100;n>zoom;n-=10)await page.getByRole('button',{name:'Working score zoom out',exact:true}).click();await page.waitForTimeout(500);await expect(head).toBeVisible();}
  await page.locator('.working-pane').evaluate(el=>window.scrollBy(0,el.getBoundingClientRect().top-100));
  if(placement==='same'){await head.focus();await head.press('Enter');}
  await expect(page.locator('.note-drag-strip')).toHaveCount(0);
  await page.getByRole('button',{name:'Notes',exact:true}).click();
  await page.getByLabel('Insertion voice',{exact:true}).fill('2');
  const palette=page.getByRole('button',{name:'Quarter note',exact:true});await expect(palette).toBeVisible();const p=(await palette.boundingBox())!;
  await expect.poll(async()=>Boolean(await head.boundingBox())).toBe(true);const b=await head.evaluate(el=>{const r=el.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height};});
  await page.mouse.move(p.x+p.width/2,p.y+p.height/2);await page.mouse.down();
  const x=placement==='space'?b.x+b.width/2+35:b.x+b.width/2;
  await page.mouse.move(x,b.y+b.height/2,{steps:15});await expect(page.locator('.note-drop-preview')).toBeVisible();
  if(placement==='cancel'){
   await page.keyboard.press('Escape');await page.mouse.up();await expect(page.locator('.note-drop-preview')).toHaveCount(0);await expect(page.getByRole('button',{name:/Note .*voice/})).toHaveCount(1);return;
  }
  await expect(page.locator('.note-drop-preview')).toHaveAttribute('data-valid','true');
  const pending=page.waitForResponse(r=>r.request().method()==='POST'&&/\/reviews\/[^/]+\/events$/.test(r.url()),{timeout:10000});await page.mouse.up();const response=await pending;expect(response.ok()).toBeTruthy();const result=await response.json();
  const notes=result.score.parts[0].measures[0].voices.flatMap((v:{events:unknown[]})=>v.events);expect(notes).toHaveLength(2);
  const original=notes.find((e:{id:string})=>e.id==='e-1');expect(original).toMatchObject({onset:'0',duration:'3',voice:'1',pitch:{step:'C',octave:5}});
  const added=notes.find((e:{id:string})=>e.id!=='e-1');expect(added.duration).toBe('1');expect(added.voice).toBe('2');
  if(placement==='same'){expect(added.onset).toBe('0');expect(added.pitch).toMatchObject({step:'C',octave:5});}else{expect(added.onset).not.toBe('0');}
  const undo=page.waitForResponse(r=>r.url().endsWith('/undo'));await page.getByRole('button',{name:/Undo/}).click();expect((await(await undo).json()).score.parts[0].measures[0].voices.flatMap((v:{events:unknown[]})=>v.events)).toHaveLength(1);
 }finally{for(const id of ids)await page.request.delete('/api/v1/reviews/'+id,{timeout:3000}).catch(()=>{});}
});
