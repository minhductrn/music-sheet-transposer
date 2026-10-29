import {test,expect,type Page} from '@playwright/test';
const owned=new WeakMap<Page,Set<string>>();
test.beforeEach(async({page})=>{const ids=new Set<string>();owned.set(page,ids);page.on('response',async r=>{if(r.request().method()==='POST'&&r.url().endsWith('/reviews')&&r.ok())ids.add((await r.json()).id);});});
test.afterEach(async({page})=>{for(const id of owned.get(page)??[])await page.request.delete('/api/v1/reviews/'+id);});
function score(rest:boolean){return '<score-partwise><movement-title>Tuplet extension</movement-title><part-list><score-part id="P1"><part-name>Concert</part-name></score-part></part-list><part id="P1"><measure number="1"><attributes><divisions>4</divisions><key><fifths>0</fifths><mode>major</mode></key><time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes><note>'+(rest?'<rest/>':'<pitch><step>C</step><octave>4</octave></pitch>')+'<duration>4</duration><voice>1</voice><type>quarter</type></note><forward><duration>8</duration></forward><note><pitch><step>G</step><octave>4</octave></pitch><duration>4</duration><voice>1</voice><type>quarter</type></note></measure></part></score-partwise>';}
for(const [name,rest,instrument] of [['notes',false,false],['rests',true,false],['instrument',false,true]] as const)test('direct tuplet divide, ratio edit and remove: '+name,async({page})=>{
 test.setTimeout(60000);await page.goto('/');await page.locator('input[type=file]').setInputFiles({name:'tuplets.musicxml',mimeType:'application/xml',buffer:Buffer.from(score(rest))});await expect(page.getByTestId('real-head-e-1')).toBeVisible();
 if(instrument){await page.getByRole('button',{name:'Instrument Scores →',exact:true}).click();await page.getByRole('button',{name:/Alto Saxophone/}).click();}
 const editor=instrument?page.locator('.instrument-editor'):page.locator('.real-workspace').first();
 await editor.getByTestId('real-head-e-1').click();await editor.getByRole('button',{name:'Groups',exact:true}).click();await expect(editor.getByLabel('Tuplet ratio',{exact:true})).toContainText('4:3');await expect(editor.getByLabel('Tuplet ratio',{exact:true})).toContainText('8:6');
 let response=page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/tuplets'));await editor.getByRole('button',{name:'Divide selected duration',exact:true}).click();let result=await response;expect(result.ok()).toBeTruthy();let data=await result.json();
 const members=data.score.parts.flatMap((p:{measures:{voices:{events:{id:string;onset:string;duration:string;kind:string}[]}[]}[]})=>p.measures.flatMap(m=>m.voices.flatMap(v=>v.events))).filter((e:{onset:string})=>Number(e.onset.split('/')[0])/Number(e.onset.split('/')[1]??1)<1);
 expect(members).toHaveLength(3);expect(members.every((e:{duration:string})=>e.duration==='1/3')).toBeTruthy();
 async function selectMembers(){await editor.getByRole('button',{name:'Groups',exact:true}).click();for(const e of members)await editor.getByTestId('real-head-'+e.id).click();}
 await selectMembers();await editor.getByLabel('Tuplet ratio',{exact:true}).selectOption('6:4');await editor.getByText('Tuplet appearance',{exact:true}).click();await editor.getByLabel('Tuplet placement').selectOption('below');await editor.getByLabel('Tuplet number').selectOption('both');response=page.waitForResponse(r=>r.url().endsWith('/tuplets')&&r.request().method()==='POST');await editor.getByRole('button',{name:'Apply to written selection',exact:true}).click();result=await response;expect(result.ok()).toBeTruthy();
 await page.screenshot({path:'evidence/task04/tuplets-active-'+name+'.png',fullPage:true});await selectMembers();response=page.waitForResponse(r=>r.url().endsWith('/tuplets')&&r.request().method()==='POST');await editor.getByRole('button',{name:'Remove selected tuplet',exact:true}).click();result=await response;expect(result.ok()).toBeTruthy();data=await result.json();expect(Buffer.from(data.musicxml_base64,'base64').toString()).not.toContain('<time-modification>');await page.screenshot({path:'evidence/task04/tuplets-'+name+'.png',fullPage:true});
});


