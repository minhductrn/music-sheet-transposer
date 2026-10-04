import { useState } from 'react'
import type { DisplaySize, EventAdd, EventPatch, Measure, ScoreEvent } from '../types/review'
import { eventLabel } from '../utils/review'

interface Props {
  event: ScoreEvent
  measure: Measure
  busy: boolean
  change: (path: string, method: 'POST' | 'PATCH' | 'DELETE', body?: unknown) => Promise<void>
}

export default function EventInspector({ event, measure, busy, change }: Props) {
  const initialStep = event.pitch ? event.pitch.step ?? '' : 'C'
  const initialOctave = event.pitch ? event.pitch.octave?.toString() ?? '' : '4'
  const [step, setStep] = useState(initialStep)
  const [alter, setAlter] = useState(event.pitch?.alter ?? '0')
  const [octave, setOctave] = useState(initialOctave)
  const initialDuration = event.duration ?? (event.grace ? '1' : '')
  const [duration, setDuration] = useState(initialDuration)
  const [voice, setVoice] = useState(event.voice)
  const [staff, setStaff] = useState(event.staff ?? 1)
  const [size, setSize] = useState<DisplaySize>(event.display_size)
  const [grace, setGrace] = useState(event.grace)
  const [addKind, setAddKind] = useState<'note' | 'rest'>('note')

  const patch: EventPatch = {}
  const pitchChanged = Boolean(event.pitch && (step !== initialStep || alter !== event.pitch.alter || octave !== initialOctave))
  const validPitch = /^[A-G]$/.test(step) && /^[0-9]$/.test(octave) && /^[+-]?\d+(?:\.\d+)?$/.test(alter)
  if (pitchChanged) patch.pitch = { step, alter, octave: Number(octave) }
  if (duration !== initialDuration) patch.duration = duration
  if (grace !== event.grace) {
    patch.grace = grace
    if (!grace) patch.duration = duration
  }
  if (voice !== event.voice) patch.voice = voice
  if (staff !== event.staff) patch.staff = staff
  if (size !== event.display_size) patch.display_size = size

  async function add(position: 'before' | 'after' | 'simultaneous') {
    const simultaneous = position === 'simultaneous'
    const request: EventAdd = {
      measure_id: measure.id, kind: simultaneous ? 'note' : addKind,
      pitch: simultaneous || addKind === 'note' ? { step, alter, octave: Number(octave) } : undefined,
      duration, voice, staff, display_size: size, grace: simultaneous ? false : grace,
      ...(simultaneous ? { chord_with_id: event.id } : position === 'before' ? { before_event_id: event.id } : { after_event_id: event.id }),
    }
    await change('events', 'POST', request)
  }

  return <section className="review-inspector" aria-label="Event inspector">
    <h3>Event inspector</h3>
    <p>{eventLabel(event)} <small>({event.id})</small></p>
    <fieldset disabled={busy}>
      <div className="review-fields">
        <label>Pitch <select value={step} onChange={(e) => setStep(e.target.value)}>
          {!initialStep && <option value="">Choose step</option>}
          {'CDEFGAB'.split('').map((value) => <option key={value}>{value}</option>)}
        </select></label>
        <label>Alter <input aria-label="Pitch alter" value={alter} onChange={(e) => setAlter(e.target.value)} /></label>
        <label>Octave <input type="number" min={0} max={9} value={octave} onChange={(e) => setOctave(e.target.value)} /></label>
        <label>Duration (quarter beats) <input value={duration} onChange={(e) => setDuration(e.target.value)} /></label>
        <label>Voice <input value={voice} onChange={(e) => setVoice(e.target.value)} /></label>
        <label>Staff <input type="number" min={1} max={measure.staves} value={staff} onChange={(e) => setStaff(Number(e.target.value))} /></label>
        <label>Display size <select value={size} onChange={(e) => setSize(e.target.value as DisplaySize)}>
          <option value="normal">Normal</option><option value="small">Small</option><option value="cue">Cue size</option>
        </select></label>
        <label><input type="checkbox" checked={grace} onChange={(e) => setGrace(e.target.checked)} /> Grace timing</label>
      </div>
      <p className="review-hint">Small size keeps normal timing. Duration, voice and grace edits apply to the shared chord. Sequential add/delete shifts later events; backup/forward are retained, so check timing diagnostics.</p>
      <div className="review-toolbar">
        <button type="button" disabled={Object.keys(patch).length === 0 || (pitchChanged && !validPitch)} onClick={() => void change(`events/${event.id}`, 'PATCH', patch)}>Apply correction</button>
        <label>Add <select value={addKind} onChange={(e) => setAddKind(e.target.value as 'note' | 'rest')}><option value="note">Note</option><option value="rest">Rest</option></select></label>
        <button type="button" disabled={addKind === 'note' && !validPitch} onClick={() => void add('before')}>Add before selected</button>
        <button type="button" disabled={addKind === 'note' && !validPitch} onClick={() => void add('after')}>Add after selected</button>
        <button type="button" disabled={event.kind !== 'note' || event.grace || !validPitch} onClick={() => void add('simultaneous')}>Add simultaneous note</button>
        <button type="button" onClick={() => void change(`events/${event.id}`, 'DELETE')}>Delete {event.kind}</button>
      </div>
    </fieldset>
  </section>
}
