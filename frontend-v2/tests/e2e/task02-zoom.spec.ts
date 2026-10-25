import {test,expect,type Locator} from '@playwright/test';
const sample=process.env.AI_SDF_TASK02_SAMPLE;const sessions=new Set<string>();
test.beforeEach(async({page})=>{page.on('response',async r=>{if(r.request().method()==='POST'&&/\/api\/v1\/reviews$/.test(r.url())&&r.status()===201){try{sessions.add((await r.json()).id);}catch{/* context closed */}}});});
test.afterEach(async({request})=>{for(const id of sessions)await request.delete(`/api/v1/reviews/${id}`).catch(()=>{});sessions.clear();});
async function headWidth(pane:Locator){return pane.locator('g.vf-notehead').first().evaluate(n=>n.getBoundingClientRect().width);}
async function tiesMeetHeads(pane:Locator){
 return pane.evaluate(el=>{const svg=el.querySelector('svg')!,inverse=svg.getScreenCTM()!.inverse();
 const bounds=(id:string)=>{const node=svg.querySelector(`[data-score-event="${id}"]`);if(!node)return null;const b=node.getBoundingClientRect(),a=new DOMPoint(b.left,b.top).matrixTransform(inverse),z=new DOMPoint(b.right,b.bottom).matrixTransform(inverse);return {x:(a.x+z.x)/2,top:a.y,bottom:z.y};};
 const curves=[...svg.querySelectorAll<SVGGElement>('[data-testid^="real-curve-tie-"]')];const visibleNative=[...svg.querySelectorAll('g.vf-stavetie')].some(n=>getComputedStyle(n).opacity!=='0');if(visibleNative)return false;
 return curves.length>0&&curves.every(g=>{const ids=g.dataset.testid!.match(/tie-(e-\d+)-(e-\d+)$/)!,a=bounds(ids[1]),b=bounds(ids[2]);if(!a||!b)return false;const p=g.querySelector<SVGPathElement>('path:last-child')!,from=p.getPointAtLength(0),to=p.getPointAtLength(p.getTotalLength()),up=g.dataset.direction==='up',sign=up?-1:1;
 const values=p.getAttribute('d')!.match(/-?\d+(?:\.\d+)?(?:e[+-]?\d+)?/gi)!.map(Number);const forward=Array.from({length:values.length/6},(_,i)=>values[i*6+4]>values[i*6]);
 return Math.abs(from.x-a.x)<.2&&Math.abs(to.x-b.x)<.2&&Math.abs(from.y-((up?a.top:a.bottom)+sign*1.5))<.2&&Math.abs(to.y-((up?b.top:b.bottom)+sign*1.5))<.2&&forward.every(Boolean)&&(values.length===6||values[10]-values[6]<=12.2);});});
}
test('Real zoom scales noteheads with ties in source and working panes, Stage1 and Stage2; Fit stays independent',async({page})=>{
 test.skip(!sample);test.setTimeout(90000);await page.goto('/');await page.locator('input[type=file]').setInputFiles(sample!);await expect(page.locator('.working-pane [data-event-id]')).toHaveCount(63);
 for(const stage of [1,2]){
  if(stage===2){const d=page.waitForEvent('download');await page.getByRole('button',{name:'Save',exact:true}).click();await d;await page.getByRole('button',{name:'I retained the downloaded file'}).click();await page.getByRole('button',{name:'Instrument Scores →'}).click();await page.getByRole('button',{name:/Alto Saxophone/}).click();await expect(page.locator('.instrument-editor .working-pane [data-event-id]')).toHaveCount(63);}
  const root=stage===2?page.locator('.instrument-editor'):page.locator('.real-workspace');
  await expect(root.locator('.working-pane [data-event-id="e-6"]')).toHaveAttribute('data-voice','2');await expect(root.getByTestId('real-lyric-e-6-1')).toHaveText('Chúng');
  for(const side of ['source','working']){
   const pane=root.locator(`.${side}-pane`),other=root.locator(`.${side==='source'?'working':'source'}-pane`);await expect(pane.locator('g.vf-notehead').first()).toBeVisible();const base=await headWidth(pane),otherBase=await headWidth(other);
   const minus=side==='source'?'Source zoom out':'Working score zoom out',plus=side==='source'?'Source zoom in':'Working score zoom in';
   for(let i=0;i<5;i++){await root.getByRole('button',{name:minus,exact:true}).click();await expect.poll(()=>headWidth(pane)).toBeCloseTo(base*(.9-i*.1),1);await expect.poll(()=>tiesMeetHeads(pane)).toBe(true);}await expect.poll(()=>headWidth(pane)).toBeLessThan(base*.55);const small=await headWidth(pane);expect(small/base).toBeCloseTo(.5,1);expect(await headWidth(other)).toBeCloseTo(otherBase,1);await expect.poll(()=>tiesMeetHeads(pane)).toBe(true);
   for(let i=0;i<10;i++){await root.getByRole('button',{name:plus,exact:true}).click();await expect.poll(()=>headWidth(pane)).toBeCloseTo(base*(.6+i*.1),1);await expect.poll(()=>tiesMeetHeads(pane)).toBe(true);}await expect.poll(()=>headWidth(pane)).toBeGreaterThan(base*1.45);expect((await headWidth(pane))/base).toBeCloseTo(1.5,1);await expect.poll(()=>tiesMeetHeads(pane)).toBe(true);
   await root.getByRole('button',{name:`Fit ${side} score`,exact:true}).click();await expect.poll(()=>headWidth(pane)).toBeCloseTo(base,1);expect(await headWidth(other)).toBeCloseTo(otherBase,1);
  }
 }
 await page.screenshot({path:'evidence/task02/real-zoom-fixed.png',fullPage:true});
});
