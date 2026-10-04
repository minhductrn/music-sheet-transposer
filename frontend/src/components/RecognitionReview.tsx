import { useRef, useState } from 'react'
import { changeReview, closeReview, getReview, getVerifiedMusicXml } from '../services/api'
import type { Harmony, Measure, ReviewIssue, ReviewSession, ScoreSelection } from '../types/review'
import EventInspector from './EventInspector'
import { eventLabel, validDuration } from '../utils/review'
import MusicSheetViewer from './MusicSheetViewer'
import SourceViewer from './SourceViewer'

type Change = (path: string, method: 'POST' | 'PATCH' | 'DELETE', body?: unknown) => Promise<void>

function TextEditor({ text, label, busy, save }: { text: string; label: string; busy: boolean; save: (value: string) => void }) {
  const [value, setValue] = useState(text)
  return <div className="review-text-editor">
    <label>{label}<input value={value} disabled={busy} onChange={(e) => setValue(e.target.value)} /></label>
    <button type="button" disabled={busy || value === text} onClick={() => save(value)}>Save</button>
  </div>
}

const harmonyKinds = ['major', 'minor', 'dominant', 'major-seventh', 'minor-seventh', 'diminished', 'augmented', 'suspended-second', 'suspended-fourth', 'other', 'none']

function HarmonyEditor({ harmony, measure, busy, change }: { harmony?: Harmony; measure: Measure; busy: boolean; change: Change }) {
  const initialRoot = harmony ? harmony.root_step ?? '' : 'C'
  const initialAlter = harmony?.root_alter ?? '0'
  const initialKind = harmony ? harmony.kind ?? '' : 'major'
  const [root, setRoot] = useState(initialRoot)
  const [alter, setAlter] = useState(initialAlter)
  const [kind, setKind] = useState(initialKind)
  const [text, setText] = useState(harmony?.text ?? '')
  const [anchor, setAnchor] = useState(measure.voices[0]?.events[0]?.id ?? '')
  async function save() {
    if (harmony) {
      const patch: Record<string, string> = {}
      if (root !== initialRoot) patch.root_step = root
      if (alter !== initialAlter) patch.root_alter = alter
      if (kind !== initialKind) patch.kind = kind
      if (text !== harmony.text) patch.text = text
      if (Object.keys(patch).length) await change(`harmonies/${harmony.id}`, 'PATCH', patch)
    } else {
      await change('harmonies', 'POST', { measure_id: measure.id, before_event_id: anchor || undefined,
        root_step: root, root_alter: alter, kind, text })
    }
  }
  return <fieldset disabled={busy} className="review-fields">
    <legend>{harmony ? `Harmony at onset ${harmony.onset ?? '?'}` : 'Add harmony'}</legend>
    {!harmony && <label>Before event <select value={anchor} onChange={(e) => setAnchor(e.target.value)}>
      <option value="">Measure end</option>{measure.voices.flatMap((v) => v.events).map((event) => <option key={event.id} value={event.id}>{eventLabel(event)}</option>)}
    </select></label>}
    <label>Root <select value={root} onChange={(e) => setRoot(e.target.value)}>{!initialRoot && <option value="">Choose root</option>}{'CDEFGAB'.split('').map((value) => <option key={value}>{value}</option>)}</select></label>
    <label>Root alter <input value={alter} onChange={(e) => setAlter(e.target.value)} /></label>
    <label>Kind <select value={kind} onChange={(e) => setKind(e.target.value)}>{!initialKind && <option value="">Choose kind</option>}{Array.from(new Set([kind, ...harmonyKinds])).filter(Boolean).map((value) => <option key={value}>{value}</option>)}</select></label>
    <label>Displayed symbol <input value={text} onChange={(e) => setText(e.target.value)} /></label>
    <button type="button" onClick={() => void save()}>{harmony ? 'Save harmony' : 'Add harmony'}</button>
  </fieldset>
}

