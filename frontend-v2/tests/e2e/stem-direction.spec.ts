import {test,expect} from '@playwright/test';
for(const instrument of [null,'Alto Saxophone','Soprano Saxophone','Tenor Saxophone'])test('Explicit stem direction persists · '+(instrument??'Concert'),async({page})=>{
 const ids=new Set<string>();page.on('response',async r=>{if(r.request().method()==='POST'&&(r.url().endsWith('/reviews')||r.url().endsWith('/document-correction'))&&r.ok())ids.add((await r.json()).id);});
 try{
 await page.goto('/');await page.locator('input[type=file]').setInputFiles('tests/fixtures/task02.musicxml');await expect(page.getByTestId('real-head-e-1')).toBeVisible();
 if(instrument){await page.getByRole('button',{name:'Instrument Scores →',exact:true}).click();await page.getByRole('button',{name:new RegExp(instrument)}).click();}
 const scope=page.locator(instrument?'.instrument-editor':'.real-workspace');const head=scope.getByTestId('real-head-e-1');await expect(head).toBeVisible();await head.press('Enter');const panel=scope.getByRole('region',{name:'Selected note tools',exact:true});await panel.locator('summary').filter({hasText:'Notation & expressions'}).click();
 for(const direction of ['Down','Up','Auto']){
 if(direction!=='Down'){await scope.getByTestId('real-head-e-1').press('Enter');if(!(await panel.getByRole('group',{name:'Stem direction',exact:true}).isVisible()))await panel.locator('summary').filter({hasText:'Notation & expressions'}).click();}
  const pending=page.waitForResponse(r=>r.url().endsWith('/document-correction')&&r.request().method()==='POST');await panel.getByRole('group',{name:'Stem direction',exact:true}).getByRole('button',{name:direction,exact:true}).click();const response=await pending;expect(response.ok()).toBeTruthy();const result=await response.json();
  const xml=Buffer.from(result.musicxml_base64,'base64').toString();const stem=await page.evaluate(xml=>{const doc=new DOMParser().parseFromString(xml,'application/xml');const note=doc.querySelector('part measure note');return note?.querySelector('stem')?.textContent??null;},xml);expect(stem).toBe(direction==='Auto'?null:direction.toLowerCase());
 }
 }finally{for(const id of ids)await page.request.delete('/api/v1/reviews/'+id).catch(()=>{});}
});
