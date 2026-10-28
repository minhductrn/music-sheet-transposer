import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
const sessions=new Set<string>();
test.beforeEach(async({page})=>{page.on('response',async r=>{if(r.request().method()==='POST'&&/\/api\/v1\/reviews$/.test(r.url())&&r.status()===201){try{sessions.add((await r.json()).id);}catch{/* closed context */}}});});
test.afterEach(async({request})=>{for(const id of sessions)await request.delete(`/api/v1/reviews/${id}`).catch(()=>{});sessions.clear();});
test('Stage2 independent editor, Fit, added improv measure, cached variants, XML reimport and PDF',async({page})=>{
 test.setTimeout(120000);await page.goto('/');await page.locator('input[type=file]').setInputFiles('tests/fixtures/task02.musicxml');await expect(page.getByTestId('real-head-e-1')).toBeVisible();
 let d=page.waitForEvent('download');await page.getByRole('button',{name:'Save',exact:true}).click();await d;await page.getByRole('button',{name:'I retained the downloaded file'}).click();
 await page.getByRole('button',{name:'Instrument Scores →'}).click();await page.getByRole('button',{name:/Alto Saxophone/}).click();
 const editor=page.locator('.instrument-editor'),working=editor.locator('.working-pane'),source=editor.locator('.source-pane');
 await expect(working.getByTestId('real-head-e-1')).toBeVisible();await expect(source.locator('[data-event-id]')).toHaveCount(0);
 const original=await source.locator('.real-score').textContent();
 for(const pane of ['source','working']){await editor.getByRole('button',{name:`Fit ${pane} score`}).click();await expect(page.locator('.instrument-notice')).toContainText('fitted to pane width');}
 await working.getByTestId('real-head-e-2').focus();await page.keyboard.press('Enter');await editor.getByRole('button',{name:'Edit lyrics',exact:true}).click();await page.getByRole('textbox',{name:'Lyric syllable'}).fill('Giang tấu tiếng Việt');await page.getByRole('textbox',{name:'Lyric syllable'}).press('Enter');
 await expect(working.locator('.real-score')).toContainText('Giang tấu tiếng Việt');
 await editor.getByRole('button',{name:'Add measure',exact:true}).click();await expect(working.getByRole('button',{name:'Gap in measure 4, voice 1'})).toBeVisible();
 await working.getByRole('button',{name:'Gap in measure 4, voice 1'}).focus();await page.keyboard.press('Enter');await editor.getByRole('button',{name:'Quarter note',exact:true}).click();await expect(working.locator('[data-event-id]')).toHaveCount(10);
 await expect(source.locator('.real-score')).toHaveText(original!);
 await page.getByRole('button',{name:/Soprano Saxophone/}).click();await expect(working.locator('.real-score')).not.toContainText('Giang tấu tiếng Việt');
 await page.getByRole('button',{name:/Alto Saxophone/}).click();await expect(working.locator('.real-score')).toContainText('Giang tấu tiếng Việt');await expect(working.locator('[data-event-id]')).toHaveCount(10);
 await page.getByRole('combobox',{name:'Instrument direction'}).selectOption('down');await page.getByRole('button',{name:/Alto Saxophone/}).click();await expect(working.locator('.real-score')).not.toContainText('Giang tấu tiếng Việt');await page.getByRole('combobox',{name:'Instrument direction'}).selectOption('up');await page.getByRole('button',{name:/Alto Saxophone/}).click();await expect(working.locator('.real-score')).toContainText('Giang tấu tiếng Việt');
 d=page.waitForEvent('download');await page.getByRole('button',{name:'Export instrument MusicXML'}).click();const xml=await readFile((await(await d).path())!);d=page.waitForEvent('download');await page.locator('.app-header').getByRole('button',{name:'Export saved MusicXML',exact:true}).click();expect(await readFile((await(await d).path())!)).toEqual(await readFile('tests/fixtures/task02.musicxml'));expect(xml.toString()).toContain('Giang tấu tiếng Việt');expect(xml.toString()).toContain('number="4"');
 d=page.waitForEvent('download');await editor.getByRole('button',{name:'Export PDF',exact:true}).click();const pdf=await d;expect(pdf.suggestedFilename()).toContain('alto-up-');const pdfBytes=await readFile((await pdf.path())!);expect(pdfBytes.subarray(0,5).toString()).toBe('%PDF-');await pdf.saveAs('evidence/task02/stage2-improv.pdf');
 await page.screenshot({path:'evidence/task02/stage2-editing.png',fullPage:true});
 // Reimport the instrument export through the normal importer, without replacing the source file.
 const imported=await page.request.post('/api/v1/reviews',{multipart:{musicxml:{name:'instrument.musicxml',mimeType:'application/xml',buffer:xml}}});expect(imported.status()).toBe(201);const review=await imported.json();sessions.add(review.id);expect(review.score.parts[0].measures).toHaveLength(4);expect(review.score.lyrics.some((l:{text:string})=>l.text==='Giang tấu tiếng Việt')).toBeTruthy();
});

