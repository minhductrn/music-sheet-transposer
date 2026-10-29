import {existsSync} from 'node:fs';
import {test,expect,type Page} from '@playwright/test';
import {mkdir} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
const output='/home/dtran/music-sheet-transposer/frontend-v2/evidence/task04/pdf-a4/output/pdf';
const reviews=new WeakMap<Page,Set<string>>();
test.beforeEach(async({page})=>{const ids=new Set<string>();reviews.set(page,ids);page.on('response',async r=>{if(r.request().method()==='POST'&&r.url().endsWith('/reviews')&&r.ok()){ids.add((await r.json()).id);}});});
test.afterEach(async({page})=>{await Promise.all([...(reviews.get(page)??[])].map(id=>page.request.delete('/api/v1/reviews/'+id)));});
function score(count:number){return '<score-partwise version="4.0"><movement-title>Kiểm thử bố cục A4</movement-title><identification><creator type="composer">Người soạn thử</creator></identification><part-list><score-part id="P1"><part-name>Concert</part-name></score-part></part-list><part id="P1">'+Array.from({length:count},(_,m)=>'<measure number="'+(m+1)+'">'+(m===0?'<attributes><divisions>4</divisions><key><fifths>0</fifths><mode>major</mode></key><time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes>':'')+Array.from({length:4},(_,n)=>'<note><pitch><step>C</step><octave>4</octave></pitch><duration>4</duration><voice>1</voice><type>quarter</type><lyric number="1"><text>Lời'+(m*4+n+1)+'</text></lyric><lyric number="2"><text>Niềm</text></lyric></note>').join('')+'</measure>').join('')+'</part></score-partwise>';}
function inspect(file:string){return JSON.parse(execFileSync('/home/dtran/music-sheet-transposer/backend/.venv/bin/python',['-B','-c',`import json,re,sys
from pypdf import PdfReader
r=PdfReader(sys.argv[1]);print(json.dumps([{'width':float(p.mediabox.width),'height':float(p.mediabox.height),'words':[int(n) for n in re.findall(r'Lời(\\d+)',p.extract_text())],'title':p.extract_text().count('Kiểm thử bố cục A4'),'footer':str(i+1)+' / '+str(len(r.pages)) in p.extract_text()} for i,p in enumerate(r.pages)],ensure_ascii=False))`,file],{encoding:'utf8'})) as {width:number;height:number;words:number[];title:number;footer:boolean}[];}
for(const [name,count,instrument] of [['short',4,false],['long',80,false],['instrument',40,true]] as const)test('portrait A4 '+name+' score has complete systems and unique lyrics',async({page})=>{
 test.setTimeout(120000);await mkdir(output,{recursive:true});await page.goto('/');await page.locator('input[type=file]').setInputFiles({name:'a4-'+name+'.musicxml',mimeType:'application/xml',buffer:Buffer.from(score(count))});await expect(page.getByTestId('real-head-e-1')).toBeVisible({timeout:30000});
 if(instrument){await page.getByRole('button',{name:'Instrument Scores →',exact:true}).click();await page.getByRole('button',{name:/Alto Saxophone/}).click();await expect(page.locator('.instrument-editor').getByTestId('real-head-e-1')).toBeVisible({timeout:30000});}
 let edits=0;page.on('request',r=>{if(r.method()==='PATCH'||r.url().endsWith('/document-correction'))edits++;});const download=page.waitForEvent('download',{timeout:90000});await page.getByRole('button',{name:'Export PDF',exact:true}).click();if(name!=='short')await page.getByLabel('PDF page layout').selectOption('multiple-pages');await page.getByRole('dialog',{name:'PDF layout'}).getByRole('button',{name:'Export',exact:true}).click();const file=output+'/a4-'+name+'.pdf';await (await download).saveAs(file);const pages=inspect(file);if(name==='short')expect(pages.length).toBe(1);else expect(pages.length).toBeGreaterThan(1);for(const p of pages){expect(p.width).toBeCloseTo(595.28,1);expect(p.height).toBeCloseTo(841.89,1);expect(p.footer).toBeTruthy();}expect(pages.flatMap(p=>p.words).sort((a,b)=>a-b)).toEqual(Array.from({length:count*4},(_,i)=>i+1));expect(pages.reduce((sum,p)=>sum+p.title,0)).toBe(1);expect(edits).toBe(0);
});

 test('actual local Tien Buoc score fits one A4 page with compact print spacing',async({page})=>{
 test.setTimeout(120000);await page.goto('/');await page.locator('input[type=file]').setInputFiles(privateFixture('/mnt/c/Users/dtran/Downloads/TienBuocVaoNhaChua_hn.musicxml'));await expect(page.getByTestId('real-head-e-1')).toBeVisible({timeout:30000});
 const download=page.waitForEvent('download',{timeout:90000});await page.getByRole('button',{name:'Export PDF',exact:true}).click();await page.getByRole('dialog',{name:'PDF layout'}).getByRole('button',{name:'Export',exact:true}).click();const file=output+'/tien-buoc-compact-a4.pdf';await (await download).saveAs(file);const pages=inspect(file);expect(pages.length).toBe(1);expect(pages[0].width).toBeCloseTo(595.28,1);expect(pages[0].height).toBeCloseTo(841.89,1);
 });

