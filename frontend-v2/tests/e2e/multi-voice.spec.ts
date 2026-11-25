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
 const panel=scope.getByRole('region',{name:'Selected note tools',exact:true});await panel.getByLabel('Selected event voice',{exact:true}).fill('2');await panel.getByLabel('Selected event voice',{exact:true}).press('Enter');
 await expect(page.getByText('2 notes updated to Voice 2 · Small.',{exact:true})).toBeVisible();
 for(const id of ['e-4','e-5'])await expect(scope.getByTestId('real-head-'+id)).toHaveAttribute('aria-label',new RegExp('voice 2'));
 }finally{for(const id of ids)await page.request.delete('/api/v1/reviews/'+id).catch(()=>{});}
});
