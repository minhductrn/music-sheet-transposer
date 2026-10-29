import {A4,a4Slices,a4SinglePageScale} from './a4Layout';
import {createRoot} from 'react-dom/client';
import {RenderedScore} from './RenderedScore';
import type {Review} from './api';

type PDFLayout='one-page'|'multiple-pages';
async function choosePDFLayout():Promise<PDFLayout|null>{
 const dialog=document.createElement('dialog');dialog.setAttribute('aria-label','PDF layout');
 dialog.style.cssText='padding:20px;border:1px solid #bdcede;border-radius:12px;max-width:360px';
 dialog.innerHTML='<form method="dialog"><h3>Export PDF</h3><label>Layout <select aria-label="PDF page layout"><option value="one-page">Fit in 1 A4 page</option><option value="multiple-pages">Multiple A4 pages</option></select></label><p>Fit scales the complete score uniformly. Long scores may be easier to read on multiple pages.</p><button value="export">Export</button> <button value="cancel">Cancel</button></form>';
 document.body.append(dialog);
 return new Promise(resolve=>{dialog.addEventListener('close',()=>{const value=dialog.returnValue==='export'?(dialog.querySelector('select')!.value as PDFLayout):null;dialog.remove();resolve(value);},{once:true});dialog.showModal();});
}

// Render a separate, fixed-width snapshot; PDF never changes viewport zoom or XML.
export async function exportScorePDF(review:Review,name:string){
 const layout=await choosePDFLayout();if(!layout)return false;
 const [{jsPDF}]=await Promise.all([import('jspdf'),import('svg2pdf.js')]);
 const container=document.createElement('div');container.style.cssText='position:fixed;left:-10000px;top:0;width:1100px;background:white';document.body.append(container);
 const root=createRoot(container);
 try{
  await new Promise<void>((resolve,reject)=>{const timeout=window.setTimeout(()=>reject(Error('PDF rendering timed out; no file exported.')),30000);root.render(<RenderedScore printCompact review={review} readOnly zoom={1} onReady={()=>{clearTimeout(timeout);resolve();}}/>);});
  const pdf=new jsPDF({unit:'mm',format:'a4',orientation:'portrait',compress:true});
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
   const ink=original.getBBox();const contentHeight=Math.min(height,Math.max(ink.y+ink.height,...textBounds.map(b=>b?.bottom??0))+16);
   const breaks=(JSON.parse(original.getAttribute('data-pdf-breaks')??'[]') as number[]).filter(y=>y>0&&y<height);
   const pageScale=layout==='one-page'?a4SinglePageScale(width,contentHeight):1;
   for(const {start,end} of a4Slices(width/pageScale,contentHeight,breaks,textBounds.filter((b):b is {top:number;bottom:number}=>b!==null))){
    if(pages++)pdf.addPage();
    const svg=template.cloneNode(true) as SVGSVGElement;
    [...svg.querySelectorAll('text')].forEach((node,i)=>{const b=textBounds[i];if(b && (b.bottom<start || b.top>end))node.remove();});
    svg.setAttribute('viewBox',`0 ${start} ${width} ${end-start}`);svg.setAttribute('width',String(width));svg.setAttribute('height',String(end-start));
    // Clip all notation to its own page, including curves spanning systems.
    const ns='http://www.w3.org/2000/svg',defs=document.createElementNS(ns,'defs'),clip=document.createElementNS(ns,'clipPath'),rect=document.createElementNS(ns,'rect'),group=document.createElementNS(ns,'g');
    const clipId='score-a4-page-'+pages;clip.setAttribute('id',clipId);clip.setAttribute('clipPathUnits','userSpaceOnUse');rect.setAttribute('x','0');rect.setAttribute('y',String(start));rect.setAttribute('width',String(width));rect.setAttribute('height',String(end-start));clip.append(rect);defs.append(clip);group.setAttribute('clip-path','url(#'+clipId+')');
    for(const child of [...svg.childNodes]){if(child instanceof Element&&child.localName==='defs')continue;group.append(child);}svg.append(defs,group);
    const contentWidth=(A4.width-2*A4.margin)*pageScale;
    await pdf.svg(svg,{x:(A4.width-contentWidth)/2,y:A4.margin,width:contentWidth,height:(end-start)*contentWidth/width});
   }
  }
  if(!pages)throw Error('No score pages to export.');
  for(let page=1;page<=pages;page++){pdf.setPage(page);pdf.setFont('DejaVuSerif','normal');pdf.setFontSize(8);pdf.setTextColor(90);pdf.text(page+' / '+pages,A4.width/2,A4.height-6,{align:'center'});}
  pdf.save(name.replace(/\.(musicxml|xml)$/i,'')+'.pdf');return true;
 }finally{root.unmount();container.remove();}
}
