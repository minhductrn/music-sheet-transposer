import {createRoot} from 'react-dom/client';
import {RenderedScore} from './RenderedScore';
import type {Review} from './api';

// Render a separate, fixed-width snapshot; PDF never changes viewport zoom or XML.
export async function exportScorePDF(review:Review,name:string){
 const [{jsPDF}]=await Promise.all([import('jspdf'),import('svg2pdf.js')]);
 const container=document.createElement('div');container.style.cssText='position:fixed;left:-10000px;top:0;width:794px;background:white';document.body.append(container);
 const root=createRoot(container);
 try{
  await new Promise<void>((resolve,reject)=>{const timeout=window.setTimeout(()=>reject(Error('PDF rendering timed out; no file exported.')),30000);root.render(<RenderedScore review={review} readOnly zoom={1} onReady={()=>{clearTimeout(timeout);resolve();}}/>);});
  const pdf=new jsPDF({unit:'mm',format:'a4'});
  for(const [file,style] of [['DejaVuSerif','normal'],['DejaVuSerif-Bold','bold'],['DejaVuSerif-Italic','italic'],['DejaVuSerif-BoldItalic','bolditalic']]){
   const response=await fetch(`/fonts/${file}.ttf`);if(!response.ok)throw Error('PDF Unicode font could not be loaded.');
   const bytes=new Uint8Array(await response.arrayBuffer());let binary='';for(const b of bytes)binary+=String.fromCharCode(b);
   pdf.addFileToVFS(`${file}.ttf`,btoa(binary));pdf.addFont(`${file}.ttf`,'DejaVuSerif',style);
  }
  let pages=0;
  for(const original of container.querySelectorAll<SVGSVGElement>('svg')){
   const template=original.cloneNode(true) as SVGSVGElement;
   // Hit areas are editor-only and must not change PDF opacity/painting state.
   template.querySelectorAll('[stroke="transparent"],[fill="transparent"]').forEach(node=>node.remove());
   const inverse=original.getScreenCTM()?.inverse();
   const textBounds=[...original.querySelectorAll('text')].map(node=>{const b=node.getBoundingClientRect();return inverse ? {top:new DOMPoint(b.left,b.top).matrixTransform(inverse).y,bottom:new DOMPoint(b.right,b.bottom).matrixTransform(inverse).y} : null;});
   template.querySelectorAll('text,tspan').forEach(t=>{t.setAttribute('font-family','DejaVuSerif');(t as SVGElement).style.fontFamily='DejaVuSerif';});
   const width=original.viewBox.baseVal.width || original.width.baseVal.value;
   const height=original.viewBox.baseVal.height || original.height.baseVal.value;
   if(!(width>0&&height>0))throw Error('PDF has no rendered score.');
   const capacity=277*width/190;
   const breaks=(JSON.parse(original.getAttribute('data-pdf-breaks')??'[]') as number[]).filter(y=>y>0&&y<height);
   let start=0;
   while(start<height-.1){
    const limit=Math.min(height,start+capacity);
    const end=height<=limit?height:breaks.filter(y=>y>start+1&&y<=limit).at(-1);
    if(end===undefined)throw Error('A music system exceeds an A4 page; PDF was not exported to avoid clipping.');
    if(pages++)pdf.addPage();
    const svg=template.cloneNode(true) as SVGSVGElement;
    [...svg.querySelectorAll('text')].forEach((node,i)=>{const b=textBounds[i];if(b && (b.bottom<start || b.top>end))node.remove();});
    svg.setAttribute('viewBox',`0 ${start} ${width} ${end-start}`);svg.setAttribute('width',String(width));svg.setAttribute('height',String(end-start));
    await pdf.svg(svg,{x:10,y:10,width:190,height:(end-start)*190/width});start=end;
   }
  }
  if(!pages)throw Error('No score pages to export.');
  pdf.save(name.replace(/\.(musicxml|xml)$/i,'')+'.pdf');
 }finally{root.unmount();container.remove();}
}
