export function concertKeyRange(keys:number[],source:number,target:number){
 const signatures=keys.length?keys:[source];const fits=(destination:number)=>signatures.every(key=>Math.abs(key+destination-source)<=7);
 if(fits(target))return {supported:true,alternative:null};
 const alternative=[target-12,target+12].find(value=>Math.abs(value)<=7&&fits(value))??null;
 return {supported:false,alternative};
}
