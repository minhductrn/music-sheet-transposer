import {useEffect,useRef,useState} from 'react';
import type {PDFDocumentProxy,RenderTask} from 'pdfjs-dist';
import workerURL from 'pdfjs-dist/build/pdf.worker.min.mjs?url';

export function PDFSource({file,zoom}:{file:File;zoom:number}){
 const host=useRef<HTMLDivElement>(null);
 const [document,setDocument]=useState<PDFDocumentProxy|null>(null);
 const [width,setWidth]=useState(500),[error,setError]=useState(''),[loading,setLoading]=useState(true);
 useEffect(()=>{const el=host.current;if(!el)return;const observer=new ResizeObserver(()=>setWidth(Math.max(100,el.clientWidth)));observer.observe(el);setWidth(Math.max(100,el.clientWidth));return()=>observer.disconnect();},[]);
 useEffect(()=>{let disposed=false;let task:{destroy:()=>Promise<void>}|undefined;
  setLoading(true);setError('');setDocument(null);
  void (async()=>{try{
   const pdfjs=await import('pdfjs-dist');pdfjs.GlobalWorkerOptions.workerSrc=workerURL;
   const loadingTask=pdfjs.getDocument({data:new Uint8Array(await file.arrayBuffer())});task=loadingTask;
   const doc=await loadingTask.promise;
   if(disposed){await loadingTask.destroy();return;}
   if(doc.numPages<1||doc.numPages>10){await loadingTask.destroy();throw Error('Source PDF must contain 1–10 pages.');}
   setDocument(doc);
  }catch(ex){if(!disposed){setError(ex instanceof Error?ex.message:'Cannot display the original PDF.');setLoading(false);}}})();
  return()=>{disposed=true;void task?.destroy();};
 },[file]);
 useEffect(()=>{const el=host.current;if(!el||!document)return;let disposed=false;const tasks:RenderTask[]=[];el.replaceChildren();setLoading(true);setError('');
  void(async()=>{try{let pixels=0;
   for(let number=1;number<=document.numPages;number++){
    const page=await document.getPage(number);if(disposed)return;
    const base=page.getViewport({scale:1}),viewport=page.getViewport({scale:width*zoom/base.width});
    const ratio=Math.min(window.devicePixelRatio||1,2);pixels+=Math.ceil(viewport.width*ratio)*Math.ceil(viewport.height*ratio);
    if(pixels>40000000)throw Error('PDF display exceeds its pixel budget. Reduce source zoom.');
    const canvas=window.document.createElement('canvas');canvas.width=Math.ceil(viewport.width*ratio);canvas.height=Math.ceil(viewport.height*ratio);canvas.style.width=viewport.width+'px';canvas.style.height=viewport.height+'px';canvas.style.display='block';canvas.style.marginBottom='12px';canvas.setAttribute('aria-label','Original PDF page '+number);el.append(canvas);
    const render=page.render({canvas,viewport,transform:ratio===1?undefined:[ratio,0,0,ratio,0,0]});tasks.push(render);await render.promise;
   }
   if(!disposed)setLoading(false);
  }catch(ex){if(!disposed){setError(ex instanceof Error?ex.message:'PDF display failed.');setLoading(false);}}})();
  return()=>{disposed=true;for(const task of tasks)task.cancel();};
 },[document,width,zoom]);
 return <div title="Original PDF source">{loading&&<p role="status">Displaying original PDF…</p>}{error&&<p role="alert">{error}</p>}<div ref={host}/></div>;
}
