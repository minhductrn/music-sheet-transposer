import { events, rational, type Review } from './api';
// Preserve the full XML document, modifying only explicitly selected beam tags.
export function beamSelected(review: Review, ids: string[], count: number) {
    if (ids.length !== count || new Set(ids).size !== count)
        throw Error(`Select exactly ${count} distinct notes.`);
    const selected = events(review).filter(e => ids.includes(e.id));
    if (selected.length !== count)
        throw Error('Selected notes changed. Select again.');
    const first = selected[0];
    if (selected.some(e => e.kind !== 'note' || e.chord_id || e.grace || e.voice !== first.voice || e.staff !== first.staff || e.measure_id !== first.measure_id || !['eighth', '16th'].includes(e.notated_duration?.type ?? '')))
        throw Error('Select consecutive single eighth or sixteenth notes in one measure, voice and staff.');
    const xml = new DOMParser().parseFromString(review.xml, 'application/xml');
    if (xml.querySelector('parsererror'))
        throw Error('MusicXML could not be parsed.');
    const ns = xml.documentElement.namespaceURI;
    const children = (e: Element, n: string) => [...e.children].filter(c => c.localName === n && c.namespaceURI === ns);
    const text = (e: Element, n: string, f = '') => children(e, n)[0]?.textContent ?? f;
    const nodes = new Map<string, Element>();
    let measureIndex = 0;
    for (const part of children(xml.documentElement, 'part')) {
        let divisions = 1;
        for (const measure of children(part, 'measure')) {
            const mid = `m-${++measureIndex}`, model = review.score.parts.flatMap(p => p.measures).find(m => m.id === mid);
            let cursor = 0, previous = 0;
            for (const n of measure.children) {
                if (n.localName === 'attributes') {
                    divisions = Number(text(n, 'divisions', String(divisions)));
                    continue;
                }
                if (n.localName === 'backup') {
                    cursor -= Number(text(n, 'duration')) / divisions;
                    continue;
                }
                if (n.localName === 'forward') {
                    cursor += Number(text(n, 'duration')) / divisions;
                    continue;
                }
                if (n.localName !== 'note')
                    continue;
                const chord = children(n, 'chord').length > 0, onset = chord ? previous : cursor, duration = Number(text(n, 'duration')) / divisions, pitch = children(n, 'pitch')[0], matches = model?.voices.flatMap(v => v.events).filter(e => e.voice === text(n, 'voice', '1') && e.staff === Number(text(n, 'staff', '1')) && Math.abs(rational(e.onset) - onset) < 1e-8 && Math.abs(rational(e.duration) - duration) < 1e-8 && e.pitch?.step === text(pitch ?? n, 'step') && e.pitch?.octave === Number(text(pitch ?? n, 'octave')) && Number(e.pitch?.alter) === Number(text(pitch ?? n, 'alter', '0')));
                if (matches?.length === 1)
                    nodes.set(matches[0].id, n);
                if (!chord) {
                    previous = cursor;
                    cursor += duration;
                }
            }
        }
    }
    const targets = selected.map(e => nodes.get(e.id));
    if (targets.some(n => !n))
        throw Error('Ambiguous XML note mapping; no beam changes applied.');
    const parent = targets[0]!.parentElement!, ordered = [...parent.children].filter(n => n.localName === 'note' && text(n, 'voice', '1') === first.voice && Number(text(n, 'staff', '1')) === first.staff), indexes = targets.map(n => ordered.indexOf(n!));
    indexes.sort((a, b) => a - b);
    if (indexes.some((n, i) => n !== indexes[0] + i))
        throw Error('Select consecutive notes, without skipping another event.');
    const sorted = targets.map(n => n!).sort((a, b) => ordered.indexOf(a) - ordered.indexOf(b));
    if (sorted.some(n => children(n, 'time-modification').length || children(n, 'notations').some(x => children(x, 'tuplet').length)))
        throw Error('Existing tuplets must not be overwritten.');
    sorted.forEach((n, i) => { for (const old of children(n, 'beam'))
        old.remove(); const levels = text(n, 'type') === '16th' ? 2 : 1; for (let level = 1; level <= levels; level++) {
        const beam = xml.createElementNS(ns, 'beam');
        beam.setAttribute('number', String(level));
        beam.textContent = i === 0 ? 'begin' : i === sorted.length - 1 ? 'end' : 'continue';
        const before = [...n.children].find(c => ['notations', 'lyric', 'play', 'listen'].includes(c.localName));
        n.insertBefore(beam, before ?? null);
    } });
    return new XMLSerializer().serializeToString(xml);
}

