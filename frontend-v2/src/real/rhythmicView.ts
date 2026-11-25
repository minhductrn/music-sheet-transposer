/** Render transient same-voice overlaps on independent engraving tracks.
 * MusicXML, user voice IDs and onsets remain canonical and are never rewritten.
 */
export function prepareRhythmicView(xml:string){
    const doc=new DOMParser().parseFromString(xml,'application/xml');if(doc.querySelector('parsererror'))throw Error('Invalid MusicXML.');
    const children=(e:Element,name:string)=>[...e.children].filter(n=>n.localName===name);
    const text=(e:Element,name:string,fallback:string)=>children(e,name)[0]?.textContent??fallback;
    const used=new Set([...doc.getElementsByTagNameNS('*','voice')].map(n=>n.textContent??'1'));
    const durationOrigins=new Map<string,number>();
    const voices=new Map<string,string>(),tracks=new Map<string,string>();let changed=false,next=1;
    const key=(part:number,staff:number,voice:string)=>[part,staff,voice].join('|');
    children(doc.documentElement,'part').forEach((part,partIndex)=>{
        let divisions=1;
        for(const measure of children(part,'measure')){
            let cursor=0,previous=0;
            const groups=new Map<string,{onset:number;end:number;staff:number;voice:string;notes:Element[]}>();
            for(const node of measure.children){
                if(node.localName==='attributes'){const value=Number(text(node,'divisions',String(divisions)));if(value>0)divisions=value;}
                if(node.localName==='backup'||node.localName==='forward'){cursor+=Number(text(node,'duration','0'))/divisions*(node.localName==='backup'?-1:1);continue;}
                if(node.localName!=='note')continue;
                const chord=children(node,'chord').length>0,onset=chord?previous:cursor,duration=Number(text(node,'duration','0'))/divisions;
                if(!children(node,'grace').length&&!chord)cursor+=duration;previous=onset;
                if(children(node,'grace').length||!Number.isFinite(onset)||!(duration>0))continue;
                const staff=Number(text(node,'staff','1')),voice=text(node,'voice','1'),id=key(partIndex,staff,voice)+'|'+onset;
                const existing=groups.get(id);if(existing){existing.end=Math.max(existing.end,onset+duration);existing.notes.push(node);}else groups.set(id,{onset,end:onset+duration,staff,voice,notes:[node]});
            }
            const ends=new Map<string,number[]>();
            // Keep explicitly beamed notes on one engraving track even during
            // a temporary overlap. This changes rendering only, never timing.
            const beamLanes=new Map<string,number>();
            for(const group of [...groups.values()].sort((a,b)=>a.onset-b.onset)){
                const owner=key(partIndex,group.staff,group.voice);if(!ends.has(owner))ends.set(owner,[]);const lanes=ends.get(owner)!;
                const mark=group.notes.flatMap(n=>children(n,'beam')).find(b=>(b.getAttribute('number')??'1')==='1')?.textContent;
                let lane=(mark==='continue'||mark==='end')?beamLanes.get(owner)??-1:-1;
                if(lane<0)lane=lanes.findIndex(end=>end<=group.onset+1e-7);if(lane<0)lane=lanes.length;lanes[lane]=Math.max(lanes[lane]??0,group.end);
                if(mark==='begin')beamLanes.set(owner,lane);else if(mark==='end')beamLanes.delete(owner);
                if(lane===0)continue;
                const laneKey=owner+'|'+lane;let rendered=tracks.get(laneKey);
                if(!rendered){while(used.has(String(next)))next++;rendered=String(next++);used.add(rendered);tracks.set(laneKey,rendered);voices.set(key(partIndex,group.staff,rendered),group.voice);}
                for(const note of group.notes){
                    let voice=children(note,'voice')[0];if(!voice){voice=doc.createElementNS(doc.documentElement.namespaceURI,'voice');note.insertBefore(voice,[...note.children].find(n=>['type','dot','accidental','time-modification','stem','notehead','staff','beam','notations','lyric'].includes(n.localName))??null);}voice.textContent=rendered;
                    if(!children(note,'stem').length){const stem=doc.createElementNS(doc.documentElement.namespaceURI,'stem');stem.textContent=Number(group.voice)%2===0?'down':'up';note.insertBefore(stem,[...note.children].find(n=>['notehead','staff','beam','notations','lyric'].includes(n.localName))??null);}
                    changed=true;
                }
            }
            // Rebuild only the disposable engraving stream in time order per
            // track. Native voice formatters otherwise pack append-order edits
            // together and put simultaneous voices in different columns.
            const make=(name:string,value?:string)=>{const e=doc.createElementNS(doc.documentElement.namespaceURI,name);if(value!==undefined)e.textContent=value;return e;};
            const original=[...measure.children];let originalCursor=0;
            const metadata:{node:Element;onset:number}[]=[];
            for(const node of original){
                if(node.localName==='backup'||node.localName==='forward'){originalCursor+=Number(text(node,'duration','0'))/divisions*(node.localName==='backup'?-1:1);continue;}
                if(node.localName==='note'){if(!children(node,'chord').length&&!children(node,'grace').length)originalCursor+=Number(text(node,'duration','0'))/divisions;continue;}
                metadata.push({node,onset:originalCursor});
            }
            // Grace notes retain their original ordering and attachment.
            if(original.some(n=>n.localName==='note'&&children(n,'grace').length))continue;
            for(const node of original)node.remove();
            let engravingCursor=0;
            const seek=(at:number)=>{const units=Math.round((at-engravingCursor)*divisions);if(units){const move=make(units<0?'backup':'forward');move.append(make('duration',String(Math.abs(units))));measure.append(move);}engravingCursor=at;};
            for(const item of metadata){seek(item.onset);measure.append(item.node);}
            const engravingTracks=new Map<string,typeof groups extends Map<string,infer V>?V[]:never>();
            for(const group of groups.values()){const owner=key(partIndex,group.staff,text(group.notes[0],'voice','1'));if(!engravingTracks.has(owner))engravingTracks.set(owner,[]);engravingTracks.get(owner)!.push(group);}
            for(const track of engravingTracks.values()){
                track.sort((a,b)=>a.onset-b.onset);seek(0);let end=0;
                for(let i=0;i<track.length;i++){
                    const group=track[i],renderedVoice=text(group.notes[0],'voice','1');
                    if(group.onset>end+1e-7){const rest=make('note');rest.setAttribute('print-object','no');rest.setAttribute('print-spacing','yes');rest.append(make('rest'),make('duration',String(Math.round((group.onset-end)*divisions))),make('voice',renderedVoice),make('staff',String(group.staff)));measure.append(rest);engravingCursor=group.onset;}
                    seek(group.onset);
                    const nextOnset=track[i+1]?.onset??Infinity;
                    for(const note of group.notes){
                        const duration=children(note,'duration')[0];
                        if(duration&&group.end>nextOnset+1e-7){const pitch=children(note,'pitch')[0];const identity=[partIndex,group.staff,renderedVoice,group.onset,pitch?text(pitch,'step','')+text(pitch,'octave',''):'rest'].join('|');durationOrigins.set(identity,Number(duration.textContent)/divisions);duration.textContent=String(Math.round((nextOnset-group.onset)*divisions));}
                        measure.append(note);
                        if(!children(note,'chord').length)engravingCursor=group.onset+Number(duration?.textContent??0)/divisions;
                    }
                    end=Math.min(group.end,nextOnset);
                }
            }
            changed=true;
        }
    });
    const rendered=changed?new XMLSerializer().serializeToString(doc):xml;
    return {xml:/^\s*<\?xml\b/.test(rendered)?rendered:'<?xml version="1.0" encoding="utf-8"?>\n'+rendered,originalDuration:(part:number,staff:number,voice:string,onset:number,pitch:string,fallback:number)=>durationOrigins.get([part,staff,voice,onset,pitch].join('|'))??fallback,originalVoice:(part:number,staff:number,voice:string)=>voices.get(key(part,staff,String(voice)))??String(voice)};
}
