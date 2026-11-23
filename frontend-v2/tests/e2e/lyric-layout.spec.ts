import {test,expect} from '@playwright/test';
const lyric=(number:number,text:string)=>`<lyric number="${number}" placement="below" default-y="${number===1?-99:-133}"><syllabic>single</syllabic><text>${text}</text></lyric>`;
const note=(step:string,voice:number,words:string)=>`<note><pitch><step>${step}</step><octave>5</octave></pitch><duration>32</duration><voice>${voice}</voice><type>whole</type>${words}</note>`;
const xml=`<score-partwise version="4.0"><part-list><score-part id="P"><part-name>Voice</part-name></score-part></part-list><part id="P"><measure number="1"><attributes><divisions>8</divisions><time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes>${note('C',1,lyric(1,'Ôi một')+lyric(2,'Ôi hai'))}<backup><duration>32</duration></backup>${note('E',2,lyric(1,'Chúa'))}</measure><measure number="2"><print new-system="yes"/>${note('D',1,lyric(1,'Lời một')+lyric(2,'Lời hai'))}<backup><duration>32</duration></backup>${note('F',2,lyric(1,'Giê'))}</measure></part></score-partwise>`;
for(const zoom of [100,80])test('Voice lyrics fit below their staff and retain original verse at '+zoom+'%',async({page})=>{
 const ids=new Set<string>();let baseline='';page.on('response',async r=>{if(r.request().method()==='POST'&&r.url().endsWith('/reviews')&&r.ok()){const body=await r.json();ids.add(body.id);baseline=body.musicxml_base64;}});
 try{
  await page.goto('/');await page.locator('input[type=file]').setInputFiles({name:'polyphonic-lyrics.musicxml',mimeType:'application/xml',buffer:Buffer.from(xml.replace('</part>',Array.from({length:6},(_,i)=>`<measure number="${i+3}">${note('D',1,lyric(1,'Lời một')+lyric(2,'Lời hai'))}<backup><duration>32</duration></backup>${note('F',2,lyric(1,'Giê'))}</measure>`).join('')+'</part>'))});
  if(zoom<100)for(let i=100;i>zoom;i-=10)await page.getByRole('button',{name:'Working score zoom out',exact:true}).click();
  const voice1=page.getByTestId('real-lyric-e-1-1'),voice2=page.getByTestId('real-lyric-e-2-1');await expect(voice2).toBeVisible();await page.waitForTimeout(250);
  const positions=await page.locator('.working-scroll svg').first().evaluate(svg=>{
   const groups=[...svg.querySelectorAll('g.vf-measure')];
   const staff=(g:Element)=>[...g.children].filter(n=>n.tagName==='path').slice(0,5).map(n=>n.getBoundingClientRect());
   const first=staff(groups[0]);const currentLine=groups[0].closest('g.staffline')!;const nextLine=[...svg.querySelectorAll('g.staffline')].find(line=>line!==currentLine&&line.getBoundingClientRect().top>currentLine.getBoundingClientRect().top)!;if(!nextLine)throw Error('Fixture must wrap onto a second system');const second=staff(nextLine.querySelector('g.vf-measure')!);const l=svg.querySelector('[data-testid="real-lyric-e-2-1"]')!.getBoundingClientRect();
   return {bottom:Math.max(...first.map(b=>b.bottom)),nextTop:Math.min(...second.map(b=>b.top)),lyricTop:l.top,lyricBottom:l.bottom};
  });expect(positions.lyricTop).toBeGreaterThan(positions.bottom);expect(positions.lyricBottom).toBeLessThan(positions.nextTop);
  expect((await voice2.boundingBox())!.y).toBeGreaterThan((await voice1.boundingBox())!.y);
  const current=await(await page.request.get('/api/v1/reviews/'+[...ids][0])).json();expect(current.musicxml_base64).toBe(baseline);
  await voice2.evaluate(node=>{const pane=node.closest('.working-scroll')!;const y=Math.min(pane.getBoundingClientRect().top+pane.clientHeight/2,innerHeight-80);pane.scrollTop+=node.getBoundingClientRect().top-y;});await expect(voice2).toBeInViewport();const hit=await voice2.boundingBox();await page.mouse.click(hit!.x+hit!.width/2,hit!.y+hit!.height/2);const editor=page.getByTestId('inline-lyric-editor');await expect(editor).toHaveAttribute('data-event-id','e-2');await expect(editor).toHaveAttribute('data-verse','1');await expect(page.getByLabel('Lyric syllable',{exact:true})).toHaveValue('Chúa');
 }finally{for(const id of ids)await page.request.delete('/api/v1/reviews/'+id,{timeout:3000}).catch(()=>{});}
});

