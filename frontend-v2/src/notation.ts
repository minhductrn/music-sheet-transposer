import { num } from './model';
import type { R } from './model';
// Finite synthetic 4/4 layout. Rendering never changes event timing.
export const layout={beatsPerMeasure:4,measuresPerSystem:2,measureStart:150,measureWidth:342.5,noteStart:170,beatWidth:75.625,staffTop:160,staffBottom:200,systemHeight:245,barEnd:835};
export const systemFor=(onset:R)=>Math.floor(num(onset)/(layout.beatsPerMeasure*layout.measuresPerSystem));
export function measureBox(index:number){const column=index%layout.measuresPerSystem,row=Math.floor(index/layout.measuresPerSystem),start=layout.measureStart+column*layout.measureWidth;return {start,end:start+layout.measureWidth,top:layout.staffTop+row*layout.systemHeight,bottom:layout.staffBottom+row*layout.systemHeight};}
const steps=[0,0,1,2,2,3,3,4,5,5,6,6];
const naturals=[0,2,4,5,7,9,11];
export function spelled(pitch:number){const octave=Math.floor(pitch/12)-1,pc=((pitch%12)+12)%12,degree=steps[pc];return {step:octave*7+degree,alter:pc-naturals[degree]};}
export function pitchAtStep(step:number){const octave=Math.floor(step/7),degree=((step%7)+7)%7;return (octave+1)*12+naturals[degree];}
export function dragPitch(pitch:number,dy:number){const s=spelled(pitch);return Math.max(36,Math.min(96,pitchAtStep(s.step-Math.round(dy/5))+s.alter));}
export function point(onset:R,pitch:number){const measure=Math.floor(num(onset)/4),column=measure%layout.measuresPerSystem;return {x:layout.noteStart+column*layout.measureWidth+(num(onset)%4)*layout.beatWidth,y:layout.staffBottom+systemFor(onset)*layout.systemHeight-(spelled(pitch).step-30)*5};}
export function ledgerLines(onset:R,pitch:number){const y=point(onset,pitch).y,offset=systemFor(onset)*layout.systemHeight,lines:number[]=[];for(let line=layout.staffTop+offset-10;line>=y;line-=10)lines.push(line);for(let line=layout.staffBottom+offset+10;line<=y;line+=10)lines.push(line);return lines;}
export function anchorAt(x:number,y:number){const row=y>320?1:0,column=Math.max(0,Math.min(layout.measuresPerSystem-1,Math.floor((x-layout.measureStart)/layout.measureWidth)));const start=layout.noteStart+column*layout.measureWidth;const half=Math.max(0,Math.min(7,Math.round((x-start)/(layout.beatWidth/2))));return {onset:[half+(row*layout.measuresPerSystem+column)*8,2] as R,pitch:pitchAtStep(30-Math.round((y-(layout.staffBottom+row*layout.systemHeight))/5))};}

export function fitScale(width:number,height:number){void height;return Math.max(.05,Math.min(2,width/900));}

export function isStaffInsertionArea(y:number){return [0,1].some(row=>y>=layout.staffTop+row*layout.systemHeight-55&&y<=layout.staffBottom+row*layout.systemHeight+40);}
