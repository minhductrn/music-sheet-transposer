import {useEffect,useRef,useState} from 'react';
import type {PDFDocumentProxy} from 'pdfjs-dist';
import workerURL from 'pdfjs-dist/build/pdf.worker.min.mjs?url';
type Props={blob:Blob;onStatus:(status:'loading'|'ready'|'error',message?:string)=>void};
export function PDFPreview({blob,onStatus}:Props){
 const host=useRef<HTMLDivElement>(null),canvas=useRef<HTMLCanvasElement>(null);
 const [doc,setDoc]=useState<PDFDocumentProxy|null>(null),[page,setPage]=useState(1),[width,setWidth]=useState(400);
 useEffect(()=>{const el=host.current;if(!el)return;const observer=new ResizeObserver(()=>setWidth(Math.max(100,el.clientWidth)));observer.observe(el);return()=>observer.disconnect();},[]);
 useEffect(()=>{let disposed=false;let task:{destroy:()=>Promise<void>}|undefined;setDoc(null);setPage(1);onStatus('loading');
  void(async()=>{try{const pdfjs=await import('pdfjs-dist');pdfjs.GlobalWorkerOptions.workerSrc=workerURL;if(disposed)return;const loading=pdfjs.getDocument({data:new Uint8Array(await blob.arrayBuffer())});task=loading;const loaded=await loading.promise;if(!disposed)setDoc(loaded);}catch(error){if(!disposed)onStatus('error',error instanceof Error?error.message:'Cannot preview PDF.');}})();
  return()=>{disposed=true;void task?.destroy();};
 },[blob,onStatus]);
 useEffect(()=>{if(!doc||!canvas.current)return;let disposed=false;let task:{cancel:()=>void}|undefined;onStatus('loading');
  void(async()=>{try{const pdfPage=await doc.getPage(page);if(disposed||!canvas.current)return;const base=pdfPage.getViewport({scale:1}),view=pdfPage.getViewport({scale:width/base.width});const ratio=Math.min(window.devicePixelRatio||1,2);const target=canvas.current;target.width=Math.ceil(view.width*ratio);target.height=Math.ceil(view.height*ratio);target.style.width=view.width+'px';target.style.height=view.height+'px';const rendering=pdfPage.render({canvas:target,viewport:view,transform:ratio===1?undefined:[ratio,0,0,ratio,0,0]});task=rendering;await rendering.promise;if(!disposed)onStatus('ready');}catch(error){if(!disposed)onStatus('error',error instanceof Error?error.message:'Cannot preview PDF.');}})();
  return()=>{disposed=true;task?.cancel();};
 },[doc,page,width,onStatus]);
 return <div className="pdf-preview" ref={host} data-page-count={doc?.numPages??0}><nav aria-label="PDF preview navigation"><button type="button" aria-label="Previous preview page" disabled={!doc||page===1} onClick={()=>setPage(p=>p-1)}>Previous</button><span>Page {page} of {doc?.numPages??'…'}</span><button type="button" aria-label="Next preview page" disabled={!doc||page===doc.numPages} onClick={()=>setPage(p=>p+1)}>Next</button></nav><canvas ref={canvas} aria-label={'PDF preview page '+page}/></div>;
}
