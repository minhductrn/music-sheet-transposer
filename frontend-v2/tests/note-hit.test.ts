import {describe,it,expect} from 'vitest';
import {resolveNoteHits} from '../src/real/noteHit';
const hit=(id:string,x:number,y:number,w=8,h=5)=>({id,box:{left:x,right:x+w,top:y,bottom:y+h,width:w,height:h}});
describe('notehead acquisition',()=>{
 it('selects the upper chord pitch despite overlapping padded targets',()=>expect(resolveNoteHits([hit('upper',0,0),hit('lower',0,5)],4,2).map(h=>h.id)).toEqual(['upper']));
 it('allows changing to the lower head instead of retaining the prior selection',()=>expect(resolveNoteHits([hit('upper',0,0),hit('lower',0,5)],4,7).map(h=>h.id)).toEqual(['lower']));
 it('keeps a chooser for physically identical unisons',()=>expect(resolveNoteHits([hit('voice1',0,0),hit('voice2',0,0)],4,2)).toHaveLength(2));
 it('keeps a chooser at the common center of normal and small unisons',()=>expect(resolveNoteHits([hit('normal',0,0,10,8),hit('small',1.5,1.2,7,5.6)],5,4)).toHaveLength(2));
 it('does not select an adjacent rhythmic column because of its padding',()=>expect(resolveNoteHits([hit('first',0,0),hit('next',10,0)],7,2).map(h=>h.id)).toEqual(['first']));
 it('chooses the nearest head when clicking just outside its outline',()=>expect(resolveNoteHits([hit('upper',0,0),hit('lower',0,10)],4,6).map(h=>h.id)).toEqual(['upper']));
});
