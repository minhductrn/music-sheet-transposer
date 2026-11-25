import {test,expect,type Page} from '@playwright/test';
const fixture='tests/fixtures/task02.musicxml';
async function openNote(page:Page,scope='.real-workspace'){
 const head=page.locator(scope).locator('.working-scroll').getByTestId('real-head-e-1');
 await expect(head).toBeVisible();await head.focus();await head.press('Enter');
 return page.locator(scope).getByRole('region',{name:'Selected note tools',exact:true});
}
for(const instrument of [null,'Alto Saxophone','Soprano Saxophone','Tenor Saxophone'])test('Shared organized inspector and typed voice change · '+(instrument??'Concert'),async({page})=>{
 const ids=new Set<string>();let lastReview:Record<string,unknown>|null=null;
 page.on('response',async r=>{if(r.request().method()==='POST'&&r.url().endsWith('/reviews')&&r.ok()){const body=await r.json();ids.add(body.id);lastReview=body;}});
 try{
  await page.goto('/');await page.locator('input[type=file]').setInputFiles(fixture);await expect(page.getByTestId('real-head-e-1')).toBeVisible();
  if(instrument){await page.getByRole('button',{name:'Instrument Scores →',exact:true}).click();await page.getByRole('button',{name:new RegExp(instrument)}).click();}
  const panel=await openNote(page,instrument?'.instrument-editor':'.real-workspace');
  await expect(panel.getByLabel('Selected event voice',{exact:true})).toBeVisible();await expect(panel.getByLabel('Current note voice',{exact:true})).toContainText('Main');
  await expect(panel.getByText('1 = Main · 2 = Harmony',{exact:true})).toBeVisible();
  await expect(panel.locator('details').filter({has:page.locator('summary').filter({hasText:'Notation & expressions'})})).not.toHaveAttribute('open');
  await expect(panel.getByRole('button',{name:'Add note after',exact:true})).toBeVisible();
  const spacing=await panel.locator('.note-inspector-section').first().evaluate(e=>({margin:getComputedStyle(e).margin,borderRadius:getComputedStyle(e).borderRadius,padding:getComputedStyle(e).padding}));expect(spacing).toEqual({margin:'0px',borderRadius:'0px',padding:'10px 14px'});
  const before=lastReview;
  const pending=page.waitForResponse(r=>/\/events\/e-1(?:\/ownership)?$/.test(r.url())&&['POST','PATCH'].includes(r.request().method()));
  await panel.getByLabel('Selected event voice',{exact:true}).fill('2');await panel.getByLabel('Selected event voice',{exact:true}).press('Enter');const response=await pending;expect(response.ok()).toBeTruthy();const after=await response.json();
  const events=(r:unknown)=>((r as {score:{parts:{measures:{voices:{events:{id:string;voice:string;pitch:unknown;duration:string;onset:string}[]}[]}[]}[]}}).score.parts.flatMap(p=>p.measures.flatMap(m=>m.voices.flatMap(v=>v.events))));
  const old=events(before),updated=events(after);expect(updated.find(e=>e.id==='e-1')!.voice).toBe('2');
  for(const e of old){const n=updated.find(n=>n.id===e.id)!;expect(n.pitch).toEqual(e.pitch);expect(n.duration).toBe(e.duration);expect(n.onset).toBe(e.onset);if(e.id!=='e-1')expect(n.voice).toBe(e.voice);}
  await expect(panel.getByLabel('Current note voice',{exact:true})).toHaveText('Voice 2 · Harmony');
  await panel.locator('summary').filter({hasText:'Notation & expressions'}).click();
  const sizeChange=page.waitForResponse(r=>r.url().endsWith('/events/e-1')&&r.request().method()==='PATCH');await panel.getByRole('button',{name:'Small',exact:true}).click();expect((await sizeChange).ok()).toBeTruthy();
  await panel.getByRole('button',{name:'Add note after',exact:true}).click();await expect(panel.getByLabel('New note voice',{exact:true})).toHaveValue('2');await expect(panel.getByLabel('New note size',{exact:true})).toHaveValue('small');
  const insertion=page.waitForResponse(r=>r.url().endsWith('/events')&&r.request().method()==='POST');await panel.getByRole('button',{name:'Insert note',exact:true}).click();const inserted=await insertion;expect(inserted.ok()).toBeTruthy();const extended=await inserted.json();const added=events(extended).filter(e=>!updated.some(old=>old.id===e.id));expect(added).toHaveLength(1);expect(added[0]).toMatchObject({voice:'2',display_size:'small'});
  if(!instrument){
   await page.screenshot({path:'/tmp/mst-note-inspector-concert.png'});
   await panel.getByLabel('Selected event voice',{exact:true}).fill('3');const custom=page.waitForResponse(r=>/\/events\/e-1(?:\/ownership)?$/.test(r.url())&&['POST','PATCH'].includes(r.request().method()));await panel.getByRole('button',{name:'Apply',exact:true}).click();expect((await custom).ok()).toBeTruthy();await expect(panel.getByLabel('Selected event voice',{exact:true})).toHaveValue('3');
   await expect(panel.getByRole('button',{name:'Small',exact:true})).toBeVisible();
   await panel.locator('summary').filter({hasText:'Lyrics · verse'}).click();await expect(panel.getByRole('button',{name:'Delete syllable',exact:true})).toBeVisible();
   await page.screenshot({path:'/tmp/mst-note-inspector-expanded.png'});
  }else if(instrument==='Alto Saxophone')await page.screenshot({path:'/tmp/mst-note-inspector-alto.png'});
 }finally{for(const id of ids)await page.request.delete('/api/v1/reviews/'+id,{timeout:3000}).catch(()=>{});}
});

