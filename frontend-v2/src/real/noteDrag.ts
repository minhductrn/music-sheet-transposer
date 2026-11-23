import type { PointerEvent as ReactPointerEvent } from 'react';
import { rational, type Pitch, type Review } from './api';
export type NoteDropPosition = { measure_id:string; measure_number:string; onset:string; staff:number; pitch:Pitch; x:number; y:number; aligned?:boolean; guideTop?:number; guideBottom?:number; anchorVoices?:string[] };
export type NoteDropResolver = (x:number,y:number,fine?:boolean)=>NoteDropPosition|null;
export function createColumnGuide(){
    const element=document.createElement('div');element.className='note-column-guide';element.setAttribute('aria-hidden','true');element.hidden=true;
    return {element,update:(position:NoteDropPosition|null)=>{
        element.hidden=!position?.aligned||position.guideTop===undefined||position.guideBottom===undefined;
        if(element.hidden||!position)return;
        element.style.left=position.x+'px';element.style.top=position.guideTop+'px';element.style.height=(position.guideBottom!-position.guideTop!)+'px';
        element.dataset.onset=position.onset;element.dataset.voices=position.anchorVoices?.join(',')??'';
    },remove:()=>element.remove()};
}
export function snapStaffPosition(anchors:{beat:number;x:number}[],grid:{beat:number;x:number}[],x:number,tolerance:number){
    const nearest=(items:{beat:number;x:number}[])=>items.reduce((best,p)=>Math.abs(p.x-x)<Math.abs(best.x-x)?p:best);
    if(anchors.length){const anchor=nearest(anchors);if(Math.abs(anchor.x-x)<=tolerance)return anchor;}
    return nearest(grid);
}
export function planNoteDrop(review:Review, position:NoteDropPosition, duration:string, preferredVoice:string) {
    const measure=review.score.parts.flatMap(p=>p.measures).find(m=>m.id===position.measure_id);
    const notes=measure?.voices.flatMap(v=>v.events)??[];
    const start=rational(position.onset), length=rational(duration);
    const overlaps=notes.filter(e=>e.voice===preferredVoice&&!e.grace&&rational(e.onset)<start+length&&start<rational(e.onset)+rational(e.duration));
    const chord=overlaps.length>0&&new Set(overlaps.map(e=>e.chord_id??e.id)).size===1&&overlaps.every(e=>e.kind==='note'&&rational(e.onset)===start&&e.staff===position.staff);
    const gap=measure?.insertion_gaps.find(g=>g.voice===preferredVoice&&g.staff===position.staff&&rational(g.onset)<=start&&start<rational(g.onset)+rational(g.duration));
    const voice=preferredVoice;
    const rhythmConflict=!!((overlaps.length&&!chord)||(gap&&start+length>rational(gap.onset)+rational(gap.duration)));
    return {body:{measure_id:position.measure_id,onset:position.onset,staff:position.staff,voice,kind:'note',pitch:position.pitch,duration},voice,chord:chord&&voice===preferredVoice,rhythmConflict};
}
export function startNoteDrag(event:ReactPointerEvent<HTMLButtonElement>,duration:string,resolve:()=>NoteDropResolver|null,review:Review,voice:string,onDrop:(body:Record<string,unknown>)=>void,onStart?:()=>void) {
    if(event.button!==0)return;
    const origin={x:event.clientX,y:event.clientY},pointer=event.pointerId;
    const button=event.currentTarget;let dragging=false,target:NoteDropPosition|null=null;
    const guide=document.createElement('div');guide.className='note-drop-guide';guide.setAttribute('aria-hidden','true');
    const column=createColumnGuide();
    const preview=document.createElement('div');preview.className='note-drop-preview';preview.setAttribute('role','status');preview.style.pointerEvents='none';
    const oldSelect=document.body.style.userSelect;const previousTouch=button.style.touchAction;button.style.touchAction='none';
    const move=(e:PointerEvent)=>{if(e.pointerId!==pointer)return;if(!dragging&&Math.hypot(e.clientX-origin.x,e.clientY-origin.y)<5)return;
        if(!dragging){dragging=true;onStart?.();document.body.append(preview,guide,column.element);document.body.style.userSelect='none';}
        e.preventDefault();target=resolve()?.(e.clientX,e.clientY,e.altKey)??null;
        preview.style.left=Math.max(4,Math.min(window.innerWidth-230,e.clientX+14))+'px';preview.style.top=Math.max(4,e.clientY-65)+'px';
        column.update(target);guide.hidden=!target;if(target){guide.style.left=target.x+'px';guide.style.top=target.y+'px';const plan=planNoteDrop(review,target,duration,voice);preview.textContent='♪ '+target.pitch.step+({'-1':'♭','1':'♯'}[target.pitch.alter]??'')+target.pitch.octave+' · measure '+target.measure_number+' · beat '+(rational(target.onset)+1)+' · Voice '+plan.voice+(plan.chord?' · chord':'')+(target.aligned?' · Aligned':'');preview.dataset.valid='true';}
        else{preview.textContent='Drag onto a Working Score staff';preview.dataset.valid='false';}
    };
    const cleanup=()=>{window.removeEventListener('pointermove',move);window.removeEventListener('pointerup',up);window.removeEventListener('pointercancel',cancel);window.removeEventListener('keydown',key);preview.remove();guide.remove();column.remove();document.body.style.userSelect=oldSelect;button.style.touchAction=previousTouch;};
    const cancel=()=>{cleanup();};
    const key=(e:KeyboardEvent)=>{if(e.key==='Escape'){e.preventDefault();cancel();}};
    const up=(e:PointerEvent)=>{if(e.pointerId!==pointer)return;if(dragging){e.preventDefault();const suppress=(click:MouseEvent)=>{click.preventDefault();click.stopPropagation();};window.addEventListener('click',suppress,{capture:true,once:true});setTimeout(()=>window.removeEventListener('click',suppress,true),0);target=resolve()?.(e.clientX,e.clientY,e.altKey)??null;if(target)onDrop(planNoteDrop(review,target,duration,voice).body);}cleanup();};
    window.addEventListener('pointermove',move,{passive:false});window.addEventListener('pointerup',up);window.addEventListener('pointercancel',cancel);window.addEventListener('keydown',key);
}
