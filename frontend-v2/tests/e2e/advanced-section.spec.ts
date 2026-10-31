import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
const owned=new Set<string>();
test.beforeEach(async({page})=>page.on('response',async r=>{if(r.request().method()==='POST'&&r.url().endsWith('/reviews')&&r.ok())owned.add((await r.json()).id);}));
test.afterEach(async({request})=>{for(const id of owned)await request.delete('/api/v1/reviews/'+id);owned.clear();});
async function load(page:import('@playwright/test').Page){
 const xml=(await readFile('tests/fixtures/task02.musicxml','utf8')).replace('<note>','<harmony><root><root-step>F</root-step></root><kind>major</kind></harmony><note>');
 const response=page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/reviews'));
 await page.goto('/');await page.locator('input[type=file]').setInputFiles({name:'advanced.musicxml',mimeType:'application/xml',buffer:Buffer.from(xml)});
 await expect(page.getByTestId('real-head-e-1')).toBeVisible();return {initial:await(await response).json(),xml};
}
for(const stage2 of [false,true])test('section mouse selection, preview, append, independent score and Undo: '+(stage2?'instrument':'concert'),async({page})=>{
 const {initial,xml}=await load(page);
 if(stage2){await page.getByRole('button',{name:'Instrument Scores →',exact:true}).click();await page.getByRole('button',{name:/Alto Saxophone/}).click();}
 const editor=stage2?page.locator('.instrument-editor'):page.locator('.real-workspace').first();
 await editor.getByRole('button',{name:'Create Key Change Section',exact:true}).click();
 const dialog=page.getByRole('dialog',{name:'Create Key Change Section'});
 await editor.getByRole('button',{name:'Select measure 1',exact:true}).click();
 await editor.getByRole('button',{name:'Select measure 2',exact:true}).click();
 await expect(dialog.getByLabel('Section last measure')).toHaveValue('m-2');
 await expect(dialog.getByLabel('Section Interval in tones')).toHaveText('0.0');
 await dialog.getByRole('button',{name:'Section Increase interval by half a tone'}).click();
 await expect(dialog.getByLabel('Section Interval in tones')).toHaveText('+0.5');
 const preview=page.waitForResponse(r=>r.url().endsWith('/sections/preview'));
 await dialog.getByRole('button',{name:'Preview section',exact:true}).click();const proposed=await(await preview).json();
 expect(proposed.section.count).toBe(2);expect(proposed.preview.score.parts[0].measures).toHaveLength(5);
 const live=await(await page.request.get('/api/v1/reviews/'+proposed.preview.id)).json();expect(live.score.parts[0].measures).toHaveLength(3);
 await page.screenshot({path:'evidence/advanced-v1/preview-'+(stage2?'instrument':'concert')+'.png',fullPage:true});
 const applied=page.waitForResponse(r=>r.url().endsWith('/sections/append'));
 await dialog.getByRole('button',{name:'Apply section',exact:true}).click();const result=await(await applied).json();
 expect(result.score.parts[0].measures).toHaveLength(5);await expect(dialog).toHaveCount(0);
 const out=Buffer.from(result.musicxml_base64,'base64').toString('utf8');
 expect(out).toContain('light-light');expect(out).toContain('Niềm');
 if(!stage2)expect(out).toContain('<root-step>G</root-step>');
 expect(Buffer.from((await(await page.request.get('/api/v1/reviews/'+initial.id)).json()).musicxml_base64,'base64').toString('utf8')).toBe(stage2?xml:out);
 const undo=page.waitForResponse(r=>r.url().endsWith('/undo'));await page.locator('.app-header').getByRole('button',{name:'↶ Undo',exact:true}).click();expect((await(await undo).json()).score.parts[0].measures).toHaveLength(3);
 await page.locator('.app-header').getByRole('button',{name:'↷ Redo',exact:true}).click();
 const download=page.waitForEvent('download');await page.locator('.app-header').getByRole('button',{name:'Save',exact:true}).click();const bytes=await readFile((await(await download).path())!);
 expect(bytes.toString('utf8')).toContain('number="5"');
 await page.getByRole('button',{name:'I retained the downloaded file'}).click();
 const reopened=await page.request.post('/api/v1/reviews',{multipart:{musicxml:{name:'section.musicxml',mimeType:'application/xml',buffer:bytes}}});expect(reopened.ok()).toBeTruthy();const restored=await reopened.json();owned.add(restored.id);expect(restored.score.parts[0].measures).toHaveLength(5);
});
test('Concert key stepper is non-mutating until Apply and source key stays editable',async({page})=>{
 const {initial}=await load(page);
 await page.getByRole('button',{name:'Concert Key',exact:true}).click();const panel=page.locator('#concert-key-panel');
 await expect(panel.getByLabel('Source key',{exact:true})).toHaveValue('-1');
 await panel.getByRole('button',{name:'Decrease interval by half a tone',exact:true}).click();await expect(panel.getByLabel('Interval in tones',{exact:true})).toHaveText('-0.5');
 await panel.getByLabel('Mode',{exact:true}).selectOption('minor');await panel.getByLabel('Source key',{exact:true}).selectOption('0');
 await expect(panel.getByLabel('New concert key')).toHaveValue('5');
 expect((await(await page.request.get('/api/v1/reviews/'+initial.id)).json()).revision).toBe(initial.revision);
 await panel.getByRole('checkbox').check();await panel.getByRole('button',{name:'Preview concert key'}).click();await expect(panel.locator('.concert-preview svg').first()).toBeVisible();
 expect((await(await page.request.get('/api/v1/reviews/'+initial.id)).json()).revision).toBe(initial.revision);
 await panel.getByRole('button',{name:'Apply concert key'}).click();await expect(page.getByTestId('real-concert-key')).toContainText('G♯ minor');
});
test('Cancel and rejected tie boundary do not change the score',async({page})=>{
 await page.goto('/');await page.locator('input[type=file]').setInputFiles('tests/fixtures/accidental-tie.musicxml');await expect(page.getByTestId('real-head-e-1')).toBeVisible();
 await page.getByRole('button',{name:'Create Key Change Section'}).click();const d=page.getByRole('dialog',{name:'Create Key Change Section'});
 await d.getByRole('button',{name:'Preview section'}).click();await expect(d.getByRole('alert')).toContainText('complete tie');await expect(d.getByRole('button',{name:'Apply section'})).toBeDisabled();
 await d.getByRole('button',{name:'Cancel',exact:true}).click();await expect(d).toHaveCount(0);await expect(page.getByText('Imported MusicXML · unchanged')).toBeVisible();
});

