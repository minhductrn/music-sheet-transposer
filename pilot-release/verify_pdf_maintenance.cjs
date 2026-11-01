// Existing-host verification; private samples are never distributed.
const {firefox}=require('../frontend-v2/node_modules/playwright');
const fs=require('node:fs'),path=require('node:path');
const baseURL=process.env.MST_BASE_URL||'http://127.0.0.1:5299';
const output=process.env.MST_OUTPUT||'/tmp/mst-pdf-maintenance-check';
const samples=[['concert-G',process.env.MST_MUSICXML_G],['concert-Gb',process.env.MST_MUSICXML_GB],['alto-down',process.env.MST_MUSICXML_ALTO]];
async function main(){
 for(const [name,file] of samples)if(!file||!fs.existsSync(file))throw Error('Missing private '+name+' sample. Set MST_MUSICXML_G, MST_MUSICXML_GB and MST_MUSICXML_ALTO.');
 fs.mkdirSync(output,{recursive:true});
 const browser=await firefox.launch({headless:true,executablePath:process.env.MST_FIREFOX||'/home/dtran/.cache/ms-playwright/firefox-1555/firefox/firefox'});
 const results=[];
 try{for(const [name,file] of samples){
  const page=await browser.newPage({viewport:{width:1440,height:1000}});let mutations=0;const errors=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(['PATCH','PUT','DELETE'].includes(r.method())||r.url().endsWith('/document-correction'))mutations++;});
  await page.addInitScript(()=>{
   window.centerChecks=[];const original=Element.prototype.setAttribute;
   Element.prototype.setAttribute=function(key,value){const tagged=key==='transform'&&this.hasAttribute('data-pdf-note-center-x');const ret=original.call(this,key,value);
    if(tagged){const svg=this.ownerSVGElement,b=this.getBoundingClientRect(),inverse=svg.getScreenCTM().inverse();const x=new DOMPoint(b.x+b.width/2,b.y).matrixTransform(inverse).x;window.centerChecks.push(Math.abs(x-Number(this.getAttribute('data-pdf-note-center-x'))));}return ret;};
  });
  await page.goto(baseURL);await page.locator('input[type=file]').setInputFiles(file);await page.getByTestId('real-head-e-1').waitFor({timeout:30000});
  await page.getByRole('button',{name:'Export PDF',exact:true}).click();
  const dialog=page.getByRole('dialog',{name:'PDF layout'});
  await page.waitForFunction(()=>{const d=document.querySelector('dialog');return d&&[...d.querySelectorAll('button')].some(b=>b.textContent==='Export'&&!b.disabled);},null,{timeout:60000});
  if(await page.locator('.pdf-preview').getAttribute('data-page-count')!=='1')throw Error(name+': expected one A4 page.');
  const checks=await page.evaluate(()=>window.centerChecks);
  if(!checks.length||checks.some(error=>error>0.1))throw Error(name+': lyric center mismatch.');
  fs.writeFileSync(path.join(output,name+'.png'),Buffer.from(await page.locator('.pdf-preview canvas').evaluate(c=>c.toDataURL('image/png').split(',')[1]),'base64'));
  const pending=page.waitForEvent('download');await dialog.getByRole('button',{name:'Export',exact:true}).click();await(await pending).saveAs(path.join(output,name+'.pdf'));
  if(mutations||errors.length)throw Error(name+': musical mutation or browser error.');
  results.push({name,fixture:'Private local MusicXML sample',centeredLyrics:checks.length,maxCenterError:Math.max(...checks),musicalMutationRequests:mutations,pageErrors:errors});await page.close();
 }}finally{await browser.close();}
 const report={status:'PASS',results};fs.writeFileSync(path.join(output,'verification.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
}
main().catch(error=>{console.error(error.message);process.exitCode=1;});