test('Single lyric voice ignores stale imported offsets and aligns both verses',async({page})=>{
 let id='',baseline='';page.on('response',async r=>{if(r.request().method()==='POST'&&r.url().endsWith('/reviews')&&r.ok()){const body=await r.json();id=body.id;baseline=body.musicxml_base64;}});
 try{
  const source=xml.replace(/<backup><duration>32<\/duration><\/backup><note>[\s\S]*?<\/note>/g,'').replace('Lời một','Ôi một');
  await page.goto('/');await page.locator('input[type=file]').setInputFiles({name:'single-voice-offsets.musicxml',mimeType:'application/xml',buffer:Buffer.from(source)});
  const first=page.getByTestId('real-lyric-e-1-1');await expect(first).toBeVisible();await page.waitForTimeout(250);
  const layout=await page.locator('.working-scroll svg').first().evaluate(svg=>{
   const staff=svg.querySelector('g.vf-measure')!;
   const bottom=Math.max(...[...staff.children].filter(e=>e.tagName==='path').slice(0,5).map(e=>e.getBoundingClientRect().bottom));
   const lyrics=[...svg.querySelectorAll('[data-testid^="real-lyric-"]')].map(e=>({id:e.getAttribute('data-testid'),y:e.getBoundingClientRect().top}));
   return {bottom,lyrics};
  });
  const row=layout.lyrics.find(l=>l.id==='real-lyric-e-1-1')!;
  expect(row.y-layout.bottom).toBeGreaterThan(0);expect(row.y-layout.bottom).toBeLessThan(100);
  expect(Math.abs(row.y-layout.lyrics.find(l=>l.id==='real-lyric-e-2-1')!.y)).toBeLessThan(1);
  const current=await(await page.request.get('/api/v1/reviews/'+id)).json();expect(current.musicxml_base64).toBe(baseline);
 }finally{if(id)await page.request.delete('/api/v1/reviews/'+id,{timeout:3000}).catch(()=>{});}
});

test('Verse one stays on the same row when its owner changes voice in the next measure',async({page})=>{
 let id='';page.on('response',async r=>{if(r.request().method()==='POST'&&r.url().endsWith('/reviews')&&r.ok())id=(await r.json()).id;});
 try{
  const source=`<score-partwise version="4.0"><part-list><score-part id="P"><part-name>Voice</part-name></score-part></part-list><part id="P"><measure number="1"><attributes><divisions>8</divisions><time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes>${note('C',2,lyric(1,'Ôi')+lyric(2,'Oi'))}</measure><measure number="2">${note('D',1,lyric(1,'Chúa'))}</measure></part></score-partwise>`;
  await page.goto('/');await page.locator('input[type=file]').setInputFiles({name:'cross-voice-verses.musicxml',mimeType:'application/xml',buffer:Buffer.from(source)});
  const a=page.getByTestId('real-lyric-e-1-1'),b=page.getByTestId('real-lyric-e-2-1');await expect(b).toBeVisible();await page.waitForTimeout(250);
  const baseline=(node:Element)=>{const text=node.querySelector('text') as SVGTextElement;return new DOMPoint(0,Number(text.getAttribute('y'))).matrixTransform(text.getScreenCTM()!).y;};
  // Accents have different ink bounds; text rows must share the same baseline.
  expect(Math.abs(await a.evaluate(baseline)-await b.evaluate(baseline))).toBeLessThan(0.1);
 }finally{if(id)await page.request.delete('/api/v1/reviews/'+id,{timeout:3000}).catch(()=>{});}
});