// Explicit user action: add one empty, inherited-meter measure to a single written part.
export function appendMeasure(review: Review) {
    if(review.score.parts.length!==1)throw Error('Add measure supports one instrument part.');
    const doc=new DOMParser().parseFromString(review.xml,'application/xml');
    if(doc.querySelector('parsererror'))throw Error('Invalid MusicXML.');
    const ns=doc.documentElement.namespaceURI;
    const children=(e:Element,n:string)=>[...e.children].filter(x=>x.localName===n);
    const part=children(doc.documentElement,'part')[0], measures=children(part,'measure');
    const last=review.score.parts[0].measures.at(-1);
    if(!last || !last.expected_duration)throw Error('Confirm a supported time signature before adding a measure.');
    let divisions=1,staves=1;
    for(const m of measures)for(const a of children(m,'attributes')){const d=children(a,'divisions')[0],s=children(a,'staves')[0];if(d)divisions=Number(d.textContent);if(s)staves=Number(s.textContent);}
    if(staves!==1)throw Error('Add measure supports a single staff.');
    const duration=rational(last.expected_duration)*divisions;
    if(!Number.isSafeInteger(duration)||duration<=0)throw Error('The inherited meter cannot be represented safely.');
    const m=doc.createElementNS(ns,'measure');m.setAttribute('number',String((Number(measures.at(-1)?.getAttribute('number'))||measures.length)+1));
    const forward=doc.createElementNS(ns,'forward');
    for(const [tag,value] of [['duration',String(duration)],['voice','1'],['staff','1']]){const n=doc.createElementNS(ns,tag);n.textContent=value;forward.append(n);}
    m.append(forward);part.append(m);
    return new XMLSerializer().serializeToString(doc);
}


