import { exportScorePDF } from './scorePDF';
import { beamSelected, appendMeasure } from './xmlEdits';
import { useEffect, useRef, useState } from 'react';
import { RenderedScore, type Curve } from './RenderedScore';
import { closeReview, concertXML, edit, events, keyInfo, openXML, rational, saxXML, xmlBlob, previewTriplet, dottedWritten, type Key, type Pitch, type Review } from './api';
import { download, writeLocal, chooseLocal, type Handle } from './files';
import { MusicIcon } from '../MusicIcon';
import './real.css';
const lengths = [{ value: '4', name: 'Whole' }, { value: '2', name: 'Half' }, { value: '1', name: 'Quarter' }, { value: '1/2', name: 'Eighth' }, { value: '1/4', name: '16th' }];
const saxes = [{ id: 'alto', name: 'Alto Saxophone E♭', offset: 9 }, { id: 'soprano', name: 'Soprano Saxophone B♭', offset: 2 }, { id: 'tenor', name: 'Tenor Saxophone B♭', offset: 14 }];
const offsetLabel = (offset: number) => `${offset >= 0 ? '+' : ''}${offset}`;
const majors = ['C♭', 'G♭', 'D♭', 'A♭', 'E♭', 'B♭', 'F', 'C', 'G', 'D', 'A', 'E', 'B', 'F♯', 'C♯'];
const minors = ['A♭', 'E♭', 'B♭', 'F', 'C', 'G', 'D', 'A', 'E', 'B', 'F♯', 'C♯', 'G♯', 'D♯', 'A♯'];
export const keyName = (key: Key) => `${(key.mode === 'minor' ? minors : majors)[key.fifths + 7]} ${key.mode}`;
type Tool = 'Select' | 'Notes' | 'Rest' | 'Tie' | 'Slur' | 'Groups' | 'Lyrics' | 'Text';
type Draft = {
    event: string;
    verse: string;
    text: string;
    x: number;
    y: number;
};
type SavedScore = { xml: string; bytes: Uint8Array; name: string; projection: Review };
type InstrumentEditor = { reference: Review; referenceName: string; label: string; onChange: (r: Review) => void; onBusy: (busy: boolean) => void; saved?: SavedScore; onSave: (saved: SavedScore) => void };
export function RealWorkspace({ file, onExit, instrumentEditor }: {
    instrumentEditor?: InstrumentEditor;
    file: File;
    onExit: () => void;
}) {
    const [review, setReview] = useState<Review | null>(null), [original, setOriginal] = useState<Review | null>(null), [busy, setBusy] = useState(false), [notice, setNotice] = useState('Opening MusicXML…');
    const lock = useRef(false), sessions = useRef(new Set<string>()), handle = useRef<Handle | null>(null), input = useRef<HTMLInputElement>(null);
    const [history, setHistory] = useState<string[]>([]), [future, setFuture] = useState<string[]>([]), [saved, setSaved] = useState<{
        xml: string;
        bytes: Uint8Array;
        name: string;
        projection: Review;
    } | null>(null), [receipt, setReceipt] = useState<{
        xml: string;
        bytes: Uint8Array;
        name: string;
        projection: Review;
    } | null>(null);
    const [selected, setSelected] = useState<string | null>(null), [tool, setTool] = useState<Tool>('Select'), [palette, setPalette] = useState(false), [pending, setPending] = useState<string | null>(null), [zoom, setZoom] = useState(1), [sourceZoom, setSourceZoom] = useState(1), [compare, setCompare] = useState(true), [split, setSplit] = useState(48);
    const [concert, setConcert] = useState(false), [detected, setDetected] = useState<{
        fifths: number;
        mode: 'major' | 'minor' | null;
    } | null>(null), [sourceKey, setSourceKey] = useState<Key>({ fifths: 0, mode: 'major' }), [confirmed, setConfirmed] = useState(false), [target, setTarget] = useState(0), [direction, setDirection] = useState<'up' | 'down'>('up');
    const [curve, setCurve] = useState<Curve | null>(null), [anchorBox, setAnchorBox] = useState<DOMRect | null>(null);
    const [insertAccidentalExplicit,setInsertAccidentalExplicit]=useState(false);
    const [equalBase,setEqualBase]=useState('1/2');
    const [groupIds, setGroupIds] = useState<string[]>([]), [insertPitch, setInsertPitch] = useState({ step: 'C', alter: '0', octave: 4 });
    const [editorBusy,setEditorBusy]=useState(false);
    const [homePrompt,setHomePrompt]=useState(false),[instrumentSaves,setInstrumentSaves]=useState<Record<string,SavedScore>>({});
    const initialFiles=useRef(new Map<string,File>());
    const [instrumentDirection,setInstrumentDirection]=useState<'up'|'down'>('up');
    const [stage, setStage] = useState(1), [outputs, setOutputs] = useState<Record<string, Review>>({}), [instrument, setInstrument] = useState<string | null>(null), [saveAs, setSaveAs] = useState(false), [name, setName] = useState(file.name), [validation, setValidation] = useState(false), [draft, setDraft] = useState<Draft | null>(null), [textDraft, setTextDraft] = useState<{
        id: string | null;
        text: string;
        x: number;
        y: number;
    } | null>(null), [verse, setVerse] = useState('1'), [mapped, setMapped] = useState(0), [insertion, setInsertion] = useState<{
        measure_id: string;
        onset: string;
        voice: string;
        staff: number;
    } | null>(null);
    useEffect(() => { const release = () => { for (const id of sessions.current)
        void closeReview(id); }; window.addEventListener('pagehide', release); return () => window.removeEventListener('pagehide', release); }, []);
    const [fitVersions,setFitVersions]=useState({source:0,working:0});
    const [voiceChoice, setVoiceChoice] = useState<{
        ids: string[];
        dy: number;
        box: DOMRect;
    } | null>(null);
    const workingViewport = useRef<HTMLDivElement>(null), sourceViewport = useRef<HTMLDivElement>(null), lyricInput = useRef<HTMLInputElement>(null);
    const draftLive = useRef<Draft | null>(null);
    draftLive.current = draft;
    const textLive = useRef<typeof textDraft>(null);
    textLive.current = textDraft;
    const all = review ? events(review) : [], event = all.find(e => e.id === selected), dirty = !!review && saved?.xml !== review.xml;
    useEffect(()=>{if(review)instrumentEditor?.onChange(review);},[review]); // Cache each written document, never the concert input.
    useEffect(()=>{instrumentEditor?.onBusy(busy || !!receipt || !!draft || !!textDraft);return ()=>instrumentEditor?.onBusy(false);},[busy,receipt,draft,textDraft]);
    const canGenerate = !!review && !!saved && !dirty;
    async function run(fn: () => Promise<void>) { if (lock.current)
        return; lock.current = true; setBusy(true); instrumentEditor?.onBusy(true); try {
        await fn();
    }
    catch (error) {
        setNotice(error instanceof Error ? error.message : 'Operation failed; no successful save is claimed.');
    }
    finally {
        lock.current = false;
        setBusy(false);
    } }
    async function remember(r: Review) { sessions.current.add(r.id); return r; }
    async function releaseExcept(id: string) { for (const old of [...sessions.current])
        if (old !== id) {
            await closeReview(old).catch(() => { });
            sessions.current.delete(old);
        } }
    async function detect(r: Review) { try {
        const k = await keyInfo(r.xml);
        setDetected(k);
        setSourceKey({ fifths: k.fifths, mode: k.mode ?? 'major' });
    }
    catch {
        const first = r.score.parts[0]?.measures[0]?.key_signature[0];
        setDetected(first ? { fifths: Number(first.fifths), mode: null } : null);
    } setConfirmed(false); }
    function accept(next: Review) { if (!review)
        return; if (next.xml === review.xml) {
        setReview(next);
        return;
    } setHistory(h => [...h, review.xml].slice(-50)); setFuture([]); setReview(next); setOutputs({}); setInstrumentSaves({}); setInstrument(null); setInsertion(null); }
    function allowConcertChange(){return !!instrumentEditor || !Object.keys(outputs).length || window.confirm("Changing the concert score clears the instrument workspaces. Save any instrument edits to local files before continuing. Continue?");}
    async function replace(xml: string) { if(!allowConcertChange())return; const next = await remember(await openXML(xmlBlob(xml))); accept(next); setSelected(null); setPending(null); setCurve(null); setGroupIds([]); setDraft(null); await releaseExcept(next.id); await detect(next); }
    async function mutate(path: string, body?: unknown, method = 'POST', successMessage?: string) { if (!review)
        return; if(!allowConcertChange())return; const next = await edit(review, path, body, method); accept(next); if(successMessage)setNotice(successMessage); }
    useEffect(() => { let disposed = false; run(async () => { const r = await remember(await openXML(file)); if (disposed) { await closeReview(r.id); sessions.current.delete(r.id); return; } setReview(r); setOriginal(instrumentEditor?.reference ?? r); if(instrumentEditor?.saved?.xml===r.xml){setSaved({...instrumentEditor.saved,projection:r});setName(instrumentEditor.saved.name);} await detect(r); setNotice('MusicXML opened. Editing is real; source remains unchanged until an explicit save.'); }); return () => { disposed = true; for (const id of sessions.current)
        void closeReview(id); }; }, [file]); // One review per opened document; no recognition call.
    useEffect(() => { lyricInput.current?.focus(); lyricInput.current?.select(); }, [draft?.event, draft?.verse]);
    function fit(pane: 'working' | 'source') { const el = (pane === 'working' ? workingViewport : sourceViewport).current; if (!el)
        return; (pane === 'working' ? setZoom : setSourceZoom)(1);setFitVersions(v=>({...v,[pane]:v[pane]+1})); el.scrollTop = 0; el.scrollLeft = 0;setNotice((pane==='source'?'Original Source':'Working Score')+' fitted to pane width. Scroll vertically to continue.'); }
    async function historyMove(redo = false) { if(!allowConcertChange())return; if (!review)
        return; const stack = redo ? future : history; if (!stack.length)
        return; const xml = stack[stack.length - 1], next = await remember(await openXML(xmlBlob(xml))); if (redo) {
        setHistory(h => [...h, review.xml]);
        setFuture(h => h.slice(0, -1));
    }
    else {
        setFuture(h => [...h, review.xml]);
        setHistory(h => h.slice(0, -1));
    } setReview(next); await releaseExcept(next.id); setSelected(null); setPending(null); setCurve(null); setInsertion(null); setGroupIds([]); setDraft(null); setOutputs({}); setInstrumentSaves({}); setInstrument(null); await detect(next); }
    function beginLyric(id: string, number = verse, box?: DOMRect) { if (!review)
        return; const e = events(review).find(e => e.id === id); if (!e || e.kind !== 'note')
        return; const b = box ?? document.querySelector(`[data-testid="real-head-${id}"]`)?.getBoundingClientRect(); const l = review.score.lyrics.find(l => l.event_id === id && l.number === number); if (l && l.segments.length > 1) {
        setNotice('This lyric has multiple XML text segments; no automatic merge or replacement was applied.');
        return;
    } setSelected(id); setVerse(number); setDraft({ event: id, verse: number, text: l?.text ?? '', x: Math.max(8, Math.min(window.innerWidth - 210, b?.left ?? 180)), y: Math.max(8, Math.min(window.innerHeight - 65, (b?.bottom ?? 240) + 8)) }); }
    async function commitText() {
        const current = textLive.current;
        if (!review || !current) return;
        textLive.current = null;
        setTextDraft(null);
        if (review.score.texts.find(t => t.id === current.id)?.text !== current.text)
            await mutate(`texts/${current.id}`, {text: current.text}, 'PATCH');
    }
    async function commitLyric(move = 0) { const current = draftLive.current; if (!review || !current)
        return; draftLive.current = null; setDraft(null); const l = review.score.lyrics.find(l => l.event_id === current.event && l.number === current.verse); if (l) {
        if (current.text !== l.text)
            await mutate(`lyrics/${l.id}`, { text: current.text }, 'PATCH');
    }
    else if (current.text)
        await mutate(`events/${current.event}/lyrics`, { text: current.text, number: current.verse }); if (move) {
        const owner = all.find(e => e.id === current.event), targets = all.filter(e => e.kind === 'note' && e.voice === owner?.voice && e.staff === owner.staff);
        const index = targets.findIndex(e => e.id === current.event);
        if (targets[index + move])
            beginLyric(targets[index + move].id, current.verse);
    } }
    function select(id: string, dy = 0) {
        if (!review || busy)
            return;
        const e = all.find(e => e.id === id);
        if (!e)
            return;
        setCurve(null);
        if (tool === 'Tie' || tool === 'Slur') {
            if (!pending) {
                setPending(id);
                setSelected(id);
                setNotice('Choose a later destination note in the same voice and staff.');
                return;
            }
            const source = all.find(e => e.id === pending);
            if (!source || e.kind !== 'note' || source.voice !== e.voice || source.staff !== e.staff) {
                setNotice('Choose a pitched destination in the same voice and staff.');
                return;
            }
            void run(async () => { if (tool === 'Tie')
                await mutate(`events/${pending}`, { tie_to_event_id: id }, 'PATCH');
            else
                await mutate('slurs', { source_event_id: pending, target_event_id: id }); setPending(null); setSelected(id); setNotice(`${tool} applied to the selected XML notes.`); });
            return;
        }
        setSelected(id);
        setInsertion(null);
        if (tool === 'Groups') {
            setGroupIds(ids => ids.includes(id) ? ids.filter(i => i !== id) : [...ids, id]);
            return;
        }
        if (tool === 'Lyrics') {
            beginLyric(id);
            return;
        }
        if (Math.abs(dy) >= .75 && e.pitch) {
            const letters = 'CDEFGAB', step = e.pitch.octave * 7 + letters.indexOf(e.pitch.step) - Math.round(dy);
            void run(() => mutate(`events/${id}`, { pitch: { ...e.pitch, step: letters[((step % 7) + 7) % 7], alter:movedAlter(e,letters[((step % 7) + 7) % 7]), octave: Math.floor(step / 7) } }, 'PATCH'));
        }
    }
    function chooseTool(next: Tool) { setTool(next); setPalette(next === 'Notes' || next === 'Groups'); setPending(next === 'Tie' || next === 'Slur' ? selected : null); if (next !== 'Lyrics')
        setDraft(null); if (next === 'Lyrics' && selected)
        beginLyric(selected); if (next === 'Groups')
        setGroupIds(selected ? [selected] : []); if (next === 'Text')
        setNotice('Click an existing score text to edit it inline.'); }
    async function duration(value: string, dot = false) { if (!review)
        return; if (insertion) {
        const effective = dottedWritten(value, dot);
        const owner = all.find(e => e.measure_id === insertion.measure_id && e.voice === insertion.voice && e.staff === insertion.staff && e.onset !== null && rational(e.onset) === rational(insertion.onset));
        await mutate('events', owner?.kind === 'note' && tool !== 'Rest' ? { measure_id: insertion.measure_id, voice: insertion.voice, staff: insertion.staff, chord_with_id: owner.id, kind: 'note', pitch: insertPitch } : { ...insertion, kind: tool === 'Rest' ? 'rest' : 'note', pitch: tool === 'Rest' ? null : insertPitch, duration: effective });
        setInsertion(null);
        setAnchorBox(null);
        setPalette(false);
        return;
    } if (!event) {
        setNotice('Select a note or an explicit rhythmic gap first.');
        return;
    } const written = dottedWritten(value, dot), effective = event.palette_duration_options[written]; if (!effective)
        throw Error('This written duration cannot be represented without changing the existing rhythmic structure.'); await mutate(`events/${event.id}`, { duration: effective, preserve_onsets: true }, 'PATCH'); setPalette(false); }
    function keyAlter(step:string,measure:string,keys?:{fifths:string}[]){
        const fifths=Number((keys??review?.score.parts.flatMap(p=>p.measures).find(m=>m.id===measure)?.key_signature)?.[0]?.fifths??0);
        return (fifths>=0?'FCGDAEB':'BEADGCF').slice(0,Math.abs(fifths)).includes(step)?String(fifths>=0?1:-1):'0';
    }
    function movedAlter(note:typeof event,step:string){
        if(!note?.pitch)return '0';
        const pinned=!!note.accidental?.text || Number(note.pitch.alter)!==Number(keyAlter(note.pitch.step,note.measure_id,note.key_signature));
        return pinned?note.pitch.alter:keyAlter(step,note.measure_id,note.key_signature);
    }
    async function changePitch(change: Partial<Pitch>) {
        if(!event?.pitch)return;
        await mutate(`events/${event.id}`,{pitch:{...event.pitch,...change,alter:change.alter??movedAlter(event,change.step??event.pitch.step)}},'PATCH');
    }
    async function applyAccidental(written:string,alter:string){
        if(!event?.pitch)return;
        await mutate(`events/${event.id}`,{pitch:{...event.pitch,alter},written_accidental:written},'PATCH');
    }
    async function equalGroup() {
        if(!review)return;
        if(insertion?.voice){
            await mutate('triplets',{...insertion,pattern:'equal',base_duration:equalBase,pitches:[insertPitch,insertPitch,insertPitch]},'POST','Equal triplet applied to the working score.');
            setInsertion(null);
        } else {
            const selected=all.filter(e=>groupIds.includes(e.id));
            if(selected.length!==3 || selected.some(e=>e.kind!=='note'||!e.pitch||e.voice!==selected[0].voice||e.staff!==selected[0].staff||e.measure_id!==selected[0].measure_id))throw Error('Select three consecutive single notes in one measure, voice and staff, or choose an empty gap.');
            await mutate('triplets',{measure_id:selected[0].measure_id,voice:selected[0].voice,staff:selected[0].staff,pattern:'equal',base_duration:equalBase,event_ids:selected.map(e=>e.id)},'POST','Equal triplet applied to the selected notes.');
        }
        setGroupIds([]);setSelected(null);setPalette(false);setTool('Select');
    }
    async function mixedGroup() {
        if (!review)
            return;
        if (insertion?.voice) {
            await mutate('triplets', { ...insertion, base_duration: '1', pattern: 'quarter-eighth', member_counts: [1, 1], pitches: [insertPitch, insertPitch] });
            setInsertion(null);
            setPalette(false);setTool('Select');
            return;
        }
        if (event && groupIds.length <= 1) {
            const members = event.chord_id ? all.filter(e => e.chord_id === event.chord_id) : [event];
            if (members.length > 2 || members.some(e => !e.pitch))
                throw Error('Choose a single pitched note or a complete two-note chord.');
            await mutate(`events/${event.id}/replace-triplet`, { pattern: 'quarter-eighth', preserve_associations: true, original_member_ids: members.map(e => e.id), member_counts: [members.length, 1], pitches: [...members.map(e => e.pitch), members[0].pitch] });
            setSelected(null);
            setGroupIds([]);
            setPalette(false);setTool('Select');
            return;
        }
        const preview = await previewTriplet(review, groupIds);
        if (!preview.valid || !preview.command)
            throw Error(preview.reason ?? preview.message ?? 'Select a note/chord or an empty rhythmic gap.');
        await mutate('triplets', preview.command);
        setGroupIds([]);
        setPalette(false);setTool('Select');
    }
    async function remove() { if (!review)
        return; if (curve) {
        if (curve.kind === 'tie')
            await mutate(`events/${curve.from}`, { tie_to_event_id: null }, 'PATCH');
        else
            await mutate('slurs', { source_event_id: curve.from, target_event_id: curve.to, remove: true });
        setCurve(null);
        return;
    } if (!event)
        return; if (event.pitch)
        setInsertPitch(event.pitch); await mutate(`events/${event.id}/delete-preserve-timing`); setSelected(null); setDraft(null); }
    async function save(copy = false) { if (!review)
        return; if (!name.trim())
        throw Error('Choose a filename before saving.'); if (!review.validation.can_verify)
        throw Error('Correct technical XML errors before saving. Validate lists the specific errors.'); const outputName = name.toLowerCase().endsWith('.musicxml') ? name : name + '.musicxml'; const chosen = await chooseLocal(outputName, handle.current, copy); const verified = await edit(review, 'verify', { confirmed_source_comparison: true }); setReview(verified); const target = await writeLocal(verified.bytes, outputName, chosen); setSaveAs(false); if (target) {
        handle.current = target;
        recordSave({ xml: verified.xml, bytes: verified.bytes, name: outputName, projection: verified });
        setNotice(instrumentEditor ? 'Instrument score saved to your selected file.' : 'Canonical Concert Score saved to your selected file.');
    }
    else {
        setReceipt({ xml: verified.xml, bytes: verified.bytes, name: outputName, projection: verified });
        setNotice(instrumentEditor ? 'Download requested. Confirm that you retained the instrument file.' : 'Download requested. Confirm that you retained the file before it becomes the saved concert source.');
    } }
    async function transpose() { if (!review || !confirmed)
        throw Error('Confirm the source key and mode first.'); const xml = await concertXML(review.xml, sourceKey, target, direction); await replace(xml); setNotice('Concert key changed. Save this new concert score before generating instrument scores.'); }
    const variant = (id: string, direction = instrumentDirection) => `${id}-${direction}`;
    async function generate(id: string, requestedDirection = instrumentDirection) {
        if (!saved || !canGenerate) throw Error('Save the current Concert Score before generating instrument scores.');
        const key=variant(id,requestedDirection);if(instrument===id && requestedDirection===instrumentDirection)return;
        if (!outputs[key]) {
            const next=await openXML(xmlBlob(await saxXML(saved.xml,id,requestedDirection)));
            await closeReview(next.id);
            initialFiles.current.set(key,new File([next.bytes.slice().buffer],`${key}-${saved.name}`,{type:'application/xml'}));
            setOutputs(o=>({...o,[key]:next}));
        }
        else initialFiles.current.set(key,new File([outputs[key].bytes.slice().buffer],`${key}-${saved.name}`,{type:'application/xml'}));
        setInstrumentDirection(requestedDirection); setInstrument(id); setNotice('Independent instrument workspace. Edits affect only the right-hand written score.');
    }
    useEffect(() => { const listener = (e: KeyboardEvent) => { if (busy || receipt || homePrompt || (stage === 2) || (e.target as HTMLElement).closest('input,textarea,select,[role=dialog]'))
        return; if (e.key === 'Escape') {
        setPending(null);
        setInsertion(null);
        setTool('Select');
        setDraft(null);
    } if (stage === 1 && (e.ctrlKey || e.metaKey) && e.key === 'z') {
        e.preventDefault();
        void run(() => historyMove(e.shiftKey));
    } if ((e.key === 'Delete' || e.key === 'Backspace') && (selected || curve) && stage === 1) {
        e.preventDefault();
        void run(remove);
    } }; window.addEventListener('keydown', listener); return () => window.removeEventListener('keydown', listener); });
    function recordSave(next: SavedScore) { setSaved(next); instrumentEditor?.onSave(next); }
    const unsavedInstruments = Object.keys(outputs).filter(key=>outputs[key].xml!==instrumentSaves[key]?.xml);
    function requestHome() {
        if(lock.current || busy || receipt || editorBusy || draftLive.current || textLive.current) return;
        if(dirty || unsavedInstruments.length) { setHomePrompt(true); return; }
        onExit();
    }
    function openToSave(key: string) {
        setHomePrompt(false);
        if(key==='concert') { setStage(1); setNotice('Save the Concert Score, then choose Home.'); return; }
        const [id,direction]=key.split('-');
        setStage(2);
        void run(async()=>{await generate(id,direction as 'up'|'down');setNotice('Save this instrument score, then choose Home.');});
    }
    const currentKey = detected ? `${(detected.mode === 'minor' ? minors : majors)[detected.fifths + 7]}${detected.mode ? ' ' + detected.mode : ' · mode unconfirmed'}` : 'Key unavailable';
    return <><input ref={input} className="file-input" type="file" accept=".musicxml,.xml" onChange={e => { const f = e.target.files?.[0]; e.target.value = ''; if (!f)
        return; if ((dirty || Object.keys(outputs).length) && !window.confirm('Leave this score and discard any changes not saved to a local file, including instrument edits?'))
        return; void run(async () => { const next = await remember(await openXML(f)); setReview(next); setOriginal(next); setHistory([]); setFuture([]); setSaved(null); handle.current = null; setName(f.name); setOutputs({}); setInstrumentSaves({}); initialFiles.current.clear(); setSelected(null); setPending(null); setCurve(null); setInsertion(null); setTextDraft(null); setGroupIds([]); setDraft(null); setTool('Select'); setStage(1); await releaseExcept(next.id); await detect(next); }); }}/>
 <fieldset className={"real-workspace"+(instrumentEditor ? " instrument-editor" : "")} disabled={busy || !!receipt || homePrompt}>
 <header className={instrumentEditor ? "instrument-editor-header" : "app-header"}><div className="workspace-brand">{!instrumentEditor && <nav aria-label="Main navigation" className="home-navigation"><button disabled={editorBusy || !!draft || !!textDraft} onClick={requestHome}><svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M3 10 12 3l9 7M5 9v12h5v-7h4v7h5V9"/></svg><span>Home</span></button></nav>}<div className="brand"><strong>Music Sheet Transposer</strong><small>MusicXML workspace · real editing</small></div></div><nav className="header-actions">{!instrumentEditor && <><button disabled={!review || stage !== 1} onClick={() => setConcert(!concert)}>Concert Key</button><button disabled={editorBusy} onClick={() => input.current?.click()}>Open MusicXML</button></>}<button disabled={!review} onClick={() => setValidation(!validation)}>Validate</button><button disabled={!history.length || stage !== 1} onClick={() => void run(() => historyMove())}>↶ Undo</button><button disabled={!future.length || stage !== 1} onClick={() => void run(() => historyMove(true))}>↷ Redo</button><button disabled={!review || stage !== 1} className="primary" onClick={() => void run(() => save())}>Save</button><button disabled={!review || stage !== 1} onClick={() => setSaveAs(!saveAs)}>Save As</button><button disabled={!saved} onClick={() => { if (saved) {
        download(saved.bytes, saved.name);
        setNotice(dirty ? 'Exported the prior saved concert file; unsaved edits excluded.' : 'Exported saved Concert MusicXML.');
    } }}>Export saved MusicXML</button><button disabled={!review || editorBusy} hidden={!!instrumentEditor} onClick={() => { setSaveAs(false); setConcert(false); setPalette(false); setPending(null); setInsertion(null); setVoiceChoice(null); setStage(stage === 1 ? 2 : 1); }}>{stage === 1 ? 'Instrument Scores →' : '← Concert Score'}</button>{stage === 1 && <button disabled={!review} onClick={()=>void run(async()=>{if(review)await exportScorePDF(review,name);setNotice('Working score exported as PDF.');})}>Export PDF</button>}</nav></header>
 {saveAs && <div className="real-save-popover"><label>Filename<input value={name} onChange={e => setName(e.target.value)}/></label><button onClick={() => void run(() => save(true))}>Save Copy</button><button onClick={() => setSaveAs(false)}>Cancel</button></div>}
 {!review ? <main><p role="status">{notice}</p></main> : stage === 1 ? <div className="shell"><aside className="rail"><strong>EDIT</strong>{instrumentEditor && <button aria-label="Add measure" onClick={()=>void run(async()=>{if(review)await replace(appendMeasure(review));})}><svg aria-hidden="true" width="27" height="29" viewBox="0 0 30 32" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M4 8h15v18H4zM4 14h15M4 20h15M24 3v12M18 9h12"/></svg><span>Add measure</span></button>}{(['Select', 'Notes', 'Rest', 'Tie', 'Slur', 'Groups', 'Lyrics', 'Text'] as Tool[]).map(t => <div className="rail-slot" key={t}><button aria-label={t} className={tool === t ? 'active' : ''} onClick={() => chooseTool(t)}>{['Notes', 'Rest', 'Tie', 'Slur', 'Groups'].includes(t) ? <MusicIcon kind={t === 'Notes' ? 'Quarter' : t}/> : <span className="tool-icon">{t === 'Lyrics' ? 'Aa' : t === 'Text' ? 'T' : '↖'}</span>}<span>{t}</span></button>{palette && tool === t && <div className={"rail-palette"+(t === "Groups" ? " groups-palette" : "")}>{t === 'Notes' ? lengths.map(v => <button key={v.value} aria-label={v.name + ' note'} onClick={() => void run(() => duration(v.value))}><MusicIcon kind={v.name}/>{v.name}</button>) : <><p>Mixed 3:2: a note/chord or gap. Equal-duration triplet: three consecutive single notes or an empty gap. Each pitch is editable; insertion starts at the chosen pitch.</p><p>{groupIds.length} selected notes</p><label className="equal-triplet-value">Equal triplet note value<select aria-label="Equal triplet note value" value={equalBase} onChange={e=>setEqualBase(e.target.value)}>{[...lengths,{value:'1/8',name:'32nd'},{value:'1/16',name:'64th'}].map(v=><option key={v.value} value={v.value}>{v.name}</option>)}</select></label><button onClick={() => void run(mixedGroup)}>♩♪ 3:2</button><button disabled={groupIds.length!==3&&!insertion?.voice} onClick={()=>void run(equalGroup)}>3 equal notes 3:2</button>{[2, 3, 4, 5, 6, 8].map(n => <button disabled={groupIds.length !== n} key={n} onClick={() => void run(async () => { await replace(beamSelected(review, groupIds, n)); setGroupIds([]); setPalette(false); setTool('Select'); })}>Beam {n}</button>)}</>}<button onClick={() => setPalette(false)}>Close palette</button></div>}</div>)}<button aria-label="Delete" onClick={() => void run(remove)}>⌫<span>Delete</span></button></aside>
 <main><section className="workspace-heading"><div><span className="phase">{instrumentEditor ? "STAGE 2" : "STAGE 1"}</span><strong>{instrumentEditor?.label ?? "Compare & correct"}</strong></div><span className={'save-state ' + (dirty ? 'dirty' : '')}>{!saved ? 'Not yet saved locally' : dirty ? 'Unsaved changes' : instrumentEditor ? 'Instrument file saved' : 'Concert file saved'}</span></section>
 {concert && <section className="concert-panel"><strong>Concert Key</strong><p>Confirm the source key; changing the concert key transposes the actual score.</p><label>Source key<select aria-label="Source key" value={sourceKey.fifths} onChange={e => { setSourceKey(k => ({ ...k, fifths: Number(e.target.value) })); setConfirmed(false); }}>{majors.map((k, i) => <option value={i - 7} key={i}>{sourceKey.mode === 'minor' ? minors[i] : k}</option>)}</select></label><label>Mode<select aria-label="Mode" value={sourceKey.mode} onChange={e => { setSourceKey(k => ({ ...k, mode: e.target.value as Key['mode'] })); setConfirmed(false); }}><option value="major">Major</option><option value="minor">Minor</option></select></label><label><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)}/>Confirm source key: {keyName(sourceKey)}</label><label>New concert key<select aria-label="New concert key" value={target} onChange={e => setTarget(Number(e.target.value))}>{majors.map((k, i) => <option value={i - 7} key={i}>{sourceKey.mode === 'minor' ? minors[i] : k}</option>)}</select></label><label>Direction<select aria-label="Direction" value={direction} onChange={e => setDirection(e.target.value as 'up' | 'down')}><option value="up">Up</option><option value="down">Down</option></select></label><button onClick={() => setConcert(false)}>Keep Original</button><button disabled={!confirmed} onClick={() => void run(transpose)}>Apply concert key</button></section>}
 <div className="compare-toolbar"><div><button className={compare ? 'active' : ''} onClick={() => setCompare(true)}>Compare</button><button hidden={!!instrumentEditor} className={!compare ? 'active' : ''} onClick={() => setCompare(false)}>Edit Only</button></div><small>Original XML is read-only · independent zoom and scroll</small></div>
 <div className={'compare-layout ' + (!compare ? 'edit-only' : '')} style={compare ? { gridTemplateColumns: `minmax(0,${split}fr) 10px minmax(0,${100 - split}fr)` } : undefined}>
 {compare && original && <><section className="source-pane"><div className="pane-heading"><strong>{instrumentEditor ? "Saved concert input · read-only" : "Original Source"}</strong><span className="tag">Read-only MusicXML</span></div><div className="source-tools"><span>{instrumentEditor?.referenceName ?? file.name}</span><div><button aria-label="Fit source score" onClick={() => fit('source')}>Fit</button><button aria-label="Source zoom out" onClick={() => setSourceZoom(z => Math.max(.25, z - .1))}>−</button><output>{Math.round(sourceZoom * 100)}%</output><button aria-label="Source zoom in" onClick={() => setSourceZoom(z => Math.min(2, z + .1))}>+</button></div></div><div ref={sourceViewport} className="score-viewport source-scroll"><RenderedScore review={original} readOnly zoom={sourceZoom} fitVersion={fitVersions.source}/></div><p className="pane-foot">Original MusicXML reference · no OMR or image alignment.</p></section><div className="splitter" role="separator" aria-label="Resize source and working score" aria-orientation="vertical" aria-valuenow={split} tabIndex={0} onPointerDown={e => e.currentTarget.setPointerCapture(e.pointerId)} onPointerMove={e => { if (e.buttons) {
            const b = e.currentTarget.parentElement!.getBoundingClientRect();
            setSplit(Math.max(25, Math.min(70, (e.clientX - b.left) / b.width * 100)));
        } }} onKeyDown={e => { if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
            e.preventDefault();
            setSplit(s => Math.max(25, Math.min(70, s + (e.key === 'ArrowLeft' ? -2 : 2))));
        } }}>⋮</div></>}
 <section className="working-pane"><div className="pane-heading"><strong>Working Score</strong><span className="tag editable">Real MusicXML</span><span className="tag" data-testid="real-concert-key">{instrumentEditor ? "Written key:" : "Concert key:"} {currentKey}</span><div className="zoom"><button aria-label="Fit working score" onClick={() => fit('working')}>Fit</button><button aria-label="Working score zoom out" onClick={() => setZoom(z => Math.max(.25, z - .1))}>−</button><output>{Math.round(zoom * 100)}%</output><button aria-label="Working score zoom in" onClick={() => setZoom(z => Math.min(2, z + .1))}>+</button></div></div>
 <div className="note-context">{event ? <><span>Voice {event.voice} · measure {review.score.parts.flatMap(p => p.measures).find(m => m.id === event.measure_id)?.number}</span>{event.pitch && <><label>Pitch<select aria-label="Selected note pitch" value={event.pitch.step} onChange={e=>void run(()=>changePitch({step:e.target.value}))}>{[..."CDEFGAB"].map(step=><option key={step}>{step}</option>)}</select></label><label>Octave<select aria-label="Selected note octave" value={event.pitch.octave} onChange={e=>void run(()=>changePitch({octave:Number(e.target.value)}))}>{Array.from({length:10},(_,i)=><option key={i} value={i}>{i}</option>)}</select></label></>}{event.pitch && <div className="accidental-buttons" role="group" aria-label="Note accidentals">{[['flat-flat','-2','Double flat','♭♭'],['flat','-1','Flat','♭'],['natural','0','Natural','♮'],['sharp','1','Sharp','♯'],['double-sharp','2','Double sharp','×']].map(([written,alter,label,symbol])=><button key={written} aria-label={label+' accidental'} title={label} aria-pressed={event.accidental?.text===written} className={event.accidental?.text===written?'active':''} onClick={()=>void run(()=>applyAccidental(written,alter))}><span aria-hidden="true">{symbol}</span></button>)}</div>}<button onClick={() => void run(() => duration(({ whole: '4', half: '2', quarter: '1', eighth: '1/2', '16th': '1/4' }[event.notated_duration?.type ?? 'quarter'] ?? '1'), !event.notated_duration?.dots))}>Dot</button>{event.pitch && <><button onClick={() => void run(() => mutate(`events/${event.id}`, { display_size: 'normal' }, 'PATCH'))}>Normal</button><button onClick={() => void run(() => mutate(`events/${event.id}`, { display_size: 'small' }, 'PATCH'))}>Small</button><button onClick={() => beginLyric(event.id)}>Edit lyrics</button><button onClick={() => beginLyric(event.id, String(Math.max(0, ...review.score.lyrics.filter(l => l.event_id === event.id).map(l => Number(l.number) || 0)) + 1))}>Add Verse</button></>}
            <button onClick={() => void run(remove)}>Delete selected</button></> : <span>{curve ? `${curve.kind} selected · drag up/down or Delete` : 'Select a notehead to edit; choose Notes or Rest, then click the staff to insert.'}</span>}</div>
 {event && <div className="note-context"><label>Verse<select value={verse} onChange={e => setVerse(e.target.value)}>{Array.from({ length: Math.max(1, ...review.score.lyrics.map(l => Number(l.number) || 1)) }, (_, i) => <option key={i}>{i + 1}</option>)}</select></label><button onClick={() => beginLyric(event.id)}>Edit selected lyric</button><button onClick={() => void run(async () => { const l = review.score.lyrics.find(l => l.event_id === event.id && l.number === verse); if (l)
            await mutate(`lyrics/${l.id}`, undefined, 'DELETE'); })}>Delete syllable</button></div>}
 {insertion && insertion.voice && <div className="note-context"><strong>Insert at beat {rational(insertion.onset) + 1}</strong><label>Pitch<select value={insertPitch.step} onChange={e => setInsertPitch(p => ({ ...p, step: e.target.value,alter:insertAccidentalExplicit?p.alter:keyAlter(e.target.value,insertion.measure_id) }))}>{[..."CDEFGAB"].map(p => <option key={p}>{p}</option>)}</select></label><label>Accidental<select aria-label="Insertion accidental" value={insertPitch.alter} onChange={e => {setInsertAccidentalExplicit(true);setInsertPitch(p => ({ ...p, alter: e.target.value }));}}>{[["-2", "Double flat"], ["-1", "Flat"], ["0", "Natural"], ["1", "Sharp"], ["2", "Double sharp"]].map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label>Octave<input type="number" min="0" max="9" value={insertPitch.octave} onChange={e => setInsertPitch(p => ({ ...p, octave: Number(e.target.value) }))}/></label><label>Voice<select value={insertion.voice} onChange={e => setInsertion({ ...insertion, voice: e.target.value })}>{[...new Set(all.map(e => e.voice))].map(v => <option key={v}>{v}</option>)}</select></label><button onClick={() => setTool(tool === 'Rest' ? 'Notes' : 'Rest')}>{tool === 'Rest' ? 'Insert note' : 'Insert rest'}</button><button onClick={() => setInsertion(null)}>Cancel</button></div>}
 <div ref={workingViewport} className="score-viewport working-scroll"><RenderedScore review={review} zoom={zoom} fitVersion={fitVersions.working} selected={selected} onHead={select} onLyric={(id, v, b) => beginLyric(id, v, b)} onReady={setMapped} onGap={(measure_id, onset, voice, staff) => { setInsertAccidentalExplicit(false);setInsertPitch(p=>({...p,alter:keyAlter(p.step,measure_id)}));setInsertion({ measure_id, onset, voice, staff }); setSelected(null); setGroupIds([]); if (tool !== 'Groups')
            setTool('Notes'); setPalette(true); }} onCurve={(c, dy) => { setCurve(c); setSelected(null); if (Math.abs(dy) > 5)
            void run(async () => { const direction = dy < 0 ? 'up' : 'down'; if (c.kind === 'tie')
                await mutate(`events/${c.from}`, { tie_direction: direction }, 'PATCH');
            else
                await mutate('slurs', { source_event_id: c.from, target_event_id: c.to, direction }); setCurve({ ...c, direction }); }); }} onAnchor={(measure, onset, staff, pitch, box) => { if (tool === 'Tie' || tool === 'Slur') {
            setNotice('Choose noteheads; empty staff is unchanged.');
            return;
        } if (tool !== 'Notes' && tool !== 'Rest' && tool !== 'Groups')
            return; setSelected(null); setGroupIds([]); setInsertAccidentalExplicit(false);setInsertPitch(pitch); setAnchorBox(box); setInsertion({ measure_id: measure, onset, staff, voice: '' }); }} onText={(id, b) => { const t = review.score.texts.find(t => t.id === id); if (t)
            setTextDraft({ id, text: t.text, x: Math.max(8, Math.min(window.innerWidth - 220, b.left)), y: Math.max(8, Math.min(window.innerHeight - 70, b.bottom + 5)) }); }} onAmbiguous={(ids, dy, box) => setVoiceChoice({ ids, dy, box })}/></div><p className="pane-foot">{mapped} mapped noteheads · select or drag to change pitch · Unicode lyrics</p>

 </section></div></main></div> : <main className="stage-two"><h1>Instrument Scores <span className="tag">Real MusicXML</span></h1><section><h2>1 · Saved Canonical Concert Score</h2>{canGenerate ? <p>{saved?.name} · current saved version</p> : <p className="warning">Save the current Concert Score in Stage 1 before generating instrument scores. Unsaved edits cannot be used.</p>}</section><section><h2>2 · Choose an instrument</h2><fieldset className="instrument-selection" disabled={editorBusy}><div className="instrument-cards">{saxes.map(s=><button disabled={!canGenerate} key={s.id} className={instrument===s.id ? 'chosen' : ''} onClick={()=>void run(()=>generate(s.id))}><strong>{s.name}</strong><span>Concert {offsetLabel(s.offset-(instrumentDirection==='down'?12:0))} semitones · independent written score</span></button>)}</div><label>Direction <select aria-label="Instrument direction" value={instrumentDirection} onChange={e=>{const next=e.target.value as 'up'|'down';if(instrument)void run(()=>generate(instrument,next));else setInstrumentDirection(next);}}><option value="up">Up · standard written register</option><option value="down">{instrument==='tenor' ? 'Down · like Soprano notation (+2)' : 'Down · one octave below standard'}</option></select></label><p>Down writes one octave below the standard output. Tenor Down uses +2 semitones, like Soprano Up notation; played on Tenor B♭ it sounds one octave below the saved Concert Score. Concert source and instrument transposition metadata stay unchanged. Each instrument and direction keeps its own edits during this session; save an instrument file to retain them after leaving.</p></fieldset></section><section className="instrument-work"><h2>3 · Compose & export</h2>{instrument && saved && outputs[variant(instrument)] && initialFiles.current.get(variant(instrument)) ? <><button disabled={editorBusy} onClick={()=>download(outputs[variant(instrument)].bytes,`${variant(instrument)}-${saved.name}`)}>Export instrument MusicXML</button><RealWorkspace key={variant(instrument)} file={initialFiles.current.get(variant(instrument))!} onExit={()=>{}} instrumentEditor={{reference:saved.projection,referenceName:saved.name,label:`${saxes.find(s=>s.id===instrument)?.name} · ${instrumentDirection==='up'?'Up':'Down'}`,saved:instrumentSaves[variant(instrument)],onSave:next=>{const key=variant(instrument);setInstrumentSaves(s=>({...s,[key]:next}));},onBusy:setEditorBusy,onChange:r=>{const key=variant(instrument);setOutputs(o=>o[key]?.xml===r.xml ? o : {...o,[key]:r});}}}/></> : <p>Select an instrument to open the read-only concert input and editable instrument score.</p>}</section></main>}

 </fieldset>
 {insertion && !insertion.voice && anchorBox && <div className="anchor-menu" style={{ left: Math.max(5, Math.min(window.innerWidth - 245, anchorBox.left)), top: Math.max(5, Math.min(window.innerHeight - 160, anchorBox.top)) }}><strong>Choose voice for insertion</strong>{[...new Set(all.filter(e => e.measure_id === insertion.measure_id && e.staff === insertion.staff).map(e => e.voice))].map(v => <button key={v} disabled={busy} onClick={() => { setInsertion({ ...insertion, voice: v }); setPalette(true); }}>Voice {v}</button>)}<button onClick={() => setInsertion(null)}>Cancel</button></div>}
 {voiceChoice && <div className="anchor-menu" style={{ left: Math.min(window.innerWidth - 245, voiceChoice.box.left), top: Math.min(window.innerHeight - 170, voiceChoice.box.bottom + 8) }}><strong>Choose the note voice</strong>{voiceChoice.ids.map(id => <button disabled={busy} key={id} onClick={() => { select(id, voiceChoice.dy); setVoiceChoice(null); }}>Voice {all.find(e => e.id === id)?.voice} · {id}</button>)}<button onClick={() => setVoiceChoice(null)}>Cancel</button></div>}
 {draft && <div className="real-lyric-input" style={{ left: draft.x, top: draft.y }}><input ref={lyricInput} aria-label="Lyric syllable" value={draft.text} onChange={e => setDraft(d => d ? { ...d, text: e.target.value } : null)} onKeyDown={e => { if (e.nativeEvent.isComposing)
        return; if (e.key === 'Escape') {
        e.preventDefault();
        draftLive.current = null;
        setDraft(null);
    } if (e.key === 'Enter' || e.key === 'Tab') {
        e.preventDefault();
        void run(() => commitLyric(e.key === 'Tab' ? (e.shiftKey ? -1 : 1) : 0));
    } }} onBlur={() => { if (draftLive.current)
        void run(() => commitLyric()); }}/><small>Enter saves · Esc cancels · Tab next note</small></div>}
 {textDraft && <div className="real-lyric-input" style={{left:textDraft.x,top:textDraft.y}}><input autoFocus aria-label="Score text" value={textDraft.text} onChange={e=>setTextDraft({...textDraft,text:e.target.value})} onKeyDown={e=>{if(e.nativeEvent.isComposing)return;if(e.key==='Escape'){textLive.current=null;setTextDraft(null);}if(e.key==='Enter'){e.preventDefault();void run(commitText);}}} onBlur={()=>{if(textLive.current)void run(commitText);}}/><small>Enter or blur saves · Esc cancels</small></div>}
 {receipt && <section role="dialog" aria-label={instrumentEditor ? "Confirm downloaded instrument file" : "Confirm downloaded concert file"} className="real-receipt"><strong>Keep the downloaded {instrumentEditor ? "Instrument" : "Concert"} MusicXML</strong><p>The browser cannot confirm that your download was retained.</p><button onClick={() => { recordSave(receipt); setReceipt(null); setNotice(instrumentEditor ? 'You confirmed the local Instrument MusicXML was retained.' : 'You confirmed the local Concert MusicXML was retained.'); }}>I retained the downloaded file</button><button onClick={() => { setReceipt(null); setNotice('No new save confirmed. Any previous saved file remains unchanged.'); }}>Cancel confirmation</button></section>}
 {!instrumentEditor && homePrompt && <section role="dialog" aria-modal="true" aria-label="Save before Home" className="real-receipt home-prompt" onKeyDown={e=>{if(e.key==='Escape')setHomePrompt(false);}}><strong>Save before returning Home</strong><p>Save each listed score before importing a new file. Your work is still open.</p>{dirty && <p><button disabled={busy || editorBusy} onClick={()=>openToSave('concert')}>Open Concert to save</button></p>}{unsavedInstruments.map(key=>{const [id,direction]=key.split('-');return <p key={key}><button disabled={busy || editorBusy} onClick={()=>openToSave(key)}>Open {saxes.find(s=>s.id===id)?.name} · {direction==='up'?'Up':'Down'} to save</button></p>;})}<button autoFocus onClick={()=>setHomePrompt(false)}>Continue editing</button></section>}
 {validation && review && <section className="validation real-validation"><div className="validation-head"><strong>Validate</strong><button onClick={() => setValidation(false)}>Close</button></div><div>{review.validation.diagnostics.length ? review.validation.diagnostics.map((d, i) => <p key={i}>{d.blocking ? 'Technical error: ' : 'Advisory: '}{d.message}</p>) : <p>No technical diagnostics.</p>}<p>Checks do not alter the score.</p></div></section>}
 <div className={instrumentEditor ? "instrument-notice" : "notice"} role="status">{busy ? 'Working… ' : ''}{notice}</div></>;
}
