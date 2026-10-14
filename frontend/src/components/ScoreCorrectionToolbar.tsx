import { useState, type ReactNode } from 'react'
import type { Measure, Pitch, ReviewSession, ScoreEvent } from '../types/review'
import type { VisualInsertionPosition } from '../utils/scoreInsertion'
import { durationChoices, movePitch } from '../utils/visualReview'
import { LyricEditor } from './VisualNoteEditor'

type Change = (path: string, method: 'POST' | 'PATCH' | 'DELETE', body?: unknown) => Promise<void>
export type EditorTool = 'select' | 'note' | 'lyrics' | 'tie' | 'more'
interface Props {
  group?: EditorTool; onGroup?: (group: EditorTool) => void; context?: ReactNode
  review: ReviewSession; event?: ScoreEvent; measure?: Measure; position: VisualInsertionPosition | null
  adding: boolean; tying: boolean; disabled: boolean; readOnly: boolean
  anchorPosition: () => void; change: Change; select: () => void; add: () => void; tie: () => void; advanced: () => void
  tieTargets?: { id: string; label: string }[]
  lyricOwner?: ScoreEvent | null; selectLyricOwner?: () => void
}
const paths: Record<string, string> = {
  select: 'M5 3v16l4-5 5 5 3-3-5-5 6-2Z', add: 'M13 5v11a3 3 0 1 1-2-2V5m2 0 5 2M4 5h6M7 2v6',
  delete: 'M4 6h16M9 6V3h6v3M6 6l1 14h10l1-14M10 10v6M14 10v6', pitch: 'M12 3v18M8 7l4-4 4 4M8 17l4 4 4-4',
  duration: 'M15 3v13a4 3 0 1 1-2-2V3m2 0c6 3 5 6 2 7', accidental: 'M8 3v18M15 2v18M4 9l15-3M4 16l15-3',
  size: 'M4 13h7v7H4ZM14 4h6v6h-6ZM4 6h6M7 3v6', timing: 'M12 3a9 9 0 1 0 9 9M12 7v5l4 2M18 2v6M15 5h6',
  tie: 'M3 10c5 10 13 10 18 0M3 7v3M21 7v3', lyric: 'M4 4h16M12 4v16M8 20h8',
  undo: 'M8 4 3 9l5 5M3 9h10a7 7 0 0 1 7 7', redo: 'M16 4l5 5-5 5M21 9H11a7 7 0 0 0-7 7', more: 'M5 11h1v1H5ZM11 11h1v1h-1ZM17 11h1v1h-1Z',
}
export function CorrectionIcon({ name }: { name: string }) {
  return <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false"><path d={paths[name]} fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" /></svg>
}

