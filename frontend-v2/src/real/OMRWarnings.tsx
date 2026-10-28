type Warning={code?:string;message:string;measure?:string|null;part_id?:string|null};
export function OMRWarnings({warnings}:{warnings:Warning[]}){
 const groups=new Map<string,{message:string;count:number;locations:Set<string>}>();
 for(const w of warnings){const key=w.code??w.message;const g=groups.get(key)??{message:w.message,count:0,locations:new Set<string>()};g.count++;if(w.measure)g.locations.add((w.part_id?w.part_id+' · ':'')+'measure '+w.measure);groups.set(key,g);}
 return warnings.length?<details className="omr-warning-groups"><summary>Recognition warnings: {warnings.length} · {groups.size} types (expand to review)</summary><ul>{[...groups].map(([id,g])=><li key={id}><strong>{g.message}</strong>{g.count>1&&<span> · {g.count} occurrences</span>}{g.locations.size>0&&<p>Affected: {[...g.locations].join(', ')}</p>}</li>)}</ul><p>Advisory only. No notes, accidentals or lyrics are automatically corrected.</p></details>:null;
}
