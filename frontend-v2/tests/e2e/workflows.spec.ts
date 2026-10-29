import { test,expect } from '@playwright/test';
import type { Page } from '@playwright/test';
import { point } from '../../src/notation';
const working=(page:Page)=>page.locator('.working-pane');
async function load(page:Page){await page.goto('/');await page.getByRole('button',{name:'Try Demo Score',exact:true}).click();await expect(working(page)).toBeVisible();}
async function clickHead(page:Page,id:string){await working(page).getByTestId('head-'+id).locator('ellipse').last().click();}
async function drag(page:Page,locator:ReturnType<Page['locator']>,dy:number){const box=await locator.boundingBox();if(!box)throw Error('No target');await page.mouse.move(box.x+box.width/2,box.y+box.height/2);await page.mouse.down();await page.mouse.move(box.x+box.width/2,box.y+box.height/2+dy,{steps:8});await page.mouse.up();}
async function shot(page:Page,name:string){await page.screenshot({path:'evidence/'+name+'.png',fullPage:true});}
test('Import, Compare, note pitch/size, undo and view continuity',async({page})=>{
 await load(page);await expect(page.locator('.source-pane')).toBeVisible();await shot(page,'compare-desktop');
 await clickHead(page,'n1');await page.getByRole('button',{name:'Small',exact:true}).click();await expect(working(page).getByTestId('head-n1')).toHaveAttribute('data-small','true');
 await drag(page,working(page).getByTestId('head-n1').locator('ellipse').last(),-20);await expect(working(page).getByTestId('head-n1')).toHaveAttribute('data-pitch','74');
 await page.getByRole('button',{name:'Edit Only',exact:true}).click();await expect(page.locator('.source-pane')).toHaveCount(0);await expect(working(page).getByTestId('head-n1')).toHaveAttribute('data-small','true');await shot(page,'edit-only-note-context');
 await page.getByRole('button',{name:'Undo',exact:true}).click();await expect(working(page).getByTestId('head-n1')).toHaveAttribute('data-pitch','67');
 await page.getByRole('button',{name:'Redo',exact:true}).click();await expect(working(page).getByTestId('head-n1')).toHaveAttribute('data-pitch','74');
 await page.getByRole('button',{name:'Compare',exact:true}).click();await expect(page.locator('.source-pane')).toBeVisible();
 await page.getByRole('button',{name:'Source zoom in'}).click();await expect(page.locator('.source-tools output')).toHaveText('95%');await expect(page.locator('.zoom output')).toHaveText('100%');
 const sep=page.getByRole('separator');await sep.focus();await page.keyboard.press('ArrowRight');await expect(sep).toHaveAttribute('aria-valuenow','50');
});
test('Delete chord head, delete event, gap insertion and 3:2 paths',async({page})=>{
 await load(page);await clickHead(page,'n2');await page.getByRole('button',{name:'Delete',exact:true}).click();await expect(working(page).getByTestId('head-n1')).toBeVisible();await expect(working(page).locator('.gap')).toHaveCount(0);
 await clickHead(page,'n3');await page.keyboard.press('Delete');await expect(working(page).getByTestId('gap-e2')).toBeVisible();await shot(page,'delete-gap');
 await working(page).getByTestId('gap-e2').click();await page.getByRole('button',{name:'Groups',exact:true}).click();await page.getByRole('button',{name:'♩♪ 3:2',exact:true}).click();await expect(working(page).getByTestId('gap-e2')).toHaveCount(0);await expect(working(page).getByText('3:2',{exact:true})).toHaveCount(1);await shot(page,'triplet-gap');
 await page.getByRole('button',{name:'Undo',exact:true}).click();await page.getByRole('button',{name:'Undo',exact:true}).click();await clickHead(page,'n1');await page.getByRole('button',{name:'Groups',exact:true}).click();await page.getByRole('button',{name:'♩♪ 3:2',exact:true}).click();await expect(working(page).getByTestId('head-n1')).toBeVisible();await expect(working(page).getByText('3:2',{exact:true})).toHaveCount(1);await shot(page,'triplet-convert');
});
test('Tie tool refuses empty insertion, duplicate safe, curve drag, remove and Undo',async({page})=>{
 await load(page);await clickHead(page,'n1');await page.getByRole('button',{name:'Tie',exact:true}).click();
 const score=working(page).locator('svg.score'),box=await score.boundingBox();if(!box)throw Error('No SVG');await page.mouse.click(box.x+350,box.y+300);await expect(working(page).locator('.note')).toHaveCount(8);await expect(page.locator('.anchor-menu')).toHaveCount(0);
 await clickHead(page,'n3');await expect(working(page).locator('.curve')).toHaveCount(2);
 await clickHead(page,'n1');await clickHead(page,'n3');await expect(working(page).locator('.curve')).toHaveCount(2);
 await page.getByRole('button',{name:'Select',exact:true}).click();const curve=working(page).locator('.curve').last();const path=curve.locator('path').last();await path.evaluate(e=>{e.setAttribute('data-hit','yes');});
 // Use the actual visible curve midpoint (quadratic at t=.5).
 const bounds=await score.boundingBox();if(!bounds)throw Error('No SVG');const midpoint=await curve.locator('path').last().evaluate(node=>{const path=node as SVGPathElement;const q=path.getPointAtLength(path.getTotalLength()/2);const p=path.ownerSVGElement!.createSVGPoint();p.x=q.x;p.y=q.y;const screen=p.matrixTransform(path.getScreenCTM()!);return {x:screen.x,y:screen.y};});await page.mouse.move(midpoint.x,midpoint.y);await page.mouse.down();await page.mouse.move(midpoint.x,midpoint.y+40,{steps:8});await page.mouse.up();
 await expect(curve).toHaveAttribute('data-direction','down');await shot(page,'tie-down');await page.getByRole('button',{name:'Delete selected',exact:true}).click();await expect(working(page).locator('.curve')).toHaveCount(1);await expect(working(page).getByTestId('head-n1')).toBeVisible();await page.getByRole('button',{name:'Undo',exact:true}).click();await expect(working(page).locator('.curve')).toHaveCount(2);
});
test('Unicode inline lyrics, navigation, verse, direct text and validation',async({page})=>{
 await load(page);await working(page).getByTestId('lyric-l1').click();await page.getByRole('textbox',{name:'Edit lyric'}).fill('Yêu thương');await page.keyboard.press('Tab');await expect(page.getByRole('textbox',{name:'Edit lyric'})).toHaveValue('tin');await page.keyboard.press('Escape');await expect(working(page).getByTestId('lyric-l1')).toContainText('Yêu thương');
 await clickHead(page,'n1');await page.getByRole('button',{name:'Add Verse',exact:true}).click();await expect(page.getByRole('textbox',{name:'Edit lyric'})).toBeFocused();await page.getByRole('textbox',{name:'Edit lyric'}).fill('Niềm vui');await page.keyboard.press('Enter');await expect(working(page).locator('.lyric')).toHaveCount(4);await shot(page,'lyrics-verse');
 await working(page).getByTestId('text-annotation').click();await page.getByRole('textbox',{name:'Edit score text'}).fill('ĐK: Hy vọng');await page.keyboard.press('Enter');await expect(working(page).getByTestId('text-annotation')).toHaveText('ĐK: Hy vọng');await drag(page,working(page).getByTestId('text-annotation'),20);
 await page.getByRole('button',{name:'Validate',exact:true}).click();await expect(page.locator('.validation')).toBeVisible();await page.getByRole('button',{name:'Collapse',exact:true}).click();await page.getByRole('button',{name:'Expand',exact:true}).click();await page.getByRole('button',{name:'Close validation'}).click();await expect(page.locator('.validation')).toHaveCount(0);
});
test('Save copy, concert metadata and Stage 2 saved-only independent outputs',async({page})=>{
 await load(page);await page.getByRole('button',{name:'Instrument Scores →',exact:true}).click();await expect(page.getByRole('button',{name:/Alto Saxophone/})).toBeDisabled();await expect(page.locator('.rail')).toHaveCount(0);await page.getByRole('button',{name:'← Back to Stage 1',exact:true}).click();
 await page.getByRole('button',{name:'Concert Key',exact:true}).click();await page.getByRole('button',{name:'Preview key change',exact:true}).click();await shot(page,'concert-preview');await page.getByRole('button',{name:'Save',exact:true}).click();
 await page.getByRole('button',{name:'Save As',exact:true}).click();await page.getByLabel('Filename').fill('Independent copy');await page.getByRole('button',{name:'Save Copy',exact:true}).click();await expect(page.getByText(/Simulated separate copy: Independent copy/)).toBeVisible();
 await clickHead(page,'n2');await page.getByRole('button',{name:'Delete',exact:true}).click();await page.getByRole('button',{name:'Instrument Scores →',exact:true}).click();await expect(page.getByText(/Unsaved Stage 1 changes are excluded/)).toBeVisible();
 await page.getByRole('button',{name:/Alto Saxophone/}).click();await expect(page.getByText('Simulated preview — notation is copied, not transposed.')).toBeVisible();await shot(page,'stage-two');await page.getByRole('button',{name:/Soprano Saxophone/}).click();await page.getByRole('button',{name:/Tenor Saxophone/}).click();await page.getByRole('button',{name:'Export PDF',exact:true}).click();await page.getByRole('dialog',{name:'PDF layout'}).getByRole('button',{name:'Export',exact:true}).click();await expect(page.locator('.notice')).toContainText('no file written');
 await page.getByRole('button',{name:'← Back to Stage 1',exact:true}).click();await expect(working(page).getByTestId('head-n2')).toHaveCount(0);await expect(page.locator('.source-pane').getByTestId('head-n2')).toBeVisible();
});
test('Narrow and stacked responsive layouts plus palette',async({page})=>{
 await load(page);await page.setViewportSize({width:1024,height:900});await page.getByRole('button',{name:'Notes',exact:true}).click();await shot(page,'narrow-1024');await page.getByRole('button',{name:'Close palette',exact:true}).click();await page.setViewportSize({width:390,height:844});await shot(page,'stacked-mobile');await expect(page.locator('.source-pane')).toBeVisible();await expect(working(page)).toBeVisible();const total=await page.evaluate(()=>document.documentElement.scrollWidth);expect(total).toBeLessThanOrEqual(390);await page.getByRole('button',{name:'Edit Only',exact:true}).click();await expect(page.locator('.source-pane')).toHaveCount(0);
});
test('Insertion voice choice, rest, regular beams, slur and text preserve source',async({page})=>{
 await load(page);await page.getByRole('button',{name:'Edit Only',exact:true}).click();
 await page.getByRole('button',{name:'Notes',exact:true}).click();await page.getByRole('button',{name:'Quarter note',exact:true}).click();
 let bounds=await working(page).locator('svg.score').boundingBox();if(!bounds)throw Error('No SVG');
 await page.mouse.click(bounds.x+point([2,1],71).x,bounds.y+point([2,1],71).y);await expect(page.getByText('Choose voice for insertion',{exact:true})).toBeVisible();await page.getByRole('button',{name:'Voice 2',exact:true}).click();await expect(working(page).locator('.note')).toHaveCount(9);await shot(page,'voice-insertion');
 await page.getByRole('button',{name:'Rest',exact:true}).click();bounds=await working(page).locator('svg.score').boundingBox();if(!bounds)throw Error('No SVG');await page.mouse.click(bounds.x+point([5,2],71).x,bounds.y+point([5,2],71).y);await page.getByRole('button',{name:'Voice 2',exact:true}).click();await expect(working(page).locator('.rest')).toHaveCount(1);await shot(page,'rest-insertion');
 await page.getByRole('button',{name:'Select',exact:true}).click();await clickHead(page,'n1');await page.getByRole('button',{name:'Slur',exact:true}).click();await clickHead(page,'n4');await expect(working(page).locator('.curve')).toHaveCount(2);await shot(page,'slur');
 await page.getByRole('button',{name:'Select',exact:true}).click();await page.getByRole('button',{name:'Groups',exact:true}).click(); // palette can be dismissed without document changes
 await page.getByRole('button',{name:'Close palette',exact:true}).click();
 await page.getByRole('button',{name:'Text',exact:true}).click();bounds=await working(page).locator('svg.score').boundingBox();if(!bounds)throw Error('No SVG');await page.mouse.click(bounds.x+450,bounds.y+310);await expect(working(page).locator('.score-text')).toHaveCount(4);await page.getByRole('button',{name:'Delete selected',exact:true}).click();await expect(working(page).locator('.score-text')).toHaveCount(3);
});

