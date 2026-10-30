import {A4,planA4,type PDFSettings,type InkBounds} from './a4Layout';
import {createRoot} from 'react-dom/client';
import {RenderedScore} from './RenderedScore';
import {PDFExportDialog,type PDFArtifact} from './PDFExportDialog';
import type {Review} from './api';
type FontAsset={file:string;style:string;bytes:ArrayBuffer};
let fonts:Promise<FontAsset[]>|undefined;
function exportFonts(){
 return fonts??=Promise.all([['DejaVuSerif','normal','400','normal'],['DejaVuSerif-Bold','bold','700','normal'],['DejaVuSerif-Italic','italic','400','italic'],['DejaVuSerif-BoldItalic','bolditalic','700','italic']].map(async([file,style,weight,fontStyle])=>{
  const response=await fetch('/fonts/'+file+'.ttf');if(!response.ok)throw Error('PDF Unicode font could not be loaded.');const bytes=await response.arrayBuffer();const face=await new FontFace('DejaVuSerif',bytes,{weight,style:fontStyle}).load();document.fonts.add(face);return{file,style,bytes};
 })).catch(error=>{fonts=undefined;throw error;});
}
function active(node:Element,svg:SVGSVGElement){
 for(let n:Element|null=node;n&&n!==svg;n=n.parentElement){const css=getComputedStyle(n);if(css.display==='none'||css.visibility==='hidden'||Number(css.opacity)===0)return false;}
 return !node.closest('defs,clipPath,mask');
}
function inSVG(node:SVGGraphicsElement,svg:SVGSVGElement):InkBounds|null{
 const inverse=svg.getScreenCTM()?.inverse(),matrix=node.getScreenCTM();if(!inverse||!matrix)return null;
 const b=node.getBBox();if(![b.x,b.y,b.width,b.height].every(Number.isFinite))return null;
 const points=[[b.x,b.y],[b.x+b.width,b.y],[b.x,b.y+b.height],[b.x+b.width,b.y+b.height]].map(([x,y])=>new DOMPoint(x,y).matrixTransform(matrix).matrixTransform(inverse));
 const x=Math.min(...points.map(p=>p.x)),y=Math.min(...points.map(p=>p.y));return{x,y,width:Math.max(...points.map(p=>p.x))-x,height:Math.max(...points.map(p=>p.y))-y};
}
function measureInk(svg:SVGSVGElement):InkBounds{
 const boxes=[...svg.querySelectorAll<SVGGraphicsElement>('path,text,line,rect,ellipse,circle,polygon,polyline,use')].filter(node=>active(node,svg)).map(n=>inSVG(n,svg)).filter((b):b is InkBounds=>!!b&&(b.width>0||b.height>0));
 if(!boxes.length)throw Error('PDF has no visible score content.');
 const x=Math.min(...boxes.map(b=>b.x))-4,y=Math.min(...boxes.map(b=>b.y))-4;
 return{x,y,width:Math.max(...boxes.map(b=>b.x+b.width))+4-x,height:Math.max(...boxes.map(b=>b.y+b.height))+4-y};
}
async function generatePDF(review:Review,settings:PDFSettings,signal:AbortSignal):Promise<PDFArtifact>{
 const [{jsPDF},assets]=await Promise.all([import('jspdf'),exportFonts(),import('svg2pdf.js')]);signal.throwIfAborted();
 const container=document.createElement('div');container.style.cssText='position:fixed;left:-10000px;top:0;width:1100px;background:white';document.body.append(container);const root=createRoot(container);
 try{
  await new Promise<void>((resolve,reject)=>{const finish=(error?:Error)=>{clearTimeout(timeout);signal.removeEventListener('abort',abort);if(error)reject(error);else resolve();};const abort=()=>finish(new DOMException('PDF generation canceled.','AbortError'));const timeout=window.setTimeout(()=>finish(Error('PDF rendering timed out; no file exported.')),30000);signal.addEventListener('abort',abort,{once:true});root.render(<RenderedScore printCompact review={review} readOnly zoom={1} onReady={()=>finish()}/>);});
  signal.throwIfAborted();await new Promise<void>(resolve=>requestAnimationFrame(()=>requestAnimationFrame(()=>resolve())));signal.throwIfAborted();
  const pdf=new jsPDF({unit:'mm',format:'a4',orientation:'portrait',compress:true});
  for(const {file,style,bytes} of assets){let binary='';for(const b of new Uint8Array(bytes))binary+=String.fromCharCode(b);pdf.addFileToVFS(file+'.ttf',btoa(binary));pdf.addFont(file+'.ttf','DejaVuSerif',style);}
  let pages=0;
  for(const original of [...container.querySelectorAll<SVGSVGElement>('svg')]){
   const template=original.cloneNode(true) as SVGSVGElement;template.querySelectorAll('[stroke="transparent"],[fill="transparent"]').forEach(n=>n.remove());
   template.querySelectorAll('text,tspan').forEach(t=>{t.setAttribute('font-family','DejaVuSerif');(t as SVGElement).style.fontFamily='DejaVuSerif';});
   const measure=document.createElement('div');container.append(measure);measure.append(template);
   try{
    const ink=measureInk(template),width=template.viewBox.baseVal.width||template.width.baseVal.value,height=template.viewBox.baseVal.height||template.height.baseVal.value;
    const texts=[...template.querySelectorAll('text')].map(n=>inSVG(n,template));
    const bounds=settings.margins==='auto'?ink:{x:0,y:0,width,height:Math.min(height,ink.y+ink.height+12)};
    const breaks=JSON.parse(template.getAttribute('data-pdf-breaks')??'[]') as number[];
    const plan=planA4(bounds,settings,breaks,texts.filter((b):b is InkBounds=>!!b).map(b=>({top:b.y,bottom:b.y+b.height})));
    for(const {source,target} of plan.pages){
     signal.throwIfAborted();if(pages++)pdf.addPage();const svg=template.cloneNode(true) as SVGSVGElement;
     [...svg.querySelectorAll('text')].forEach((n,i)=>{const b=texts[i];if(b&&(b.y+b.height<source.y||b.y>source.y+source.height))n.remove();});
     svg.setAttribute('viewBox',`${source.x} ${source.y} ${source.width} ${source.height}`);svg.setAttribute('width',String(source.width));svg.setAttribute('height',String(source.height));
     const ns='http://www.w3.org/2000/svg',defs=document.createElementNS(ns,'defs'),clip=document.createElementNS(ns,'clipPath'),rect=document.createElementNS(ns,'rect'),group=document.createElementNS(ns,'g');const id='score-a4-page-'+pages;
     clip.setAttribute('id',id);clip.setAttribute('clipPathUnits','userSpaceOnUse');for(const [k,v] of Object.entries(source))rect.setAttribute(k,String(v));clip.append(rect);defs.append(clip);group.setAttribute('clip-path','url(#'+id+')');
     for(const child of [...svg.childNodes])if(!(child instanceof Element&&child.localName==='defs'))group.append(child);svg.append(defs,group);
     await pdf.svg(svg,{x:target.x,y:target.y,width:target.width,height:target.height});
    }
   }finally{measure.remove();}
  }
  if(!pages)throw Error('No score pages to export.');signal.throwIfAborted();
  for(let page=1;page<=pages;page++){pdf.setPage(page);pdf.setFont('DejaVuSerif','normal');pdf.setFontSize(8);pdf.setTextColor(90);pdf.text(page+' / '+pages,A4.width/2,A4.height-6,{align:'center'});}
  return{blob:new Blob([pdf.output('arraybuffer')],{type:'application/pdf'}),pages};
 }finally{root.unmount();container.remove();}
}
// Export choices and preview never edit the document or the score viewport.
export async function exportScorePDF(review:Review,name:string){
 const focus=document.activeElement as HTMLElement|null,container=document.createElement('div');document.body.append(container);const root=createRoot(container);
 const generate=(settings:PDFSettings,signal:AbortSignal)=>generatePDF(review,settings,signal);
 try{return await new Promise<boolean>(resolve=>root.render(<PDFExportDialog name={name} generate={generate} done={resolve}/>));}
 finally{root.unmount();container.remove();focus?.focus({preventScroll:true});}
}