test('Stage2 busy operation locks navigation, output switches and exports until edits settle',async({page})=>{
 await page.goto('/');await page.locator('input[type=file]').setInputFiles('tests/fixtures/task02.musicxml');await expect(page.getByTestId('real-head-e-1')).toBeVisible();let d=page.waitForEvent('download');await page.getByRole('button',{name:'Save',exact:true}).click();await d;await page.getByRole('button',{name:'I retained the downloaded file'}).click();await page.getByRole('button',{name:'Instrument Scores →'}).click();await page.getByRole('button',{name:/Alto Saxophone/}).click();
 const editor=page.locator('.instrument-editor');await expect(editor.getByTestId('real-head-e-2')).toBeVisible();await editor.getByTestId('real-head-e-2').focus();await page.keyboard.press('Enter');
 let release!:()=>void;const wait=new Promise<void>(resolve=>release=resolve);
 await page.route('**/api/v1/reviews/*/events/e-2',async route=>{await wait;await route.continue();});
 await editor.getByRole('button',{name:'Small',exact:true}).click();
 for(const name of ['← Concert Score','Open MusicXML','Home','Export instrument MusicXML'])await expect(page.getByRole('button',{name,exact:true})).toBeDisabled();
 await expect(page.getByRole('button',{name:/Soprano Saxophone/})).toBeDisabled();release();
 await expect(editor.getByRole('button',{name:'Save',exact:true})).toBeEnabled();await page.getByRole('button',{name:/Soprano Saxophone/}).click();await expect(editor.locator('.workspace-heading strong')).toContainText('Soprano');await expect(editor.getByRole('button',{name:'Save',exact:true})).toBeEnabled();await page.getByRole('button',{name:/Alto Saxophone/}).click();await expect(editor.locator('.workspace-heading strong')).toContainText('Alto');await expect(editor.getByRole('button',{name:'Save',exact:true})).toBeEnabled();
 d=page.waitForEvent('download');await editor.getByRole('button',{name:'Save',exact:true}).click();const xml=await readFile((await(await d).path())!,'utf8');expect(xml).toContain('small');await page.getByRole('button',{name:'I retained the downloaded file'}).click();await expect(page.getByRole('button',{name:'← Concert Score'})).toBeEnabled();
});

test('PDF exports concert and instrument from PO file and paginates a long synthetic score',async({page})=>{
 test.setTimeout(120000);
 const sample=process.env.AI_SDF_TASK02_SAMPLE;test.skip(!sample);
 await page.goto('/');await page.locator('input[type=file]').setInputFiles(sample!);await expect(page.locator('.working-pane [data-event-id]')).toHaveCount(63);
 let d=page.waitForEvent('download');await page.getByRole('button',{name:'Export PDF',exact:true}).click();await(await d).saveAs('evidence/task02/real-concert.pdf');
 d=page.waitForEvent('download');await page.getByRole('button',{name:'Save',exact:true}).click();await d;await page.getByRole('button',{name:'I retained the downloaded file'}).click();await page.getByRole('button',{name:'Instrument Scores →'}).click();await page.getByRole('button',{name:/Alto Saxophone/}).click();await expect(page.locator('.instrument-editor .working-pane [data-event-id]')).toHaveCount(63);
 d=page.waitForEvent('download');await page.locator('.instrument-editor').getByRole('button',{name:'Export PDF',exact:true}).click();await(await d).saveAs('evidence/task02/real-instrument.pdf');
 await page.getByRole('button',{name:'← Concert Score'}).click();page.once('dialog',d=>d.accept());const text=await readFile('tests/fixtures/task02.musicxml','utf8');const first=text.match(/<measure number="1">[\s\S]*?<\/measure>/)![0];const long=text.replace(/<measure number="2">[\s\S]*<\/part>/,Array.from({length:39},(_,i)=>first.replace('number="1"',`number="${i+2}"`).replace(/<attributes>[\s\S]*?<\/attributes>/,'')).join('')+'</part>');
 await page.locator('input[type=file]').setInputFiles({name:'long-synthetic.musicxml',mimeType:'application/xml',buffer:Buffer.from(long)});await expect(page.locator('.working-pane [data-event-id]')).toHaveCount(120,{timeout:20000});
 d=page.waitForEvent('download');await page.getByRole('button',{name:'Export PDF',exact:true}).click();await(await d).saveAs('evidence/task02/long-synthetic.pdf');
});
