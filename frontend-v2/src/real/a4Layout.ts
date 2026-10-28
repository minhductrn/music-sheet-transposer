export const A4={width:210,height:297,margin:12} as const;
export function a4Slices(width:number,height:number,breaks:number[],textBounds:{top:number;bottom:number}[]=[]){
 if(!(Number.isFinite(width)&&Number.isFinite(height)&&width>0&&height>0))throw Error('PDF has no rendered score.');
 const capacity=(A4.height-2*A4.margin)*width/(A4.width-2*A4.margin);
 const safe=[...new Set(breaks)].filter(y=>Number.isFinite(y)&&y>0&&y<height&&!textBounds.some(b=>b.top<y&&b.bottom>y)).sort((a,b)=>a-b);
 const pages:{start:number;end:number}[]=[];let start=0;
 while(start<height-.1){const limit=Math.min(height,start+capacity);const end=height<=limit?height:safe.filter(y=>y>start+1&&y<=limit).at(-1);if(end===undefined)throw Error('A music system exceeds an A4 page; PDF was not exported to avoid clipping.');pages.push({start,end});start=end;}
 return pages;
}
