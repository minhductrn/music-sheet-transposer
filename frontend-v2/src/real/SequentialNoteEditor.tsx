import { useState } from 'react';
import { dottedWritten, rational, type Event, type Review } from './api';

type Props = { event: Event; review: Review; busy: boolean; onAdd: (body: Record<string, unknown>) => Promise<boolean> };

/** Explicit sequential correction; never infer the missing musical content. */
export function SequentialNoteEditor({ event, review, busy, onAdd }: Props) {
    const [placement, setPlacement] = useState<'before' | 'after' | null>(null);
    const [step, setStep] = useState(event.pitch?.step ?? 'C');
    const [alter, setAlter] = useState(event.pitch?.alter ?? '0');
    const [octave, setOctave] = useState(event.pitch?.octave ?? 5);
    const [length, setLength] = useState('1');
    const [dots, setDots] = useState(false);
    const [voice, setVoice] = useState(event.voice);
    const [displaySize, setDisplaySize] = useState(event.display_size);
    function begin(next:'before'|'after'){
        setVoice(event.voice);setDisplaySize(event.display_size);
        setStep(event.pitch?.step??'C');setAlter(event.pitch?.alter??'0');setOctave(event.pitch?.octave??5);
        setPlacement(next);
    }
    const measure = review.score.parts.flatMap(p => p.measures).find(m => m.id === event.measure_id);
    const duration = dottedWritten(length, dots);
    const sameVoice = voice.trim() === event.voice;
    const onset = rational(event.onset ?? '0') + (placement === 'after' && !event.grace ? rational(event.duration ?? '0') : 0);
    const extent = Math.max(0, ...(measure?.voices.flatMap(v => v.events).filter(e => e.voice === voice.trim() && !e.grace).map(e => rational(e.onset ?? '0') + rational(e.duration ?? '0')) ?? []));
    const exceeds = measure?.expected_duration != null && (sameVoice ? extent + rational(duration) : onset + rational(duration)) > rational(measure.expected_duration);
    return <div className="note-context" aria-label="Add note beside selection">
        <button disabled={busy} onClick={() => begin('before')}>Add note before</button>
        <button disabled={busy} onClick={() => begin('after')}>Add note after</button>
        {placement && <fieldset><legend>Add note {placement} selected note</legend>
            <label>Pitch<select aria-label="New note pitch" value={step} onChange={e => setStep(e.target.value)}>{[...'CDEFGAB'].map(s => <option key={s}>{s}</option>)}</select></label>
            <label>Accidental<select aria-label="New note accidental" value={alter} onChange={e => setAlter(e.target.value)}>{[['-2','Double flat'],['-1','Flat'],['0','Natural'],['1','Sharp'],['2','Double sharp']].map(([v,n]) => <option key={v} value={v}>{n}</option>)}</select></label>
            <label>Octave<input aria-label="New note octave" type="number" min="0" max="9" value={octave} onChange={e => setOctave(Number(e.target.value))}/></label>
            <label>Duration<select aria-label="New note duration" value={length} onChange={e => setLength(e.target.value)}>{[['4','Whole'],['2','Half'],['1','Quarter'],['1/2','Eighth'],['1/4','16th'],['1/8','32nd'],['1/16','64th']].map(([v,n]) => <option key={v} value={v}>{n}</option>)}</select></label>
            <label><input type="checkbox" checked={dots} onChange={e => setDots(e.target.checked)}/>Dotted</label>
            <label>Voice<input aria-label="New note voice" value={voice} onChange={e => {setVoice(e.target.value);if(e.target.value.trim()==='2')setDisplaySize('small');}}/></label>
            <label>Size<select aria-label="New note size" value={displaySize} onChange={e=>setDisplaySize(e.target.value as Event['display_size'])}><option value="normal">Normal</option><option value="small">Small</option><option value="cue">Cue</option></select></label>
            <p>{sameVoice ? 'Sequential insertion moves following content in this measure. Review all voices afterward.' : 'A different voice keeps existing notes in place.'}</p>
            {exceeds && <p role="status">This insertion exceeds the measure duration. You can add it, then correct the OMR timing and use Validate.</p>}
            <button disabled={busy || !/^\S+$/.test(voice.trim()) || !Number.isInteger(octave) || octave < 0 || octave > 9} onClick={async () => {
                const added = await onAdd({measure_id: event.measure_id, voice: voice.trim(), staff: event.staff, display_size: displaySize, kind: 'note', pitch: {step, alter, octave}, duration,
                    ...(sameVoice ? {[placement === 'before' ? 'before_event_id' : 'after_event_id']: event.id} : {onset: String(onset)})});
                if (added) setPlacement(null);
            }}>Insert note</button>
            <button disabled={busy} onClick={() => setPlacement(null)}>Cancel adding note</button>
        </fieldset>}
    </div>;
}
