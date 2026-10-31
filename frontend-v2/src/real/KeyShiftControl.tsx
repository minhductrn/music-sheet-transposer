import type {Key} from './api';
export const majorKeys=['C♭','G♭','D♭','A♭','E♭','B♭','F','C','G','D','A','E','B','F♯','C♯'];
export const minorKeys=['A♭','E♭','B♭','F','C','G','D','A','E','B','F♯','C♯','G♯','D♯','A♯'];
const mod=(n:number,m:number)=>((n%m)+m)%m;
export function destinationFor(source:number,steps:number,preferred?:number){
 if(steps%12===0)return source;
 const pc=mod(7*source+steps,12),options=Array.from({length:15},(_,i)=>i-7).filter(f=>mod(7*f,12)===pc);
 if(preferred!==undefined&&options.includes(preferred))return preferred;
 return options.sort((a,b)=>Math.abs(a)-Math.abs(b)||(source<0?a-b:b-a))[0];
}
export function intervalFor(source:number,target:number,direction:'up'|'down'){
 const up=mod(7*(target-source),12);return direction==='down'?(up?up-12:-12):up;
}
type Props={source:Key;target:number;steps:number;prefix?:string;onChange:(source:Key,target:number,steps:number)=>void};
export function KeyShiftControl({source,target,steps,prefix='',onChange}:Props){
 const names=source.mode==='minor'?minorKeys:majorKeys;
 const label=(text:string)=>prefix?prefix+' '+text:text;
 function shift(next:number){if(next>=-24&&next<=24)onChange(source,destinationFor(source.fifths,next,target),next);}
 function changeSource(next:Key){onChange(next,destinationFor(next.fifths,steps,target),steps);}
 return <div className="key-shift-control">
 <label>Source key<select aria-label={label('Source key')} value={source.fifths} onChange={e=>changeSource({...source,fifths:Number(e.target.value)})}>{names.map((n,i)=><option key={i} value={i-7}>{n}</option>)}</select></label>
 <label>Mode<select aria-label={label('Mode')} value={source.mode} onChange={e=>changeSource({...source,mode:e.target.value as Key['mode']})}><option value="major">Major</option><option value="minor">Minor</option></select></label>
 <div className="interval-stepper" role="group" aria-label={label('Interval')}><button type="button" aria-label={label('Decrease interval by half a tone')} disabled={steps<=-24} onClick={()=>shift(steps-1)}>−</button><output aria-label={label('Interval in tones')}>{steps>0?'+':''}{(steps/2).toFixed(1)}</output><span>tones</span><button type="button" aria-label={label('Increase interval by half a tone')} disabled={steps>=24} onClick={()=>shift(steps+1)}>+</button></div>
 <label>Destination<select aria-label={prefix?prefix+' Destination key':'New concert key'} value={target} onChange={e=>{const next=Number(e.target.value);onChange(source,next,intervalFor(source.fifths,next,steps<0?'down':'up'));}}>{names.map((n,i)=><option key={i} value={i-7}>{n}</option>)}</select></label>
 <label>Direction<select aria-label={label('Direction')} value={steps<0?'down':'up'} onChange={e=>onChange(source,target,intervalFor(source.fifths,target,e.target.value as 'up'|'down'))}><option value="up">Up</option><option value="down">Down</option></select></label>
 </div>;
}