function IssueHandling({ issue, busy, change }: { issue: ReviewIssue; busy: boolean; change: Change }) {
  const [note, setNote] = useState('')
  return <div>
    {issue.handling.note && <p>Handling: {issue.handling.note}</p>}
    {issue.status === 'REVIEW_REQUIRED' && <>
      <label>Correction / source comparison note <input disabled={busy} value={note} maxLength={2000}
        onChange={(event) => setNote(event.target.value)} /></label>
      <button type="button" disabled={busy || !note.trim() || !issue.can_mark_corrected}
        onClick={() => void change('issues/resolve', 'POST', { issue_id: issue.id, disposition: 'MANUALLY_CORRECTED', note })}>Confirm related correction</button>
      <button type="button" disabled={busy || !note.trim()}
        onClick={() => void change('issues/resolve', 'POST', { issue_id: issue.id, disposition: 'ACCEPTED', note })}>Accept after source comparison</button>
    </>}
  </div>
}

function EmptyMeasureAdder({ measure, busy, change }: { measure: Measure; busy: boolean; change: Change }) {
  const [step, setStep] = useState('C')
  const [octave, setOctave] = useState(4)
  const [duration, setDuration] = useState('1')
  const [kind, setKind] = useState('note')
  return <fieldset disabled={busy} className="review-fields">
    <legend>Add the first event to this measure</legend>
    <label>Kind <select value={kind} onChange={(e) => setKind(e.target.value)}><option>note</option><option>rest</option></select></label>
    <label>Step <select value={step} onChange={(e) => setStep(e.target.value)}>{'CDEFGAB'.split('').map((value) => <option key={value}>{value}</option>)}</select></label>
    <label>Octave <input type="number" min={0} max={9} value={octave} onChange={(e) => setOctave(Number(e.target.value))} /></label>
    <label>Quarter beats <input value={duration} onChange={(e) => setDuration(e.target.value)} /></label>
    <button type="button" disabled={!validDuration(duration) || !Number.isInteger(octave) || octave < 0 || octave > 9} onClick={() => void change('events', 'POST', { measure_id: measure.id, kind, duration,
      pitch: kind === 'note' ? { step, alter: '0', octave } : undefined })}>Add event</button>
  </fieldset>
}

interface Props {
  review: ReviewSession
  onChange: (review: ReviewSession | null) => void
  onBusy: (busy: boolean) => void
  download: (blob: Blob, filename: string) => void
}