test('Accepted demo Stage 2 keyboard cannot edit Stage 1 and exports stay simulated',async({page})=>{
 await load(page);
 await clickHead(page,'n1');await page.getByRole('button',{name:'Save',exact:true}).click();await page.getByRole('button',{name:'Instrument Scores →',exact:true}).click();await page.keyboard.press('Delete');await page.getByRole('button',{name:'← Back to Stage 1',exact:true}).click();await expect(working(page).getByTestId('head-n1')).toBeVisible();
 await page.getByRole('button',{name:'Export',exact:true}).click();await expect(page.locator('.notice')).toContainText('no file written');await page.getByRole('button',{name:'Preview MusicXML',exact:true}).click();await page.getByRole('button',{name:'Reimport preview',exact:true}).click();await expect(page.locator('.notice')).toContainText('no XML parsed');
});
test('Groups 3:2 tool-first applies directly to a deleted gap',async({page})=>{
 await load(page);await clickHead(page,'n3');await page.getByRole('button',{name:'Delete',exact:true}).click();
 await page.getByRole('button',{name:'Groups',exact:true}).click();await page.getByRole('button',{name:'♩♪ 3:2',exact:true}).click();
 await working(page).getByTestId('gap-e2').click();await expect(working(page).getByTestId('gap-e2')).toHaveCount(0);await expect(working(page).getByText('3:2',{exact:true})).toHaveCount(1);
});
test('Grouped glyphs distinguish tuplet eighth and regular double beams',async({page})=>{
 await load(page);await page.getByRole('button',{name:'Edit Only',exact:true}).click();await clickHead(page,'n1');await page.getByRole('button',{name:'Groups',exact:true}).click();await page.getByRole('button',{name:'♩♪ 3:2',exact:true}).click();await expect(working(page).locator('.note-flags')).toHaveCount(3);await shot(page,'triplet-flags');
 await page.getByRole('button',{name:'Undo',exact:true}).click();await page.getByRole('button',{name:'Select',exact:true}).click();await clickHead(page,'n6');await page.getByRole('button',{name:'Groups',exact:true}).click();await page.getByRole('button',{name:'♬ Beam 4',exact:true}).click();await expect(working(page).locator('.regular-beam .beam-level')).toHaveCount(2);await shot(page,'regular-beams');
});
test('Source-first Slur: ordinary note selection, tool, next note; repeat after a curve exists',async({page})=>{
 await load(page);await page.getByRole('button',{name:'Edit Only',exact:true}).click();
 await working(page).getByRole('button',{name:'Note n1, pitch 67, voice 1',exact:true}).click();
 await page.getByRole('button',{name:'Slur',exact:true}).click();
 await expect(working(page).getByTestId('head-n1')).toHaveClass(/pending/);
 await working(page).getByRole('button',{name:'Note n3, pitch 67, voice 1',exact:true}).click();
 await expect(working(page).locator('.curve')).toHaveCount(2);
 await page.getByRole('button',{name:'Select',exact:true}).click();
 await working(page).getByRole('button',{name:'Note n2, pitch 71, voice 1',exact:true}).click();
 await page.getByRole('button',{name:'Slur',exact:true}).click();
 await working(page).getByRole('button',{name:'Note n4, pitch 69, voice 1',exact:true}).click();
 await expect(working(page).locator('.curve')).toHaveCount(3);
});
test('Source-first Tie uses ordinary note hit targets and validates pitch without losing source',async({page})=>{
 await load(page);
 await working(page).getByRole('button',{name:'Note n1, pitch 67, voice 1',exact:true}).click();
 await page.getByRole('button',{name:'Tie',exact:true}).click();
 await expect(working(page).getByTestId('head-n1')).toHaveClass(/pending/);
 await working(page).getByRole('button',{name:'Note n4, pitch 69, voice 1',exact:true}).click();
 await expect(working(page).locator('.curve')).toHaveCount(1);
 await expect(working(page).getByTestId('head-n1')).toHaveClass(/pending/);
 await working(page).getByRole('button',{name:'Note n3, pitch 67, voice 1',exact:true}).click();
 await expect(working(page).locator('.curve')).toHaveCount(2);
 await expect(working(page).locator('.curve.selected')).toHaveCount(1);
 await expect(working(page).getByTestId('head-n1')).toHaveAttribute('data-pitch','67');
 await expect(working(page).getByTestId('head-n4')).toHaveAttribute('data-pitch','69');
 await page.screenshot({path:'evidence/tie-source-first.png',fullPage:true});
 await page.getByRole('button',{name:'Undo',exact:true}).click();await expect(working(page).locator('.curve')).toHaveCount(1);
 await page.getByRole('button',{name:'Redo',exact:true}).click();await expect(working(page).locator('.curve')).toHaveCount(2);
});

