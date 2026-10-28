export function parseChordInput(value:string){
 const m=/^([A-Ga-g])([#♯b♭]?)(.*)$/.exec(value.trim());
 if(!m)throw new Error('Enter a chord such as Bm, G or E7.');
 const suffix=m[3].trim();
 if(suffix.includes('/'))throw new Error('Slash chords are available through the detailed chord tools.');
 const kinds:Record<string,string>={'':'major',m:'minor','7':'dominant',maj7:'major-seventh',m7:'minor-seventh',dim:'diminished',aug:'augmented',sus2:'suspended-second',sus4:'suspended-fourth','6':'major-sixth',m6:'minor-sixth','9':'dominant-ninth','m(b5)':'diminished','m7(b5)':'half-diminished'};
 return {root_step:m[1].toUpperCase(),root_alter:m[2]==='b'||m[2]==='♭'?'-1':m[2]?'1':'0',kind:kinds[suffix]??'other',text:suffix};
}

export function chordInputText(h:{root_step:string;root_alter:string;kind:string;text:string}){
 const suffix:Record<string,string>={major:'',minor:'m',dominant:'7','major-seventh':'maj7','minor-seventh':'m7',diminished:'dim',augmented:'aug','suspended-second':'sus2','suspended-fourth':'sus4','half-diminished':'m7(b5)','major-sixth':'6','minor-sixth':'m6','dominant-ninth':'9'};
 return h.root_step+(h.root_alter==='1'?'#':h.root_alter==='-1'?'b':'')+(h.text||suffix[h.kind]||'');
}
