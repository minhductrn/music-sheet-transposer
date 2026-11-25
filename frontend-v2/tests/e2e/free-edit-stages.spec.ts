import {test,expect} from '@playwright/test';
const xml='<score-partwise version="4.0"><part-list><score-part id="P"><part-name>Voice</part-name></score-part></part-list><part id="P"><measure number="1"><attributes><divisions>2</divisions><key><fifths>0</fifths><mode>major</mode></key><time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes><note><pitch><step>C</step><octave>5</octave></pitch><duration>8</duration><voice>1</voice><type>whole</type></note><note><pitch><step>D</step><octave>5</octave></pitch><duration>1</duration><voice>2</voice><type>eighth</type></note></measure></part></score-partwise>';
for(const instrument of [null,'Alto Saxophone','Soprano Saxophone','Tenor Saxophone'])test('Conflicting selected rhythm can be beamed and saved · '+(instrument??'Concert'),async({page})=>{
 const owned=new Set<string>();page.on('response',async r=>{if(r.request().method()==='POST'&&r.url().endsWith('/reviews')&&r.ok())owned.add((await r.json()).id);});
 try{
  await page.goto('/');await page.locator('input[type=file]').setInputFiles({name:'draft-conflict.musicxml',mimeType:'application/xml',buffer:Buffer.from(xml)});await expect(page.getByTestId('real-head-e-1')).toBeVisible();
  if(instrument){await page.getByRole('button',{name:'Instrument Scores →',exact:true}).click();await page.getByRole('button',{name:new RegExp(instrument)}).click();}
  const editor=instrument?page.locator('.instrument-editor'):page.locator('.real-workspace').first();await expect(editor.getByRole('button',{name:'Save',exact:true})).toBeEnabled();
  await editor.getByRole('button',{name:'Groups',exact:true}).click();
  for(const id of ['e-1','e-2']){await editor.getByTestId('real-head-'+id).focus();await editor.getByTestId('real-head-'+id).press('Enter');}
  const pending=page.waitForResponse(r=>r.url().endsWith('/document-correction'));
  await editor.getByRole('button',{name:'Beam 2',exact:true}).click();const result=await pending;expect(result.ok()).toBeTruthy();const body=await result.json();
  expect(Buffer.from(body.musicxml_base64,'base64').toString()).toContain('>begin</');
  const notes=body.score.parts[0].measures[0].voices.flatMap((v:{events:{id:string;voice:string;duration:string}[]})=>v.events);
  expect(notes.find((n:{id:string})=>n.id==='e-1')).toMatchObject({voice:'1',duration:'4'});expect(notes.find((n:{id:string})=>n.id==='e-2')).toMatchObject({voice:'2',duration:'1/2'});
  const download=page.waitForEvent('download');await page.locator('.app-header').getByRole('button',{name:'Save',exact:true}).click();const file=await download;const stream=await file.createReadStream();const chunks:Buffer[]=[];for await(const chunk of stream!)chunks.push(Buffer.from(chunk));expect(Buffer.concat(chunks).toString()).toBe(Buffer.from(body.musicxml_base64,'base64').toString());
 }finally{for(const id of owned)await page.request.delete('/api/v1/reviews/'+id,{timeout:3000}).catch(()=>{});}
});
