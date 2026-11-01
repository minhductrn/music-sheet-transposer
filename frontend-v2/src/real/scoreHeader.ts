import type {Review} from './api';
import {outputHeading} from './outputHeading';
export type HeaderPosition={x:number;y:number};
function bounds(node:SVGGraphicsElement,svg:SVGSVGElement){
 const inverse=svg.getScreenCTM()?.inverse();if(!inverse)return null;
 const b=node.getBoundingClientRect(),a=new DOMPoint(b.left,b.top).matrixTransform(inverse),z=new DOMPoint(b.right,b.bottom).matrixTransform(inverse);
 return{x:a.x,y:a.y,width:z.x-a.x,height:z.y-a.y};
}
const clamp=(n:number,a:number,b:number)=>Math.max(a,Math.min(b,n));
// Header objects occupy existing page whitespace; adding an object never adds a row.
export function renderScoreHeader(svg:SVGSVGElement,review:Review,editable:boolean,onHeader?:(box:DOMRect,position:HeaderPosition)=>void){
 const title=[...svg.querySelectorAll<SVGGraphicsElement>('text')].map(node=>({node,box:bounds(node,svg)})).filter(v=>v.box&&v.node.textContent?.trim()).sort((a,b)=>b.box!.height-a.box!.height)[0];
 const size=Math.max(18,Math.min(30,(title?.box?.height??40)*0.55));
 const view=svg.viewBox.baseVal,left=view.x,top=view.y,width=view.width||svg.width.baseVal.value;
 const heads=[...svg.querySelectorAll<SVGGraphicsElement>('.vf-notehead')].map(n=>bounds(n,svg)).filter(b=>!!b);
 const bottom=Math.max(top+size*2,heads.length?Math.min(...heads.map(b=>b!.y))-45:(title?.box?title.box.y+title.box.height+50:100)),height=bottom-top;
 const auto=outputHeading(review.xml),manual=review.score.texts.filter(t=>t.role==='printed_mst-header');
 const labels=[...(auto?[{text:auto,id:review.score.texts.find(t=>t.role==='output_heading')?.id,automatic:true,position:review.score.texts.find(t=>t.role==='output_heading')?.header_position}]:[]),...manual.map(t=>({text:t.text,id:t.id,automatic:false,position:t.header_position}))];
 labels.forEach((item,index)=>{
  const label=document.createElementNS('http://www.w3.org/2000/svg','text');
  const x=item.position?left+item.position.x*width:item.automatic?left+width/2:left+width*(index%2?0.8:0.2);
  const y=item.position?top+item.position.y*height:Math.max(top+size,(title?.box?.y??top+size*2)-8);
  label.setAttribute('x',String(x));label.setAttribute('y',String(y));label.setAttribute('text-anchor','middle');label.setAttribute('font-family','serif');label.setAttribute('font-size',String(size));label.textContent=item.text;
  if(item.id)label.setAttribute('data-text-id',item.id);
  label.setAttribute(item.automatic?'data-output-heading':'data-user-header','true');
  label.setAttribute('data-header-region',JSON.stringify({left,top,width,height}));svg.append(label);
 });
 if(editable&&onHeader){
  const hit=document.createElementNS('http://www.w3.org/2000/svg','rect');
  hit.setAttribute('x',String(left));hit.setAttribute('y',String(top));hit.setAttribute('width',String(width));hit.setAttribute('height',String(height));hit.setAttribute('fill','transparent');hit.setAttribute('data-testid','add-header-text-area');hit.style.cursor='text';
  hit.onpointerdown=e=>e.stopPropagation();hit.onclick=e=>{e.stopPropagation();const inverse=svg.getScreenCTM()?.inverse();if(!inverse)return;const point=new DOMPoint(e.clientX,e.clientY).matrixTransform(inverse);onHeader(new DOMRect(e.clientX,e.clientY,0,0),{x:clamp((point.x-left)/width,0,1),y:clamp((point.y-top)/height,0,1)});};svg.prepend(hit);
 }
}
export function installHeaderDrag(hit:SVGGElement,node:SVGTextElement,svg:SVGSVGElement,onMove:(position:HeaderPosition)=>void){
 const raw=node.getAttribute('data-header-region');if(!raw)return;
 const region=JSON.parse(raw) as {left:number;top:number;width:number;height:number};
 let start:{clientX:number;clientY:number;x:number;y:number;px:number;py:number}|null=null,moved=false,suppress=false;
 hit.style.cursor='move';
 hit.onpointerdown=e=>{e.stopPropagation();e.preventDefault();const inverse=svg.getScreenCTM()?.inverse();if(!inverse)return;const point=new DOMPoint(e.clientX,e.clientY).matrixTransform(inverse);start={clientX:e.clientX,clientY:e.clientY,x:Number(node.getAttribute('x')),y:Number(node.getAttribute('y')),px:point.x,py:point.y};moved=false;hit.setPointerCapture(e.pointerId);};
 hit.onpointermove=e=>{if(!start)return;if(!moved&&Math.hypot(e.clientX-start.clientX,e.clientY-start.clientY)<4)return;moved=true;const inverse=svg.getScreenCTM()?.inverse();if(!inverse)return;const point=new DOMPoint(e.clientX,e.clientY).matrixTransform(inverse),box=node.getBBox();
 const x=clamp(start.x+point.x-start.px,region.left+box.width/2,region.left+region.width-box.width/2),y=clamp(start.y+point.y-start.py,region.top+box.height,region.top+region.height);
 node.setAttribute('x',String(x));node.setAttribute('y',String(y));hit.setAttribute('transform',`translate(${x-start.x} ${y-start.y})`);};
 hit.onpointerup=e=>{if(!start)return;hit.releasePointerCapture(e.pointerId);if(moved){suppress=true;onMove({x:clamp((Number(node.getAttribute('x'))-region.left)/region.width,0,1),y:clamp((Number(node.getAttribute('y'))-region.top)/region.height,0,1)});}start=null;};
 hit.onpointercancel=()=>{if(start){node.setAttribute('x',String(start.x));node.setAttribute('y',String(start.y));hit.removeAttribute('transform');}start=null;};
 hit.addEventListener('click',e=>{if(suppress){suppress=false;e.stopImmediatePropagation();e.preventDefault();}},true);
}
