import {test,expect} from '@playwright/test';
test('Classic retains vertical editor and plain Add Chord in Stage 1 and Stage 2',async({page})=>{
 await page.goto('/');await page.locator('input[type=file]').setInputFiles('tests/fixtures/task02.musicxml');
 const button=page.getByRole('button',{name:'Add Chord',exact:true});await expect(button).toBeVisible();await expect(button).toHaveText('Add Chord');
 const rail=page.locator('.real-workspace .rail').first();expect((await rail.boundingBox())!.width).toBeLessThan(150);
 await page.getByRole('button',{name:'Edit Only',exact:true}).click();await expect(button).toHaveText('Add Chord');
 await page.getByRole('button',{name:'Instrument Scores →',exact:true}).click();await page.getByRole('button',{name:/Alto Saxophone/}).click();
 const editor=page.locator('.instrument-editor');await expect(editor.getByRole('button',{name:'Add Chord',exact:true})).toHaveText('Add Chord');
 await page.screenshot({path:'evidence/classic-hotfix-stage2.png'});
});
