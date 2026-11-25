import {test,expect} from '@playwright/test';
for(const instrument of [null,'Alto Saxophone','Soprano Saxophone','Tenor Saxophone'])test('Ctrl-click changes selected notes to small Voice 2 · '+(instrument??'Concert'),async({page})=>{
 const ids=new Set<string>();page.on('response',async r=>{if(r.request().method()==='POST'&&r.url().endsWith('/reviews')&&r.ok())ids.add((await r.json()).id);});
 try{
 await page.goto('/');await page.locator('input[type=file]').setInputFiles('tests/fixtures/task02.musicxml');await expect(page.getByTestId('real-head-e-4')).toBeVisible();
 if(instrument){await page.getByRole('button',{name:'Instrument Scores →',exact:true}).click();await page.getByRole('button',{name:new RegExp(instrument)}).click();}
 const scope=page.locator(instrument?'.instrument-editor':'.real-workspace');
 await scope.getByTestId('real-head-e-4').click({modifiers:['Control']});
 await scope.getByRole('button',{name:'Close selected note tools'}).click();
 await scope.getByTestId('real-head-e-5').click({modifiers:['Control']});
 await expect(scope.locator('.real-selected')).toHaveCount(2);
 const panel=scope.getByRole('region',{name:'Selected note tools',exact:true});await panel.getByLabel('Selected event voice',{exact:true}).fill('2');const pending=page.waitForResponse(r=>r.url().endsWith('/events/e-5')&&r.request().method()==='PATCH'&&r.request().postDataJSON()?.display_size==='small');await panel.getByLabel('Selected event voice',{exact:true}).press('Enter');const response=await pending;expect(response.ok()).toBeTruthy();const updated=await response.json();const selected=updated.score.parts.flatMap((p:{measures:{voices:{events:{id:string;voice:string;display_size:string}[]}[]}[]})=>p.measures.flatMap(m=>m.voices.flatMap(v=>v.events))).filter((e:{id:string})=>['e-4','e-5'].includes(e.id));expect(selected).toHaveLength(2);for(const note of selected)expect(note).toMatchObject({voice:'2',display_size:'small'});
 for(const id of ['e-4','e-5'])await expect(scope.getByTestId('real-head-'+id)).toHaveAttribute('aria-label',new RegExp('voice 2'));
 }finally{for(const id of ids)await page.request.delete('/api/v1/reviews/'+id).catch(()=>{});}
});