// Explicit source correction at the beginning of the chosen measure. This does
// not transpose notes or infer meter/key from OMR confidence.
export function measureContext(review: Review, measureId: string, field: 'time'|'key'|'clef'|'staves'|'partial'|'barline', value: string, staff=1) {
    const doc = new DOMParser().parseFromString(review.xml,'application/xml');
    if(doc.querySelector('parsererror'))throw Error('Invalid MusicXML.');
    const ns=doc.documentElement.namespaceURI;
    const child=(n:Element,tag:string)=>[...n.children].find(c=>c.localName===tag);
    const parts=[...doc.documentElement.children].filter(n=>n.localName==='part');
    let target:Element|undefined;
    review.score.parts.forEach((p,i)=>{const j=p.measures.findIndex(m=>m.id===measureId);if(j>=0)target=[...parts[i].children].filter(n=>n.localName==='measure')[j];});
    if(!target)throw Error('Choose a measure.');
    const measure=target;
    const create=(tag:string,text?:string)=>{const n=doc.createElementNS(ns,tag);if(text!==undefined)n.textContent=text;return n;};
    if(field==='partial'){if(!['yes','no'].includes(value))throw Error('Partial measure uses yes or no.');measure.setAttribute('implicit',value==='yes'?'yes':'no');}
    else if(field==='barline'){
        if(!['regular','light-light','light-heavy','heavy-light','dashed','dotted','none'].includes(value))throw Error('Choose a supported barline style.');
        let bar=[...measure.children].find(n=>n.localName==='barline'&&n.getAttribute('location')!=='left');
        if(!bar){bar=create('barline');bar.setAttribute('location','right');measure.append(bar);}
        child(bar,'bar-style')?.remove();bar.prepend(create('bar-style',value));
    } else {
        let attr:Element|undefined;for(const node of measure.children){if(['note','forward','backup'].includes(node.localName))break;if(node.localName==='attributes'){attr=node;break;}}
        if(!attr){attr=create('attributes');measure.prepend(attr);}
        const name=field==='staves'?'staves':field;
        const old=field==='clef'?[...attr.children].find(n=>n.localName==='clef'&&Number(n.getAttribute('number')??1)===staff):child(attr,name);
        const replacement=create(name);
        if(field==='time'){
            const [beats,type]=value.split('/');if(!/^[1-9]\d?(?:\+[1-9]\d?)*$/.test(beats)||!['1','2','4','8','16','32','64'].includes(type))throw Error('Enter a valid meter such as 4/4, 3/8 or 3+2/8.');
            replacement.append(create('beats',beats),create('beat-type',type));
        }else if(field==='key'){
            const fifths=Number(value);if(!Number.isInteger(fifths)||Math.abs(fifths)>7)throw Error('Choose a key signature from -7 to +7.');replacement.append(create('fifths',value));
        }else if(field==='clef'){
            const [sign,line]=value.split(':');if(!['G','F','C'].includes(sign)||!['1','2','3','4','5'].includes(line))throw Error('Choose a valid clef, such as G:2 or F:4.');replacement.setAttribute('number',String(staff));replacement.append(create('sign',sign),create('line',line));
        }else{
            const count=Number(value),model=review.score.parts.flatMap(p=>p.measures).find(m=>m.id===measureId);
            if(!Number.isInteger(count)||count<1||count>8||model?.voices.some(v=>v.events.some(e=>e.staff>count)))throw Error('Staff count must include all existing notes and be between 1 and 8.');replacement.textContent=value;
        }
        if(old)old.replaceWith(replacement);else {
            const rank=['divisions','key','time','staves','part-symbol','instruments','clef','staff-details','transpose','directive','measure-style'];
            attr.insertBefore(replacement,[...attr.children].find(n=>rank.indexOf(n.localName)>rank.indexOf(name))??null);
        }
    }
    return new XMLSerializer().serializeToString(doc);
}

// Explicit user declaration only: add missing initial key without transposing notes.
export function declareInitialKey(xml:string,fifths:number,mode:'major'|'minor'){
 if(!Number.isInteger(fifths)||Math.abs(fifths)>7)throw Error('Choose a supported original key.');
 const doc=new DOMParser().parseFromString(xml,'application/xml');if(doc.querySelector('parsererror'))throw Error('Invalid MusicXML.');const ns=doc.documentElement.namespaceURI;
 const children=(e:Element,n:string)=>[...e.children].filter(c=>c.localName===n);const create=(name:string)=>doc.createElementNS(ns,name);
 for(const part of children(doc.documentElement,'part')){const first=children(part,'measure')[0];if(!first)continue;const initial:Element[]=[];for(const node of first.children){if(['note','forward','backup'].includes(node.localName))break;if(node.localName==='attributes')initial.push(node);}if(initial.some(a=>children(a,'key').length))continue;
 let attrs=initial[0];if(!attrs){attrs=create('attributes');first.prepend(attrs);}const key=create('key'),f=create('fifths'),m=create('mode');f.textContent=String(fifths);m.textContent=mode;key.append(f,m);attrs.insertBefore(key,[...attrs.children].find(c=>c.localName!=='divisions')??null);
 }
 const result=new XMLSerializer().serializeToString(doc);return /^\s*<\?xml\b/.test(result)?result:'<?xml version="1.0" encoding="utf-8"?>\n'+result;
}