export default function ScoreCorrectionToolbar({ review, event, measure, position, adding, tying, disabled, readOnly, anchorPosition, change, select, add, tie, lyricOwner, selectLyricOwner, group = 'select', onGroup, context, tieTargets = [] }: Props) {
  const [tool, setTool] = useState(group === 'lyrics' ? 'lyric' : '')
  const selected = event?.kind === 'note' && event.pitch?.step && event.pitch.octave !== null
    ? { step: event.pitch.step, alter: event.pitch.alter, octave: event.pitch.octave } as Pitch : null
  const [pitch, setPitch] = useState<Pitch>((!adding && selected) || { step: 'C', octave: 4, alter: '0' })
  const [duration, setDuration] = useState(adding ? '1' : event?.duration ?? '1')
  const [explicitAccidental, setExplicitAccidental] = useState<string | null>(adding ? null : event?.accidental?.text ?? null)
  const [display, setDisplay] = useState('normal')
  const [grace, setGrace] = useState(false)
  const positionMeasure = review.score.parts.flatMap((p) => p.measures).find((m) => m.id === position?.measureId)
  const part = review.score.parts.find((p) => p.measures.some((m) => m.id === position?.measureId))
  const voices = Array.from(new Set(part?.measures.flatMap((m) => m.voices.map((v) => v.id)) ?? []))
  const staffVoices = Array.from(new Set(positionMeasure?.voices.filter((v) => v.events.some((e) => e.staff === position?.staff)).map((v) => v.id) ?? []))
  const [voiceChoice, setVoiceChoice] = useState('')
  const secondary = String(Math.max(1, ...voices.filter((v) => /^\d+$/.test(v)).map(Number)) + 1)
  // Empty parts have one explicit initial voice. Multiple existing choices require selection.
  const defaultVoice = staffVoices.length === 1 ? staffVoices[0] : !staffVoices.length && voices.length <= 1 ? voices[0] ?? '1' : ''
  const voice = voiceChoice === 'secondary' ? secondary : voiceChoice || defaultVoice
  const editable = !disabled && !readOnly
  const patch = (body: unknown) => event && change(`events/${event.id}`, 'PATCH', body)
  const choose = (name: string) => { if (selected) setPitch(selected); setDuration(event?.duration ?? '1'); setExplicitAccidental(event?.accidental?.text ?? null); setTool(tool === name ? '' : name) }
  const icon = (name: string, label: string, action: () => void, unavailable = false, active = false) => <button type="button" key={name} title={label} aria-label={label} disabled={unavailable} aria-pressed={active} onClick={action}><CorrectionIcon name={name} /><span>{label}</span></button>
  const options = durationChoices(adding ? positionMeasure?.divisions ?? null : event?.divisions ?? measure?.divisions ?? null,
    !adding && !event?.grace ? event?.duration_options : undefined)
  const pitchControls = <>
    <label>Pitch<select aria-label="Note pitch" value={pitch.step} onChange={(e) => setPitch({ ...pitch, step: e.target.value })}>{'CDEFGAB'.split('').map((step) => <option key={step}>{step}</option>)}</select></label>
    <label>Octave<select aria-label="Note octave" value={pitch.octave} onChange={(e) => setPitch({ ...pitch, octave: Number(e.target.value) })}>{Array.from({ length: 10 }, (_, i) => <option key={i}>{i}</option>)}</select></label>
  </>
  const contextMeasure = adding ? positionMeasure : event?.key_signature && measure ? { ...measure, key_signature: event.key_signature } : measure
  const followPitch = contextMeasure ? movePitch(pitch, 0, contextMeasure, adding ? position?.staff ?? null : event?.staff ?? null) : null
  const accidentals = [
    ['flat-flat', '-2', '♭♭', 'Double flat'], ['flat', '-1', '♭', 'Flat'],
    ['natural', '0', '♮', 'Natural'], ['sharp', '1', '♯', 'Sharp'], ['double-sharp', '2', '𝄪', 'Double sharp'],
  ] as const
  const effectivePitch = explicitAccidental ? { ...pitch, alter: accidentals.find(([name]) => name === explicitAccidental)?.[1] ?? pitch.alter } : followPitch
  const accidentalControl = <div role="group" aria-label="Note accidental" className="musical-symbol-controls">
    {accidentals.map(([name, , symbol, label]) => <button type="button" key={name} title={label} aria-label={label} aria-pressed={explicitAccidental === name}
      onClick={() => setExplicitAccidental(explicitAccidental === name ? null : name)}><span aria-hidden="true">{symbol}</span></button>)}
    <button type="button" className="accidental-clear" title="Clear accidental" aria-label="Clear accidental" disabled={!explicitAccidental} onClick={() => setExplicitAccidental(null)}>Clear accidental</button>
    <span className="score-context-status" role="status">{explicitAccidental ? 'Click active sign or Clear accidental, then Apply.' : 'Follow key context'}</span>
  </div>
  const durationControl = <div role="group" aria-label="Note value" className="musical-symbol-controls">
    {options.map(([value, symbol, label]) => <button type="button" key={value} title={`${label} note`} aria-label={`${label} note`} aria-pressed={duration === value}
      onClick={() => { setDuration(value); if (!adding && tool === 'duration') void patch({ duration: value, duration_scope: 'note', preserve_onsets: true }) }}><span aria-hidden="true">{symbol}</span></button>)}
    {!options.some(([value]) => value === duration) && <span>Choose a supported note value; unusual rhythms are available in Advanced.</span>}
  </div>
  const panel = !readOnly && !adding && !tying && event && tool
  return <div className="score-correction-tools">
    <div role="toolbar" aria-label="My Score editing tools" className="score-tool-tabs">
      {(['select', 'note', 'lyrics', 'tie', 'more'] as const).map(name => <button type="button" key={name}
        disabled={disabled || readOnly} aria-label={name[0].toUpperCase() + name.slice(1)} title={name[0].toUpperCase() + name.slice(1)} aria-pressed={group === name} onClick={() => {
          setTool(name === 'lyrics' ? 'lyric' : ''); select(); onGroup?.(name)

        }}><CorrectionIcon name={{ select: 'select', note: 'duration', lyrics: 'lyric', tie: 'tie', more: 'more' }[name]} />
        {name[0].toUpperCase() + name.slice(1)}</button>)}
    </div>
    {group === 'note' && <div className="context-actions" role="group" aria-label="Note operations">
      {icon('add', 'Add note', () => { setTool(''); add() }, !editable, adding)}
      {event && !adding && <>
      {icon('delete', 'Delete selected notation', () => { void change(`events/${event!.id}`, 'DELETE') }, !editable || !event || adding || tying)}
      {icon('pitch', 'Pitch', () => choose('pitch'), !editable || !selected || adding || tying, tool === 'pitch')}
      {icon('duration', 'Duration', () => choose('duration'), !editable || !event || event.grace || adding || tying, tool === 'duration')}
      {icon('accidental', 'Accidental', () => choose('accidental'), !editable || !selected || adding || tying, tool === 'accidental')}
      {icon('size', 'Normal / Small', () => choose('size'), !editable || !event || adding || tying, tool === 'size')}
      {icon('timing', 'Duration-bearing / Grace', () => choose('timing'), !editable || !selected || event?.cue || adding || tying, tool === 'timing')}
      </>}
    </div>}
    {group === 'tie' && selected && <div className="context-actions" role="group" aria-label="Tie operations">
      {icon('tie', tying ? 'Cancel tie' : 'Add tie', () => { setTool(''); tie() }, !editable || !selected || adding || (!tying && event?.tie_source_editable === false), tying)}
      {event && <label>Destination<select aria-label="Tie destination" value={event.tie_target_id ?? ''} disabled={!editable || tying}
        onChange={e => void patch({ tie_to_event_id: e.target.value || null })}>
        <option value="">No tie</option>
        {Array.from(new Set([...(event.tie_target_ids ?? []), ...(event.tie_target_id ? [event.tie_target_id] : [])])).map(id => <option key={id} value={id}>{tieTargets.find(target => target.id === id)?.label ?? 'Existing tie target'}</option>)}
      </select></label>}
    </div>}
    {group === 'tie' && !tying && !adding && event?.tie_correction_error && <p role="status">{event.tie_correction_error}</p>}
    {group === 'tie' && tying && <div className="score-context-status" role="status">Tie mode active: the source note is selected. Choose the target note, or Cancel tie. {event?.tie_target_id && <button disabled={!editable} onClick={() => void patch({ tie_to_event_id: null })}>Remove tie</button>}</div>}
    {group === 'tie' && !adding && !tying && event?.tie_target_id && <button className="score-remove-tie" disabled={!editable} onClick={() => void patch({ tie_to_event_id: null })}>Remove tie</button>}
    {group === 'tie' && selected && <div role="group" aria-label="Tie direction">
      <button type="button" disabled={!editable || !selected || adding || tying} aria-pressed={event?.tie_direction === 'up'}
        onClick={() => void patch({ tie_direction: 'up' })}>Tie Up</button>
      <button type="button" disabled={!editable || !selected || adding || tying} aria-pressed={event?.tie_direction === 'down'}
        onClick={() => void patch({ tie_direction: 'down' })}>Tie Down</button>
    </div>}
    {group === 'note' && adding && <fieldset disabled={!editable} className="score-property-panel" aria-label="Add note properties">
      <legend>Add note</legend>
      <p role="status">{positionMeasure ? `Insertion selected in measure ${positionMeasure.number}.` : 'Click a supported empty position on the score to place the caret.'}</p>
      {event?.onset !== null && event?.staff && measure && <button onClick={() => { setVoiceChoice(event.voice); anchorPosition() }}>Use selected note’s exact onset</button>}
      <div className="score-property-fields">{pitchControls}{accidentalControl}{durationControl}
        <label>Size<select aria-label="New note size" value={display} onChange={(e) => setDisplay(e.target.value)}><option value="normal">Normal</option><option value="small">Small</option></select></label>
        <label>Timing<select aria-label="New note timing" value={grace ? 'grace' : 'duration-bearing'} onChange={(e) => setGrace(e.target.value === 'grace')}><option value="duration-bearing">Duration-bearing</option><option value="grace">Grace</option></select></label>
      </div>
      <details open={!voice || undefined}><summary>Voice{positionMeasure && positionMeasure.staves > 1 ? ` / staff ${position?.staff}` : ''}</summary>
        <label>Voice<select aria-label="New note voice" value={voiceChoice || defaultVoice} onChange={(e) => setVoiceChoice(e.target.value)}>
          <option value="">Choose voice</option>{voices.map((v, i) => <option key={v} value={v}>Voice {i + 1}</option>)}
          {!voices.length && <option value="1">Primary voice</option>}<option value="secondary">New secondary voice</option>
        </select></label>
      </details>
      <button disabled={!position || !positionMeasure || !effectivePitch || !voice || (voiceChoice !== 'secondary' && voices.length > 0 && !voices.includes(voice)) || !options.some(([value]) => value === duration)} onClick={() => position && void change('events', 'POST', { measure_id: position.measureId, onset: position.onset, staff: position.staff, voice, kind: 'note', pitch: effectivePitch, duration, display_size: display, grace, written_accidental: explicitAccidental })}>Add</button>
      <button onClick={select}>Cancel</button>
    </fieldset>}
    {(group === 'note' || group === 'lyrics') && panel && <fieldset disabled={!editable} className="score-property-panel" aria-label={`${tool} properties`}><legend>{tool === 'size' ? 'Display size' : tool === 'timing' ? 'Timing' : tool[0].toUpperCase() + tool.slice(1)}</legend>
      <div className="score-property-fields">
        {tool === 'pitch' && <>{pitchControls}<button onClick={() => void patch({ pitch })}>Apply pitch</button></>}
        {tool === 'accidental' && <>{accidentalControl}<button disabled={!effectivePitch} onClick={() => void patch({ pitch: effectivePitch, written_accidental: explicitAccidental })}>Apply accidental</button></>}
        {tool === 'duration' && durationControl}
        {tool === 'size' && <label>Size<select aria-label="Selected note size" value={event.display_size} onChange={(e) => void patch({ display_size: e.target.value })}>
          {event.display_size === 'cue' && <option value="cue">Current cue display</option>}<option value="normal">Normal</option><option value="small">Small</option>
        </select></label>}
        {tool === 'timing' && <>{event.grace && durationControl}<label>Timing<select aria-label="Selected note timing" value={event.grace ? 'grace' : 'duration-bearing'} onChange={(e) => void patch(e.target.value === 'grace' ? { grace: true } : { grace: false, duration })}><option value="duration-bearing">Duration-bearing</option><option value="grace">Grace</option></select></label></>}
      </div>
      {group === 'lyrics' && <LyricEditor event={event} lyrics={review.score.lyrics.filter((l) => l.event_id === event.id)} busy={disabled} change={change} lyricOwner={lyricOwner} selectLyricOwner={selectLyricOwner} />}
      <button onClick={() => setTool('')}>Close properties</button>
    </fieldset>}
    {context}
  </div>
}