function privateFixture(path:string){test.skip(!existsSync(path),'Private local fixture is not distributed with the repository.');return path;}

for(const instrument of [false,true])test('user Dieu Ran fixture fits one A4 '+(instrument?'Alto':'Concert'),async({page})=>{
 test.setTimeout(120000);await mkdir(output,{recursive:true});await page.goto('/');
 await page.locator('input[type=file]').setInputFiles(privateFixture('/mnt/c/Users/dtran/Downloads/Gb-DieuRanTrongNhat_BUI NINH_01Page.musicxml'));
 await expect(page.getByTestId('real-head-e-1')).toBeVisible({timeout:30000});
 if(instrument){await page.getByRole('button',{name:'Instrument Scores →',exact:true}).click();await page.getByRole('button',{name:/Alto Saxophone/}).click();await expect(page.locator('.instrument-editor').getByTestId('real-head-e-1')).toBeVisible({timeout:30000});}
 let edits=0;page.on('request',r=>{if(r.method()==='PATCH'||r.url().endsWith('/document-correction'))edits++;});
 const download=page.waitForEvent('download',{timeout:90000});await page.getByRole('button',{name:'Export PDF',exact:true}).click();
 await expect(page.getByLabel('PDF page layout')).toHaveValue('one-page');await page.getByRole('dialog',{name:'PDF layout'}).getByRole('button',{name:'Export',exact:true}).click();
 const file=output+'/dieu-ran-'+(instrument?'alto':'concert')+'-fit-a4.pdf';await(await download).saveAs(file);const pages=inspect(file);expect(pages).toHaveLength(1);expect(pages[0].width).toBeCloseTo(595.28,1);expect(pages[0].height).toBeCloseTo(841.89,1);expect(edits).toBe(0);
});

test('PDF layout cancellation creates no download or success notice',async({page})=>{
 await page.goto('/');await page.locator('input[type=file]').setInputFiles({name:'cancel.musicxml',mimeType:'application/xml',buffer:Buffer.from(score(1))});await expect(page.getByTestId('real-head-e-1')).toBeVisible();
 let downloads=0;page.on('download',()=>downloads++);await page.getByRole('button',{name:'Export PDF',exact:true}).click();await page.getByRole('dialog',{name:'PDF layout'}).getByRole('button',{name:'Cancel',exact:true}).click();await expect(page.getByRole('dialog',{name:'PDF layout'})).toHaveCount(0);expect(downloads).toBe(0);await expect(page.getByRole('status').filter({hasText:'Working score exported as PDF.'})).toHaveCount(0);
});
