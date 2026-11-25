/** All voices share the same visual row for a verse. Canonical lyric numbers,
 * text and note associations are preserved; imported coordinates affect neither
 * edited syllables nor their alignment with the rest of the verse. */
export function prepareLyricLayout(xml:string,_canonicalVoice?:(part:number,staff:number,voice:string)=>string){
    const doc=new DOMParser().parseFromString(xml,'application/xml');
    if(doc.querySelector('parsererror'))throw Error('Invalid MusicXML.');
    let changed=false;
    for(const lyric of [...doc.getElementsByTagNameNS('*','lyric')]){
        for(const attribute of ['default-x','default-y','relative-x','relative-y']){
            if(lyric.hasAttribute(attribute)){lyric.removeAttribute(attribute);changed=true;}
        }
        if(lyric.getAttribute('placement')==='above'){lyric.setAttribute('placement','below');changed=true;}
    }
    const rendered=changed?new XMLSerializer().serializeToString(doc):xml;
    const inline=/^\s*<\?xml\b/.test(rendered)?rendered:'<?xml version="1.0" encoding="utf-8"?>\n'+rendered;
    return {xml:inline,originalVerse:(_part:number,_staff:number,_voice:string,verse:string)=>String(verse)};
}