test('Measure layout: 4/4, correct diatonic placement, ledger lines and shared chord stem',async({page})=>{
 await load(page);await page.getByRole('button',{name:'Edit Only',exact:true}).click();
 await expect(working(page).locator('.time-signature')).toHaveCount(1);
 await expect(working(page).getByTestId('bar-end-0')).toHaveAttribute('x1','492.5');
 const g=working(page).getByTestId('head-n1').locator('ellipse').last(),b=working(page).getByTestId('head-n2').locator('ellipse').last();
 await expect(g).toHaveAttribute('cy','190');await expect(b).toHaveAttribute('cy','180');
 await expect(g).toHaveAttribute('cx','170');await expect(working(page).getByTestId('head-n3').locator('ellipse').last()).toHaveAttribute('cx','245.625');
 await expect(working(page).locator('.ledger-line')).toHaveCount(1);await expect(working(page).locator('.event-stem[data-event="e1"]')).toHaveCount(1);
 await page.screenshot({path:'evidence/measure-layout-corrected.png',fullPage:true});
});


test('Voice 2 Slur explains invalid source/voice and connects the intended earlier-to-later pair',async({page})=>{
 await load(page);
 await working(page).getByRole('button',{name:'Note v2, pitch 62, voice 2',exact:true}).click();await page.getByRole('button',{name:'Slur',exact:true}).click();
 await expect(page.locator('.working-pane .pane-foot')).toContainText('last eligible note in Voice 2');
 await working(page).getByRole('button',{name:'Note n3, pitch 67, voice 1',exact:true}).click();await expect(page.locator('.notice')).toContainText('source is Voice 2, destination is Voice 1');await expect(working(page).locator('.curve')).toHaveCount(1);
 await page.keyboard.press('Escape');await working(page).getByRole('button',{name:'Note v1, pitch 60, voice 2',exact:true}).click();await page.getByRole('button',{name:'Slur',exact:true}).click();await working(page).getByRole('button',{name:'Note v2, pitch 62, voice 2',exact:true}).click();
 await expect(working(page).locator('.curve')).toHaveCount(2);await expect(working(page).locator('.curve.selected')).toHaveCount(1);await page.screenshot({path:'evidence/voice2-slur-confirmed.png',fullPage:true});
});


