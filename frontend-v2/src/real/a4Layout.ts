export const A4={width:210,height:297,margin:12} as const;
export function a4Slices(width:number,height:number,breaks:number[],textBounds:{top:number;bottom:number}[]=[]){
 if(!(Number.isFinite(width)&&Number.isFinite(height)&&width>0&&height>0))throw Error('PDF has no rendered score.');
 const capacity=(A4.height-2*A4.margin)*width/(A4.width-2*A4.margin);
 const safe=[...new Set(breaks)].filter(y=>Number.isFinite(y)&&y>0&&y<height&&!textBounds.some(b=>b.top<y&&b.bottom>y)).sort((a,b)=>a-b);
 const pages:{start:number;end:number}[]=[];let start=0;
 while(start<height-.1){const limit=Math.min(height,start+capacity);const end=height<=limit?height:safe.filter(y=>y>start+1&&y<=limit).at(-1);if(end===undefined)throw Error('A music system exceeds an A4 page; PDF was not exported to avoid clipping.');pages.push({start,end});start=end;}
 return pages;
}

// Uniform fit is explicit and works for any score length without changing notation.
export function a4SinglePageScale(width:number,height:number){
 if(!(Number.isFinite(width)&&Number.isFinite(height)&&width>0&&height>0))throw Error('PDF has no rendered score.');
 const capacity=(A4.height-2*A4.margin)*width/(A4.width-2*A4.margin);
 return Math.min(1,capacity/height);
}

export type PDFSettings={layout:'one-page'|'multiple-pages';margins:'auto'|'standard'};
export type InkBounds={x:number;y:number;width:number;height:number};
export type PDFPage={source:InkBounds;target:InkBounds};
export type PDFPlan={pages:PDFPage[];profile:string};
const profiles=[
 {name:'Balanced',left:16,right:16,top:16,bottom:16},
 {name:'Standard',left:12,right:12,top:12,bottom:12},
 {name:'Compact',left:10,right:10,top:10,bottom:12},
];
// Plan print placement only. No canonical score data is read or changed here.
export function planA4(bounds:InkBounds,settings:PDFSettings,breaks:number[],texts:{top:number;bottom:number}[]=[]):PDFPlan{
 const {x,y,width,height}=bounds;
 if(![x,y,width,height].every(Number.isFinite)||width<=0||height<=0)throw Error('PDF has no rendered score.');
 const reference=186/1100;
 const safe=[...new Set(breaks)].filter(v=>v>y&&v<y+height&&!texts.some(t=>t.top<v&&t.bottom>v)).sort((a,b)=>a-b);
 const edges=[y,...safe,y+height];
 const requiredHeight=settings.layout==='one-page'?height:Math.max(...edges.slice(1).map((v,i)=>v-edges[i]));
 const profile=settings.margins==='standard'?profiles[1]:profiles.find(m=>width*reference<=210-m.left-m.right+1e-7&&requiredHeight*reference<=297-m.top-m.bottom+1e-7)??profiles[2];
 const availableWidth=210-profile.left-profile.right,availableHeight=297-profile.top-profile.bottom;
 const scale=settings.layout==='one-page'?Math.min(reference,availableWidth/width,availableHeight/height):Math.min(reference,availableWidth/width);
 const pages:PDFPage[]=[];let start=y;
 while(start<y+height-.01){
  const limit=start+availableHeight/scale;
  const end=settings.layout==='one-page'||y+height<=limit+1e-7?y+height:safe.filter(v=>v>start+.01&&v<=limit).at(-1);
  if(end===undefined)throw Error('A music system exceeds an A4 page. Choose Fit in 1 A4 page.');
  pages.push({source:{x,y:start,width,height:end-start},target:{x:(210-width*scale)/2,y:profile.top,width:width*scale,height:(end-start)*scale}});start=end;
 }
 return {pages,profile:profile.name};
}