test('global Undo and Redo restore a dragged instrument pitch without changing Concert',async({page})=>{
 test.setTimeout(60000);await page.goto('/');const opened=page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/reviews'));await page.locator('input[type=file]').setInputFiles({name:'history.musicxml',mimeType:'application/xml',buffer:Buffer.from(score(false))});const concert=await (await opened).json();await expect(page.getByTestId('real-head-e-1')).toBeVisible();await page.getByRole('button',{name:'Instrument Scores →',exact:true}).click();await page.getByRole('button',{name:/Alto Saxophone/}).click();
 const head=page.locator('.instrument-editor').getByTestId('real-head-e-1');await expect(head).toBeVisible();await expect(page.locator('.instrument-editor').getByRole('button',{name:'Save',exact:true})).toBeEnabled();await head.click();const pitch=await head.getAttribute('data-pitch');const box=(await head.boundingBox())!;
 const changed=page.waitForResponse(r=>r.request().method()==='PATCH'&&r.url().endsWith('/events/e-1'));await page.mouse.move(box.x+box.width/2,box.y+box.height/2);await page.mouse.down();await page.mouse.move(box.x+box.width/2,box.y+box.height/2-12,{steps:4});await page.mouse.up();expect((await changed).ok()).toBeTruthy();await expect(head).not.toHaveAttribute('data-pitch',pitch!);const moved=await head.getAttribute('data-pitch');
 const top=page.locator('.app-header');await expect(top.getByRole('button',{name:'↶ Undo',exact:true})).toBeEnabled();await top.getByRole('button',{name:'↶ Undo',exact:true}).click();await expect(head).toHaveAttribute('data-pitch',pitch!);await top.getByRole('button',{name:'↷ Redo',exact:true}).click();await expect(head).toHaveAttribute('data-pitch',moved!);
 expect((await (await page.request.get('/api/v1/reviews/'+concert.id)).json()).musicxml_base64).toBe(concert.musicxml_base64);
});


for(const instrument of [false,true])test('Small changes only display size in Compare and Edit Only '+(instrument?'instrument':'Concert'),async({page})=>{
 test.setTimeout(60000);await page.goto('/');await page.locator('input[type=file]').setInputFiles({name:'small.musicxml',mimeType:'application/xml',buffer:Buffer.from(score(false))});await expect(page.getByTestId('real-head-e-1')).toBeVisible();if(instrument){await page.getByRole('button',{name:'Instrument Scores →',exact:true}).click();await page.getByRole('button',{name:/Alto Saxophone/}).click();}
 const editor=instrument?page.locator('.instrument-editor'):page.locator('.real-workspace').first();const head=editor.getByTestId('real-head-e-1');await expect(head).toBeVisible();await head.click();const pitch=await head.getAttribute('data-pitch'),duration=await head.getAttribute('data-duration');const normal=(await head.boundingBox())!;
 for(const mode of ['Compare','Edit Only']){const close=editor.getByRole('button',{name:'Close selected note tools'});if(await close.isVisible())await close.click();await editor.getByRole('button',{name:mode,exact:true}).click();await head.click();const change=page.waitForResponse(r=>r.request().method()==='PATCH'&&r.url().endsWith('/events/e-1'));await editor.getByRole('button',{name:'Small',exact:true}).click();const result=await change;expect(result.ok()).toBeTruthy();const data=await result.json();const current=data.score.parts[0].measures[0].voices[0].events.find((e:{id:string})=>e.id==='e-1');expect(current.display_size).toBe('small');await expect(head).toHaveAttribute('data-pitch',pitch!);await expect(head).toHaveAttribute('data-duration',duration!);await expect.poll(async()=>(await head.boundingBox())!.width).toBeLessThan(normal.width*.95);const reset=page.waitForResponse(r=>r.request().method()==='PATCH'&&r.url().endsWith('/events/e-1'));await editor.getByRole('button',{name:'Normal',exact:true}).click();expect((await reset).ok()).toBeTruthy();}
});


test('global Validate, Save As, Save and saved export target the active instrument editor',async({page})=>{
 await page.goto('/');await page.locator('input[type=file]').setInputFiles({name:'actions.musicxml',mimeType:'application/xml',buffer:Buffer.from(score(false))});await expect(page.getByTestId('real-head-e-1')).toBeVisible();await page.getByRole('button',{name:'Instrument Scores →',exact:true}).click();await page.getByRole('button',{name:/Alto Saxophone/}).click();const editor=page.locator('.instrument-editor');await expect(editor.getByTestId('real-head-e-1')).toBeVisible();const top=page.locator('.app-header');
 await top.getByRole('button',{name:'Validate',exact:true}).click();await expect(page.locator('.instrument-work .real-validation')).toBeVisible();await page.locator('.instrument-work .real-validation').getByRole('button',{name:'Close',exact:true}).click();
 await top.getByRole('button',{name:'Save As',exact:true}).click();await expect(editor.getByLabel('Filename')).toBeVisible();await editor.locator('.real-save-popover').getByRole('button',{name:'Cancel',exact:true}).click();
 const download=page.waitForEvent('download');await top.getByRole('button',{name:'Save',exact:true}).click();const file=await download;expect(file.suggestedFilename()).toContain('alto-down');await page.getByRole('dialog',{name:'Confirm downloaded instrument file'}).getByRole('button',{name:'I retained the downloaded file',exact:true}).click();await expect(top.getByRole('button',{name:'Export saved MusicXML',exact:true})).toBeEnabled();const exported=page.waitForEvent('download');await top.getByRole('button',{name:'Export saved MusicXML',exact:true}).click();expect((await exported).suggestedFilename()).toContain('alto-down');
});