test('Lyrics on missing notes and direct inline editing remain usable in a narrow pane',async({page})=>{
 await page.setViewportSize({width:650,height:590});await load(page);await page.getByRole('button',{name:'Edit Only',exact:true}).click();
 await page.getByRole('button',{name:'Lyrics',exact:true}).click();await working(page).getByRole('button',{name:'Note n5, pitch 69, voice 1',exact:true}).click();
 const input=page.getByRole('textbox',{name:'Edit lyric'});await expect(input).toBeFocused();await input.fill('Ánh sáng');await page.screenshot({path:'evidence/lyrics-new-note-inline.png',fullPage:true});await page.keyboard.press('Enter');await expect(working(page).getByText('Ánh sáng',{exact:true})).toBeVisible();
 await working(page).getByTestId('lyric-l1').click();await expect(input).toBeFocused();await input.fill('Niềm thương');await page.keyboard.press('Enter');await expect(working(page).getByTestId('lyric-l1')).toContainText('Niềm thương');
 await page.getByRole('button',{name:'Undo',exact:true}).click();await expect(working(page).getByTestId('lyric-l1')).toContainText('Niềm');
 await page.getByRole('button',{name:'Fit working score',exact:true}).click();await working(page).getByRole('button',{name:'Note n6, pitch 72, voice 1',exact:true}).click();await input.fill('Canceled');await page.keyboard.press('Escape');await expect(working(page).getByText('Canceled',{exact:true})).toHaveCount(0);
 await page.screenshot({path:'evidence/lyrics-narrow-corrected.png',fullPage:true});
});

