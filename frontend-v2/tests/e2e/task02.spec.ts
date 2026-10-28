import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
// Release only sessions created by this browser test; abrupt context close need not fire pagehide.
const testSessions=new Set<string>();
test.beforeEach(async({page})=>{page.on('response',async response=>{if(response.request().method()==='POST'&&/\/api\/v1\/reviews$/.test(response.url())&&response.status()===201){try{const p=await response.json();testSessions.add(p.id);}catch{/* context may already be closed */}}});});
test.afterEach(async({request})=>{for(const id of testSessions)await request.delete(`/api/v1/reviews/${encodeURIComponent(id)}`).catch(()=>{});testSessions.clear();});
const sample=process.env.AI_SDF_TASK02_SAMPLE;
test('Task02 local PO MusicXML opens as real 2/4 score with all semantic heads',async({page})=>{
 test.skip(!sample,'Local-only PO sample; not bundled.');await page.goto('/');await page.locator('input[type=file]').setInputFiles(sample!);
 await expect(page.getByText('MusicXML workspace · real editing',{exact:true})).toBeVisible();await expect(page.locator('.working-pane .real-score svg').first()).toBeVisible();
 await expect(page.locator('.working-pane [data-event-id]')).toHaveCount(63);await expect(page.locator('[role=alert]')).toHaveCount(0);await expect(page.getByTestId('real-lyric-e-6-1')).toBeVisible();
 await page.screenshot({path:'evidence/task02/real-sample-open.png',fullPage:true});
});
test('Task02 actual edits, concert transpose, durable save gate and independent Sax downloads',async({page})=>{
 test.setTimeout(90000);
 test.skip(!sample,'Local-only PO sample; not bundled.');await page.goto('/');await page.locator('input[type=file]').setInputFiles(sample!);
 await expect(page.locator('.working-pane [data-event-id]')).toHaveCount(63);
 await page.getByRole('button',{name:'Edit Only',exact:true}).click();await expect(page.getByTestId('real-head-e-1')).toBeVisible();{await page.getByTestId('real-head-e-1').scrollIntoViewIfNeeded();const b=await page.getByTestId('real-head-e-1').boundingBox();if(!b)throw Error('Missing note');await page.mouse.click(b.x+b.width/2,b.y+b.height/2);await page.getByRole('button',{name:'Voice 1 · e-1',exact:true}).click();}await page.getByRole('button',{name:'Small',exact:true}).click();
 await expect(page.getByRole('button',{name:'↶ Undo',exact:true})).toBeEnabled();await page.getByRole('button',{name:'↶ Undo',exact:true}).click();await page.getByRole('button',{name:'↷ Redo',exact:true}).click();
 await expect(page.getByRole('button',{name:'↷ Redo',exact:true})).toBeDisabled();await expect(page.getByRole('button',{name:'Save',exact:true})).toBeEnabled();await page.getByTestId('real-head-e-1').focus();await page.keyboard.press('Enter');await page.getByRole('button',{name:'Edit lyrics',exact:true}).click();await page.getByRole('textbox',{name:'Lyric syllable'}).fill('Niềm tin mới');await page.getByRole('textbox',{name:'Lyric syllable'}).press('Enter');await expect(page.getByTestId('real-lyric-e-1-1')).toBeVisible();const added=await page.getByTestId('real-lyric-e-1-1').boundingBox(),existing=await page.getByTestId('real-lyric-e-6-1').boundingBox();if(!added||!existing)throw Error('Missing lyric owner');expect(added.y+added.height).toBeLessThanOrEqual(existing.y+1);
 await page.getByRole('button',{name:'Concert Key',exact:true}).click();await page.getByLabel('Mode',{exact:true}).selectOption('major');await page.getByLabel('Confirm source key:').check();await page.getByLabel('New concert key').selectOption('1');await page.getByRole('button',{name:'Apply concert key',exact:true}).click();await expect(page.getByTestId('real-concert-key')).toHaveText('Concert key: G major');
 await page.getByRole('button',{name:'Instrument Scores →',exact:true}).click();await expect(page.getByRole('button',{name:/Alto Saxophone/})).toBeDisabled();await page.getByRole('button',{name:'← Concert Score',exact:true}).click();
 const downloadPromise=page.waitForEvent('download');await page.getByRole('button',{name:'Save',exact:true}).click();const dl=await downloadPromise;const saved=await readFile((await dl.path())!,'utf8');expect(saved).toContain('Niềm tin mới');expect(saved).toContain('<fifths>1</fifths>');
 await expect(page.getByRole('dialog',{name:'Confirm downloaded concert file'})).toBeVisible();await page.getByRole('button',{name:'I retained the downloaded file'}).click();
 await page.getByRole('button',{name:'Instrument Scores →',exact:true}).click();
 for(const id of ['Alto Saxophone','Soprano Saxophone','Tenor Saxophone']){await page.getByRole('button',{name:new RegExp(id)}).click();await expect(page.getByRole('button',{name:'Export instrument MusicXML'})).toBeEnabled({timeout:15000});const out=page.waitForEvent('download');await page.getByRole('button',{name:'Export instrument MusicXML'}).click();const result=await out;const xml=await readFile((await result.path())!,'utf8');expect(xml).toContain('<transpose>');expect(xml).toContain('Niềm tin mới');}
 await page.keyboard.press('Control+z');await expect(page.getByRole('button',{name:'Export instrument MusicXML'})).toBeEnabled({timeout:15000});await page.screenshot({path:'evidence/task02/real-sax-generated.png',fullPage:true});
 await page.getByRole('button',{name:'← Concert Score',exact:true}).click();await page.getByRole('button',{name:'Open MusicXML',exact:true}).click();await page.locator('input[type=file]').setInputFiles({name:'saved-concert.musicxml',mimeType:'application/vnd.recordare.musicxml+xml',buffer:Buffer.from(saved)});await expect(page.getByTestId('real-concert-key')).toHaveText('Concert key: G major');await expect(page.locator('.working-pane .real-score')).toContainText('Niềm tin mới');
});