test('Changing or closing Concert preview releases its temporary review',async({page})=>{
 const {initial}=await load(page);await page.getByRole('button',{name:'Concert Key',exact:true}).click();const panel=page.locator('#concert-key-panel');
 await panel.getByRole('checkbox').check();const created=page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/reviews'));
 await panel.getByRole('button',{name:'Preview concert key'}).click();const temporary=await(await created).json();await expect(panel.locator('.concert-preview')).toBeVisible();
 const released=page.waitForResponse(r=>r.request().method()==='DELETE'&&r.url().endsWith('/reviews/'+temporary.id));
 await panel.getByRole('button',{name:'Increase interval by half a tone'}).click();await released;
 expect((await page.request.get('/api/v1/reviews/'+temporary.id)).status()).toBe(404);
 expect((await(await page.request.get('/api/v1/reviews/'+initial.id)).json()).revision).toBe(initial.revision);
});

test('A delayed Preview cannot authorize a different measure range',async({page})=>{
 await load(page);await page.getByRole('button',{name:'Create Key Change Section'}).click();const panel=page.getByRole('dialog',{name:'Create Key Change Section'});
 let release!:()=>void;const held=new Promise<void>(resolve=>{release=resolve;});let intercepted!:()=>void;const arrived=new Promise<void>(resolve=>{intercepted=resolve;});
 await page.route('**/sections/preview',async route=>{const response=await route.fetch();intercepted();await held;await route.fulfill({response});});
 await panel.getByRole('button',{name:'Preview section',exact:true}).click();await arrived;
 await page.getByRole('button',{name:'Select measure 2',exact:true}).click();release();
 await expect(panel.getByRole('button',{name:'Preview section',exact:true})).toBeEnabled();await expect(panel.getByRole('button',{name:'Apply section',exact:true})).toBeDisabled();await expect(panel.locator('.section-preview')).toHaveCount(0);
});
