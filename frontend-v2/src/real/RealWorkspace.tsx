import { concertKeyRange } from './concertKeyRange';
import { suggestOriginalKey } from './originalKeySuggestion';
import { parseChordInput, chordInputText } from './chordInput';
import { HarmonyEditor } from './HarmonyEditor';
import { LyricsRepair } from './LyricsRepair';
import { OMRWarnings } from './OMRWarnings';
import { PDFSource } from './PDFSource';
import { exportScorePDF } from './scorePDF';
import { declareInitialKey, measureContext, beamSelected, appendMeasure } from './xmlEdits';
import { useEffect, useRef, useState } from 'react';
import { RenderedScore, type Curve } from './RenderedScore';
import { keepReviewAlive, manualSource, recognizeSource, correctDocument, closeReview, concertXML, edit, events, keyInfo, openXML, rational, saxXML, xmlBlob, previewTriplet, dottedWritten, type Key, type Pitch, type Review } from './api';
import { download, writeLocal, chooseLocal, type Handle } from './files';
import { MusicIcon } from '../MusicIcon';
import './real.css';
const lengths = [{ value: '4', name: 'Whole' }, { value: '2', name: 'Half' }, { value: '1', name: 'Quarter' }, { value: '1/2', name: 'Eighth' }, { value: '1/4', name: '16th' }, { value: '1/8', name: '32nd' }, { value: '1/16', name: '64th' }];
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
    segment: number;
    x: number;
    y: number;
};
type SavedScore = { xml: string; bytes: Uint8Array; name: string; projection: Review };
type EditorHistory = {canUndo:boolean;canRedo:boolean;canEdit:boolean;canExport:boolean;undo:()=>void;redo:()=>void;validate:()=>void;save:()=>void;saveAs:()=>void;exportXML:()=>void};
type InstrumentEditor = { onHistory?: (history:EditorHistory|null)=>void; reference: Review; referenceName: string; label: string; onChange: (r: Review) => void; onBusy: (busy: boolean) => void; saved?: SavedScore; onSave: (saved: SavedScore) => void };
export function RealWorkspace({ file, onExit, instrumentEditor, recognitionProfile }: {
    recognitionProfile?: string;
    instrumentEditor?: InstrumentEditor;
    file: File;
    onExit: () => void;
}) {
    const [instrumentHistory,setInstrumentHistory]=useState<EditorHistory|null>(null);
    const [review, setReview] = useState<Review | null>(null), [original, setOriginal] = useState<Review | null>(null), [busy, setBusy] = useState(false), [notice, setNotice] = useState('Opening MusicXML…');
    const [openedXML,setOpenedXML]=useState<File|null>(null);
    const isSource = !openedXML && /\.(pdf|png|jpe?g)$/i.test(file.name);
    const [sourceURL,setSourceURL] = useState('');
    const [sourceCompared,setSourceCompared] = useState(false);
    const [implicitInitialKey,setImplicitInitialKey]=useState(false);
    const [recognitionWarnings,setRecognitionWarnings] = useState<{code?:string;message:string;measure?:string|null;part_id?:string|null}[]>([]);
    useEffect(()=>{if(!isSource)return;const url=URL.createObjectURL(file);setSourceURL(url);return()=>URL.revokeObjectURL(url);},[file,isSource]);
    const lock = useRef(false), sessions = useRef(new Set<string>()), handle = useRef<Handle | null>(null), input = useRef<HTMLInputElement>(null);
    const [saved, setSaved] = useState<{
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
    const [saveKeyPrompt,setSaveKeyPrompt]=useState<{copy:boolean;fifths:string;mode:''|'major'|'minor'}|null>(null);
    const [importBaseline,setImportBaseline]=useState<SavedScore|null>(null);
    const [toolsOpen,setToolsOpen]=useState(false),[noteTools,setNoteTools]=useState(false),[chordMode,setChordMode]=useState(false);
    const [harmonyChoice,setHarmonyChoice]=useState<{ids:string[];x:number;y:number}|null>(null);
    const [chordDraft,setChordDraft]=useState<{id:string|null;measure_id:string;onset:string;text:string;x:number;y:number}|null>(null);
    const chordLive=useRef<typeof chordDraft>(null);chordLive.current=chordDraft;
    function beginChord(measure_id:string,onset:string,box?:DOMRect,id:string|null=null){
        const h=review?.score.harmonies?.find(h=>h.id===id);
        setHarmonyChoice(null);
        setChordDraft({id,measure_id,onset,text:h?chordInputText(h):'',x:Math.max(8,Math.min(window.innerWidth-250,box?.left??workingViewport.current?.getBoundingClientRect().left??200)),y:Math.max(76,Math.min(window.innerHeight-100,box?.top??180))});
        setToolsOpen(false);setNoteTools(false);setObjectMenu(null);
    }
    async function commitChord(){const d=chordLive.current;if(!d)return;const body=parseChordInput(d.text);await mutate(d.id?'harmonies/'+d.id:'harmonies',d.id?body:{...body,measure_id:d.measure_id,...(all.find(e=>e.measure_id===d.measure_id&&rational(e.onset)===rational(d.onset))?{before_event_id:all.find(e=>e.measure_id===d.measure_id&&rational(e.onset)===rational(d.onset))!.id}:{onset:d.onset})},d.id?'PATCH':'POST');chordLive.current=null;setChordDraft(null);setChordMode(false);}
    const [chordPosition]=useState<{measure_id:string;onset:string}|null>(null),[chordEditId]=useState<string|null>(null);
    const [contextBox,setContextBox]=useState({x:20,y:90}),[objectMenu,setObjectMenu]=useState<{kind:'mark'|'text';id:string;x:number;y:number}|null>(null);
    function beside(box:DOMRect){const rail=workingViewport.current?.closest('.shell')?.querySelector('aside.rail')?.getBoundingClientRect();const left=Math.max(8,(rail?.right??0)+8);return {x:Math.max(left,Math.min(window.innerWidth-390,box.left-390)),y:Math.max(76,Math.min(window.innerHeight-265,box.top))};}
    const [selection,setSelection]=useState<string[]>([]),[boxSelect,setBoxSelect]=useState(false);
    const [selectedMark,setSelectedMark]=useState<string|null>(null);
    const [selectedText,setSelectedText]=useState<string|null>(null);
    const [selected, setSelected] = useState<string | null>(null), [tool, setTool] = useState<Tool>('Select'), [palette, setPalette] = useState(false), [pending, setPending] = useState<string | null>(null), [zoom, setZoom] = useState(1), [sourceZoom, setSourceZoom] = useState(1), [compare, setCompare] = useState(true), [split, setSplit] = useState(48);
    const concertButton=useRef<HTMLButtonElement>(null);
    function closeConcert(){setConcert(false);concertButton.current?.focus({preventScroll:true});}
    const [concert, setConcert] = useState(false), [detected, setDetected] = useState<{
        fifths: number;
        mode: 'major' | 'minor' | null;
    } | null>(null), [sourceKey, setSourceKey] = useState<Key>({ fifths: 0, mode: 'major' }), [confirmed, setConfirmed] = useState(false), [target, setTarget] = useState(0), [direction, setDirection] = useState<'up' | 'down'>('up');
    const [curve, setCurve] = useState<Curve | null>(null), [anchorBox, setAnchorBox] = useState<DOMRect | null>(null);
    const [insertAccidentalExplicit,setInsertAccidentalExplicit]=useState(false);
    const [equalBase,setEqualBase]=useState('1/2');
    const [tupletRatio,setTupletRatio]=useState('3:2');
    const [tupletBracket,setTupletBracket]=useState('yes'),[tupletPlacement,setTupletPlacement]=useState('above'),[tupletNumber,setTupletNumber]=useState('actual');
    const [measureChoice,setMeasureChoice]=useState('');
    const [manualOnset,setManualOnset]=useState('0'),[manualVoice,setManualVoice]=useState('1'),[manualStaff,setManualStaff]=useState('1');
    const [contextField,setContextField]=useState<'time'|'key'|'clef'|'staves'|'partial'|'barline'>('time');
    const [contextValue,setContextValue]=useState('4/4');
    const [lyricMoveTarget,setLyricMoveTarget]=useState('');
    const [lyricMoveVerse,setLyricMoveVerse]=useState('1');
    const [expression,setExpression]=useState('fermata:normal');
    const [groupIds, setGroupIds] = useState<string[]>([]), [insertPitch, setInsertPitch] = useState({ step: 'C', alter: '0', octave: 4 });
    const [editorBusy,setEditorBusy]=useState(false);
    const [homePrompt,setHomePrompt]=useState(false),[instrumentSaves,setInstrumentSaves]=useState<Record<string,SavedScore>>({});
    const initialFiles=useRef(new Map<string,File>());
    const [instrumentDirection,setInstrumentDirection]=useState<'up'|'down'>('down');
    const [instrumentDirections,setInstrumentDirections]=useState<Record<string,'up'|'down'>>({alto:'down',soprano:'up',tenor:'down'});
    const [stage, setStage] = useState(1), [outputs, setOutputs] = useState<Record<string, Review>>({}), [instrument, setInstrument] = useState<string | null>(null), [saveAs, setSaveAs] = useState(false), [name, setName] = useState(isSource ? file.name.replace(/\.[^.]+$/,'.musicxml') : file.name), [validation, setValidation] = useState(false), [draft, setDraft] = useState<Draft | null>(null), [textDraft, setTextDraft] = useState<{
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
    useEffect(()=>{
        if(!review?.id)return;
        let disposed=false,flight=false;
        const renew=async()=>{if(document.visibilityState!=='visible'||flight)return;flight=true;try{await keepReviewAlive(review.id);}catch(error){if(!disposed)setNotice(error instanceof Error?error.message:'Cannot keep the editing session open.');}finally{flight=false;}};
        const timer=window.setInterval(()=>void renew(),60000);
        const visible=()=>void renew();document.addEventListener('visibilitychange',visible);
        void renew();return()=>{disposed=true;window.clearInterval(timer);document.removeEventListener('visibilitychange',visible);};
    },[review?.id]);
    const [fitVersions,setFitVersions]=useState({source:0,working:0});
    const [voiceChoice, setVoiceChoice] = useState<{
        ids: string[];
        dy: number;
        box: DOMRect;
    } | null>(null);
    useEffect(()=>{setSelectedMark(null);},[review?.revision]);
    const workingViewport = useRef<HTMLDivElement>(null), sourceViewport = useRef<HTMLDivElement>(null), lyricInput = useRef<HTMLInputElement>(null);
    const draftLive = useRef<Draft | null>(null);
    draftLive.current = draft;
    const textLive = useRef<typeof textDraft>(null);
    textLive.current = textDraft;
    const all = review ? events(review) : [], event = all.find(e => e.id === selected), dirty = !!review && (saved?.xml??importBaseline?.xml) !== review.xml;
    const concertInput=saved??importBaseline;
    const concertRange=concertKeyRange([sourceKey.fifths,...(review?.score.parts.flatMap(p=>p.measures.flatMap(m=>m.key_signature.map(k=>Number(k.fifths))))??[])],sourceKey.fifths,target);
    const originalSuggestion=review?suggestOriginalKey(review.score.harmonies??[],review.score.parts[0]?.measures[0]?.id):null;
    useEffect(()=>{if(review)instrumentEditor?.onChange(review);},[review]); // Cache each written document, never the concert input.
    useEffect(()=>{instrumentEditor?.onBusy(busy || !!receipt || !!draft || !!textDraft || !!chordDraft);return ()=>instrumentEditor?.onBusy(false);},[busy,receipt,draft,textDraft,chordDraft]);
    const canGenerate = !!review && !!concertInput && !dirty && !implicitInitialKey;
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
    async function detect(r: Review) { setImplicitInitialKey(false); try {
        const k = await keyInfo(r.xml);
        setDetected(k);
        setSourceKey({ fifths: k.fifths, mode: k.mode ?? 'major' });
    }
    catch {
        const first = r.score.parts[0]?.measures[0]?.key_signature[0];
        const mode=first?.mode==='major'||first?.mode==='minor'?first.mode:null;setDetected({ fifths: Number(first?.fifths??0), mode });setImplicitInitialKey(!first);setSourceKey({fifths:Number(first?.fifths??0),mode:mode??'major'});
    } setConfirmed(false); }
    function accept(next: Review) { if (!review)
        return; if (next.xml === review.xml) {
        setReview(next);
        return;
    } setSourceCompared(false); setReview(next); setOutputs({}); setInstrumentSaves({}); setInstrument(null); setInsertion(null); }
    function allowConcertChange(){return !!instrumentEditor || !Object.keys(outputs).length || window.confirm("Changing the concert score clears the instrument workspaces. Save any instrument edits to local files before continuing. Continue?");}
    async function replace(xml: string) { if(!allowConcertChange())return; if(!review)return; const next = await correctDocument(review,xml); accept(next); setSelected(null); setPending(null); setCurve(null); setGroupIds([]); setDraft(null); await releaseExcept(next.id); await detect(next); }
    async function mutate(path: string, body?: unknown, method = 'POST', successMessage?: string) { if (!review)
        return; if(!allowConcertChange())return; const next = await edit(review, path, body, method); accept(next); if(successMessage)setNotice(successMessage); }
    useEffect(() => { let disposed = false; run(async () => { const recognized = isSource ? await recognizeSource(file,recognitionProfile) : null; const r = await remember(recognized?.review ?? await openXML(file)); if(recognized)setRecognitionWarnings(recognized.recognition.warnings); if (disposed) { await closeReview(r.id); sessions.current.delete(r.id); return; } setReview(r); setOriginal(instrumentEditor?.reference ?? r); if(!isSource&&!instrumentEditor)setImportBaseline({xml:r.xml,bytes:r.bytes,name:file.name,projection:r}); if(instrumentEditor?.saved?.xml===r.xml){setSaved({...instrumentEditor.saved,projection:r});setName(instrumentEditor.saved.name);} await detect(r); setNotice(isSource ? 'OMR draft ready. Compare with the original, correct notes, voices and lyrics, then save MusicXML.' : 'MusicXML opened. Editing is real; source remains unchanged until an explicit save.'); }); return () => { disposed = true; for (const id of sessions.current)
        void closeReview(id); }; }, [file]); // One review per opened document; no recognition call.
    useEffect(() => { lyricInput.current?.focus({preventScroll:true}); lyricInput.current?.select(); }, [draft?.event, draft?.verse]);
    function fit(pane: 'working' | 'source') { const el = (pane === 'working' ? workingViewport : sourceViewport).current; if (!el)
        return; (pane === 'working' ? setZoom : setSourceZoom)(1);setFitVersions(v=>({...v,[pane]:v[pane]+1})); el.scrollTop = 0; el.scrollLeft = 0;setNotice((pane==='source'?'Original Source':'Working Score')+' fitted to pane width. Scroll vertically to continue.'); }
    async function historyMove(redo = false) { if(!allowConcertChange())return; if (!review)
        return; if (redo ? !review.can_redo : !review.can_undo)
        return; const next = await edit(review,redo?'redo':'undo'); setSourceCompared(false); setReview(next); await releaseExcept(next.id); setSelected(null); setPending(null); setCurve(null); setInsertion(null); setGroupIds([]); setDraft(null); setOutputs({}); setInstrumentSaves({}); setInstrument(null); await detect(next); }
    function beginLyric(id: string, number = verse, box?: DOMRect, segment=0) { if (!review)
        return; const e = events(review).find(e => e.id === id); if (!e || e.kind !== 'note')
        return; const b = box ?? document.querySelector(`[data-testid="real-head-${id}"]`)?.getBoundingClientRect(); const l = review.score.lyrics.find(l => l.event_id === id && l.number === number); setSelected(id); setVerse(number); setDraft({ event: id, verse: number, text: l?.segments[segment] ?? '', segment, x: Math.max(8, Math.min(window.innerWidth - 210, b?.left ?? 180)), y: Math.max(8, Math.min(window.innerHeight - 130, (b?.bottom ?? 240) + 8)) }); }
    function placeLyricInput(ensureVisible=false){
        const current=draftLive.current,viewport=workingViewport.current;if(!current||!viewport)return;
        const node=viewport.querySelector<SVGGraphicsElement>('[data-testid="'+CSS.escape('real-lyric-'+current.event+'-'+current.verse)+'"]')??viewport.querySelector<SVGGraphicsElement>('[data-event-id="'+CSS.escape(current.event)+'"]');if(!node)return;
        let box=node.getBoundingClientRect();const frame=viewport.getBoundingClientRect();
        if(ensureVisible&&(box.top<frame.top+20||box.bottom>frame.bottom-20)){viewport.scrollTop+=box.top-frame.top-frame.height/2;box=node.getBoundingClientRect();}
        const x=Math.max(8,Math.min(window.innerWidth-225,box.left));
        const y=Math.max(76,Math.min(window.innerHeight-135,box.top-frame.top>115?box.top-110:box.bottom+8));
        setDraft(d=>d&&d.event===current.event&&d.verse===current.verse&&(Math.abs(d.x-x)>.5||Math.abs(d.y-y)>.5)?{...d,x,y}:d);
    }
    useEffect(()=>{if(!draft)return;const position=()=>placeLyricInput();window.addEventListener('scroll',position,true);window.addEventListener('resize',position);placeLyricInput(true);return()=>{window.removeEventListener('scroll',position,true);window.removeEventListener('resize',position);};},[draft?.event,draft?.verse]);
    async function commitText() {
        const current = textLive.current;
        if (!review || !current) return;
        textLive.current = null;
        setTextDraft(null);
        if (review.score.texts.find(t => t.id === current.id)?.text !== current.text)
            await mutate(`texts/${current.id}`, {text: current.text}, 'PATCH');
    }
    async function chooseLyricVerse(number:string){
        const current=draftLive.current;if(!current||number===current.verse)return;
        await commitLyric();
        const next=review?.score.lyrics.find(l=>l.event_id===current.event&&l.number===number);
        setVerse(number);setDraft({...current,verse:number,text:next?.segments[0]??'',segment:0});
    }
    async function commitLyric(move = 0) { const current = draftLive.current; if (!review || !current)
        return; const l = review.score.lyrics.find(l => l.event_id === current.event && l.number === current.verse); if (l) {
        if (current.text !== l.segments[current.segment])
            await mutate(`lyrics/${l.id}`, { text: current.text, segment_index:current.segment }, 'PATCH');
    }
    else if (current.text)
        await mutate(`events/${current.event}/lyrics`, { text: current.text, number: current.verse }); draftLive.current=null;setDraft(null);if (move) {
        const owner = all.find(e => e.id === current.event), targets = all.filter(e => e.kind === 'note' && e.voice === owner?.voice && e.staff === owner.staff && review.score.parts.some(p=>p.measures.some(m=>m.id===owner.measure_id)&&p.measures.some(m=>m.id===e.measure_id)));
        const index = targets.findIndex(e => e.id === current.event);
        if (targets[index + move])
            beginLyric(targets[index + move].id, current.verse);
    } }
    function select(id: string, dy = 0) {
        setHarmonyChoice(null);setObjectMenu(null);setToolsOpen(false);
        const head=workingViewport.current?.querySelector<SVGGraphicsElement>('[data-event-id="'+CSS.escape(id)+'"]');
        if(head)setContextBox(beside(head.getBoundingClientRect()));
        setNoteTools(tool==='Select'||tool==='Notes');

        setSelection([]);setBoxSelect(false);
        setSelectedText(null);setSelectedMark(null);
        if (!review || busy)
            return;
        const e = all.find(e => e.id === id);
        if (!e)
            return;
        setCurve(null);
        if(chordMode){setSelected(id);beginChord(e.measure_id,e.onset??'0',head?.getBoundingClientRect());return;}
        if (tool === 'Tie' || tool === 'Slur') {
            if (!pending) {
                setPending(id);
                setSelected(id);
                setNotice('Choose a later destination note in the same voice and staff.');
                return;
            }
            const source = all.find(e => e.id === pending);
            if (!source || e.kind !== 'note' || source.voice !== e.voice || source.staff !== e.staff || !review.score.parts.some(p=>p.measures.some(m=>m.id===source.measure_id)&&p.measures.some(m=>m.id===e.measure_id))) {
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
    function chooseTool(next: Tool) { setHarmonyChoice(null);setNoteTools(false);setObjectMenu(null);setChordMode(false); setBoxSelect(false); if(next==='Groups'&&selection.length){setGroupIds(selection);setTool(next);setPalette(true);return;} setSelection([]); if(next==='Rest')setSelected(null);setTool(next); setPalette(next === 'Notes' || next === 'Rest' || next === 'Groups'); setPending(next === 'Tie' || next === 'Slur' ? selected : null); if (next !== 'Lyrics')
        setDraft(null); if (next === 'Lyrics' && selected)
        beginLyric(selected); if (next === 'Groups')
        setGroupIds(selected ? [selected] : []); if (next === 'Text')
        setNotice('Click an existing score text to edit it inline.'); }
    async function duration(value: string, dot: boolean | number = false, preserveOnsets = true) { if (!review)
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
    } const written = dottedWritten(value, dot), effective = event.grace ? written : event.palette_duration_options[written]; if (!effective)
        throw Error('This written duration cannot be represented without changing the existing rhythmic structure.'); await mutate(`events/${event.id}`, { duration: effective, preserve_onsets: preserveOnsets }, 'PATCH'); setPalette(false);setNoteTools(true); }
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
    async function workTuplet(action:'apply'|'split'|'remove'){
        const ids=groupIds.length?groupIds:selected?[selected]:[];
        if(!ids.length)throw Error('Select a note, rest, chord or complete tuplet on the working score.');
        const [actual_notes,normal_notes]=tupletRatio.split(':').map(Number);
        await mutate('tuplets',{event_ids:ids,action,actual_notes,normal_notes,bracket:tupletBracket,placement:tupletPlacement,show_number:tupletNumber},'POST',action==='remove'?'Tuplet removed; written values restored.':'Tuplet applied. Edit each note or rest directly on the score.');
        setGroupIds([]);setSelected(null);setPalette(false);setTool('Select');
    }
    async function equalGroup() {
        const [actual_notes,normal_notes]=tupletRatio.split(':').map(Number);
        if(!review)return;
        if(insertion?.voice){
            await mutate('triplets',{...insertion,pattern:'equal',base_duration:equalBase,actual_notes,normal_notes,pitches:Array.from({length:actual_notes},()=>insertPitch)},'POST','Equal triplet applied to the working score.');
            setInsertion(null);
        } else {
            const selected=all.filter(e=>groupIds.includes(e.id));
            if(selected.length!==actual_notes || selected.some(e=>e.kind!=='note'||!e.pitch||e.voice!==selected[0].voice||e.staff!==selected[0].staff||e.measure_id!==selected[0].measure_id))throw Error(`Select ${actual_notes} consecutive single notes in one measure, voice and staff, or choose an empty gap.`);
            await mutate('triplets',{measure_id:selected[0].measure_id,voice:selected[0].voice,staff:selected[0].staff,pattern:'equal',base_duration:equalBase,actual_notes,normal_notes,event_ids:selected.map(e=>e.id)},'POST','Equal triplet applied to the selected notes.');
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
        return; setNoteTools(false); if(selectedMark){await mutate(`marks/${encodeURIComponent(selectedMark)}`,undefined,'DELETE','Selected score mark deleted. Notes unchanged.');setSelectedMark(null);return;} if(selectedText){const id=selectedText;await mutate(`texts/${id}`,undefined,'DELETE','Selected text deleted; notes and accidentals unchanged.');textLive.current=null;setTextDraft(null);setObjectMenu(null);setSelectedText(null);return;} if (curve) {
        if (curve.kind === 'tie')
            await mutate(`events/${curve.from}`, { tie_to_event_id: null }, 'PATCH');
        else
            await mutate('slurs', { source_event_id: curve.from, target_event_id: curve.to, remove: true });
        setCurve(null);
        return;
    } if(selection.length){await mutate('events/delete-selection',{event_ids:selection},'POST','Selected notes deleted. Undo restores the entire selection.');setSelection([]);setSelected(null);return;} if (!event)
        return; if (event.pitch)
        setInsertPitch(event.pitch); await mutate(`events/${event.id}/delete-preserve-timing`); setSelected(null); setDraft(null); }
    async function save(copy = false,declaredKey?:Key) { if (!review)
        return; if (!name.trim())
        throw Error('Choose a filename before saving.'); if(isSource && !sourceCompared)throw Error('Compare the corrected score with the original PDF/image and confirm comparison before saving.'); if (!review.validation.can_verify)
        throw Error('Correct technical XML errors before saving. Validate lists the specific errors.');if(!instrumentEditor&&implicitInitialKey&&!declaredKey){setSaveKeyPrompt({copy,fifths:'',mode:''});return;} const outputName = name.toLowerCase().endsWith('.musicxml') ? name : name + '.musicxml'; const chosen = await chooseLocal(outputName, handle.current, copy);let current=review;if(declaredKey){const corrected=await correctDocument(current,declareInitialKey(current.xml,declaredKey.fifths,declaredKey.mode));accept(corrected);current=corrected;if(isSource)setSourceCompared(true);await detect(corrected);setSaveKeyPrompt(null);} const verified = await edit(current, 'verify', { confirmed_source_comparison: true }); setReview(verified); const target = await writeLocal(verified.bytes, outputName, chosen); setSaveAs(false); if (target) {
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
    async function generate(id: string, requestedDirection = instrumentDirections[id]??'up') {
        if (!concertInput || !canGenerate) throw Error('Save the current Concert Score before generating instrument scores.');
        const key=variant(id,requestedDirection);if(instrument===id && requestedDirection===instrumentDirection)return;
        if (!outputs[key]) {
            const next=await openXML(xmlBlob(await saxXML(concertInput.xml,id,requestedDirection)));
            await closeReview(next.id);
            initialFiles.current.set(key,new File([next.bytes.slice().buffer],`${key}-${concertInput.name}`,{type:'application/xml'}));
            setOutputs(o=>({...o,[key]:next}));
        }
        else initialFiles.current.set(key,new File([outputs[key].bytes.slice().buffer],`${key}-${concertInput.name}`,{type:'application/xml'}));
        setInstrumentDirection(requestedDirection);setInstrumentDirections(current=>({...current,[id]:requestedDirection})); setInstrument(id); setNotice('');
    }
    useEffect(() => { const listener = (e: KeyboardEvent) => { if(concert&&e.key==='Escape'){e.preventDefault();closeConcert();return;} if (busy || receipt || homePrompt || (stage === 2) || (e.target as HTMLElement).closest('input,textarea,select,[role=dialog]'))
        return; if (e.key === 'Escape') {
        setPending(null);
        setInsertion(null);
        setTool('Select');
        setDraft(null);
    } if (stage === 1 && (e.ctrlKey || e.metaKey) && e.key === 'z') {
        e.preventDefault();
        void run(() => historyMove(e.shiftKey));
    } if ((e.key === 'Delete' || e.key === 'Backspace') && (selected || curve || selection.length || selectedText || selectedMark) && stage === 1) {
        e.preventDefault();
        void run(remove);
    } }; window.addEventListener('keydown', listener); return () => window.removeEventListener('keydown', listener); });
    useEffect(()=>{
        if(!instrumentEditor)return;
        instrumentEditor.onHistory?.({canEdit:!!review&&!busy&&!receipt,canExport:!!saved&&!busy&&!receipt,canUndo:!!review?.can_undo&&!busy&&!receipt,canRedo:!!review?.can_redo&&!busy&&!receipt,
            undo:()=>void run(()=>historyMove()),redo:()=>void run(()=>historyMove(true)),validate:()=>setValidation(v=>!v),save:()=>void run(()=>save()),saveAs:()=>setSaveAs(v=>!v),exportXML:()=>{if(saved)download(saved.bytes,saved.name);}});
        return()=>instrumentEditor.onHistory?.(null);
    },[review,busy,receipt,saved,name]);
    function recordSave(next: SavedScore) { setSaved(next); instrumentEditor?.onSave(next); }
    const unsavedInstruments = Object.keys(outputs).filter(key=>outputs[key].xml!==instrumentSaves[key]?.xml);
    function requestHome() {
        if(lock.current || busy || receipt || editorBusy || draftLive.current || textLive.current) return;
        if(dirty || unsavedInstruments.length) { setHomePrompt(true); return; }
        onExit();
    }
    function discardAndHome(){
        if(lock.current||busy||editorBusy||receipt||draftLive.current||textLive.current)return;
        setHomePrompt(false);
        onExit();
    }
    function openToSave(key: string) {
        setHomePrompt(false);
        if(key==='concert') { setStage(1); setNotice('Save the Concert Score, then choose Home.'); return; }
        const [id,direction]=key.split('-');
        setStage(2);
        void run(async()=>{await generate(id,direction as 'up'|'down');setNotice('Save this instrument score, then choose Home.');});
    }
    const currentKey = implicitInitialKey ? 'No sharps/flats initially · key/mode unconfirmed' : detected ? `${(detected.mode === 'minor' ? minors : majors)[detected.fifths + 7]}${detected.mode ? ' ' + detected.mode : ' · mode unconfirmed'}` : 'Key unavailable';
    return <><input ref={input} className="file-input" type="file" accept=".musicxml,.xml" onChange={e => { const f = e.target.files?.[0]; e.target.value = ''; if (!f)
        return; if ((dirty || Object.keys(outputs).length) && !window.confirm('Leave this score and discard any changes not saved to a local file, including instrument edits?'))
        return; void run(async () => { const next = await remember(await openXML(f)); setReview(next); setOriginal(next);setOpenedXML(f);if(!instrumentEditor)setImportBaseline({xml:next.xml,bytes:next.bytes,name:f.name,projection:next});setRecognitionWarnings([]);setNoteTools(false);setToolsOpen(false);setObjectMenu(null); setSaved(null); handle.current = null; setName(f.name); setOutputs({}); setInstrumentSaves({}); initialFiles.current.clear(); setSelected(null); setPending(null); setCurve(null); setInsertion(null); setTextDraft(null); setGroupIds([]); setDraft(null); setTool('Select'); setStage(1); await releaseExcept(next.id); await detect(next); }); }}/>
 <fieldset className={"real-workspace"+(instrumentEditor ? " instrument-editor" : "")} disabled={busy || !!receipt || homePrompt}>
 <header className={instrumentEditor ? "instrument-editor-header" : "app-header"}><div className="workspace-brand">{!instrumentEditor && <nav aria-label="Main navigation" className="home-navigation"><button disabled={editorBusy || !!draft || !!textDraft || !!chordDraft} onClick={requestHome}><svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M3 10 12 3l9 7M5 9v12h5v-7h4v7h5V9"/></svg><span>Home</span></button></nav>}<div className="brand"><strong>Music Sheet Transposer</strong><small>MusicXML workspace · real editing</small></div></div><nav className="header-actions">{!instrumentEditor && <><button ref={concertButton} aria-expanded={concert} aria-controls="concert-key-panel" disabled={!review || stage !== 1} onClick={() => setConcert(!concert)}>Concert Key</button><button disabled={editorBusy} onClick={() => input.current?.click()}>Open MusicXML</button></>}<button disabled={stage===2?!instrumentHistory?.canEdit||editorBusy:!review} onClick={() => {if(stage===2)instrumentHistory?.validate();else setValidation(!validation);}}>Validate</button><button disabled={stage===2?!instrumentHistory?.canUndo||editorBusy:!review?.can_undo} onClick={() => {if(stage===2)instrumentHistory?.undo();else void run(() => historyMove());}}>↶ Undo</button><button disabled={stage===2?!instrumentHistory?.canRedo||editorBusy:!review?.can_redo} onClick={() => {if(stage===2)instrumentHistory?.redo();else void run(() => historyMove(true));}}>↷ Redo</button><button disabled={stage===2?!instrumentHistory?.canEdit||editorBusy:!review} className="primary" onClick={() => {if(stage===2)instrumentHistory?.save();else void run(() => save());}}>Save</button><button disabled={stage===2?!instrumentHistory?.canEdit||editorBusy:!review} onClick={() => {if(stage===2)instrumentHistory?.saveAs();else setSaveAs(!saveAs);}}>Save As</button><button disabled={stage===2?!instrumentHistory?.canExport||editorBusy:!saved} onClick={() => { if(stage===2){instrumentHistory?.exportXML();return;} if (saved) {
        download(saved.bytes, saved.name);
        setNotice(dirty ? 'Exported the prior saved concert file; unsaved edits excluded.' : 'Exported saved Concert MusicXML.');
    } }}>Export saved MusicXML</button><button disabled={!review || editorBusy} hidden={!!instrumentEditor} onClick={() => { setSaveAs(false); setConcert(false); setPalette(false); setPending(null); setInsertion(null); setVoiceChoice(null); setStage(stage === 1 ? 2 : 1); }}>{stage === 1 ? 'Instrument Scores →' : '← Concert Score'}</button>{stage === 1 && <button disabled={!review} onClick={()=>void run(async()=>{if(review&&await exportScorePDF(review,name))setNotice('Working score exported as PDF.');})}>Export PDF</button>}</nav></header>
 {saveKeyPrompt&&<section className="real-save-popover" role="dialog" aria-label="Confirm original Concert key"><strong>Choose the original key before saving</strong><p>The score has no initial key declaration. Choose its original key; this does not transpose notes.</p>{originalSuggestion&&<div><p>Suggested key: {originalSuggestion.tonic} {originalSuggestion.mode==='minor'?'minor':'major'} — based on the first chord {originalSuggestion.chord}. Choose the key that matches the original score.</p><button onClick={()=>setSaveKeyPrompt({...saveKeyPrompt,fifths:String(originalSuggestion.fifths),mode:originalSuggestion.mode})}>Use suggestion</button></div>}<label>Major / Minor<select aria-label="Original key mode" value={saveKeyPrompt.mode} onChange={e=>setSaveKeyPrompt({...saveKeyPrompt,mode:e.target.value as 'major'|'minor',fifths:''})}><option value="">Choose</option><option value="major">Major</option><option value="minor">Minor</option></select></label><label>Original key<select aria-label="Original Concert key" disabled={!saveKeyPrompt.mode} value={saveKeyPrompt.fifths} onChange={e=>setSaveKeyPrompt({...saveKeyPrompt,fifths:e.target.value})}><option value="">Choose</option>{(saveKeyPrompt.mode==='minor'?minors:majors).map((key,i)=><option key={i} value={String(i-7)}>{key}</option>)}</select></label><button disabled={!saveKeyPrompt.mode||saveKeyPrompt.fifths===''} onClick={()=>{const choice=saveKeyPrompt;if(choice.mode&&choice.fifths!=='')void run(()=>save(choice.copy,{fifths:Number(choice.fifths),mode:choice.mode as 'major'|'minor'}));}}>Confirm and save MusicXML</button><button onClick={()=>setSaveKeyPrompt(null)}>Cancel</button></section>}
 {saveAs && <div className="real-save-popover"><label>Filename<input value={name} onChange={e => setName(e.target.value)}/></label><button onClick={() => void run(() => save(true))}>Save Copy</button><button onClick={() => setSaveAs(false)}>Cancel</button></div>}
 {!review ? <main><h2>{isSource?'Recognize source':'Open MusicXML'}</h2><p role="status">{busy && isSource?'Recognition in progress. No score is final until you compare and correct it.':notice}</p>{isSource&&!busy&&<button onClick={()=>void run(async()=>{const next=await remember(await manualSource(file));setReview(next);setOriginal(next);setName(file.name.replace(/\.[^.]+$/,'.musicxml'));setRecognitionWarnings([{message:'Manual reconstruction explicitly selected. No recognized notes have been supplied. Set meter/key and add the source notes yourself.'}]);await detect(next);setNotice('Empty working score created by your choice. Reconstruct the notes from the original source, then save MusicXML.');})}>Create empty working score from this source</button>}</main> : stage === 1 ? <div className="shell"><aside className="rail"><strong>EDIT</strong>{<button aria-label="Add measure" onClick={()=>void run(async()=>{if(review)await replace(appendMeasure(review));})}><svg aria-hidden="true" width="27" height="29" viewBox="0 0 30 32" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M4 8h15v18H4zM4 14h15M4 20h15M24 3v12M18 9h12"/></svg><span>Add measure</span></button>}<button aria-label="Select note area" aria-pressed={boxSelect} onClick={()=>{setNoteTools(false);setToolsOpen(false);setObjectMenu(null);setBoxSelect(v=>!v);setTool('Select');setPalette(false);setNotice('Drag a rectangle around notes in Working Score, then Delete or Groups.');}}>▧<span>Select area</span></button><details className="dot-tools" open><summary>Dots</summary><div role="group" aria-label="Augmentation dots"><button aria-label="Correct missing quarter-note dot" title="Restore an omitted dot: add half a beat to this note/chord and advance following events in this measure" disabled={!event||event.grace||event.notated_duration?.type!=='quarter'||!!event.notated_duration?.dots} onClick={()=>void run(()=>duration('1',1,false))}><span className="tool-icon">♩·</span><span>Missing dot +½</span></button><button aria-label="Toggle augmentation dot" title="Augmentation dot: duration × 1.5; not staccato" disabled={!event} aria-pressed={event?.notated_duration?.dots===1} onClick={()=>void run(()=>duration(({whole:'4',half:'2',quarter:'1',eighth:'1/2','16th':'1/4','32nd':'1/8','64th':'1/16'}[event?.notated_duration?.type??'quarter']??'1'),event?.notated_duration?.dots===1?0:1))}><span className="tool-icon">♩·</span><span>Dot</span></button><button aria-label="Toggle double augmentation dot" title="Double augmentation dot: duration × 1.75" disabled={!event} aria-pressed={event?.notated_duration?.dots===2} onClick={()=>void run(()=>duration(({whole:'4',half:'2',quarter:'1',eighth:'1/2','16th':'1/4','32nd':'1/8','64th':'1/16'}[event?.notated_duration?.type??'quarter']??'1'),event?.notated_duration?.dots===2?0:2))}><span className="tool-icon">♩··</span><span>Double dot</span></button></div></details><button aria-label="Add Chord" aria-pressed={chordMode} onClick={()=>{setChordMode(v=>!v);setPalette(false);setToolsOpen(false);setNoteTools(false);setNotice('Click the desired position in Working Score to write a chord.');}}>G<span>Add Chord</span></button><button aria-label="More tools" onClick={()=>{setToolsOpen(v=>!v);setNoteTools(false);}}>⋯<span>More</span></button>{(['Select', 'Notes', 'Rest', 'Tie', 'Slur', 'Groups', 'Lyrics', 'Text'] as Tool[]).map(t => <div className="rail-slot" key={t}><button aria-label={t} className={tool === t ? 'active' : ''} onClick={() => chooseTool(t)}>{['Notes', 'Rest', 'Tie', 'Slur', 'Groups'].includes(t) ? <MusicIcon kind={t === 'Notes' ? 'Quarter' : t}/> : <span className="tool-icon">{t === 'Lyrics' ? 'Aa' : t === 'Text' ? 'T' : '↖'}</span>}<span>{t}</span></button>{palette && tool === t && <div className={"rail-palette"+(t === "Groups" ? " groups-palette" : "")}>{t === 'Notes' || t==='Rest' ? lengths.map(v => <button key={v.value} aria-label={v.name + (t==='Rest'?' rest':' note')} onClick={() => void run(() => duration(v.value))}><MusicIcon kind={t==='Rest'?v.name+' rest':v.name}/>{v.name}{t==='Rest'?' rest':''}</button>) : <><p>Choose a ratio, then divide one duration or apply it to a written selection. Each resulting pitch remains editable.</p><p>{groupIds.length} selected notes</p><label>Tuplet ratio<select aria-label="Tuplet ratio" value={tupletRatio} onChange={e=>setTupletRatio(e.target.value)}>{['3:2','2:3','4:3','5:4','6:4','7:4','8:6','9:8'].map(r=><option key={r}>{r}</option>)}</select></label><p role="status" aria-label="Selected tuplet ratio explanation">{tupletRatio}: {tupletRatio.split(':')[0]} written units in the time of {tupletRatio.split(':')[1]}. Select one note/rest to divide its full duration, or complete rhythmic positions to apply this ratio.</p><button aria-label="Divide selected duration" onClick={()=>void run(()=>workTuplet('split'))}>Divide duration · {tupletRatio}</button><button aria-label="Apply to written selection" onClick={()=>void run(()=>workTuplet('apply'))}>Apply to selection · {tupletRatio}</button><button onClick={()=>void run(()=>workTuplet('remove'))}>Remove selected tuplet</button><details><summary>Tuplet appearance</summary><label>Bracket<select aria-label="Tuplet bracket" value={tupletBracket} onChange={e=>setTupletBracket(e.target.value)}><option value="yes">Show</option><option value="no">Hide</option></select></label><label>Position<select aria-label="Tuplet placement" value={tupletPlacement} onChange={e=>setTupletPlacement(e.target.value)}><option value="above">Above</option><option value="below">Below</option></select></label><label>Number<select aria-label="Tuplet number" value={tupletNumber} onChange={e=>setTupletNumber(e.target.value)}><option value="actual">Number</option><option value="both">Ratio</option><option value="none">Hide</option></select></label></details><label className="equal-triplet-value">Equal tuplet note value<select aria-label="Equal triplet note value" value={equalBase} onChange={e=>setEqualBase(e.target.value)}>{lengths.map(v=><option key={v.value} value={v.value}>{v.name}</option>)}</select></label><p>Fixed mixed rhythm and beam tools (independent of the ratio above)</p><button aria-label="♩♪ 3:2" onClick={() => void run(mixedGroup)}>Mixed quarter + eighth · 3:2</button><button disabled={groupIds.length!==Number(tupletRatio.split(':')[0])&&!insertion?.voice} onClick={()=>void run(equalGroup)}>{tupletRatio==='3:2'?'3 equal notes 3:2':'Apply equal tuplet '+tupletRatio}</button>{[2, 3, 4, 5, 6, 8].map(n => <button disabled={groupIds.length !== n} key={n} onClick={() => void run(async () => { await replace(beamSelected(review, groupIds, n)); setGroupIds([]); setPalette(false); setTool('Select'); })}>Beam {n}</button>)}</>}<button onClick={() => setPalette(false)}>Close palette</button></div>}</div>)}<button aria-label="Delete" onPointerDown={e=>{if(selectedText)e.preventDefault();}} onClick={() => void run(remove)}>⌫<span>Delete</span></button></aside>
 <main>{isSource && <section className="omr-review"><strong>OMR draft · manual correction required</strong><label><input type="checkbox" checked={sourceCompared} onChange={e=>setSourceCompared(e.target.checked)}/>I compared this revision with the original source, including voices and verses.</label></section>}<section className="workspace-heading"><div><span className="phase">{instrumentEditor ? "STAGE 2" : "STAGE 1"}</span><strong>{instrumentEditor?.label ?? "Compare & correct"}</strong></div><span className={'save-state ' + (dirty ? 'dirty' : '')}>{!saved ? (importBaseline&&!dirty?'Imported MusicXML · unchanged':'Not yet saved locally') : dirty ? 'Unsaved changes' : instrumentEditor ? 'Instrument file saved' : 'Concert file saved'}</span></section>
 {concert && <section id="concert-key-panel" className="concert-panel"><div className="concert-panel-heading"><strong>Concert Key</strong><button type="button" aria-label="Close Concert Key" title="Close (Esc)" onClick={closeConcert}>×</button></div><p>Confirm the source key; changing the concert key transposes the actual score.</p><label>Source key<select aria-label="Source key" value={sourceKey.fifths} onChange={e => { setSourceKey(k => ({ ...k, fifths: Number(e.target.value) })); setConfirmed(false); }}>{majors.map((k, i) => <option value={i - 7} key={i}>{sourceKey.mode === 'minor' ? minors[i] : k}</option>)}</select></label><label>Mode<select aria-label="Mode" value={sourceKey.mode} onChange={e => { setSourceKey(k => ({ ...k, mode: e.target.value as Key['mode'] })); setConfirmed(false); }}><option value="major">Major</option><option value="minor">Minor</option></select></label><label><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)}/>Confirm source key: {keyName(sourceKey)}</label><label>New concert key<select aria-label="New concert key" value={target} onChange={e => setTarget(Number(e.target.value))}>{majors.map((k, i) => <option value={i - 7} key={i}>{sourceKey.mode === 'minor' ? minors[i] : k}</option>)}</select></label><label>Direction<select aria-label="Direction" value={direction} onChange={e => setDirection(e.target.value as 'up' | 'down')}><option value="up">Up</option><option value="down">Down</option></select></label><button onClick={() => setConcert(false)}>Keep Original</button>{target===sourceKey.fifths&&<p role="status">{direction==='down'?'Keep the key and lower all notes by one octave (−12 semitones).':'Same key + Up keeps the current pitches. Choose Down to lower one octave.'}</p>}{confirmed&&!concertRange.supported&&<div role="status"><p>This target puts a key change outside seven sharps or flats.</p>{concertRange.alternative!==null?<><p>You can use {keyName({fifths:concertRange.alternative,mode:sourceKey.mode})}: equivalent pitch to the selected key, with supported notation in every section.</p><button onClick={()=>setTarget(concertRange.alternative!)}>Use equivalent key {keyName({fifths:concertRange.alternative,mode:sourceKey.mode})}</button></>:<p>Choose another target key within the supported key signature range.</p>}</div>}<button disabled={!confirmed||!concertRange.supported} onClick={() => void run(transpose)}>Apply concert key</button></section>}
 <div className="compare-toolbar"><div><button className={compare ? 'active' : ''} onClick={() => setCompare(true)}>Compare</button><button className={!compare ? 'active' : ''} onClick={() => setCompare(false)}>Edit Only</button></div><small>{isSource?"Original PDF/image is read-only · independent zoom and scroll":"Original XML is read-only · independent zoom and scroll"}</small></div>
 <div className="score-tool-popover" hidden={!toolsOpen} role="region" aria-label="Additional score tools"><button className="close-score-tools" aria-label="Close additional score tools" onClick={()=>setToolsOpen(false)}>×</button><details className="score-structure"><summary>Select OCR text or score mark to delete</summary><label>Score object<select aria-label="Select OCR object" value={selectedMark?'mark:'+selectedMark:selectedText?'text:'+selectedText:''} onChange={e=>{const value=e.target.value;if(value.startsWith('mark:')){setSelectedMark(value.slice(5));setSelectedText(null);}else{setSelectedText(value.slice(5)||null);setSelectedMark(null);}setSelected(null);setCurve(null);}}><option value="">Choose object</option>{review.score.texts.filter(t=>t.role==='direction').map(t=><option key={t.id} value={'text:'+t.id}>Text: {t.text}</option>)}{review.score.omr_marks?.map(m=><option key={m.id} value={'mark:'+m.id}>{m.kind} {m.type} · {m.measure_id} · staff {m.staff}</option>)}</select></label><button disabled={!selectedText&&!selectedMark} onPointerDown={e=>e.preventDefault()} onClick={()=>void run(remove)}>Delete selected OCR object</button><p>Original PDF and note pitches remain unchanged. Undo restores a deleted object.</p></details><HarmonyEditor position={chordPosition} editingId={chordEditId} review={review} selected={selected} onCommand={async(path,body,method)=>{await run(()=>mutate(path,body,method));}}/><LyricsRepair review={review} onApply={async(id,mappings,remove_source)=>{let success=false;await run(async()=>{await mutate(`texts/${id}/to-lyrics`,{mappings,remove_source},'POST','Text converted to lyrics using your confirmed note and verse assignments. No pitches were changed.');success=true;});return success;}}/><details className="score-structure"><summary>Measure, meter, key signature and staff correction</summary><label>Measure<select aria-label="Correction measure" value={measureChoice} onChange={e=>setMeasureChoice(e.target.value)}><option value="">Choose measure</option>{review.score.parts.flatMap(p=>p.measures.map(m=><option key={m.id} value={m.id}>{p.name} · {m.number}</option>))}</select></label><label>Property<select aria-label="Measure correction property" value={contextField} onChange={e=>{const field=e.target.value as typeof contextField;setContextField(field);setContextValue({time:'4/4',key:'0',clef:'G:2',staves:'1',partial:'yes',barline:'regular'}[field]);}}><option value="time">Time signature</option><option value="key">Key signature (no transposition)</option><option value="clef">Clef (selected staff)</option><option value="staves">Staff count</option><option value="partial">Pickup/partial (yes/no)</option><option value="barline">Right barline style</option></select></label><label>Value<input aria-label="Measure correction value" value={contextValue} onChange={e=>setContextValue(e.target.value)}/></label><button disabled={!measureChoice} onClick={()=>void run(async()=>{await replace(measureContext(review,measureChoice,contextField,contextValue,event?.staff??1));setToolsOpen(false);})}>Apply measure correction</button><fieldset><legend>Insert missing content at an explicit position</legend><label>Onset in quarter beats<input aria-label="Manual insertion onset" value={manualOnset} onChange={e=>setManualOnset(e.target.value)}/></label><label>Voice<input aria-label="Manual insertion voice" value={manualVoice} onChange={e=>setManualVoice(e.target.value)}/></label><label>Staff<input aria-label="Manual insertion staff" value={manualStaff} onChange={e=>setManualStaff(e.target.value)}/></label><button disabled={!measureChoice} onClick={()=>{const staff=Number(manualStaff),m=review.score.parts.flatMap(p=>p.measures).find(m=>m.id===measureChoice);if(!m||!manualVoice.trim()||!/^(?:0|[1-9]\d*)(?:\/[1-9]\d*)?$/.test(manualOnset)||!Number.isInteger(staff)||staff<1||staff>((m as {staves?:number}).staves??1)){setNotice('Choose a valid measure, nonnegative rational onset, voice and declared staff.');return;}setInsertion({measure_id:measureChoice,onset:manualOnset,voice:manualVoice.trim(),staff});setTool('Notes');setPalette(true);setToolsOpen(false);setNoteTools(true);}}>Choose this insertion position</button></fieldset><p>Explicit correction only. Existing notes and later context changes remain unchanged. Clef examples: G:2, F:4, C:3. Barline: regular, light-light, light-heavy.</p></details></div><div className={'compare-layout ' + (!compare ? 'edit-only' : '')} style={compare ? { gridTemplateColumns: `minmax(0,${split}fr) 10px minmax(0,${100 - split}fr)` } : undefined}>
 {compare && original && <><section className="source-pane"><div className="pane-heading"><strong>{instrumentEditor ? "Concert input · read-only" : "Original Source"}</strong><span className="tag">{isSource?"Read-only original PDF/image":"Read-only MusicXML"}</span></div><div className="source-tools"><span>{instrumentEditor?.referenceName ?? (openedXML??file).name}</span><div><button aria-label="Fit source score" onClick={() => fit('source')}>Fit</button><button aria-label="Source zoom out" onClick={() => setSourceZoom(z => Math.max(.25, z - .1))}>−</button><output>{Math.round(sourceZoom * 100)}%</output><button aria-label="Source zoom in" onClick={() => setSourceZoom(z => Math.min(2, z + .1))}>+</button></div></div><div ref={sourceViewport} className="score-viewport source-scroll">{isSource ? /\.pdf$/i.test(file.name) ? <PDFSource file={file} zoom={sourceZoom}/> : <img alt="Original source score" src={sourceURL} style={{width:Math.round(sourceZoom*100)+'%',maxWidth:'none'}}/> : <RenderedScore review={original} readOnly zoom={sourceZoom} fitVersion={fitVersions.source}/>}</div><p className="pane-foot">{isSource?"Original source is unchanged. Compare pages manually; no automatic note-to-image alignment is claimed.":"Original MusicXML reference · no OMR or image alignment."}</p></section><div className="splitter" role="separator" aria-label="Resize source and working score" aria-orientation="vertical" aria-valuenow={split} tabIndex={0} onPointerDown={e => e.currentTarget.setPointerCapture(e.pointerId)} onPointerMove={e => { if (e.buttons) {
            const b = e.currentTarget.parentElement!.getBoundingClientRect();
            setSplit(Math.max(25, Math.min(70, (e.clientX - b.left) / b.width * 100)));
        } }} onKeyDown={e => { if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
            e.preventDefault();
            setSplit(s => Math.max(25, Math.min(70, s + (e.key === 'ArrowLeft' ? -2 : 2))));
        } }}>⋮</div></>}
 <section className="working-pane"><div className="pane-heading"><strong>Working Score</strong><span className="tag editable">Real MusicXML</span><span className="tag" data-testid="real-concert-key">{instrumentEditor ? "Written key:" : "Concert key:"} {currentKey}</span><div className="zoom"><button aria-label="Fit working score" onClick={() => fit('working')}>Fit</button><button aria-label="Working score zoom out" onClick={() => setZoom(z => Math.max(.25, z - .1))}>−</button><output>{Math.round(zoom * 100)}%</output><button aria-label="Working score zoom in" onClick={() => setZoom(z => Math.min(2, z + .1))}>+</button></div></div>
 <div className="score-note-popover" hidden={!noteTools} style={{left:contextBox.x,top:contextBox.y}} role="region" aria-label="Selected note tools"><button aria-label="Close selected note tools" onClick={()=>setNoteTools(false)}>×</button><div className="note-context">{event ? <><span>Voice {event.voice} · measure {review.score.parts.flatMap(p => p.measures).find(m => m.id === event.measure_id)?.number}</span><label>Duration<select aria-label="Selected note duration" value={lengths.find(v=>v.name.toLowerCase()===event.notated_duration?.type)?.value??({'16th':'1/4','32nd':'1/8','64th':'1/16'}[event.notated_duration?.type??'']??'1')} onChange={e=>void run(()=>duration(e.target.value,false,false))}>{lengths.map(v=><option key={v.value} value={v.value}>{v.name}</option>)}</select></label>{event.pitch && <><label>Pitch<select aria-label="Selected note pitch" value={event.pitch.step} onChange={e=>void run(()=>changePitch({step:e.target.value}))}>{[..."CDEFGAB"].map(step=><option key={step}>{step}</option>)}</select></label><label>Octave<select aria-label="Selected note octave" value={event.pitch.octave} onChange={e=>void run(()=>changePitch({octave:Number(e.target.value)}))}>{Array.from({length:10},(_,i)=><option key={i} value={i}>{i}</option>)}</select></label></>}{event.pitch && <div className="accidental-buttons" role="group" aria-label="Note accidentals">{[['flat-flat','-2','Double flat','♭♭'],['flat','-1','Flat','♭'],['natural','0','Natural','♮'],['sharp','1','Sharp','♯'],['double-sharp','2','Double sharp','×']].map(([written,alter,label,symbol])=><button key={written} aria-label={label+' accidental'} title={label} aria-pressed={event.accidental?.text===written} className={event.accidental?.text===written?'active':''} onClick={()=>void run(()=>applyAccidental(written,alter))}><span aria-hidden="true">{symbol}</span></button>)}</div>}<label>Voice<input aria-label="Selected event voice" key={event.id+event.voice} defaultValue={event.voice} size={3} onBlur={e=>{const voice=e.target.value.trim();if(voice && voice!==event.voice)void run(()=>mutate(`events/${event.id}`,{voice},'PATCH'));}}/></label><label>Staff<select aria-label="Selected event staff" value={event.staff} onChange={e=>void run(()=>mutate(`events/${event.id}`,{staff:Number(e.target.value)},'PATCH'))}>{Array.from({length:(review.score.parts.flatMap(p=>p.measures).find(m=>m.id===event.measure_id) as {staves?:number})?.staves??event.staff},(_,i)=><option key={i+1}>{i+1}</option>)}</select></label><button onClick={() => void run(() => duration(({ whole: '4', half: '2', quarter: '1', eighth: '1/2', '16th': '1/4', '32nd':'1/8', '64th':'1/16' }[event.notated_duration?.type ?? 'quarter'] ?? '1'), !event.notated_duration?.dots))}>Dot</button><button aria-label="Double dot" onClick={()=>void run(()=>duration(({whole:'4',half:'2',quarter:'1',eighth:'1/2','16th':'1/4','32nd':'1/8','64th':'1/16'}[event.notated_duration?.type??'quarter']??'1'),event.notated_duration?.dots===2?0:2))}>Double dot</button>{event.pitch && <><button aria-pressed={event.display_size==='normal'} title="Normal display size; timing unchanged" onClick={() => void run(() => mutate(`events/${event.id}`, { display_size: 'normal' }, 'PATCH','Normal note size applied.'))}>Normal</button><button aria-pressed={event.display_size==='small'} title="Small display size; pitch and duration unchanged" onClick={() => void run(() => mutate(`events/${event.id}`, { display_size: 'small' }, 'PATCH','Small note applied. Pitch and duration unchanged.'))}>Small</button><button aria-label="Add grace note before" onClick={()=>void run(()=>mutate('events',{measure_id:event.measure_id,before_event_id:event.id,voice:event.voice,staff:event.staff,kind:'note',pitch:event.pitch,duration:'1/2',grace:true,grace_slash:false}))}>Grace before</button><button aria-label="Add slashed grace note before" onClick={()=>void run(()=>mutate('events',{measure_id:event.measure_id,before_event_id:event.id,voice:event.voice,staff:event.staff,kind:'note',pitch:event.pitch,duration:'1/2',grace:true,grace_slash:true}))}>Slashed grace</button><button onClick={() => beginLyric(event.id)}>Edit lyrics</button><button onClick={() => beginLyric(event.id, String(Math.max(0, ...review.score.lyrics.filter(l => l.event_id === event.id).map(l => Number(l.number) || 0)) + 1))}>Add Verse</button></>}
            <button onClick={() => void run(remove)}>Delete selected</button></> : <span>{curve ? `${curve.kind} selected · drag up/down or Delete` : 'Select a notehead to edit; choose Notes or Rest, then click the staff to insert.'}</span>}</div>
 {event && <div className="note-context"><label>Expression<select aria-label="Selected note expression" value={expression} onChange={e=>setExpression(e.target.value)}>{[['fermata:normal','Fermata'],['articulation:staccato','Staccato'],['articulation:tenuto','Tenuto'],['articulation:accent','Accent'],['articulation:strong-accent','Strong accent'],['articulation:staccatissimo','Staccatissimo'],['articulation:breath-mark','Breath mark'],...['ppp','pp','p','mp','mf','f','ff','fff','sfz'].map(d=>['dynamic:'+d,d])].map(([v,label])=><option key={v} value={v}>{label}</option>)}</select></label><button onClick={()=>void run(()=>mutate(`events/${event.id}/notation`,{field:expression.split(':')[0],value:expression.split(':')[1]}))}>Add expression</button><button onClick={()=>void run(()=>mutate(`events/${event.id}/notation`,{field:expression.split(':')[0],value:expression.split(':')[1],remove:true}))}>Remove expression</button></div>}
 {event && <div className="note-context"><label>Verse<select value={verse} onChange={e => setVerse(e.target.value)}>{Array.from({ length: Math.max(1, ...review.score.lyrics.map(l => Number(l.number) || 1)) }, (_, i) => <option key={i}>{i + 1}</option>)}</select></label><button onClick={() => beginLyric(event.id)}>Edit selected lyric</button><button onClick={() => void run(async () => { const l = review.score.lyrics.find(l => l.event_id === event.id && l.number === verse); if (l)
            await mutate(`lyrics/${l.id}`, undefined, 'DELETE'); })}>Delete syllable</button></div>}
 {event && review.score.lyrics.filter(l=>l.event_id===event.id&&l.number===verse&&l.segments.length>1).map(l=><div className="note-context" key={l.id}>Lyric segments: {l.segments.map((text,i)=><button key={i} onClick={()=>beginLyric(event.id,verse,undefined,i)}>Edit segment {i+1}: {text}</button>)}</div>)}
 {event && review.score.lyrics.some(l=>l.event_id===event.id&&l.number===verse) && <div className="note-context"><label>Move lyric to note<select aria-label="Lyric destination note" value={lyricMoveTarget} onChange={e=>setLyricMoveTarget(e.target.value)}><option value="">Choose note</option>{all.filter(e=>e.kind==='note').map(e=><option key={e.id} value={e.id}>{e.id} · Voice {e.voice} · Staff {e.staff} · {e.pitch?.step}{e.pitch?.octave}</option>)}</select></label><label>Destination verse<input aria-label="Lyric destination verse" size={3} value={lyricMoveVerse} onChange={e=>setLyricMoveVerse(e.target.value)}/></label><button disabled={!lyricMoveTarget||!lyricMoveVerse.trim()} onClick={()=>void run(async()=>{const lyric=review.score.lyrics.find(l=>l.event_id===event.id&&l.number===verse);if(lyric)await mutate(`lyrics/${lyric.id}/move`,{source_event_id:event.id,destination_event_id:lyricMoveTarget,number:lyricMoveVerse});setLyricMoveTarget('');})}>Move lyric</button></div>}
 {insertion && insertion.voice && <div className="note-context"><strong>Insert at beat {rational(insertion.onset) + 1}</strong><label>Pitch<select value={insertPitch.step} onChange={e => setInsertPitch(p => ({ ...p, step: e.target.value,alter:insertAccidentalExplicit?p.alter:keyAlter(e.target.value,insertion.measure_id) }))}>{[..."CDEFGAB"].map(p => <option key={p}>{p}</option>)}</select></label><label>Accidental<select aria-label="Insertion accidental" value={insertPitch.alter} onChange={e => {setInsertAccidentalExplicit(true);setInsertPitch(p => ({ ...p, alter: e.target.value }));}}>{[["-2", "Double flat"], ["-1", "Flat"], ["0", "Natural"], ["1", "Sharp"], ["2", "Double sharp"]].map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label>Octave<input type="number" min="0" max="9" value={insertPitch.octave} onChange={e => setInsertPitch(p => ({ ...p, octave: Number(e.target.value) }))}/></label><label>Voice<select value={insertion.voice} onChange={e => setInsertion({ ...insertion, voice: e.target.value })}>{[...new Set(all.map(e => e.voice))].map(v => <option key={v}>{v}</option>)}</select></label><button onClick={() => setTool(tool === 'Rest' ? 'Notes' : 'Rest')}>{tool === 'Rest' ? 'Insert note' : 'Insert rest'}</button><button onClick={() => setInsertion(null)}>Cancel</button></div>}
 </div><div ref={workingViewport} className="score-viewport working-scroll"><RenderedScore onStaffContext={(measure,box)=>{setMeasureChoice(measure);const m=review.score.parts.flatMap(p=>p.measures).find(m=>m.id===measure);setContextField('time');setContextValue(m?.time_signature[0]?.pairs.map(p=>p.beats+'/'+p.beat_type).join('+')||'4/4');setContextBox(beside(box));setToolsOpen(true);setNoteTools(false);setObjectMenu(null);requestAnimationFrame(()=>{document.querySelectorAll<HTMLDetailsElement>('.score-tool-popover details').forEach(d=>{d.open=d.querySelector('summary')?.textContent?.startsWith('Measure, meter')??false;});});}} selection={selection} boxSelect={boxSelect} onSelection={ids=>{if(busy)return;setNoteTools(false);setObjectMenu(null);setSelection(ids);setGroupIds(ids);setSelected(ids[0]??null);setSelectedMark(null);setSelectedText(null);setCurve(null);setNotice(ids.length+' notes selected. Delete removes this selection; Groups converts it.');}} selectedMark={selectedMark} onMark={id=>{setNoteTools(false);setToolsOpen(false);const node=workingViewport.current?.querySelector<SVGGraphicsElement>('[data-mark-id="'+CSS.escape(id)+'"]');if(node){const b=node.getBoundingClientRect();setObjectMenu({kind:'mark',id,x:Math.max(8,Math.min(window.innerWidth-170,b.left)),y:Math.max(76,Math.min(window.innerHeight-60,b.bottom+6))});}setVoiceChoice(null);setAnchorBox(null);setSelectedMark(id);setSelectedText(null);setSelected(null);setCurve(null);setNotice('');}} selectedText={selectedText} review={review} zoom={zoom} fitVersion={fitVersions.working} selected={selected} onHead={select} onLyric={(id, v, b) => beginLyric(id, v, b)} onReady={count=>{setMapped(count);placeLyricInput(true);if(selected){const head=workingViewport.current?.querySelector<SVGGraphicsElement>('[data-event-id="'+CSS.escape(selected)+'"]');if(head)setContextBox(beside(head.getBoundingClientRect()));}}} onGap={(measure_id, onset, voice, staff) => { if(chordMode){beginChord(measure_id,onset);return;} setNoteTools(true);setInsertAccidentalExplicit(false);setInsertPitch(p=>({...p,alter:keyAlter(p.step,measure_id)}));setInsertion({ measure_id, onset, voice, staff }); setSelected(null); setGroupIds([]); if (tool !== 'Groups' && tool !== 'Rest')
            setTool('Notes'); setPalette(true); }} onCurve={(c, dy) => { setCurve(c); setSelected(null); if (Math.abs(dy) > 5)
            void run(async () => { const direction = dy < 0 ? 'up' : 'down'; if (c.kind === 'tie')
                await mutate(`events/${c.from}`, { tie_direction: direction }, 'PATCH');
            else
                await mutate('slurs', { source_event_id: c.from, target_event_id: c.to, direction }); setCurve({ ...c, direction }); }); }} onHarmonyCandidates={(ids,box)=>{chordLive.current=null;setChordDraft(null);setToolsOpen(false);setNoteTools(false);setObjectMenu(null);setHarmonyChoice({ids,x:Math.max(8,Math.min(window.innerWidth-240,box.left)),y:Math.max(76,Math.min(window.innerHeight-240,box.bottom+6))});}} onHarmony={(id,box)=>{const h=review.score.harmonies?.find(h=>h.id===id);if(h)beginChord(h.measure_id,h.onset,box,id);}} onAnchor={(measure, onset, staff, pitch, box) => { if(chordMode){beginChord(measure,onset,box);return;} if (tool === 'Tie' || tool === 'Slur') {
            setNotice('Choose noteheads; empty staff is unchanged.');
            return;
        } if (tool !== 'Notes' && tool !== 'Rest' && tool !== 'Groups')
            return; setSelected(null); setGroupIds([]); setInsertAccidentalExplicit(false);setInsertPitch(pitch); setAnchorBox(box); setInsertion({ measure_id: measure, onset, staff, voice: '' }); }} onText={(id, b) => { setNoteTools(false);setToolsOpen(false);setObjectMenu(tool==='Text'?null:{kind:'text',id,x:Math.max(8,Math.min(window.innerWidth-220,b.left)),y:Math.max(76,Math.min(window.innerHeight-60,b.bottom+6))});setVoiceChoice(null);setAnchorBox(null);setSelectedText(id);setSelectedMark(null);setSelected(null);setCurve(null);setDraft(null);const t = review.score.texts.find(t => t.id === id); if(tool!=='Text'){setNotice('');return;}if (t)
            setTextDraft({ id, text: t.text, x: Math.max(8, Math.min(window.innerWidth - 220, b.left)), y: Math.max(8, Math.min(window.innerHeight - 70, b.bottom + 5)) }); }} onAmbiguous={(ids, dy, box) => setVoiceChoice({ ids, dy, box })}/></div><p className="pane-foot">{mapped} mapped noteheads · select or drag to change pitch · Unicode lyrics</p>

 </section></div></main></div> : <main className="stage-two"><h1>Instrument Scores <span className="tag">Real MusicXML</span></h1><section><h2>1 · {saved?'Saved Canonical Concert Score':'Original imported Concert Score'}</h2>{canGenerate ? <p>{concertInput?.name} · {saved?'saved version':'original imported MusicXML · unchanged'}</p> : <p className="warning">Save the current Concert Score in Stage 1 before generating instrument scores. Unsaved edits cannot be used.</p>}</section><section><h2>2 · Choose an instrument</h2><fieldset className="instrument-selection" disabled={editorBusy}><div className="instrument-cards">{saxes.map(s=><button disabled={!canGenerate} key={s.id} className={instrument===s.id ? 'chosen' : ''} onClick={()=>void run(()=>generate(s.id))}><strong>{s.name}</strong><span>Concert {offsetLabel(s.offset-(instrumentDirections[s.id]==='down'?12:0))} semitones · independent written score</span></button>)}</div><label>Direction <select aria-label="Instrument direction" disabled={!instrument} value={instrumentDirection} onChange={e=>{const next=e.target.value as 'up'|'down';if(instrument)void run(()=>generate(instrument,next));else setInstrumentDirection(next);}}><option value="up">Up · standard written register</option><option value="down">{instrument==='tenor' ? 'Down · like Soprano notation (+2)' : 'Down · one octave below standard'}</option></select></label><p>Down writes one octave below the standard output. Tenor Down uses +2 semitones, like Soprano Up notation; played on Tenor B♭ it sounds one octave below the saved Concert Score. Concert source and instrument transposition metadata stay unchanged. Each instrument and direction keeps its own edits during this session; save an instrument file to retain them after leaving.</p></fieldset></section><section className="instrument-work"><h2>3 · Compose & export</h2>{instrument && concertInput && outputs[variant(instrument)] && initialFiles.current.get(variant(instrument)) ? <><button disabled={editorBusy} onClick={()=>download(outputs[variant(instrument)].bytes,`${variant(instrument)}-${concertInput.name}`)}>Export instrument MusicXML</button><RealWorkspace key={variant(instrument)} file={initialFiles.current.get(variant(instrument))!} onExit={()=>{}} instrumentEditor={{onHistory:setInstrumentHistory,reference:concertInput.projection,referenceName:concertInput.name,label:`${saxes.find(s=>s.id===instrument)?.name} · ${instrumentDirection==='up'?'Up':'Down'}`,saved:instrumentSaves[variant(instrument)],onSave:next=>{const key=variant(instrument);setInstrumentSaves(s=>({...s,[key]:next}));},onBusy:setEditorBusy,onChange:r=>{const key=variant(instrument);setOutputs(o=>o[key]?.xml===r.xml ? o : {...o,[key]:r});}}}/></> : <p>Select an instrument to open the read-only concert input and editable instrument score.</p>}</section></main>}

 </fieldset>
 {insertion && !insertion.voice && anchorBox && <div className="anchor-menu" style={{ left: Math.max(5, Math.min(window.innerWidth - 245, anchorBox.left)), top: Math.max(5, Math.min(window.innerHeight - 160, anchorBox.top)) }}><strong>Choose voice for insertion</strong>{[...new Set(all.filter(e => e.measure_id === insertion.measure_id && e.staff === insertion.staff).map(e => e.voice))].map(v => <button key={v} disabled={busy} onClick={() => { setInsertion({ ...insertion, voice: v }); setPalette(true); }}>Voice {v}</button>)}<label>New voice<input aria-label="New insertion voice" placeholder="e.g. 3" onKeyDown={e=>{if(e.key==='Enter'&&e.currentTarget.value.trim()){setInsertion({...insertion,voice:e.currentTarget.value.trim()});setPalette(true);}}}/></label><button onClick={() => setInsertion(null)}>Cancel</button></div>}
 {voiceChoice && <div className="anchor-menu" style={{ left: Math.min(window.innerWidth - 245, voiceChoice.box.left), top: Math.min(window.innerHeight - 170, voiceChoice.box.bottom + 8) }}><strong>Choose the note voice</strong>{voiceChoice.ids.map(id => <button disabled={busy} key={id} onClick={() => { select(id, voiceChoice.dy); setVoiceChoice(null); }}>Voice {all.find(e => e.id === id)?.voice} · {id}</button>)}<button onClick={() => setVoiceChoice(null)}>Cancel</button></div>}
 {draft && <div data-testid="inline-lyric-editor" data-event-id={draft.event} data-verse={draft.verse} className="real-lyric-input" style={{ left: draft.x, top: draft.y }}><div><label>Verse <select aria-label="Lyric verse" value={draft.verse} onChange={e=>void run(()=>chooseLyricVerse(e.target.value))}>{Array.from({length:Math.max(2,Number(draft.verse)||1,...(review?.score.lyrics.map(l=>Number(l.number)||1)??[]))+1},(_,i)=><option key={i+1} value={String(i+1)}>Verse {i+1}</option>)}</select></label><button onPointerDown={e=>e.preventDefault()} onClick={()=>void run(()=>chooseLyricVerse(String(Math.max(Number(draft.verse)||1,...(review?.score.lyrics.map(l=>Number(l.number)||1)??[]))+1)))}>+ Verse</button></div><input ref={lyricInput} aria-label="Lyric syllable" value={draft.text} onChange={e => setDraft(d => d ? { ...d, text: e.target.value } : null)} onKeyDown={e => { if (e.nativeEvent.isComposing)
        return; if (e.key === 'Escape') {
        e.preventDefault();
        draftLive.current = null;
        setDraft(null);
    } if (e.key === 'Enter' || e.key === 'Tab') {
        e.preventDefault();
        void run(() => commitLyric(e.key === 'Tab' ? (e.shiftKey ? -1 : 1) : 0));
    } }} onBlur={e => { if(e.relatedTarget instanceof Element&&e.relatedTarget.closest('.real-lyric-input'))return;if (draftLive.current)
        void run(() => commitLyric()); }}/><small>Enter saves · Esc cancels · Tab next note</small></div>}
 {objectMenu && <div className="score-object-actions" style={{left:objectMenu.x,top:objectMenu.y}} role="toolbar" aria-label="Selected score object actions">{objectMenu.kind==='text'&&review?.score.texts.find(t=>t.id===objectMenu.id)?.role==='direction'&&<button onPointerDown={e=>e.preventDefault()} onClick={()=>void run(async()=>{const text=review?.score.texts.find(t=>t.id===objectMenu.id);if(text)await mutate('texts/'+text.id,{text:text.text,header_role:'composer'},'PATCH');setObjectMenu(null);setSelectedText(null);})}>Move to composer header</button>}{objectMenu.kind==='text'&&<button onClick={()=>{const text=review?.score.texts.find(t=>t.id===objectMenu.id);if(text){setTool('Text');setTextDraft({id:text.id,text:text.text,x:objectMenu.x,y:objectMenu.y});}setObjectMenu(null);}}>Edit text</button>}<button onPointerDown={e=>e.preventDefault()} onClick={()=>void run(remove)}>Delete object</button><button aria-label="Close object actions" onClick={()=>setObjectMenu(null)}>×</button></div>}
 {harmonyChoice&&<div className="real-lyric-input" style={{left:harmonyChoice.x,top:harmonyChoice.y,maxHeight:'220px',overflowY:'auto'}} role="dialog" aria-label="Choose overlapping chord"><small>Multiple chords occupy this position. Choose the chord to edit:</small>{harmonyChoice.ids.map((id,i)=>{const h=review?.score.harmonies?.find(h=>h.id===id);return h&&<button key={id} aria-label={'Edit chord '+(i+1)+': '+chordInputText(h)} onClick={()=>beginChord(h.measure_id,h.onset,new DOMRect(harmonyChoice.x,harmonyChoice.y,0,0),id)}>{i+1}. {chordInputText(h)}</button>;})}<button onClick={()=>setHarmonyChoice(null)}>Cancel</button></div>}
 {chordDraft && <div className="real-lyric-input" style={{left:chordDraft.x,top:chordDraft.y}}><input autoFocus aria-label="Write chord" placeholder="Bm, G, E7…" value={chordDraft.text} onChange={e=>setChordDraft({...chordDraft,text:e.target.value})} onKeyDown={e=>{if(e.nativeEvent.isComposing)return;if(e.key==='Escape'){chordLive.current=null;setChordDraft(null);}if(e.key==='Enter'){e.preventDefault();void run(commitChord);}}}/><small>Enter saves · Esc cancels</small>{chordDraft.id&&<button onClick={()=>void run(async()=>{await mutate('harmonies/'+chordDraft.id,undefined,'DELETE');chordLive.current=null;setChordDraft(null);})}>Delete chord</button>}</div>}
 {textDraft && <div className="real-lyric-input" style={{left:textDraft.x,top:textDraft.y}}><input autoFocus aria-label="Score text" value={textDraft.text} onChange={e=>setTextDraft({...textDraft,text:e.target.value})} onKeyDown={e=>{if(e.nativeEvent.isComposing)return;if(e.key==='Escape'){textLive.current=null;setTextDraft(null);}if(e.key==='Enter'){e.preventDefault();void run(commitText);}}} onBlur={()=>{if(textLive.current)void run(commitText);}}/><small>Enter or blur saves · Esc cancels</small>{review?.score.texts.find(t=>t.id===textDraft.id)?.role==='direction'&&<button onPointerDown={e=>e.preventDefault()} onClick={()=>void run(async()=>{const draft=textDraft;textLive.current=null;await mutate('texts/'+draft.id,{text:draft.text,header_role:'composer'},'PATCH');setTextDraft(null);setObjectMenu(null);setSelectedText(null);})}>Move to composer header</button>}<button onPointerDown={e=>e.preventDefault()} onClick={()=>void run(remove)}>Delete object</button></div>}
 {receipt && <section role="dialog" aria-label={instrumentEditor ? "Confirm downloaded instrument file" : "Confirm downloaded concert file"} className="real-receipt"><strong>Keep the downloaded {instrumentEditor ? "Instrument" : "Concert"} MusicXML</strong><p>The browser cannot confirm that your download was retained.</p><button onClick={() => { recordSave(receipt); setReceipt(null); setNotice(instrumentEditor ? 'You confirmed the local Instrument MusicXML was retained.' : 'You confirmed the local Concert MusicXML was retained.'); }}>I retained the downloaded file</button><button onClick={() => { setReceipt(null); setNotice('No new save confirmed. Any previous saved file remains unchanged.'); }}>Cancel confirmation</button></section>}
 {!instrumentEditor && homePrompt && <section role="dialog" aria-modal="true" aria-label="Return Home" className="real-receipt home-prompt" onKeyDown={e=>{if(e.key==='Escape')setHomePrompt(false);}}><strong>Return Home?</strong><p>Save your work, continue editing, or discard unsaved Concert and instrument changes. Saved files stay unchanged.</p>{dirty && <p><button disabled={busy || editorBusy} onClick={()=>openToSave('concert')}>Open Concert to save</button></p>}{unsavedInstruments.map(key=>{const [id,direction]=key.split('-');return <p key={key}><button disabled={busy || editorBusy} onClick={()=>openToSave(key)}>Open {saxes.find(s=>s.id===id)?.name} · {direction==='up'?'Up':'Down'} to save</button></p>;})}<button autoFocus onClick={()=>setHomePrompt(false)}>Continue editing</button><button className="discard-home" disabled={busy||editorBusy||!!receipt} onClick={discardAndHome}>Discard changes and go Home</button></section>}
 {validation && review && <section className="validation real-validation"><div className="validation-head"><strong>Validate</strong><button onClick={() => setValidation(false)}>Close</button></div><div><OMRWarnings warnings={recognitionWarnings}/>{review.validation.diagnostics.length ? review.validation.diagnostics.map((d, i) => <p key={i}>{d.blocking ? 'Technical error: ' : 'Advisory: '}{d.message}</p>) : <p>No technical diagnostics.</p>}<p>Checks do not alter the score.</p></div></section>}
 <div className={instrumentEditor ? "instrument-notice" : "notice"} role="status" hidden={!busy&&!notice}>{busy ? 'Working… ' : ''}{notice}{notice&&<button type="button" aria-label="Dismiss notification" title="Close notification" onClick={()=>setNotice('')}>×</button>}</div></>;
}
