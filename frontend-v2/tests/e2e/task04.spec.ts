import {test,expect} from '@playwright/test';
import fs from 'node:fs';
const ownedReviews=new Set<string>();
test.beforeEach(async({page})=>{page.on('response',async response=>{if(response.request().method()==='POST'&&/\/api\/v1\/reviews$/.test(response.url())&&response.status()===201){try{ownedReviews.add((await response.json()).id);}catch{/* context closed */}}});});
test.afterEach(async({request})=>{for(const id of ownedReviews)await request.delete('/api/v1/reviews/'+id).catch(()=>{});ownedReviews.clear();});

const evidence='/home/dtran/music-sheet-transposer/frontend-v2/evidence/task04';
test('PDF draft keeps source and review identity through correction, undo, source confirmation and MusicXML save',async({page})=>{
 test.setTimeout(120000);test.skip(!fs.existsSync(evidence+'/PDF-01-recognition.json'),'Private recognition replay is local evidence only.');
 const captured=JSON.parse(fs.readFileSync(evidence+'/PDF-01-recognition.json','utf8'));
 let recognitions=0;
 await page.route('**/api/v1/recognize',route=>{recognitions++;return route.fulfill({json:captured});});
 await page.goto('/');
 await page.locator('input[type=file]').first().setInputFiles('/mnt/c/Users/dtran/Downloads/music sample/TienBuocVaoNhaChua_hn.pdf');
 await expect(page.getByText('OMR draft · manual correction required')).toBeVisible({timeout:60000});
 await expect(page.getByTitle('Original PDF source')).toBeVisible();await expect(page.getByLabel('Original PDF page 1')).toBeVisible();await expect(page.getByText('Displaying original PDF…')).toHaveCount(0);
 await page.screenshot({path:evidence+'/real-pdf-draft-key-corrected.png',fullPage:true});const head=page.locator('[data-testid^="real-head-"]').first();await head.click();
 const voice=page.getByLabel('Selected event voice');await expect(voice).toBeVisible();
 const ids:string[]=[];page.on('request',request=>{const match=/reviews\/([^/]+)\/(events|undo|redo|verify)/.exec(request.url());if(match)ids.push(match[1]);});
 const oldOctave=await page.getByLabel('Selected note octave').inputValue();await page.getByLabel('Selected note octave').selectOption(oldOctave==='5'?'4':'5');
 await expect(page.getByRole('button',{name:'↶ Undo',exact:true})).toBeEnabled({timeout:20000});
 await page.getByRole('button',{name:'↶ Undo',exact:true}).click();
 await page.getByRole('button',{name:'↷ Redo',exact:true}).click();
 await expect(page.getByRole('button',{name:'Save',exact:true})).toBeEnabled({timeout:20000});await page.getByTestId('real-head-e-102').focus();await page.keyboard.press('Enter');const dotReply=page.waitForResponse(r=>r.request().method()==='PATCH'&&r.url().endsWith('/events/e-102'));await page.getByRole('button',{name:'Correct missing quarter-note dot'}).click();const corrected=await(await dotReply).json();const bar=corrected.score.parts.flatMap((p:{measures:{number:string;actual_duration:string;voices:{events:{id:string;duration:string;onset:string}[]}[]}[]})=>p.measures).find((m:{number:string})=>m.number==='26');expect(bar.actual_duration).toBe('2');expect(bar.voices.flatMap((v:{events:{id:string;duration:string;onset:string}[]})=>v.events).map((e:{duration:string;onset:string})=>[e.onset,e.duration])).toEqual([['0','3/2'],['0','3/2'],['3/2','1/2'],['3/2','1/2']]);await page.screenshot({path:evidence+'/actual-e7-missing-dot-repaired.png',fullPage:true});
 await page.getByRole('button',{name:'Save',exact:true}).click();
 await expect(page.getByRole('status').last()).toContainText('confirm comparison');
 await page.getByLabel('I compared this revision').check();
 const download=page.waitForEvent('download');await page.getByRole('button',{name:'Save',exact:true}).click();const keyPrompt=page.getByRole('dialog',{name:'Confirm original Concert key'});if(await keyPrompt.isVisible()){await keyPrompt.getByLabel('Original key mode').selectOption('minor');await keyPrompt.getByLabel('Original Concert key',{exact:true}).selectOption('0');await keyPrompt.getByRole('button',{name:'Confirm and save MusicXML',exact:true}).click();}
 expect((await download).suggestedFilename()).toMatch(/\.musicxml$/);
 await page.getByRole('button',{name:'I retained the downloaded file'}).click();
 await expect(page.getByText('Concert file saved',{exact:true})).toBeVisible();
 expect(recognitions).toBe(1);expect(new Set(ids).size).toBe(1);
});

