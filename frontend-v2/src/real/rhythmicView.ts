/** Render transient same-voice overlaps on independent engraving tracks.
 * MusicXML, user voice IDs and onsets remain canonical and are never rewritten.
 */
export function prepareRhythmicView(xml:string){
    const doc=new DOMParser().parseFromString(xml,'application/xml');if(doc.querySelector('parsererror'))throw Error('Invalid MusicXML.');
    const children=(e:Element,name:string)=>[...e.children].filter(n=>n.localName===name);
    const text=(e:Element,name:string,fallback:string)=>children(e,name)[0]?.textContent??fallback;
    const used=new Set([...doc.getElementsByTagNameNS('*','voice')].map(n=>n.textContent??'1'));
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
            for(const group of [...groups.values()].sort((a,b)=>a.onset-b.onset)){
                const owner=key(partIndex,group.staff,group.voice);if(!ends.has(owner))ends.set(owner,[]);const lanes=ends.get(owner)!;
                let lane=lanes.findIndex(end=>end<=group.onset+1e-7);if(lane<0)lane=lanes.length;lanes[lane]=group.end;
                if(lane===0)continue;
                const laneKey=owner+'|'+lane;let rendered=tracks.get(laneKey);
                if(!rendered){while(used.has(String(next)))next++;rendered=String(next++);used.add(rendered);tracks.set(laneKey,rendered);voices.set(key(partIndex,group.staff,rendered),group.voice);}
                for(const note of group.notes){
                    let voice=children(note,'voice')[0];if(!voice){voice=doc.createElementNS(doc.documentElement.namespaceURI,'voice');note.insertBefore(voice,[...note.children].find(n=>['type','dot','accidental','time-modification','stem','notehead','staff','beam','notations','lyric'].includes(n.localName))??null);}voice.textContent=rendered;
                    if(!children(note,'stem').length){const stem=doc.createElementNS(doc.documentElement.namespaceURI,'stem');stem.textContent=Number(group.voice)%2===0?'down':'up';note.insertBefore(stem,[...note.children].find(n=>['notehead','staff','beam','notations','lyric'].includes(n.localName))??null);}
                    changed=true;
                }
            }
        }
    });
    const rendered=changed?new XMLSerializer().serializeToString(doc):xml;
    return {xml:/^\s*<\?xml\b/.test(rendered)?rendered:'<?xml version="1.0" encoding="utf-8"?>\n'+rendered,originalVoice:(part:number,staff:number,voice:string)=>voices.get(key(part,staff,String(voice)))??String(voice)};
}