test('Tab and Shift+Tab traverse notes without lyrics in the selected verse',async({page})=>{
 await load(page);await working(page).getByTestId('lyric-l3').click();const input=page.getByRole('textbox',{name:'Edit lyric'});await expect(input).toHaveValue('sáng');await page.keyboard.press('Tab');await expect(input).toBeFocused();await expect(input).toHaveValue('');await input.fill('Hy vọng');await page.keyboard.press('Tab');await expect(input).toHaveValue('');await page.keyboard.press('Shift+Tab');await expect(input).toHaveValue('Hy vọng');await page.keyboard.press('Enter');await expect(working(page).getByText('Hy vọng',{exact:true})).toBeVisible();
});

test('Fit source and working score independently reveals complete measures',async({page})=>{
 await page.setViewportSize({width:650,height:590});await load(page);
 const workingZoom=await page.locator('.working-pane .zoom output').textContent();await page.getByRole('button',{name:'Fit source score',exact:true}).click();await expect(page.locator('.working-pane .zoom output')).toHaveText(workingZoom!);
 await page.getByRole('button',{name:'Fit working score',exact:true}).click();
 for(const name of ['source-scroll','working-scroll']){const dimensions=await page.locator('.'+name).evaluate(el=>{const svg=el.querySelector('svg')!;return {pane:el.clientWidth,page:svg.getBoundingClientRect().width,left:el.scrollLeft};});expect(dimensions.page).toBeLessThanOrEqual(dimensions.pane);expect(dimensions.left).toBe(0);}
 await expect(working(page).getByTestId('bar-end-0')).toBeInViewport();await expect(working(page).getByTestId('bar-end-1')).toBeInViewport();await page.screenshot({path:'evidence/fit-both-panes.png',fullPage:true});
});


