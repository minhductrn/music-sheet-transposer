// Persist an output label as metadata; do not rename user titles or musical parts.
const NAME='mst-output-heading';
export function withOutputHeading(xml:string,text:string){
 const doc=new DOMParser().parseFromString(xml,'application/xml');
 if(doc.querySelector('parsererror'))throw Error('Invalid MusicXML.');
 const root=doc.documentElement,ns=root.namespaceURI;
 let identification=[...root.children].find(n=>n.localName==='identification');
 if(!identification){identification=doc.createElementNS(ns,'identification');root.insertBefore(identification,[...root.children].find(n=>!['work','movement-number','movement-title'].includes(n.localName))??null);}
 let miscellaneous=[...identification.children].find(n=>n.localName==='miscellaneous');
 if(!miscellaneous){miscellaneous=doc.createElementNS(ns,'miscellaneous');identification.append(miscellaneous);}
 let field=[...miscellaneous.children].find(n=>n.localName==='miscellaneous-field'&&n.getAttribute('name')===NAME);
 if(!field){field=doc.createElementNS(ns,'miscellaneous-field');field.setAttribute('name',NAME);miscellaneous.append(field);}
 field.textContent=text;return new XMLSerializer().serializeToString(doc);
}
export function outputHeading(xml:string){
 const doc=new DOMParser().parseFromString(xml,'application/xml');
 return [...doc.getElementsByTagNameNS('*','miscellaneous-field')].find(n=>n.getAttribute('name')===NAME)?.textContent??'';
}
