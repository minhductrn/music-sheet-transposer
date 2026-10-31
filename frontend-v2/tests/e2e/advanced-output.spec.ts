import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
for(const instrument of [false,true])test('Appended section in Edit Only exports PDF: '+(instrument?'instrument':'concert'),async({page})=>{
 test.setTimeout(90000);const ids=new Set<string>();page.on('response',async r=>{if(r.request().method()==='POST'&&r.url().endsWith('/reviews')&&r.ok())ids.add((await r.json()).id);});
 try{
 await page.goto('/');await page.locator('input[type=file]').setInputFiles('tests/fixtures/task02.musicxml');await expect(page.getByTestId('real-head-e-1')).toBeVisible();
 if(instrument){await page.getByRole('button',{name:'Instrument Scores →',exact:true}).click();await page.getByRole('button',{name:/Soprano Saxophone/}).click();}
 const editor=instrument?page.locator('.instrument-editor'):page.locator('.real-workspace').first();
 await editor.getByRole('button',{name:'Edit Only',exact:true}).click();await expect(editor.locator('.source-pane')).toHaveCount(0);
 await editor.getByRole('button',{name:'Create Key Change Section',exact:true}).click();const panel=page.getByRole('dialog',{name:'Create Key Change Section'});
 await panel.getByLabel('Section last measure').selectOption('m-2');await panel.getByRole('button',{name:'Section Increase interval by half a tone'}).click();
 await panel.getByRole('button',{name:'Preview section',exact:true}).click();await expect(panel.getByRole('button',{name:'Apply section',exact:true})).toBeEnabled();
 const response=page.waitForResponse(r=>r.url().endsWith('/sections/append'));await panel.getByRole('button',{name:'Apply section',exact:true}).click();const result=await(await response).json();expect(result.score.parts[0].measures).toHaveLength(5);
 await editor.getByRole('button',{name:'Export PDF',exact:true}).click();const pdf=page.getByRole('dialog',{name:'PDF layout'});await expect(pdf.getByRole('button',{name:'Export',exact:true})).toBeEnabled({timeout:60000});
 const download=page.waitForEvent('download');await pdf.getByRole('button',{name:'Export',exact:true}).click();const bytes=await readFile((await(await download).path())!);expect(bytes.subarray(0,4).toString()).toBe('%PDF');expect(bytes.length).toBeGreaterThan(1000);
 const live=await(await page.request.get('/api/v1/reviews/'+result.id)).json();expect(live.revision).toBe(result.revision);
 }finally{for(const id of ids)await page.request.delete('/api/v1/reviews/'+id);}
});