test('Fit below 50 percent followed by minus never enlarges either pane',async({page})=>{
 await page.setViewportSize({width:390,height:844});await load(page);
 for(const [fit,minus,output] of [['Fit source score','Source zoom out','.source-tools output'],['Fit working score','Working score zoom out','.working-pane .zoom output']]){
  await page.getByRole('button',{name:fit,exact:true}).click();const before=parseInt((await page.locator(output).textContent())!);expect(before).toBeLessThan(50);await page.getByRole('button',{name:minus,exact:true}).click();const after=parseInt((await page.locator(output).textContent())!);expect(after).toBeLessThanOrEqual(before);
 }
});

test('Add Verse and Tab drafts keep marker/delete controls on the new lyric owner',async({page})=>{
 await load(page);await working(page).getByTestId('lyric-l1').click();await page.keyboard.press('Escape');await page.getByRole('button',{name:'Add Verse',exact:true}).click();const input=page.getByRole('textbox',{name:'Edit lyric'});await input.fill('Verse two');await page.keyboard.press('Enter');await expect(page.getByRole('combobox',{name:'Lyric verse'})).toHaveValue('2');
 await expect(page.getByRole('button',{name:'Hyphen',exact:true})).toHaveCount(0);await expect(working(page).getByTestId('lyric-l1')).toHaveText('Niềm');await expect(working(page).getByText('Verse two',{exact:true})).toBeVisible();await page.getByRole('button',{name:'Delete syllable',exact:true}).click();await expect(working(page).getByText('Verse two',{exact:true})).toHaveCount(0);await expect(working(page).getByTestId('lyric-l1')).toHaveText('Niềm');
 await working(page).getByTestId('lyric-l3').click();await page.keyboard.press('Tab');await input.fill('New at n5');await page.keyboard.press('Enter');await page.getByRole('button',{name:'Delete syllable',exact:true}).click();await expect(working(page).getByText('New at n5',{exact:true})).toHaveCount(0);await expect(working(page).getByTestId('lyric-l3')).toHaveText('sáng');
});