test('First verse has the lower reference clearance and later verses stack underneath',async({page})=>{
 let id='',baseline='';page.on('response',async r=>{if(r.request().method()==='POST'&&r.url().endsWith('/reviews')&&r.ok()){const body=await r.json();id=body.id;baseline=body.musicxml_base64;}});
 try{
  const source=`<score-partwise version="4.0"><part-list><score-part id="P"><part-name>Voice</part-name></score-part></part-list><part id="P"><measure number="1"><attributes><divisions>8</divisions><time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes>${note('G',1,lyric(1,'Tầng')+lyric(2,'Lời hai')).replace('<octave>5</octave>','<octave>3</octave>')}</measure></part></score-partwise>`;
  await page.goto('/');await page.locator('input[type=file]').setInputFiles({name:'lower-first-verse.musicxml',mimeType:'application/xml',buffer:Buffer.from(source)});
  await expect(page.getByTestId('real-lyric-e-1-2')).toBeVisible();await page.waitForTimeout(250);
  const geometry=await page.locator('.working-scroll svg').first().evaluate(svg=>{
   const measure=svg.querySelector('g.vf-measure')!;
   const paths=[...measure.children].filter(n=>n.tagName==='path').slice(0,5).map(n=>n.getBoundingClientRect());
   const top=(paths[0].top+paths[0].bottom)/2,bottom=(paths[4].top+paths[4].bottom)/2,space=(bottom-top)/4;
   const head=svg.querySelector('[data-event-id="e-1"]')!.getBoundingClientRect(),lowest=Math.max(bottom,(head.top+head.bottom)/2);
   const line=top+Math.ceil((lowest-top)/space-0.1)*space;
   const baseline=(verse:number)=>{const t=svg.querySelector(`[data-testid="real-lyric-e-1-${verse}"] text`) as SVGTextElement;return new DOMPoint(0,Number(t.getAttribute('y'))).matrixTransform(t.getScreenCTM()!).y;};
   const t=svg.querySelector('[data-testid="real-lyric-e-1-1"] text') as SVGTextElement;
   const font=Number(t.getAttribute('font-size')!.replace('px',''))*Math.abs(t.getScreenCTM()!.d);
   return {space,gap:baseline(1)-font-line,first:baseline(1),second:baseline(2)};
  });
  expect(geometry.gap/geometry.space).toBeCloseTo(7.7,0);
  expect(geometry.second-geometry.first).toBeGreaterThan(geometry.space);
  const current=await(await page.request.get('/api/v1/reviews/'+id)).json();expect(current.musicxml_base64).toBe(baseline);
 }finally{if(id)await page.request.delete('/api/v1/reviews/'+id,{timeout:3000}).catch(()=>{});}
});


test('Imported extra verses stay separate and keep their original edit identities',async({page})=>{
 let id='',baseline='';page.on('response',async r=>{if(r.request().method()==='POST'&&r.url().endsWith('/reviews')&&r.ok()){const body=await r.json();id=body.id;baseline=body.musicxml_base64;}});
 try{
  const source=`<score-partwise version="4.0"><part-list><score-part id="P"><part-name>Voice</part-name></score-part></part-list><part id="P"><measure number="1"><attributes><divisions>8</divisions><time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes>${note('C',1,lyric(1,'Khi')+lyric(2,'Khi'))}</measure><measure number="2">${note('D',1,lyric(3,'tầng')+lyric(4,'icing'))}</measure></part></score-partwise>`;
  await page.goto('/');await page.locator('input[type=file]').setInputFiles({name:'preserve-extra-verses.musicxml',mimeType:'application/xml',buffer:Buffer.from(source)});
  const first=page.getByTestId('real-lyric-e-1-1'),extra=page.getByTestId('real-lyric-e-2-3');await expect(extra).toBeVisible();await page.waitForTimeout(250);
  expect((await extra.boundingBox())!.y-(await first.boundingBox())!.y).toBeGreaterThan(30);
  const current=await(await page.request.get('/api/v1/reviews/'+id)).json();expect(current.musicxml_base64).toBe(baseline);
  await extra.evaluate(node=>{const pane=node.closest('.working-scroll')!;const y=Math.min(pane.getBoundingClientRect().top+pane.clientHeight/2,innerHeight-80);pane.scrollTop+=node.getBoundingClientRect().top-y;});await expect(extra).toBeInViewport();const hit=await extra.boundingBox();await page.mouse.click(hit!.x+hit!.width/2,hit!.y+hit!.height/2);await expect(page.getByTestId('inline-lyric-editor')).toHaveAttribute('data-verse','3');await expect(page.getByLabel('Lyric syllable',{exact:true})).toHaveValue('tầng');
 }finally{if(id)await page.request.delete('/api/v1/reviews/'+id,{timeout:3000}).catch(()=>{});}
});