test('English editor labels and tuplet commands follow every selected ratio',async({page})=>{
 await page.goto('/');await page.locator('input[type=file]').setInputFiles({name:'labels.musicxml',mimeType:'application/xml',buffer:Buffer.from(score(false))});await expect(page.getByTestId('real-head-e-1')).toBeVisible();
 await expect(page.getByRole('button',{name:'Add Chord',exact:true})).toHaveText('GAdd Chord');
 await page.getByTestId('real-head-e-1').click();await expect(page.getByLabel('Selected note duration').locator('option')).toHaveText(['Whole','Half','Quarter','Eighth','16th','32nd','64th']);
 await page.getByRole('button',{name:'Groups',exact:true}).click();
 for(const ratio of ['3:2','2:3','4:3','5:4','6:4','7:4','8:6','9:8']){
  await page.getByLabel('Tuplet ratio',{exact:true}).selectOption(ratio);
  await expect(page.getByLabel('Selected tuplet ratio explanation')).toContainText(ratio+': '+ratio.split(':')[0]+' written units in the time of '+ratio.split(':')[1]);
  await expect(page.getByRole('button',{name:'Divide selected duration',exact:true})).toHaveText('Divide duration · '+ratio);
  await expect(page.getByRole('button',{name:'Apply to written selection',exact:true})).toHaveText('Apply to selection · '+ratio);
 }
});

test('notifications dismiss and a measure text can move to the composer header with Undo',async({page})=>{
 const input=score(false).replace('<note>','<direction><direction-type><words>Composer example</words></direction-type></direction><note>');
 await page.goto('/');await page.locator('input[type=file]').setInputFiles({name:'composer-header.musicxml',mimeType:'application/xml',buffer:Buffer.from(input)});await expect(page.getByTestId('real-head-e-1')).toBeVisible();
 await page.getByRole('button',{name:'Select note area',exact:true}).click();await page.getByRole('button',{name:'Dismiss notification',exact:true}).click();await expect(page.locator('.notice')).toBeHidden();await page.getByRole('button',{name:'Select note area',exact:true}).click();
 await page.getByRole('button',{name:'Text',exact:true}).click();await page.getByRole('button',{name:'Score text Composer example',exact:true}).click();
 const changed=page.waitForResponse(r=>r.request().method()==='PATCH'&&r.url().includes('/texts/'));await page.getByRole('button',{name:'Move to composer header',exact:true}).click();const result=await changed;expect(result.ok()).toBeTruthy();const data=await result.json();expect(data.score.texts.find((t:{text:string})=>t.text==='Composer example').role).toBe('composer');
 for(const action of ['Working score zoom out','Working score zoom in']){await page.getByRole('button',{name:action,exact:true}).click();const author=page.getByRole('button',{name:'Score text Composer example',exact:true});await expect(author).toBeVisible();await expect.poll(async()=>{const a=await author.boundingBox(),n=await page.getByTestId('real-head-e-1').boundingBox();return !!a&&!!n&&a.y+a.height<n.y;}).toBeTruthy();}
 await page.getByRole('button',{name:'↶ Undo',exact:true}).click();await expect(page.getByRole('button',{name:'Score text Composer example',exact:true})).toBeVisible();
});

for(const instrument of [false,true])test('Small affects only one selected chord member '+(instrument?'instrument':'Concert'),async({page})=>{
 const input=score(false).replace('</note>','</note><note><chord/><pitch><step>E</step><octave>4</octave></pitch><duration>4</duration><voice>1</voice><type>quarter</type></note>');
 await page.goto('/');await page.locator('input[type=file]').setInputFiles({name:'small-chord.musicxml',mimeType:'application/xml',buffer:Buffer.from(input)});await expect(page.getByTestId('real-head-e-1')).toBeVisible();
 if(instrument){await page.getByRole('button',{name:'Instrument Scores →',exact:true}).click();await page.getByRole('button',{name:/Alto Saxophone/}).click();}
 const editor=instrument?page.locator('.instrument-editor'):page.locator('.real-workspace').first();await expect(editor.getByRole('button',{name:'Save',exact:true})).toBeEnabled();
 for(const mode of ['Compare','Edit Only']){
  await editor.getByRole('button',{name:mode,exact:true}).click();const lead=editor.getByTestId('real-head-e-1'),member=editor.getByTestId('real-head-e-2');await expect(member).toBeVisible();const beforeLead=(await lead.boundingBox())!.width,beforeMember=(await member.boundingBox())!.width;
  await member.click();const response=page.waitForResponse(r=>r.request().method()==='PATCH'&&r.url().endsWith('/events/e-2'));await editor.getByRole('button',{name:'Small',exact:true}).click();const data=await(await response).json();const notes=data.score.parts.flatMap((p:{measures:{voices:{events:{id:string;display_size:string}[]}[]}[]})=>p.measures.flatMap(m=>m.voices.flatMap(v=>v.events)));expect(notes.find((e:{id:string})=>e.id==='e-1').display_size).toBe('normal');expect(notes.find((e:{id:string})=>e.id==='e-2').display_size).toBe('small');
  await expect.poll(async()=>(await member.boundingBox())?.width??Infinity).toBeLessThan(beforeMember*.8);expect((await lead.boundingBox())!.width).toBeCloseTo(beforeLead,1);
  await editor.getByRole('button',{name:'Normal',exact:true}).click();await expect.poll(async()=>(await member.boundingBox())?.width??0).toBeGreaterThan(beforeMember*.95);
 }
});