test('Vietnamese NFC/NFD and IME Enter preserve exact Unicode inline',async({page})=>{
 await page.setViewportSize({width:721,height:590});await load(page);await page.getByRole('button',{name:'Edit Only',exact:true}).click();await page.getByRole('button',{name:'Lyrics',exact:true}).click();
 const text='Tiếng Việt – Đường về';
 for(const value of [text,text.normalize('NFD')]){
  await working(page).getByRole('button',{name:'Note n5, pitch 69, voice 1',exact:true}).click();const input=page.getByRole('textbox',{name:'Edit lyric'});await input.fill(value);await input.dispatchEvent('keydown',{key:'Enter',code:'Enter',isComposing:true});await expect(input).toBeFocused();await expect(input).toHaveValue(value);await page.keyboard.press('Enter');
  const lyric=working(page).locator('.lyric[data-note-id="n5"]');expect(await lyric.textContent()).toBe(value);await expect(lyric).toBeVisible();
 }
 await page.screenshot({path:'evidence/unicode-lyric-corrected.png',fullPage:true});
});

test('Clicking near lyrics outside staff does not open voice insertion',async({page})=>{
 await page.setViewportSize({width:721,height:590});await load(page);await page.getByRole('button',{name:'Edit Only',exact:true}).click();
 const svg=working(page).locator('svg.score');const rect=await svg.boundingBox();if(!rect)throw Error('No score');await page.mouse.click(rect.x+245,rect.y+270);await expect(page.locator('.anchor-menu')).toHaveCount(0);
 await working(page).getByTestId('lyric-l1').click();await expect(page.getByRole('textbox',{name:'Edit lyric'})).toBeFocused();await page.getByRole('textbox',{name:'Edit lyric'}).fill('Niềm vui');await page.keyboard.press('Enter');await expect(working(page).getByTestId('lyric-l1')).toHaveText('Niềm vui');
});


test('PO-disabled Hyphen and Melisma are absent; ordinary lyric editing remains intact',async({page})=>{
 await load(page);await expect(working(page).getByTestId('lyric-l1')).toHaveText('Niềm');await expect(working(page).getByTestId('lyric-l2')).toHaveText('tin');
 await working(page).getByTestId('lyric-l1').click();const input=page.getByRole('textbox',{name:'Edit lyric'});await input.fill('Niềm vui');await page.keyboard.press('Enter');await expect(working(page).getByTestId('lyric-l1')).toHaveText('Niềm vui');await expect(page.getByRole('button',{name:'Hyphen',exact:true})).toHaveCount(0);await expect(page.getByRole('button',{name:'Melisma',exact:true})).toHaveCount(0);await expect(page.getByRole('button',{name:'Add Verse',exact:true})).toBeVisible();
 await working(page).getByTestId('lyric-l2').click();await input.fill('tin - nguyên_văn');await page.keyboard.press('Enter');await expect(working(page).getByTestId('lyric-l2')).toHaveText('tin - nguyên_văn');await page.getByRole('button',{name:'Undo',exact:true}).click();await expect(working(page).getByTestId('lyric-l2')).toHaveText('tin');await page.screenshot({path:'evidence/lyric-markers-disabled.png',fullPage:true});
});


