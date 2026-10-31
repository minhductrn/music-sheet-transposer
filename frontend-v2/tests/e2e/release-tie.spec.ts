import {test,expect} from '@playwright/test';
for(const stage2 of [false,true])test('RC1 accidental/tie command and Undo in '+(stage2?'Stage 2':'Stage 1'),async({page})=>{
 await page.goto('/');await page.locator('input[type=file]').setInputFiles('tests/fixtures/accidental-tie.musicxml');
 await expect(page.getByText('UX Next · 1.0.0-rc1',{exact:true}).first()).toBeVisible();
 if(stage2){await page.getByRole('button',{name:'Instrument Scores →',exact:true}).click();await page.getByRole('button',{name:/Alto Saxophone/}).click();}
 const editor=stage2?page.locator('.instrument-editor'):page.locator('.real-workspace').first();
 const head=editor.getByTestId('real-head-e-1');await expect(head).toBeVisible();const before=await head.getAttribute('data-pitch');const other=await editor.getByTestId('real-head-e-4').getAttribute('data-pitch');
 await head.focus();await head.press('Enter');const response=page.waitForResponse(r=>r.request().method()==='PATCH'&&r.url().endsWith('/events/e-1'));
 await editor.getByRole('button',{name:'Flat accidental',exact:true}).click();const result=await response;expect(result.ok()).toBeTruthy();
 const data=await result.json();const all=data.score.parts.flatMap((p:{measures:{voices:{events:{id:string;pitch:{alter:string};duration:string}[]}[]}[]})=>p.measures.flatMap(m=>m.voices.flatMap(v=>v.events)));
 for(const id of ['e-1','e-2','e-3'])expect(all.find((e:{id:string})=>e.id===id).pitch.alter).toBe('-1');
 await expect(editor.getByTestId('real-head-e-4')).toHaveAttribute('data-pitch',other!);
 await page.locator('.app-header').getByRole('button',{name:'↶ Undo',exact:true}).click();await expect(head).toHaveAttribute('data-pitch',before!);
 await editor.getByRole('button',{name:'Edit Only',exact:true}).click();await expect(editor.locator('.source-pane')).toHaveCount(0);
 await head.focus();await head.press('Enter');await expect(editor.getByRole('button',{name:'Remove accidental',exact:true})).toBeVisible();
});
