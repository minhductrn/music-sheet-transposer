import {test,expect} from '@playwright/test';
for(const width of [1338,650])for(const instrument of [false,true])test('Section actions stay clear '+width+' '+(instrument?'instrument':'concert'),async({page})=>{
 const ids=new Set<string>();page.on('response',async r=>{if(r.request().method()==='POST'&&r.url().endsWith('/reviews')&&r.ok())ids.add((await r.json()).id);});
 try{await page.setViewportSize({width,height:590});await page.goto('/');await page.locator('input[type=file]').setInputFiles('tests/fixtures/task02.musicxml');await expect(page.getByTestId('real-head-e-1')).toBeVisible();
 if(instrument){await page.getByRole('button',{name:'Instrument Scores →',exact:true}).click();await page.getByRole('button',{name:/Alto Saxophone/}).click();}
 const editor=instrument?page.locator('.instrument-editor'):page.locator('.real-workspace').first();await editor.getByRole('button',{name:'Create Key Change Section'}).click();const panel=page.getByRole('dialog',{name:'Create Key Change Section'});
 const description=panel.getByText('Copy → append to end · notes + chord symbols',{exact:true});await expect(description).toBeVisible();await expect(editor.locator(instrument?'.instrument-notice':'.notice')).toBeHidden();
 const textBox=(await description.boundingBox())!;const preview=panel.getByRole('button',{name:'Preview section',exact:true});const buttonBox=(await preview.boundingBox())!;
 expect(textBox.y+textBox.height).toBeLessThanOrEqual(buttonBox.y);expect(buttonBox.y+buttonBox.height).toBeLessThan(590);
 const center=await preview.evaluate(el=>{const b=el.getBoundingClientRect();return el.contains(document.elementFromPoint(b.x+b.width/2,b.y+b.height/2));});expect(center).toBe(true);
 await page.screenshot({path:'evidence/advanced-v1/layout-'+width+'-'+instrument+'.png'});
 await panel.getByRole('button',{name:'Preview section',exact:true}).click();await expect(panel.getByRole('button',{name:'Apply section',exact:true})).toBeEnabled();
 }finally{for(const id of ids)await page.request.delete('/api/v1/reviews/'+id);}
});