test('Multiple numbered measures divide a continuous staff like the reference layout',async({page})=>{
 await load(page);await page.getByRole('button',{name:'Edit Only',exact:true}).click();await page.getByRole('button',{name:'Fit working score',exact:true}).click();
 await expect(working(page).locator('.measure-bar')).toHaveCount(4);await expect(working(page).getByTestId('bar-end-0')).toHaveAttribute('x1','492.5');await expect(working(page).getByTestId('bar-end-1')).toHaveAttribute('x1','835');
 await expect(working(page).getByTestId('head-n5').locator('ellipse').last()).toHaveAttribute('cx','512.5');await expect(working(page).getByTestId('head-n5').locator('ellipse').last()).toHaveAttribute('cy','185');
 await expect(working(page).getByTestId('bar-end-0')).toBeInViewport();await expect(working(page).getByTestId('bar-end-1')).toBeInViewport();await page.screenshot({path:'evidence/multiple-measures-reference-layout.png',fullPage:true});
});


test('Narrow editor can reach the second measure by ordinary horizontal scrolling',async({page})=>{
 await page.setViewportSize({width:650,height:590});await load(page);await page.getByRole('button',{name:'Edit Only',exact:true}).click();const pane=page.locator('.working-scroll');await pane.hover();await page.mouse.wheel(420,0);await expect.poll(()=>pane.evaluate(el=>el.scrollLeft)).toBeGreaterThan(0);const target=working(page).getByRole('button',{name:'Note n6, pitch 72, voice 1',exact:true});await expect(target).toBeInViewport();const head=await target.boundingBox(),frame=await pane.boundingBox();if(!head||!frame)throw Error('Missing visible bounds');const x=head.x+head.width/2,y=head.y+head.height/2;expect(x).toBeGreaterThan(frame.x);expect(x).toBeLessThan(frame.x+frame.width);expect(y).toBeGreaterThan(frame.y);expect(y).toBeLessThan(frame.y+frame.height);await page.mouse.click(x,y);await expect(working(page).getByTestId('head-n6')).toHaveClass(/selected/);await expect(working(page).getByTestId('head-n6')).toHaveAttribute('data-pitch','72');
});

test('Whole note has no stem, current key appears in header, Fit fills both pane widths',async({page})=>{
 await page.setViewportSize({width:1338,height:590});await load(page);
 await clickHead(page,'n3');await page.getByRole('button',{name:'Notes',exact:true}).click();await page.getByRole('button',{name:'Whole note',exact:true}).click();
 await expect(working(page).getByTestId('head-n3').locator('ellipse').last()).toHaveAttribute('fill','white');await expect(working(page).locator('.event-stem[data-event="e2"]')).toHaveCount(0);
 await expect(page.getByTestId('working-concert-key')).toHaveText('Concert key: F · simulated');
 await page.getByRole('button',{name:'Concert Key',exact:true}).click();await page.getByLabel('New concert key').selectOption('G');await page.getByRole('button',{name:'Preview key change',exact:true}).click();await expect(page.getByTestId('working-concert-key')).toHaveText('Concert key: G · simulated');
 for(const pane of ['source','working']){await page.getByRole('button',{name:`Fit ${pane} score`,exact:true}).click();const dimensions=await page.locator(`.${pane}-scroll`).evaluate(el=>{const css=getComputedStyle(el);return {inner:el.clientWidth-parseFloat(css.paddingLeft)-parseFloat(css.paddingRight),score:el.querySelector('svg')!.getBoundingClientRect().width};});expect(Math.abs(dimensions.inner-dimensions.score)).toBeLessThan(2);}
 await shot(page,'whole-key-width-fit');
});
