import {describe,it,expect} from 'vitest';
import {planNoteDrop,snapStaffPosition,type NoteDropPosition} from '../src/real/noteDrag';
import type {Review,Event} from '../src/real/api';
const position:NoteDropPosition={measure_id:'m-1',measure_number:'1',staff:1,onset:'3',pitch:{step:'C',alter:'0',octave:5},x:0,y:0};
function review(events:Partial<Event>[],gaps:unknown[]=[]):Review{return {score:{parts:[{measures:[{id:'m-1',insertion_gaps:gaps,voices:[{events:events.map(e=>({id:'e-1',voice:'1',staff:1,kind:'note',grace:false,pitch:{step:'C',alter:'0',octave:5},...e}))}]}]}]}} as unknown as Review;}
describe('drop placement preserves the occupied timeline',()=>{
 it('adds at a missing beat without shifting the dotted half',()=>{
  const r=review([{onset:'0',duration:'3'}]);const before=JSON.stringify(r);
  expect(planNoteDrop(r,position,'1','1').body).toMatchObject({voice:'1',onset:'3',duration:'1',pitch:position.pitch});expect(JSON.stringify(r)).toBe(before);
 });
 it('keeps the chosen voice during a temporary rhythm conflict',()=>{
  const plan=planNoteDrop(review([{onset:'1',duration:'3'}]),position,'1','1');expect(plan.voice).toBe('1');expect(plan.rhythmConflict).toBe(true);
 });
 it('adds a different pitch at the same onset as a chord',()=>{
  const result=planNoteDrop(review([{onset:'3',duration:'1',pitch:{step:'E',alter:'0',octave:5}}]),position,'1','1');expect(result.chord).toBe(true);expect(result.voice).toBe('1');
 });
 it('never switches voices based on note type or occupancy',()=>{
  for(const kind of ['note','rest'])expect(planNoteDrop(review([{onset:'3',duration:'1',kind}]),position,'1','1').voice).toBe('1');
 });
 it('does not extend a finite gap across an existing event',()=>{
  const plan=planNoteDrop(review([{onset:'4',duration:'1'}],[{voice:'1',staff:1,onset:'2',duration:'2'}]),position,'2','1');expect(plan.voice).toBe('1');expect(plan.rhythmConflict).toBe(true);
 });
});


describe('magnetic note-column snapping',()=>{
 const anchors=[{beat:0,x:0},{beat:3,x:100},{beat:3.5,x:120}];const grid=[{beat:2.9375,x:97},{beat:3,x:100},{beat:3.0625,x:103},{beat:3.25,x:110}];
 it('uses the existing note onset for a near miss instead of overlapping the preceding note',()=>expect(snapStaffPosition(anchors,grid,97,8).beat).toBe(3));
 it('retains the fine grid outside a note column',()=>expect(snapStaffPosition(anchors,grid,110,8).beat).toBe(3.25));
 it('allows precise placement when magnetic tolerance is disabled',()=>expect(snapStaffPosition(anchors,grid,97,0).beat).toBe(2.9375));
});
