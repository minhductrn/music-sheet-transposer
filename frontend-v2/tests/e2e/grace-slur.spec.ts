import {test,expect} from '@playwright/test';
for(const instrument of [null,'Alto Saxophone','Soprano Saxophone','Tenor Saxophone'])for(const slash of [false,true])test('Grace has a saved slur without adding beats · '+(instrument??'Concert')+' slash='+slash,async({page})=>{
 const owned=new Set<string>();page.on('response',async r=>{if(r.request().method()==='POST'&&r.url().endsWith('/reviews')&&r.ok())owned.add((await r.json()).id);});
 try{
  await page.goto('/');await page.locator('input[type=file]').setInputFiles('tests/fixtures/task02.musicxml');await expect(page.getByTestId('real-head-e-1')).toBeVisible();
  if(instrument){await page.getByRole('button',{name:'Instrument Scores →',exact:true}).click();await page.getByRole('button',{name:new RegExp(instrument)}).click();}
  const editor=instrument?page.locator('.instrument-editor'):page.locator('.real-workspace').first();await expect(editor.getByRole('button',{name:'Save',exact:true})).toBeEnabled();
  const head=editor.getByTestId('real-head-e-1');await head.focus();await head.press('Enter');await editor.locator('summary').filter({hasText:'Notation & expressions'}).click();
  const pending=page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/events'));await editor.getByRole('button',{name:slash?'Add slashed grace note before':'Add grace note before',exact:true}).click();const response=await pending;expect(response.ok()).toBeTruthy();const after=await response.json();
  const grace=after.score.parts.flatMap((p:{measures:{voices:{events:{id:string;grace:boolean;duration:null|string}[]}[]}[]})=>p.measures.flatMap(m=>m.voices.flatMap(v=>v.events))).find((e:{grace:boolean})=>e.grace);expect(grace.duration).toBeNull();
  expect(Buffer.from(after.musicxml_base64,'base64').toString()).toContain('<slur');await expect(editor.getByTestId('real-curve-slur-'+grace.id+'-e-1')).toBeVisible();
  const undo=page.waitForResponse(r=>r.url().endsWith('/undo'));await page.locator('.app-header').getByRole('button',{name:/Undo/}).click();const restored=await(await undo).json();expect(Buffer.from(restored.musicxml_base64,'base64').toString()).not.toContain('<grace');
 }finally{for(const id of owned)await page.request.delete('/api/v1/reviews/'+id,{timeout:3000}).catch(()=>{});}
});
