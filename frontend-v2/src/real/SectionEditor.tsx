import {useEffect,useRef,useState} from 'react';
import {previewSection,type Review,type Key,type SectionRequest} from './api';
import {KeyShiftControl,destinationFor} from './KeyShiftControl';
import {RenderedScore} from './RenderedScore';
type Props={review:Review;range:string[];onRange:(ids:string[])=>void;onClose:()=>void;onApply:(body:SectionRequest)=>Promise<boolean>};
export function SectionEditor({review,range,onRange,onClose,onApply}:Props){
 const measures=review.score.parts[0]?.measures??[];
 const first=measures[Math.min(...range.map(id=>measures.findIndex(m=>m.id===id)).filter(i=>i>=0))]??measures[0];
 const [source,setSource]=useState<Key>({fifths:0,mode:'major'}),[target,setTarget]=useState(0),[steps,setSteps]=useState(0);
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),[preview,setPreview]=useState<(Awaited<ReturnType<typeof previewSection>> & {fingerprint:string})|null>(null);
 const viewport=useRef<HTMLDivElement>(null);
 useEffect(()=>{const k=first?.key_signature[0];const next:Key={fifths:Number(k?.fifths??0),mode:k?.mode==='minor'?'minor':'major'};setSource(next);setTarget(destinationFor(next.fifths,steps));},[first?.id]); // A newly selected passage uses its own source context.
 const indices=range.map(id=>measures.findIndex(m=>m.id===id)).filter(i=>i>=0);
 const start=Math.min(...indices),end=Math.max(...indices);
 const body:SectionRequest={start_measure_id:measures[start]?.id??'',end_measure_id:measures[end]?.id??'',source_fifths:source.fifths,target_fifths:target,mode:source.mode,semitones:steps};
 const fingerprint=JSON.stringify([body,review.id,review.revision]);
 useEffect(()=>{setPreview(null);setError('');},[fingerprint]);
 async function showPreview(){setBusy(true);setError('');try{setPreview({...await previewSection(review,body),fingerprint});}catch(e){setError(e instanceof Error?e.message:'Cannot preview this passage.');}finally{setBusy(false);}}
 return <section className="section-editor" role="dialog" aria-label="Create Key Change Section" onKeyDown={e=>{if(e.key==='Escape'&&!busy)onClose();}}>
 <header><strong>Create Key Change Section</strong><button aria-label="Close section editor" disabled={busy} onClick={onClose}>×</button></header>
 <fieldset disabled={busy}><div className="section-range"><label>From measure<select aria-label="Section first measure" value={range[0]??''} onChange={e=>onRange([e.target.value,range.at(-1)??e.target.value])}>{measures.map(m=><option key={m.id} value={m.id}>{m.number}</option>)}</select></label><label>Through measure<select aria-label="Section last measure" value={range.at(-1)??''} onChange={e=>onRange([range[0]??e.target.value,e.target.value])}>{measures.map(m=><option key={m.id} value={m.id}>{m.number}</option>)}</select></label><span>Click the first and last measures on the working score.</span></div>
 <KeyShiftControl prefix="Section" source={source} target={target} steps={steps} onChange={(s,t,n)=>{setSource(s);setTarget(t);setSteps(n);}}/>
 <div className="section-actions"><span>Copy → append to end · notes + chord symbols</span><button disabled={!body.start_measure_id} onClick={()=>void showPreview()}>Preview section</button><button className="primary" disabled={!preview||preview.fingerprint!==fingerprint} onClick={()=>{setBusy(true);void onApply(body).then(done=>{if(done)onClose();}).catch(e=>setError(String(e))).finally(()=>setBusy(false));}}>Apply section</button><button onClick={onClose}>Cancel</button></div></fieldset>
 {error&&<p role="alert">{error}</p>}
 {preview?.fingerprint===fingerprint&&<><p role="status">{preview.section.count} measures will be appended as measures {preview.section.first_number}–{preview.section.last_number}.</p><div className="section-preview" ref={viewport}><RenderedScore review={preview.preview} readOnly zoom={.55} onReady={()=>{requestAnimationFrame(()=>{if(viewport.current)viewport.current.scrollTop=viewport.current.scrollHeight;});}}/></div></>}
 </section>;
}
