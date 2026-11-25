import {test,expect} from '@playwright/test';
import {readFileSync,writeFileSync} from 'node:fs';
test('Restored Alto workspace uses corrected Export PDF for both margins',async({page})=>{
 const xml=readFileSync('tests/fixtures/overlap-voices.musicxml');
 const open=async()=>{const r=await page.request.post('/api/v1/reviews',{multipart:{musicxml:{name:'synthetic.musicxml',mimeType:'application/xml',buffer:xml}}});expect(r.ok()).toBeTruthy();return r.json();};
 const concert=await open(),saved=await open();
 const url='/?resume='+concert.id+'&name=synthetic.musicxml&resumeOutput='+saved.id+'&resumeInstrument=alto&resumeDirection=down&resumeConcertName=synthetic.musicxml';
 try{
 await page.goto(url);await expect(page.locator('.instrument-editor .working-scroll [data-event-id]').first()).toBeVisible({timeout:30000});await expect(page.locator('.instrument-editor .working-scroll [data-event-id]')).toHaveCount(11);await expect(page.locator('.instrument-editor')).toContainText('Instrument file saved');
 for(const margins of ['auto','standard']){await page.getByRole('button',{name:'Export PDF',exact:true}).click();await page.getByLabel('PDF page layout').selectOption('multiple-pages');await page.getByLabel('PDF margins').selectOption(margins);await expect(page.getByRole('dialog').getByRole('button',{name:'Export',exact:true})).toBeEnabled({timeout:60000});const data=await page.locator('.pdf-preview canvas').evaluate(n=>(n as HTMLCanvasElement).toDataURL('image/png'));writeFileSync('/tmp/mst-pdf-tool-preview-'+margins+'.png',Buffer.from(data.split(',')[1],'base64'));await page.getByRole('button',{name:'Close PDF export'}).click();}
 const current=await(await page.request.get('/api/v1/reviews/'+saved.id)).json();expect(current.musicxml_base64).toBe(saved.musicxml_base64);expect(current.revision).toBe(saved.revision);
 }finally{await page.request.delete('/api/v1/reviews/'+saved.id).catch(()=>{});await page.request.delete('/api/v1/reviews/'+concert.id).catch(()=>{});}
});
