import {test,expect} from '@playwright/test';
test('Updated editor attaches to the same review and preserves history and selection',async({page,context})=>{
 let id='';let updated;
 try{
  await page.goto('/');const opened=page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/reviews'));await page.locator('input[type=file]').setInputFiles('tests/fixtures/task02.musicxml');const original=await(await opened).json();id=original.id;
  const edited=await page.request.patch('/api/v1/reviews/'+id+'/events/e-1',{headers:{'If-Match':String(original.revision)},data:{pitch:{step:'D',octave:4,alter:'0'},draft_edit:true}});expect(edited.ok()).toBeTruthy();const before=await edited.json();
  updated=await context.newPage();await updated.goto('/?resume='+id+'&name=task02.musicxml');await expect(updated.getByTestId('real-head-e-1')).toBeVisible();await expect(updated.getByRole('button',{name:/Undo/})).toBeEnabled();
  const after=await(await updated.request.get('/api/v1/reviews/'+id)).json();expect(after.musicxml_base64).toBe(before.musicxml_base64);expect(after.revision).toBe(before.revision);
  await updated.getByRole('button',{name:'Groups',exact:true}).click();for(const key of ['e-1','e-2']){await updated.getByTestId('real-head-'+key).focus();await updated.getByTestId('real-head-'+key).press('Enter');}
  await expect(updated.locator('.working-scroll [data-event-id].real-selected')).toHaveCount(2);await updated.getByRole('button',{name:'Working score zoom out',exact:true}).click();await expect(updated.locator('.working-scroll [data-event-id].real-selected')).toHaveCount(2);
  await updated.close();updated=undefined;expect((await page.request.get('/api/v1/reviews/'+id)).ok()).toBeTruthy();
 }finally{await updated?.close();if(id)await page.request.delete('/api/v1/reviews/'+id);}
});