test('manual reconstruction after recognition failure is explicit, keeps source and permits new voices and grace editing',async({page})=>{
 test.setTimeout(90000);test.skip(!fs.existsSync('/mnt/c/Users/dtran/Downloads/music sample/TienBuocVaoNhaChua_hn.pdf'),'Private source is not published.');
 await page.route('**/api/v1/recognize',route=>route.fulfill({status:502,json:{detail:'Recognition produced multiple movements; no score selected.'}}));
 await page.goto('/');await page.locator('input[type=file]').first().setInputFiles('/mnt/c/Users/dtran/Downloads/music sample/TienBuocVaoNhaChua_hn.pdf');
 await expect(page.getByRole('status').last()).toContainText('multiple movements');
 await page.getByRole('button',{name:'Create empty working score from this source'}).click();
 await expect(page.getByTitle('Original PDF source')).toBeVisible();await expect(page.getByLabel('Original PDF page 1')).toBeVisible();await expect(page.getByText('Displaying original PDF…')).toHaveCount(0);
 await page.getByRole('button',{name:'More tools',exact:true}).click();await page.locator('summary').filter({hasText:'Measure, meter, key signature and staff correction'}).click();await page.getByLabel('Correction measure').selectOption('m-1');
 await page.getByRole('button',{name:'Choose this insertion position'}).click();
 await page.getByRole('button',{name:'Quarter note',exact:true}).click();
 const head=page.locator('[data-testid^="real-head-"]').first();await expect(head).toBeVisible();await head.click();
 await page.getByLabel('Selected event voice').fill('2');await page.getByLabel('Selected event voice').press('Tab');
 await expect(page.getByLabel('Selected event voice')).toHaveValue('2');
 await page.getByRole('button',{name:'Add slashed grace note before'}).click();
 await expect(page.locator('.working-pane [data-event-id]')).toHaveCount(2);
 await page.locator('.working-pane [data-event-id][data-duration=""]').focus();await page.keyboard.press('Enter');await page.getByRole('button',{name:'Notes',exact:true}).click();const graceEdit=page.waitForResponse(r=>r.request().method()==='PATCH'&&/\/events\//.test(r.url()));await page.getByRole('button',{name:'32nd note',exact:true}).click();const changed=await graceEdit;expect(changed.status()).toBe(200);const projection=await changed.json();const grace=projection.score.parts.flatMap((p:{measures:{voices:{events:{grace:boolean;notated_duration:{type:string}}[]}[]}[]})=>p.measures.flatMap(m=>m.voices.flatMap(v=>v.events))).find((e:{grace:boolean})=>e.grace);expect(grace.notated_duration.type).toBe('32nd');await expect(page.locator('.working-pane [data-event-id]')).toHaveCount(2);
 await page.screenshot({path:evidence+'/manual-working-score.png',fullPage:true});
});

test('new correction tools persist short dotted notes, expressions and explicit meter without shifting later notes',async({page})=>{
 await page.goto('/');await page.locator('input[type=file]').first().setInputFiles('tests/fixtures/task02.musicxml');
 await expect(page.getByTestId('real-head-e-2')).toBeVisible();await page.getByTestId('real-head-e-2').focus();await page.keyboard.press('Enter');
 await page.getByRole('button',{name:'Notes',exact:true}).click();await page.getByRole('button',{name:'64th note',exact:true}).click();
 await expect(page.getByTestId('real-head-e-2')).toHaveAttribute('data-duration','1/16');
 await page.getByRole('button',{name:'Double dot',exact:true}).click();await expect(page.getByTestId('real-head-e-2')).toHaveAttribute('data-duration','7/64');
 await page.getByLabel('Selected note expression').selectOption('fermata:normal');await page.getByRole('button',{name:'Add expression'}).click();
 await page.getByRole('button',{name:'More tools',exact:true}).click();await page.locator('summary').filter({hasText:'Measure, meter, key signature and staff correction'}).click();await page.getByLabel('Correction measure').selectOption('m-3');await page.getByLabel('Measure correction value').fill('3/8');await page.getByRole('button',{name:'Apply measure correction'}).click();
 await expect(page.getByTestId('real-head-e-9')).toHaveAttribute('data-duration','1');
 const download=page.waitForEvent('download');await page.getByRole('button',{name:'Save',exact:true}).click();const file=await download;const xml=fs.readFileSync((await file.path())!,'utf8');expect(xml).toContain('<beats>3</beats>');expect(xml).toContain('<beat-type>8</beat-type>');expect(xml).toContain('<fermata>normal</fermata>');expect(xml).toMatch(/<type>64th<\/type>\s*<dot\s*\/>\s*<dot\s*\/>/);
});
