// MusicXML's default key before any key instruction is neutral. Some renderers
// backfill a later key when that initial instruction is absent. Make only that
// implicit default explicit in a disposable view; never rewrite note pitches.
export function renderXML(xml:string){
 const doc=new DOMParser().parseFromString(xml,'application/xml');
 if(doc.querySelector('parsererror'))throw Error('Invalid MusicXML.');
 const ns=doc.documentElement.namespaceURI;
 const children=(e:Element,n:string)=>[...e.children].filter(c=>c.localName===n);
 let changed=false;
 for(const part of children(doc.documentElement,'part')){
  const first=children(part,'measure')[0];if(!first)continue;
  const initial:Element[]=[];for(const node of first.children){if(['note','forward','backup'].includes(node.localName))break;if(node.localName==='attributes')initial.push(node);}
  if(initial.some(a=>children(a,'key').length))continue;
  let attributes=initial[0];if(!attributes){attributes=doc.createElementNS(ns,'attributes');first.prepend(attributes);}
  const key=doc.createElementNS(ns,'key'),fifths=doc.createElementNS(ns,'fifths');fifths.textContent='0';key.append(fifths);
  attributes.insertBefore(key,[...attributes.children].find(c=>c.localName!=='divisions')??null);changed=true;
 }
 const result=changed?new XMLSerializer().serializeToString(doc):xml;
 // OSMD distinguishes inline XML from URLs using the XML declaration.
 return /^\s*<\?xml\b/.test(result)?result:'<?xml version="1.0" encoding="utf-8"?>\n'+result;
}
