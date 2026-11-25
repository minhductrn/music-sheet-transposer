type Box={left:number;right:number;top:number;bottom:number;width:number;height:number};
/** Prefer the head actually clicked. Padding helps acquisition but must not
 * turn adjacent chord pitches into a voice ambiguity or pin the old selection. */
export function resolveNoteHits<T extends {box:Box}>(hits:T[],x:number,y:number):T[]{
    if(hits.length<2)return hits;
    const inside=hits.filter(h=>x>=h.box.left&&x<=h.box.right&&y>=h.box.top&&y<=h.box.bottom);
    if(inside.length===1)return inside;
    const candidates=inside.length?inside:hits;
    const ranked=candidates.map(hit=>({hit,distance:Math.hypot(x-(hit.box.left+hit.box.right)/2,y-(hit.box.top+hit.box.bottom)/2)})).sort((a,b)=>a.distance-b.distance);
    const tolerance=Math.max(0.6,Math.min(...candidates.map(h=>h.box.height))*0.12);
    return ranked.filter(h=>h.distance-ranked[0].distance<=tolerance).map(h=>h.hit);
}
