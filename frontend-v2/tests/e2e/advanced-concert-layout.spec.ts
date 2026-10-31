import {test,expect} from '@playwright/test';
for(const width of [1338,650])test('Concert Preview uses a full panel row at '+width,async({page})=>{
 const ids=new Set<string>();page.on('response',async r=>{if(r.request().method()==='POST'&&r.url().endsWith('/reviews')&&r.ok())ids.add((await r.json()).id);});
 try{await page.setViewportSize({width,height:590});await page.goto('/');await page.locator('input[type=file]').setInputFiles('tests/fixtures/task02.musicxml');await expect(page.getByTestId('real-head-e-1')).toBeVisible();
 await page.getByRole('button',{name:'Concert Key',exact:true}).click();const panel=page.locator('#concert-key-panel');await panel.getByRole('checkbox').check();await panel.getByRole('button',{name:'Increase interval by half a tone',exact:true}).click();
 await panel.getByRole('button',{name:'Preview concert key',exact:true}).click();const preview=panel.getByRole('region',{name:'Concert key preview'});await expect(preview.locator('svg').first()).toBeVisible();await preview.scrollIntoViewIfNeeded();
 const p=(await panel.boundingBox())!,v=(await preview.boundingBox())!,apply=(await panel.getByRole('button',{name:'Apply concert key',exact:true}).boundingBox())!;
 expect(v.width).toBeGreaterThan(p.width*.9);expect(v.height).toBeGreaterThanOrEqual(180);expect(v.y).toBeGreaterThanOrEqual(apply.y+apply.height);expect(await preview.evaluate(el=>el.scrollWidth<=el.clientWidth+2)).toBe(true);
 await page.screenshot({path:'evidence/advanced-v1/concert-wide-preview-'+width+'.png'});
 await panel.getByRole('button',{name:'Apply concert key',exact:true}).click();await expect(page.getByTestId('real-concert-key')).toContainText('G♭ major');
 }finally{for(const id of ids)await page.request.delete('/api/v1/reviews/'+id);}
});
