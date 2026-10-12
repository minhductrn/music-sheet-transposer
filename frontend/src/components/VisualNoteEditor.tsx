import { useState } from 'react'
import type { Lyric, Measure, Pitch, ScoreEvent } from '../types/review'
import { durationChoices, insertion, movePitch } from '../utils/visualReview'

type Change = (path: string, method: 'POST' | 'PATCH' | 'DELETE', body?: unknown) => Promise<void>
interface Props {
  measures?: { id: string; label: string; staves: number }[]
  event: ScoreEvent; measure: Measure; lyrics: Lyric[]; busy: boolean
  change: Change; startTie: () => void; advanced: () => void
  lyricOwner?: ScoreEvent | null; selectLyricOwner?: () => void
}

export function DurationPicker({ value, divisions, supported, disabled, onChange }: {
  value: string; divisions: string | null; supported?: string[]; disabled: boolean; onChange: (value: string) => void
}) {
  const options = durationChoices(divisions, supported)
  return <label>Duration <select aria-label="Duration" value={value} disabled={disabled || !options.length} onChange={(e) => onChange(e.target.value)}>
    {!options.some(([duration]) => duration === value) && <option value={value}>Current duration (use Advanced for unusual rhythms)</option>}
    {options.map(([duration, symbol, label]) => <option key={duration} value={duration}>{symbol} {label} note</option>)}
  </select></label>
}

export function AuxiliaryLyricNotice({ owner, busy, selectOwner }: { owner: ScoreEvent; busy: boolean; selectOwner: () => void }) {
  return <fieldset disabled={busy} className="review-fields">
    <legend>Lyrics on the normal note</legend>
    <p>This auxiliary small note shares a chord and melodic voice with {owner.pitch?.step}{owner.pitch?.octave}. Lyrics belong to that normal note.</p>
    <button onClick={selectOwner}>Select normal-note lyric owner</button>
  </fieldset>
}

export function LyricEditor({ event, lyrics, busy, change, lyricOwner, selectLyricOwner }: Pick<Props, 'event' | 'lyrics' | 'busy' | 'change' | 'lyricOwner' | 'selectLyricOwner'>) {
  const [verseId, setVerseId] = useState(lyrics[0]?.id ?? '')
  const verse = lyrics.find((lyric) => lyric.id === verseId)
  const [segment, setSegment] = useState(0)
  const [text, setText] = useState(verse?.segments[0] ?? '')
  const [number, setNumber] = useState(String(Math.max(0, ...lyrics.map((l) => /^\d+$/.test(l.number) ? Number(l.number) : 0)) + 1))
  function choose(id: string) {
    setVerseId(id); setSegment(0)
    setText(lyrics.find((lyric) => lyric.id === id)?.segments[0] ?? '')
  }
  if (!lyrics.length && lyricOwner && selectLyricOwner) return <AuxiliaryLyricNotice owner={lyricOwner} busy={busy} selectOwner={selectLyricOwner} />
  return <fieldset disabled={busy} className="review-fields">
    <legend>{verse ? 'Edit lyric' : 'Add lyric'}</legend>
    {(lyrics.length > 1 || (!verse && lyrics.length > 0)) && <label>Verse <select aria-label="Lyric verse" value={verseId} onChange={(e) => choose(e.target.value)}>
      <option value="">Add lyric</option>{lyrics.map((lyric) => <option key={lyric.id} value={lyric.id}>Verse {lyric.number}</option>)}
    </select></label>}
    {verse && lyrics.length === 1 && <button onClick={() => choose('')}>Add another verse</button>}
    {!verse && lyrics.length > 0 && <label>New verse <input aria-label="New verse" value={number} maxLength={16} onChange={(e) => setNumber(e.target.value)} /></label>}
    {verse && verse.segments.length > 1 && <label>Text segment <select value={segment} onChange={(e) => {
      const index = Number(e.target.value); setSegment(index); setText(verse.segments[index])
    }}>{verse.segments.map((_, index) => <option key={index} value={index}>Segment {index + 1}</option>)}</select></label>}
    <label>Lyric text <input aria-label="Lyric text" value={text} maxLength={2000} onChange={(e) => setText(e.target.value)} /></label>
    <button disabled={!text || (!verse && (!number.trim() || lyrics.some((l) => l.number === number)))} onClick={() => void change(
      verse ? `lyrics/${verse.id}` : `events/${event.id}/lyrics`, verse ? 'PATCH' : 'POST',
      verse ? { text, segment_index: segment } : { text, number },
    )}>Apply lyric</button>
    {verse && <button onClick={() => void change(`lyrics/${verse.id}`, 'DELETE')}>Delete lyric</button>}
    <p>Text edits retain syllable markings and other verses. Removing a lyric removes this verse on this note only.</p>
  </fieldset>
}

