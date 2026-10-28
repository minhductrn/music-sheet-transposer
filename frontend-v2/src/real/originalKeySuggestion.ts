type Harmony={measure_id:string;onset:string;root_step:string;root_alter:string;kind:string};
const majors=['C♭','G♭','D♭','A♭','E♭','B♭','F','C','G','D','A','E','B','F♯','C♯'];
const minors=['A♭','E♭','B♭','F','C','G','D','A','E','B','F♯','C♯','G♯','D♯','A♯'];
// A tentative opening-chord suggestion only. Never changes score or selects a key.
export function suggestOriginalKey(harmonies:Harmony[],firstMeasure:string|undefined){
 const h=harmonies.find(h=>h.measure_id===firstMeasure&&h.onset==='0');if(!h||!['major','minor'].includes(h.kind)||!['-1','0','1'].includes(h.root_alter))return null;
 const mode=h.kind as 'major'|'minor',tonic=h.root_step+(h.root_alter==='1'?'♯':h.root_alter==='-1'?'♭':'');const index=(mode==='minor'?minors:majors).indexOf(tonic);if(index<0)return null;
 return {fifths:index-7,mode,tonic,chord:tonic+(mode==='minor'?'m':'')};
}
