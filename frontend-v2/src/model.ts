// PO directive: syllable-hyphen and melisma tools are disabled; preserve stored metadata.
export const LYRIC_MARKERS_ENABLED=false;
// Step 1 only: deterministic synthetic notation, never MusicXML or real transposition.
export type R = [number, number];
const gcd = (a:number,b:number):number => b ? gcd(b,a%b) : Math.abs(a);
export function rat(n:number,d=1):R { if(!d) throw Error('Zero denominator'); const g=gcd(n,d);return [n/g,d/g]; }
export const add=(a:R,b:R):R=>rat(a[0]*b[1]+b[0]*a[1],a[1]*b[1]);
export const mul=(a:R,b:R):R=>rat(a[0]*b[0],a[1]*b[1]);
export const num=(a:R)=>a[0]/a[1];
export const eq=(a:R,b:R)=>a[0]*b[1]===b[0]*a[1];
export const clone=<T,>(v:T):T=>structuredClone(v);
export type Head={id:string;pitch:number;small:boolean};
export type Event={id:string;onset:R;duration:R;value:number;dot:boolean;voice:number;staff:number;heads:Head[];rest:boolean;group?:string};
export type Curve={id:string;kind:'tie'|'slur';from:string;to:string;direction:'up'|'down'};
export type Group={id:string;kind:'beam'|'tuplet';events:string[]};
export type Lyric={id:string;noteId:string;voice:number;verse:number;text:string;hyphen:boolean;melisma:boolean};
export type TextItem={id:string;role:string;text:string;x:number;y:number};
export type Score={title:string;key:string;events:Event[];gaps:Event[];curves:Curve[];groups:Group[];lyrics:Lyric[];texts:TextItem[];serial:number};
export type Selection={kind:'head'|'curve'|'gap'|'event'|'text';id:string}|null;
export const demo=():Score=>({title:'Bài ca hy vọng',key:'F',serial:100,
 events:[
 {id:'e1',onset:[0,1],duration:[1,1],value:4,dot:false,voice:1,staff:1,heads:[{id:'n1',pitch:67,small:false},{id:'n2',pitch:71,small:true}],rest:false},
 {id:'e2',onset:[1,1],duration:[1,1],value:4,dot:false,voice:1,staff:1,heads:[{id:'n3',pitch:67,small:false}],rest:false},
 {id:'e3',onset:[3,1],duration:[1,1],value:4,dot:false,voice:1,staff:1,heads:[{id:'n4',pitch:69,small:false}],rest:false},
 {id:'e4',onset:[4,1],duration:[1,1],value:4,dot:false,voice:1,staff:1,heads:[{id:'n5',pitch:69,small:false}],rest:false},
 {id:'e5',onset:[6,1],duration:[1,1],value:4,dot:false,voice:1,staff:1,heads:[{id:'n6',pitch:72,small:false}],rest:false},
 {id:'v2a',onset:[0,1],duration:[1,2],value:8,dot:false,voice:2,staff:1,heads:[{id:'v1',pitch:60,small:false}],rest:false},
 {id:'v2b',onset:[1,2],duration:[1,2],value:8,dot:false,voice:2,staff:1,heads:[{id:'v2',pitch:62,small:false}],rest:false}],
 gaps:[],curves:[{id:'t1',kind:'tie',from:'n4',to:'n5',direction:'up'}],groups:[],
 lyrics:[{id:'l1',noteId:'n1',voice:1,verse:1,text:'Niềm',hyphen:false,melisma:false},{id:'l2',noteId:'n3',voice:1,verse:1,text:'tin',hyphen:false,melisma:false},{id:'l3',noteId:'n4',voice:1,verse:1,text:'sáng',hyphen:false,melisma:false}],
 texts:[{id:'title',role:'Title',text:'Bài ca hy vọng',x:450,y:48},{id:'composer',role:'Composer',text:'Giai điệu minh họa',x:690,y:78},{id:'annotation',role:'Score Text',text:'ĐK:',x:80,y:320}]});