export default function RecognitionReview({ review, onChange, onBusy, download }: Props) {
  const [measureId, setMeasureId] = useState('')
  const [voiceId, setVoiceId] = useState('')
  const [eventId, setEventId] = useState('')
  const [busy, setBusy] = useState(false)
  const pending = useRef(false)
  const [candidateId, setCandidateId] = useState('')
  const [error, setError] = useState('')
  const [confirmedRevision, setConfirmedRevision] = useState<number | null>(null)
  const measures = review.score.parts.flatMap((part) => part.measures.map((measure) => ({ part, measure })))
  const current = measures.find((entry) => entry.measure.id === measureId) ?? measures[0]
  const measure = current?.measure
  const voice = measure?.voices.find((item) => item.id === voiceId) ?? measure?.voices[0]
  const event = voice?.events.find((item) => item.id === eventId) ?? voice?.events[0]
  const selectedIssue = review.review_issues.find((issue) => issue.id === candidateId
    && (issue.event_id ?? issue.anchor_id) === event?.id)
    ?? review.review_issues.find((issue) => (issue.event_id ?? issue.anchor_id) === event?.id)
  const tieTargets = current?.part.measures.filter((m) => m.index === measure?.index || m.index === (measure?.index ?? -2) + 1)
    .flatMap((m) => m.voices.flatMap((v) => v.events.filter((e) => e.kind === 'note' && !e.grace)
      .map((e) => ({ id: e.id, label: `Measure ${m.number} · voice ${e.voice} · ${eventLabel(e)}` })))) ?? []
  const selectedId = event?.id
  const selectedIndex = measure?.index
  const selectedOnset = event?.onset ?? null
  const selectedLabel = measure && event ? `${current.part.name || current.part.id}, measure ${measure.number}, voice ${event.voice}, ${eventLabel(event)}` : ''
  const selection: ScoreSelection | null = selectedId && selectedIndex !== undefined ? {
    eventId: selectedId, measureIndex: selectedIndex, onset: selectedOnset, label: selectedLabel,
  } : null

  async function perform(action: () => Promise<ReviewSession | null>) {
    if (pending.current) return
    pending.current = true
    setBusy(true)
    onBusy(true)
    setError('')
    try {
      const updated = await action()
      if (updated) {
        const oldIds = new Set(review.score.parts.flatMap((p) => p.measures.flatMap((m) => m.voices.flatMap((v) => v.events.map((e) => e.id)))))
        const entries = updated.score.parts.flatMap((p) => p.measures.flatMap((m) =>
          m.voices.flatMap((v) => v.events.map((e) => ({ measureId: m.id, event: e })))))
        const selected = entries.find(({ event: e }) => !oldIds.has(e.id))
          ?? entries.find(({ event: e }) => e.id === event?.id)
        if (selected) {
          setMeasureId(selected.measureId)
          setVoiceId(selected.event.voice)
          setEventId(selected.event.id)
        }
      }
      if (updated !== review) onChange(updated)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Correction failed. Reload the review and try again.')
    } finally {
      pending.current = false
      setBusy(false)
      onBusy(false)
    }
  }

  const change: Change = (path, method, body) => perform(() => changeReview(review, path, method, body))

  return <section className="status-card recognition-review">
    <h2>Recognition Review — <span className={`review-state state-${review.state}`}>{review.state.replaceAll('_', ' ')}</span></h2>
    <p role="status">{busy ? 'Applying correction / validating…' : review.state === 'VERIFIED'
      ? 'Approved for transposition and export.' : `${review.validation.unresolved_issue_count} unresolved issues · ${review.validation.error_count} blocking errors. Correct or explicitly handle issues, then verify.`}</p>
    <p>Compare with the original. Structural validation cannot establish recognition accuracy. Corrections do not run Audiveris again.</p>
    <p className="review-hint">This local session expires at {new Date(review.expires_at * 1000).toLocaleTimeString()}. Download corrected XML before closing or restarting the backend.</p>
    <div className="review-toolbar">
      <button disabled={busy || !review.can_undo} onClick={() => void change('undo', 'POST')}>Undo</button>
      <button disabled={busy || !review.can_redo} onClick={() => void change('redo', 'POST')}>Redo</button>
      <button disabled={busy} onClick={() => void perform(() => getReview(review.id))}>Reload review</button>
      <button disabled={busy} onClick={() => download(review.musicXml, review.state === 'VERIFIED' ? 'verified.musicxml' : 'review-draft.musicxml')}>Download corrected XML</button>
      <button disabled={busy || review.state !== 'VERIFIED'} onClick={() => void perform(async () => {
        download(await getVerifiedMusicXml(review.id), 'corrected-verified.musicxml')
        return review
      })}>Export verified corrected MusicXML</button>
      <button disabled={busy} onClick={() => void perform(async () => { await closeReview(review.id); return null })}>Close review</button>
    </div>
    {error && <p role="alert" className="status-error">{error}</p>}
    <details open>
      <summary>Review issues ({review.validation.unresolved_issue_count} unresolved)</summary>
      <p>Evidence retains its original confidence and reasons. Apply corrections, then confirm handling with a note, or explicitly accept notation after source comparison. Handling does not prove OMR accuracy.</p>
      {!review.review_issues.length && <p>No candidate issues recorded. Compare the whole score with the source before verification.</p>}
      <ul>{review.review_issues.map((candidate) => <li key={candidate.id}>
        <strong>{candidate.status.replaceAll('_', ' ')}</strong> · {candidate.classification.replaceAll('_', ' ')} · {candidate.confidence}
        {candidate.pitch && ` · ${candidate.pitch.step} (alter ${candidate.pitch.alter}) ${candidate.pitch.octave}`}
        {` · page ${candidate.evidence.sheet}, staff ${candidate.evidence.staff_number ?? '?'}, head ${candidate.evidence.id}`}
        <p>{candidate.diagnostics.map((reason) => reason.replaceAll('_', ' ')).join('; ')}.</p>
        <button disabled={busy || !measures.some(({ measure: m }) => m.voices.some((v) => v.events.some((e) => e.id === (candidate.event_id ?? candidate.anchor_id))))}
          onClick={() => {
            const id = candidate.event_id ?? candidate.anchor_id
            const target = measures.find(({ measure: m }) => m.voices.some((v) => v.events.some((e) => e.id === id)))
            const targetVoice = target?.measure.voices.find((v) => v.events.some((e) => e.id === id))
            if (target && targetVoice && id) { setCandidateId(candidate.id); setMeasureId(target.measure.id); setVoiceId(targetVoice.id); setEventId(id) }
          }}>Inspect related event and source</button>
        <IssueHandling key={`${review.revision}-${candidate.id}`} issue={candidate} busy={busy} change={change} />
      </li>)}</ul>
      {review.semantic_recovery?.diagnostics.length ? <p>{review.semantic_recovery.diagnostics.map((reason) => reason.replaceAll('_', ' ')).join('; ')}.</p> : null}
    </details>
    <div className="review-comparison">
      <SourceViewer review={review} location={selectedIssue?.source_location ?? null} />
      <div className="review-score"><MusicSheetViewer musicXml={review.musicXml} title="Corrected score" selection={selection} /></div>
    </div>
    <p className="review-hint">Select events below. The cursor marks measure/beat, with pitch, voice and staff identified in the inspector. OSMD’s mixed-size chord preview may differ from the original; per-note sizes and timing remain in the XML.</p>
    <div className="review-fields review-navigator">
      <label>Part / measure <select disabled={busy} value={measure?.id ?? ''} onChange={(e) => { setMeasureId(e.target.value); setVoiceId(''); setEventId('') }}>
        {measures.map(({ part, measure: m }) => <option key={m.id} value={m.id}>{part.name || part.id} · measure {m.number} ({m.validation_state})</option>)}
      </select></label>
      <label>Voice <select disabled={busy || !voice} value={voice?.id ?? ''} onChange={(e) => { setVoiceId(e.target.value); setEventId('') }}>
        {measure?.voices.map((v) => <option key={v.id}>{v.id}</option>)}
      </select></label>
      <label>Event <select disabled={busy || !event} value={event?.id ?? ''} onChange={(e) => setEventId(e.target.value)}>
        {voice?.events.map((item) => <option key={item.id} value={item.id}>{eventLabel(item)}</option>)}
      </select></label>
    </div>
    {measure && <p>Timing: {measure.actual_duration ?? '?'} / {measure.expected_duration ?? '?'} quarter beats. Divisions: {measure.divisions ?? '?'}. Staff count: {measure.staves}.</p>}
    {selectedIssue && <p className="review-selection">Selected issue: {selectedIssue.status.replaceAll('_', ' ')} · {selectedIssue.confidence} · {selectedIssue.diagnostics.join('; ')}</p>}
    {event && measure ? <EventInspector key={`${review.revision}-${event.id}`} event={event} measure={measure} tieTargets={tieTargets} busy={busy} change={change} />
      : measure && <EmptyMeasureAdder key={`${review.revision}-${measure.id}`} measure={measure} busy={busy} change={change} />}
    <details>
      <summary>Title, lyrics and chord symbols</summary>
      <TextEditor key={`title-${review.revision}`} text={review.score.metadata.title} label="Score title" busy={busy}
        save={(text) => void change('metadata/title', 'PATCH', { text })} />
      {review.score.metadata.credits.map((credit) => <TextEditor key={`${review.revision}-${credit.id}`} text={credit.text} label="Printed credit" busy={busy}
        save={(text) => void change(`credits/${credit.id}`, 'PATCH', { text })} />)}
      <h3>Lyrics on selected event</h3>
      {review.score.lyrics.filter((lyric) => lyric.event_id === event?.id).map((lyric) =>
        (lyric.segments.length ? lyric.segments : ['']).map((text, index) => <TextEditor key={`${review.revision}-${lyric.id}-${index}`} text={text}
          label={`Verse ${lyric.number}${lyric.segments.length > 1 ? `, segment ${index + 1}` : ''}`} busy={busy}
          save={(value) => void change(`lyrics/${lyric.id}`, 'PATCH', { text: value, segment_index: index })} />))}
      {event && <NewLyric key={`${review.revision}-${event.id}`} busy={busy} add={(text, number) => void change(`events/${event.id}/lyrics`, 'POST', { text, number })} />}
      <h3>Harmony in selected measure</h3>
      {measure && <>
        {review.score.harmonies.filter((h) => h.measure_id === measure.id).map((h) => <HarmonyEditor key={`${review.revision}-${h.id}`} harmony={h} measure={measure} busy={busy} change={change} />)}
        <HarmonyEditor key={`new-harmony-${review.revision}-${measure.id}`} measure={measure} busy={busy} change={change} />
      </>}
    </details>
    <h3>Validation and verification</h3>
    <p>{review.validation.error_count} errors · {review.validation.warning_count} warnings</p>
    <ul className="review-diagnostics">{review.validation.diagnostics.map((issue, index) => <li key={`${issue.code}-${index}`} className={issue.severity === 'ERROR' ? 'status-error' : ''}>
      <strong>{issue.severity}</strong>{issue.measure_id && ` · ${measures.find((m) => m.measure.id === issue.measure_id)?.measure.number ?? issue.measure_id}`}: {issue.message}
      {issue.event_id && <button disabled={busy} onClick={() => {
        const target = measures.find(({ measure: m }) => m.voices.some((v) => v.events.some((e) => e.id === issue.event_id)))
        const targetVoice = target?.measure.voices.find((v) => v.events.some((e) => e.id === issue.event_id))
        if (target && targetVoice) { setMeasureId(target.measure.id); setVoiceId(targetVoice.id); setEventId(issue.event_id!); setCandidateId('') }
      }}>Inspect event</button>}
    </li>)}</ul>
    {review.validation.truncated && <p>Additional diagnostics were omitted; all errors still block verification.</p>}
    <button disabled={busy} onClick={() => void change('validate', 'POST')}>Validate corrections</button>
    <label className="review-confirmation"><input type="checkbox" disabled={busy} checked={confirmedRevision === review.revision}
      onChange={(e) => setConfirmedRevision(e.target.checked ? review.revision : null)} /> I compared this corrected score with the original, including pitches, sizes, rhythms, lyrics and chord symbols.</label>
    <button disabled={busy || !review.validation.can_verify || confirmedRevision !== review.revision || review.state === 'VERIFIED'}
      onClick={() => void change('verify', 'POST', { confirmed_source_comparison: true })}>Mark VERIFIED</button>
    {review.state === 'VERIFIED' && <p className="status-success">Verified corrected MusicXML is ready for transposition. Any further correction requires verification again. <a href="#transposition-controls">Continue to transposition</a></p>}
  </section>
}

function NewLyric({ busy, add }: { busy: boolean; add: (text: string, number: string) => void }) {
  const [text, setText] = useState('')
  const [number, setNumber] = useState('1')
  return <div className="review-fields"><label>New lyric <input disabled={busy} value={text} onChange={(e) => setText(e.target.value)} /></label>
    <label>Verse <input disabled={busy} value={number} onChange={(e) => setNumber(e.target.value)} /></label>
    <button disabled={busy || !text} onClick={() => add(text, number)}>Add lyric</button></div>
}
