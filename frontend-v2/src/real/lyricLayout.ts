/** Renderer-only lyric rows: verses align across voices. Extra rows are used
 * only for simultaneous different-voice words in the same verse. Canonical
 * lyric text, numbers, attachments and imported coordinates are untouched.
 */
export function prepareLyricLayout(xml:string,canonicalVoice:(part:number,staff:number,voice:string)=>string=(_part,_staff,voice)=>voice){
    const doc=new DOMParser().parseFromString(xml,'application/xml');
    if(doc.querySelector('parsererror'))throw Error('Invalid MusicXML.');
    const children=(e:Element,name:string)=>[...e.children].filter(n=>n.localName===name);
    const field=(e:Element,name:string,fallback:string)=>children(e,name)[0]?.textContent??fallback;
    const original=new Map<string,string>();let changed=false;
    const key=(part:number,staff:number,voice:string,verse:string)=>[part,staff,voice,verse].join('|');
    children(doc.documentElement,'part').forEach((part,partIndex)=>{
        const notes=children(part,'measure').flatMap(m=>children(m,'note'));
        let next=Math.max(0,...notes.flatMap(n=>children(n,'lyric').map(l=>Number(l.getAttribute('number')??1))).filter(Number.isFinite))+1;
        const extras=new Map<string,string>();let divisions=1;
        for(const measure of children(part,'measure')){
            let cursor=0,last=0;const occupied=new Map<string,Set<string>>();
            for(const note of measure.children){
                if(note.localName==='attributes'){divisions=Number(field(note,'divisions',String(divisions)));continue;}
                const duration=Number(field(note,'duration','0'))/divisions;
                if(note.localName==='backup'){cursor-=duration;continue;}
                if(note.localName==='forward'){cursor+=duration;continue;}
                if(note.localName!=='note')continue;
                const onset=children(note,'chord').length?last:cursor;last=onset;
                if(!children(note,'chord').length&&!children(note,'grace').length)cursor+=duration;
                const staff=Number(field(note,'staff','1')),voice=canonicalVoice(partIndex,staff,field(note,'voice','1'));
                for(const lyric of children(note,'lyric')){
                    for(const attribute of ['default-x','default-y','relative-x','relative-y'])if(lyric.hasAttribute(attribute)){lyric.removeAttribute(attribute);changed=true;}
                    const verse=lyric.getAttribute('number')??'1',position=[staff,onset.toFixed(8),verse].join('|');
                    const voices=occupied.get(position)??new Set<string>();
                    if(voices.size&&!voices.has(voice)){
                        const extraKey=[staff,voice,verse].join('|');
                        if(!extras.has(extraKey))extras.set(extraKey,String(next++));
                        const lane=extras.get(extraKey)!;lyric.setAttribute('number',lane);original.set(key(partIndex,staff,voice,lane),verse);changed=true;
                    }
                    voices.add(voice);occupied.set(position,voices);
                }
            }
        }
    });
    const rendered=changed?new XMLSerializer().serializeToString(doc):xml;
    const inline=/^\s*<\?xml\b/.test(rendered)?rendered:'<?xml version="1.0" encoding="utf-8"?>\n'+rendered;
    return {xml:inline,originalVerse:(part:number,staff:number,voice:string,verse:string)=>original.get(key(part,staff,canonicalVoice(part,staff,voice),String(verse)))??String(verse)};
}