export default function VisualNoteEditor({ event, measure, measures = [], lyrics, busy, change, startTie, advanced, lyricOwner, selectLyricOwner }: Props) {
  const [ownerMeasure, setOwnerMeasure] = useState(measure.id)
  const [ownerOnset, setOwnerOnset] = useState(event.onset ?? '0')
  const [ownerVoice, setOwnerVoice] = useState(event.voice)
  const [ownerStaff, setOwnerStaff] = useState(event.staff ?? 1)
  const [tool, setTool] = useState('pitch')
  const validPitch = event.pitch?.step && event.pitch.octave !== null
    ? { step: event.pitch.step, alter: event.pitch.alter, octave: event.pitch.octave } as Pitch : null
  const [draftPitch, setDraftPitch] = useState<Pitch | null>(validPitch)
  const choices = durationChoices(event.divisions ?? measure.divisions)
  const [duration, setDuration] = useState(choices.find(([value]) => value === event.duration)?.[0] as string ?? choices.find(([value]) => value === '1')?.[0] ?? choices[0]?.[0] ?? '')
  const [position, setPosition] = useState('after')
  const patch = (body: unknown) => change(`events/${event.id}`, 'PATCH', body)
  const pitchMeasure = event.key_signature ? { ...measure, key_signature: event.key_signature } : measure
  const up = movePitch(event.pitch, 1, pitchMeasure, event.staff)
  const down = movePitch(event.pitch, -1, pitchMeasure, event.staff)
  const draftUp = movePitch(draftPitch, 1, pitchMeasure, event.staff)
  const draftDown = movePitch(draftPitch, -1, pitchMeasure, event.staff)
  const draftSteps = draftPitch && validPitch ? (draftPitch.octave - validPitch.octave) * 7 + 'CDEFGAB'.indexOf(draftPitch.step) - 'CDEFGAB'.indexOf(validPitch.step) : 0
  const note = event.kind === 'note'
  return <section className="visual-note-editor" aria-label="Visual note editor">
    <h3>Correct selected {note ? 'note' : 'rest'}</h3>
    <div className="review-toolbar" role="toolbar" aria-label="Note corrections">
      {['pitch', 'duration', 'lyric', 'add'].map((name) => <button key={name} disabled={busy || (name === 'pitch' && !validPitch)} aria-pressed={tool === name}
        onClick={() => setTool(name)}>{name === 'add' ? 'Add note' : name[0].toUpperCase() + name.slice(1)}</button>)}
      <button disabled={busy || !note || event.grace || !event.tie_target_ids?.some((id) => id !== event.tie_target_id)} onClick={startTie}>Tie</button>
      <button disabled={busy || !event.tie_target_id} onClick={() => void patch({ tie_to_event_id: null })}>Remove tie</button>
      <button disabled={busy} onClick={() => void change(`events/${event.id}`, 'DELETE')}>Delete note</button>
      <button onClick={advanced}>Advanced</button>
    </div>
    <fieldset disabled={busy} className="review-fields"><legend>Source notation properties</legend>
      <label>Display size <select aria-label="Display size" value={event.display_size} onChange={(e) => void patch({ display_size: e.target.value })}>
        {event.display_size === 'cue' && <option value="cue">Current cue-size notation</option>}<option value="normal">Normal</option><option value="small">Small</option>
      </select></label>
      <label>Timing <select aria-label="Timing" value={event.grace ? 'grace' : 'duration-bearing'} disabled={event.kind !== 'note' || event.cue} onChange={(e) => void patch(e.target.value === 'grace' ? { grace: true } : { grace: false, duration })}>
        <option value="duration-bearing">Duration-bearing</option><option value="grace">Grace</option>
      </select></label>
      {event.grace && <DurationPicker value={duration} divisions={event.divisions ?? measure.divisions} disabled={busy} onChange={setDuration} />}
      <label>Voice <input aria-label="Note voice" defaultValue={event.voice} maxLength={32} onBlur={(e) => {
        if (e.target.value !== event.voice && /^\S{1,32}$/.test(e.target.value)) void patch({ voice: e.target.value })
      }} /></label>
      <label>Staff <select aria-label="Note staff" value={event.staff ?? ''} onChange={(e) => void patch({ staff: Number(e.target.value) })}>
        {Array.from({ length: measure.staves }, (_, i) => <option key={i + 1} value={i + 1}>Staff {i + 1}</option>)}
      </select></label>
      <p>Small is a display property, independent of timing. Duration applies to this note; grace and voice changes apply to the shared chord. Staff and size apply to this note. Independent secondary voices can be inserted at an explicit position.</p>
      {event.cue && <p>Explicit cue semantics are retained; cue-to-grace conversion is unavailable.</p>}
    </fieldset>
    {note && <fieldset disabled={busy} className="review-fields"><legend>Explicit measure / secondary voice ownership</legend>
      <label>Destination measure <select aria-label="Destination measure" value={ownerMeasure} onChange={(e) => { setOwnerMeasure(e.target.value); setOwnerStaff(1) }}>
        {measures.map((m) => <option key={m.id} value={m.id}>{m.label}</option>)}
      </select></label>
      <label>Set same onset as<select aria-label="Set same onset as" value="" onChange={(e) => {
        const anchor = measure.voices.flatMap(v => v.events).find(n => n.id === e.target.value)
        if (anchor?.onset != null) { setOwnerMeasure(measure.id); setOwnerOnset(anchor.onset) }
      }}><option value="">Choose existing note</option>{measure.voices.flatMap(v => v.events).filter(n => n.id !== event.id && n.onset != null && !n.grace).map(n => <option key={n.id} value={n.id}>{n.pitch?.step ?? 'Rest'} at {n.onset}, voice {n.voice}</option>)}</select></label>
      <label>Position from start (quarter-note units)<input aria-label="Ownership position" value={ownerOnset} onChange={(e) => setOwnerOnset(e.target.value)} /></label>
      <label>Destination voice<input aria-label="Destination voice" value={ownerVoice} maxLength={32} onChange={(e) => setOwnerVoice(e.target.value)} /></label>
      <label>Destination staff<select aria-label="Destination staff" value={ownerStaff} onChange={(e) => setOwnerStaff(Number(e.target.value))}>
        {Array.from({ length: measures.find((m) => m.id === ownerMeasure)?.staves ?? measure.staves }, (_, i) => <option key={i + 1} value={i + 1}>Staff {i + 1}</option>)}
      </select></label>
      <button disabled={!ownerOnset.trim() || !/^\S{1,32}$/.test(ownerVoice) || event.grace || event.cue} onClick={() => void change(`events/${event.id}/ownership`, 'POST', { measure_id: ownerMeasure, onset: ownerOnset, voice: ownerVoice, staff: ownerStaff })}>Apply explicit ownership</button>
      <p>This note moves only to the chosen measure, position, staff and voice. Existing notes keep their positions. Remove ties before moving; unsupported relationships fail safely.</p>
    </fieldset>}
    {tool === 'pitch'  && <fieldset disabled={busy} className="review-fields"><legend>Pitch</legend>
      <label>Pitch <select aria-label="Pitch letter" value={validPitch?.step ?? ''} disabled={!validPitch} onChange={(e) => void patch({ pitch: { ...validPitch, step: e.target.value } })}>
        {'CDEFGAB'.split('').map((step) => <option key={step}>{step}</option>)}
      </select></label>
      <label>Octave <select aria-label="Pitch octave" value={validPitch?.octave ?? ''} disabled={!validPitch} onChange={(e) => void patch({ pitch: { ...validPitch, octave: Number(e.target.value) } })}>
        {Array.from({ length: 10 }, (_, i) => <option key={i}>{i}</option>)}
      </select></label>
      <button disabled={!up} title="Move one staff line or space up" onClick={() => void patch({ pitch: up })}>↑ One staff step up</button>
      <button disabled={!down} title="Move one staff line or space down" onClick={() => void patch({ pitch: down })}>↓ One staff step down</button>
      <label>Accidental <select aria-label="Accidental" value={event.pitch?.alter ?? '0'} disabled={!validPitch} onChange={(e) => void patch({ pitch: { ...validPitch, alter: e.target.value }, written_accidental: { '-1': 'flat', '0': 'natural', '1': 'sharp' }[e.target.value] })}>
        {!['-1', '0', '1'].includes(event.pitch?.alter ?? '0') && <option value={event.pitch?.alter}>Current accidental</option>}
        <option value="-1">♭ Flat</option><option value="0">♮ Natural</option><option value="1">♯ Sharp</option>
      </select></label>
      <p>Steps follow the destination note’s key signature. Use Accidental to override it. Unsupported key spelling requires Advanced review.</p>
    </fieldset>}
    {tool === 'duration' && <fieldset disabled={busy}><legend>Duration</legend>
      <DurationPicker value={event.duration ?? ''} divisions={event.divisions} supported={event.duration_options} disabled={busy || event.grace} onChange={(value) => void patch({ duration: value, duration_scope: 'note', preserve_onsets: true })} />
      {event.grace && <p>Choose a duration above before switching to Duration-bearing.</p>}
    </fieldset>}
    {tool === 'lyric' && <LyricEditor event={event} lyrics={lyrics} busy={busy} change={change} lyricOwner={lyricOwner} selectLyricOwner={selectLyricOwner} />}
    {tool === 'add' && <fieldset disabled={busy} className="review-fields"><legend>Add missing note</legend>
      <label>Placement <select aria-label="Placement" value={position} onChange={(e) => setPosition(e.target.value)}>
        <option value="before">Before selected note</option><option value="after">After selected note</option>
        {note && !event.grace && <option value="simultaneous">At selected note’s exact onset</option>}
      </select></label>
      <p>Draft starts at the selected note’s pitch. Adjust it before applying; no score change is made until Apply.</p>
      <button disabled={!draftUp} onClick={() => setDraftPitch(draftUp)}>↑ Draft pitch up</button>
      <button disabled={!draftDown} onClick={() => setDraftPitch(draftDown)}>↓ Draft pitch down</button>
      {draftPitch && <p role="status">Draft pitch: {draftSteps === 0 ? 'same staff position as selected note' : `${Math.abs(draftSteps)} staff steps ${draftSteps > 0 ? 'above' : 'below'} selected note`}.</p>}
      {draftPitch && <label>Draft accidental <select value={draftPitch.alter} onChange={(e) => setDraftPitch({ ...draftPitch, alter: e.target.value })}>
        {!['-1', '0', '1'].includes(draftPitch.alter) && <option value={draftPitch.alter}>Current accidental</option>}
        <option value="-1">♭ Flat</option><option value="0">♮ Natural</option><option value="1">♯ Sharp</option>
      </select></label>}
      <DurationPicker value={duration} divisions={event.divisions ?? measure.divisions} disabled={busy} onChange={setDuration} />
      {position === 'simultaneous' && <p>The new note uses the selected note’s exact onset and its own chosen duration.</p>}
      <p>Placement stays on this side of the barline, in the selected note’s measure. Select a note across the barline to add there.</p>
      {!draftPitch && <p>Select a pitched note as an anchor, or use Advanced review to choose the missing note’s pitch.</p>}
      <button disabled={!draftPitch || !duration} onClick={() => draftPitch && void change('events', 'POST', insertion(event, measure, draftPitch, duration, position))}>Apply new note</button>
    </fieldset>}
  </section>
}