test('Inspector stays within a small screen with voice input immediately accessible',async({page})=>{
 const ids=new Set<string>();page.on('response',async r=>{if(r.request().method()==='POST'&&r.url().endsWith('/reviews')&&r.ok())ids.add((await r.json()).id);});
 try{await page.setViewportSize({width:390,height:844});await page.goto('/');await page.locator('input[type=file]').setInputFiles(fixture);const panel=await openNote(page);const box=(await panel.boundingBox())!;expect(box.x).toBeGreaterThanOrEqual(0);expect(box.x+box.width).toBeLessThanOrEqual(390);expect(box.y+box.height).toBeLessThanOrEqual(844);await expect(panel.getByLabel('Selected event voice',{exact:true})).toBeInViewport();await page.screenshot({path:'/tmp/mst-note-inspector-mobile.png'});}
 finally{for(const id of ids)await page.request.delete('/api/v1/reviews/'+id,{timeout:3000}).catch(()=>{});}
});

test('The same inspector is available after applying a Concert key change',async({page})=>{
 const ids=new Set<string>();page.on('response',async r=>{if(r.request().method()==='POST'&&r.url().endsWith('/reviews')&&r.ok())ids.add((await r.json()).id);});
 try{
  await page.goto('/');await page.locator('input[type=file]').setInputFiles(fixture);await expect(page.getByTestId('real-head-e-1')).toBeVisible();
  await page.getByRole('button',{name:'Concert Key',exact:true}).click();const concert=page.locator('#concert-key-panel');await concert.getByRole('checkbox').check();await concert.getByRole('button',{name:'Increase interval by half a tone',exact:true}).click();await concert.getByRole('button',{name:'Preview concert key',exact:true}).click();await expect(concert.getByRole('region',{name:'Concert key preview'}).locator('svg').first()).toBeVisible();await concert.getByRole('button',{name:'Apply concert key',exact:true}).click();await expect(page.locator('.notice')).toContainText('Concert key changed.');await expect(page.getByRole('button',{name:'Save',exact:true})).toBeEnabled();await page.getByRole('button',{name:'Close Concert Key',exact:true}).click();
  const panel=await openNote(page);await expect(panel.getByLabel('Selected event voice',{exact:true})).toBeVisible();await expect(panel.getByLabel('Current note voice',{exact:true})).toContainText('Main');await expect(panel.getByText('1 = Main · 2 = Harmony',{exact:true})).toBeVisible();
  const response=page.waitForResponse(r=>/\/events\/e-1(?:\/ownership)?$/.test(r.url())&&['POST','PATCH'].includes(r.request().method()));await panel.getByLabel('Selected event voice',{exact:true}).fill('2');await panel.getByLabel('Selected event voice',{exact:true}).press('Enter');expect((await response).ok()).toBeTruthy();await expect(panel.getByLabel('Current note voice',{exact:true})).toHaveText('Voice 2 · Harmony');
 }finally{for(const id of ids)await page.request.delete('/api/v1/reviews/'+id,{timeout:3000}).catch(()=>{});}
});