export function locate(d:Score,id:string){ for(const e of d.events){const h=e.heads.find(h=>h.id===id);if(h)return {event:e,head:h};}return null; }
const fresh=(d:Score,prefix:string)=>prefix+(++d.serial);
export function deleteSelected(source:Score,s:Selection):Score {
 const d=clone(source);if(!s)return d;
 if(s.kind==='curve'){d.curves=d.curves.filter(c=>c.id!==s.id);return d;}
 if(s.kind==='text'){d.texts=d.texts.filter(t=>t.id!==s.id);return d;}
 const found=s.kind==='head'?locate(d,s.id):null;
 const event=found?.event ?? (s.kind==='event'?d.events.find(e=>e.id===s.id):undefined);
 if(!event)return d;
 const removed=found?[found.head.id]:event.heads.map(h=>h.id);
 event.heads=event.heads.filter(h=>!removed.includes(h.id));
 d.curves=d.curves.filter(c=>!removed.includes(c.from)&&!removed.includes(c.to));
 d.lyrics=d.lyrics.filter(l=>!removed.includes(l.noteId));
 if(!event.heads.length){d.events=d.events.filter(e=>e.id!==event.id);d.gaps.push({...event,heads:[],rest:false});}
 return d;
}
export function insert(source:Score,onset:R,voice:number,pitch:number,value:number,rest=false):Score {
 const d=clone(source);const existing=d.events.find(e=>e.voice===voice&&eq(e.onset,onset));
 if(existing){if(rest||existing.rest)throw Error('Choose an empty rhythmic position for a rest.');
 if(existing.heads.some(h=>h.pitch===pitch))throw Error('This chord already contains that pitch.');
 existing.heads.push({id:fresh(d,'n'),pitch,small:false});return d;}
 const gap=d.gaps.find(e=>e.voice===voice&&eq(e.onset,onset));
 d.gaps=d.gaps.filter(e=>e!==gap);
 d.events.push({id:gap?.id??fresh(d,'e'),onset:clone(onset),duration:gap?clone(gap.duration):rat(4,value),value:gap?.value??value,dot:gap?.dot??false,voice,staff:1,group:gap?.group,rest,heads:rest?[]:[{id:fresh(d,'n'),pitch,small:false}]});return d;
}
export function connect(source:Score,from:string,to:string,kind:'tie'|'slur'):Score {
 const d=clone(source),a=locate(d,from),b=locate(d,to);
 const name=kind==='tie'?'Tie':'Slur';
 if(!a||!b)throw Error(name+': select two existing noteheads.');
 if(from===to)throw Error(name+': choose a different destination notehead.');
 if(a.event.voice!==b.event.voice)throw Error(name+': source is Voice '+a.event.voice+', destination is Voice '+b.event.voice+'. Choose a later note in Voice '+a.event.voice+'.');
 if(a.event.staff!==b.event.staff)throw Error(name+': choose a note on the same staff.');
 if(num(a.event.onset)>=num(b.event.onset))throw Error(name+': the destination must come after the source. Press Escape to select an earlier source.');
 if(kind==='tie'&&a.head.pitch!==b.head.pitch)throw Error('Tie requires equal pitches. To connect different pitches in the same voice, use Slur.');
 if(d.curves.some(c=>c.kind===kind&&c.from===from&&c.to===to))return d;
 d.curves.push({id:fresh(d,kind),kind,from,to,direction:'up'});return d;
}
export function setDuration(source:Score,id:string,value:number,dot:boolean):Score {
 const d=clone(source);const e=locate(d,id)?.event??d.events.find(e=>e.id===id);if(!e)return d;
 e.value=value;e.dot=dot;e.duration=mul(rat(4,value),dot?[3,2]:[1,1]);
 const group=d.groups.find(g=>g.id===e.group);
 if(group?.kind==='tuplet'){
  e.duration=mul(e.duration,[2,3]);
  const members=group.events.map(id=>d.events.find(e=>e.id===id)??d.gaps.find(e=>e.id===id)).filter((e):e is Event=>!!e);
  let offset=members[0].onset;for(const m of members){m.onset=offset;offset=add(offset,m.duration);}
 }
 return d;
}
export function makeGroup(source:Score,target:Event|{onset:R;voice:number;pitch:number},kind:'tuplet'|'beam',count=3):Score {
 const d=clone(source);const existing='id' in target?d.events.find(e=>e.id===target.id)??d.gaps.find(e=>e.id===target.id):d.gaps.find(e=>e.voice===target.voice&&eq(e.onset,target.onset));
 const onset=existing?.onset??target.onset,voice=existing?.voice??target.voice;
 if(existing?.group)throw Error('This event already belongs to a group. Choose an ungrouped anchor.');
 const groupId=fresh(d,'g');const total=kind==='tuplet'?2:count;
 const duration:R=kind==='tuplet'?[2,3]:[1,4];
 const firstDuration=duration;
 const lastEnd=kind==='tuplet'?add(onset,[1,1]):add(onset,rat(count,4));
 if([...d.events,...d.gaps].some(e=>e.id!==existing?.id&&e.voice===voice&&num(e.onset)>=num(onset)&&num(e.onset)<num(lastEnd)))throw Error('The group would overlap an occupied onset. Choose an empty interval.');
 const first:Event=existing?{...existing,heads:existing.heads.length?existing.heads:[{id:fresh(d,'n'),pitch:67,small:false}],rest:false}: {id:fresh(d,'e'),onset:clone(onset),voice,staff:1,heads:[{id:fresh(d,'n'),pitch:'pitch' in target?target.pitch:67,small:false}],rest:false,duration:firstDuration,value:4,dot:false};
 first.group=groupId;first.duration=firstDuration;first.value=kind==='tuplet'?4:16;first.dot=false;
 d.events=d.events.filter(e=>e.id!==first.id);d.gaps=d.gaps.filter(e=>e.id!==first.id);
 const events=[first];let next=add(onset,firstDuration);
 for(let i=1;i<total;i++){const duration:R=kind==='tuplet'?[1,3]:[1,4];events.push({id:fresh(d,'e'),onset:next,duration,value:kind==='tuplet'?8:16,dot:false,voice,staff:1,heads:[{id:fresh(d,'n'),pitch:first.heads[0].pitch,small:false}],rest:false,group:groupId});next=add(next,duration);}
 d.events.push(...events);d.groups.push({id:groupId,kind,events:events.map(e=>e.id)});return d;
}
export type History={present:Score;past:Score[];future:Score[]};
export function commit(h:History,next:Score):History {if(JSON.stringify(next)===JSON.stringify(h.present))return h;return {present:clone(next),past:[...h.past,clone(h.present)],future:[]};}
export function undo(h:History):History {return h.past.length?{present:clone(h.past[h.past.length-1]),past:h.past.slice(0,-1),future:[clone(h.present),...h.future]}:h;}
export function redo(h:History):History {return h.future.length?{present:clone(h.future[0]),past:[...h.past,clone(h.present)],future:h.future.slice(1)}:h;}
export function savedInput(saved:Score|null){if(!saved)throw Error('Save a simulated canonical snapshot in Stage 1 first.');return clone(saved);}
export const instruments=[{id:'alto',name:'Alto Saxophone E-flat',offset:9},{id:'soprano',name:'Soprano Saxophone B-flat',offset:2},{id:'tenor',name:'Tenor Saxophone B-flat',offset:14}] as const;
export function connectionGuide(score:Score,sourceId:string,kind:'tie'|'slur'){
 const source=locate(score,sourceId);if(!source)return 'Choose the source notehead.';
 const name=kind==='tie'?'Tie':'Slur';
 const targets=score.events.filter(e=>e.voice===source.event.voice&&e.staff===source.event.staff&&num(e.onset)>num(source.event.onset)).flatMap(e=>e.heads).filter(h=>kind==='slur'||h.pitch===source.head.pitch);
 return targets.length?name+': source '+sourceId+' · Voice '+source.event.voice+'. Choose a later '+(kind==='tie'?'same-pitch ':'')+'note in this voice.':name+': source '+sourceId+' is the last eligible note in Voice '+source.event.voice+'. Press Escape, then select an earlier source or add a later note in this voice.';
}

export function upsertLyric(source:Score,noteId:string,verse:number,text:string):Score {
 const d=clone(source),owner=locate(d,noteId);if(!owner)throw Error('Choose an existing notehead for lyrics.');
 if(!Number.isInteger(verse)||verse<1)throw Error('Choose a valid verse.');
 const existing=d.lyrics.find(l=>l.noteId===noteId&&l.verse===verse);
 if(existing)existing.text=text;else d.lyrics.push({id:fresh(d,'l'),noteId,voice:owner.event.voice,verse,text,hyphen:false,melisma:false});
 return d;
}
