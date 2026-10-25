// Task 03 integration verification against extracted production assets and bundled runtime.
import {createRequire} from 'node:module';
import {readFile,writeFile,mkdir,mkdtemp} from 'node:fs/promises';
import {resolve,join} from 'node:path';
import {tmpdir} from 'node:os';
import {spawn,execFileSync} from 'node:child_process';
import {once} from 'node:events';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
const repo=resolve(process.argv[2]), archive=resolve(process.argv[3]), evidence=resolve(process.argv[4]);
const require=createRequire(join(repo,'frontend-v2/package.json'));
const {firefox,expect}=require('@playwright/test');
const extracted=await mkdtemp(join(tmpdir(),'mst-task03-relocated-'));
execFileSync('tar',['-xzf',archive,'-C',extracted]);
const bundle=join(extracted,archive.split('/').at(-1).replace(/\.tar\.gz$/,''));
const port=5182, url=`http://127.0.0.1:${port}`;
await mkdir(evidence,{recursive:true});
const fixture=join(repo,'frontend-v2/tests/fixtures/task02.musicxml');
const original=await readFile(fixture);const digest=b=>createHash('sha256').update(b).digest('hex');
let server,browser,context,page;const logs=[];const checks=[];const opened=[];
async function start(){
 server=spawn('/usr/bin/python3',['-I','-B',join(bundle,'start.py'),'--port',String(port)],{cwd:tmpdir(),env:{PATH:'/usr/bin:/bin',HOME:process.env.HOME,LANG:'C.UTF-8'},stdio:['ignore','pipe','pipe']});
 server.stdout.on('data',b=>logs.push(b.toString()));server.stderr.on('data',b=>logs.push(b.toString()));
 for(let i=0;i<100;i++){if(server.exitCode!==null)throw Error('Packaged server exited: '+logs.join(''));try{if((await fetch(url+'/api/v1/health')).ok)return;}catch{}await new Promise(r=>setTimeout(r,100));}
 throw Error('Packaged server failed to start');
}
async function stop(){if(server&&server.exitCode===null){server.kill('SIGINT');await once(server,'exit');}server=null;}
async function fresh(){context=await browser.newContext({acceptDownloads:true,viewport:{width:1440,height:1000}});page=await context.newPage();page.on('response',async r=>{if(r.request().method()==='POST'&&/\/api\/v1\/reviews$/.test(r.url())&&r.status()===201){try{opened.push((await r.json()).id);}catch{}}});page.setDefaultTimeout(30000);await page.goto(url);}
async function head(root,id){await expect(root.getByRole('button',{name:'Save',exact:true})).toBeEnabled();const h=root.getByTestId('real-head-'+id);await expect(h).toBeVisible();await h.focus();await page.keyboard.press('Enter');}
async function save(root,name){await root.getByRole('button',{name:'Save As',exact:true}).click();await root.getByLabel('Filename').fill(name);const d=page.waitForEvent('download');await root.getByRole('button',{name:'Save Copy',exact:true}).click();const file=await d;const path=join(evidence,name);await file.saveAs(path);await page.getByRole('button',{name:'I retained the downloaded file',exact:true}).click();return path;}
async function pdf(root,name){const d=page.waitForEvent('download');await root.getByRole('button',{name:'Export PDF',exact:true}).click();const file=await d;const path=join(evidence,name);await file.saveAs(path);assert.equal((await readFile(path)).subarray(0,5).toString(),'%PDF-');return path;}
async function projection(path){const bytes=await readFile(path);const body=new FormData();body.append('musicxml',new Blob([bytes],{type:'application/xml'}),path.split('/').at(-1));const response=await fetch(url+'/api/v1/reviews',{method:'POST',body});assert.equal(response.status,201);const result=await response.json();await fetch(url+'/api/v1/reviews/'+result.id,{method:'DELETE'});return result;}
function musical(r){return {score:r.score,slurs:r.slurs};}
try{
 await start();checks.push('Relocated package starts with system Python -I, empty application environment, no repository or Node runtime dependency');
 const html=await(await fetch(url)).text();assert(!html.includes('@vite/client'));assert(html.includes('/assets/'));
 assert.equal((await fetch(url+'/api/v1/recognize',{method:'POST'})).status,404);
 const keyForm=new FormData();keyForm.append('file',new Blob([original]),'synthetic.musicxml');assert.equal((await fetch(url+'/api/v1/concert-key',{method:'POST',body:keyForm})).status,200);
 browser=await firefox.launch({headless:true,executablePath:'/home/dtran/.cache/ms-playwright/firefox-1555/firefox/firefox'});await fresh();await page.locator('input[type=file]').setInputFiles(fixture);await expect(page.getByTestId('real-head-e-1')).toBeVisible();
 await head(page,'e-2');await page.getByRole('combobox',{name:'Selected note pitch'}).selectOption('E');await page.getByRole('combobox',{name:'Selected note octave'}).selectOption('5');await page.getByRole('button',{name:'Sharp accidental',exact:true}).click();await expect(page.getByTestId('real-head-e-2')).toHaveAttribute('data-pitch','E1/5');
 await page.getByRole('button',{name:'Edit lyrics',exact:true}).click();await page.getByRole('textbox',{name:'Lyric syllable'}).fill('Lưu Concert tiếng Việt');await page.getByRole('textbox',{name:'Lyric syllable'}).press('Enter');
 await page.getByRole('button',{name:'Select',exact:true}).click();await head(page,'e-1');await page.getByRole('button',{name:'Tie',exact:true}).click();await head(page,'e-4');await expect(page.getByTestId('real-curve-tie-e-1-e-4')).toBeVisible();
 const curve=page.getByTestId('real-curve-tie-e-1-e-4');const xy=await curve.locator('path').last().evaluate(p=>{const q=p.getPointAtLength(p.getTotalLength()/2).matrixTransform(p.getScreenCTM());return{x:q.x,y:q.y};});await page.mouse.move(xy.x,xy.y);await page.mouse.down();await page.mouse.move(xy.x,xy.y+35,{steps:8});await page.mouse.up();await expect(curve).toHaveAttribute('data-direction','down');
 const concert=await save(page,'task03-concert.musicxml');await pdf(page,'task03-concert.pdf');const concertBytes=await readFile(concert);const expectedConcert=await projection(concert);assert(concertBytes.toString().includes('Lưu Concert tiếng Việt'));assert(concertBytes.toString().includes('<time-modification>'));const oldSession=opened.at(-1);assert(oldSession);
 await page.getByRole('button',{name:'Instrument Scores →'}).click();await page.getByRole('button',{name:/Alto Saxophone/}).click();const editor=page.locator('.instrument-editor');await expect(editor.getByTestId('real-head-e-2')).toBeVisible();await head(editor,'e-2');await editor.getByRole('button',{name:'Edit lyrics',exact:true}).click();await page.getByRole('textbox',{name:'Lyric syllable'}).fill('Giang tấu đã lưu');await page.getByRole('textbox',{name:'Lyric syllable'}).press('Enter');await editor.getByRole('button',{name:'Add measure',exact:true}).click();const gap=editor.getByRole('button',{name:'Gap in measure 4, voice 1'});await gap.focus();await page.keyboard.press('Enter');await editor.getByRole('button',{name:'Quarter note',exact:true}).click();await expect(editor.locator('.working-pane [data-event-id]')).toHaveCount(10);
 const instrument=await save(editor,'task03-alto-up.musicxml');await pdf(editor,'task03-alto-up.pdf');const instrumentBytes=await readFile(instrument);const expectedInstrument=await projection(instrument);assert(instrumentBytes.toString().includes('Giang tấu đã lưu'));assert(instrumentBytes.toString().includes('<transpose>'));
 const exportConcert=page.waitForEvent('download');await page.locator('.app-header').getByRole('button',{name:'Export saved MusicXML',exact:true}).click();assert.deepEqual(await readFile((await(await exportConcert).path())),concertBytes);
 await page.screenshot({path:join(evidence,'before-restart.png'),fullPage:true});await context.close();await browser.close();browser=null;await stop();checks.push('Concert and instrument Save As, MusicXML export, independent source, and PDF downloads pass before shutdown');
 await start();assert.equal((await fetch(url+'/api/v1/reviews/'+oldSession)).status,404);browser=await firefox.launch({headless:true,executablePath:'/home/dtran/.cache/ms-playwright/firefox-1555/firefox/firefox'});await fresh();
 for(const [file,expected,label] of [[concert,expectedConcert,'concert'],[instrument,expectedInstrument,'instrument']]){
  await page.locator('input[type=file]').setInputFiles(file);await expect(page.getByTestId('real-head-e-1')).toBeVisible();await expect(page.locator('.working-pane [data-event-id]')).toHaveCount(label==='concert'?9:10);
  const reopened=await projection(file);assert.deepEqual(musical(reopened),musical(expected));assert.deepEqual(await readFile(file),label==='concert'?concertBytes:instrumentBytes);
  const pdfPath=await pdf(page,`task03-${label}-reopened.pdf`);assert((await readFile(pdfPath)).length>10000);
  const d=page.waitForEvent('download');await page.getByRole('button',{name:'Save',exact:true}).click();assert.deepEqual(await readFile((await(await d).path())),await readFile(file));await page.getByRole('button',{name:'I retained the downloaded file'}).click();await page.screenshot({path:join(evidence,`${label}-reopened.png`),fullPage:true});
  checks.push(`${label}: fresh browser + restarted backend reopen identical MusicXML and semantic projection; PDF re-export passes`);
  if(label==='concert'){await context.close();await fresh();}
 }
 assert.equal(digest(await readFile(fixture)),digest(original));checks.push('Original synthetic fixture unchanged; unsaved sessions intentionally absent after restart');
 await writeFile(join(evidence,'results.json'),JSON.stringify({status:'PASS',checks,archive,extracted_bundle:bundle,baseline:'bcac2d889da59406cefb0824a589ce20564b699a',files:{concert_sha256:digest(concertBytes),instrument_sha256:digest(instrumentBytes)}},null,2));console.log(checks.join('\n'));
}catch(error){await writeFile(join(evidence,'failure.txt'),String(error.stack??error));if(page)await page.screenshot({path:join(evidence,'failure.png'),fullPage:true}).catch(()=>{});throw error;}
finally{if(browser)await browser.close();await stop();await writeFile(join(evidence,'server.log'),logs.join(''));}
