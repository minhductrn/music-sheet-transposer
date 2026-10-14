import { chooseScoreFile, writeScoreFile, type ScoreFileHandle, type SavedScoreFile } from '../utils/localScoreFile'
import { currentLyric, type LyricBinding } from '../utils/lyricInteraction'
import { useRef, useState, type ReactNode } from 'react'
import { changeReview, checkReviewMusic, closeReview, getReview, getVerifiedMusicXml } from '../services/api'
import type { MusicCheckResult, Harmony, Measure, ReviewSession, ScoreSelection } from '../types/review'
import EventInspector from './EventInspector'
import { eventLabel, validDuration } from '../utils/review'
import MusicSheetViewer from './MusicSheetViewer'
import SourceViewer from './SourceViewer'
import VisualNoteEditor, { AuxiliaryLyricNotice } from './VisualNoteEditor'
import MusicalPositionEditor from './MusicalPositionEditor'
import ScoreCorrectionToolbar, { type EditorTool } from './ScoreCorrectionToolbar'
import type { VisualInsertionPosition } from '../utils/scoreInsertion'
import { auxiliaryLyricOwner, friendlyDiagnostic, sessionExpired } from '../utils/visualReview'

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
  savedFile?: SavedScoreFile | null
  onSaved?: (file: SavedScoreFile) => void
  moreControls?: ReactNode
  resultOnly?: boolean
  transposed?: Blob | null
}

export default function RecognitionReview({ review, onChange, onBusy, download, transposed = null, savedFile = null, onSaved, resultOnly = false, moreControls }: Props) {
  const [musicCheck, setMusicCheck] = useState<MusicCheckResult | null>(null)
  const [editorTool, setEditorTool] = useState<EditorTool>('select')
  const [advanced, setAdvanced] = useState(false)
  const [rightView, setRightView] = useState('corrected')
  const [positionStaff, setPositionStaff] = useState(1)
  const [adding, setAdding] = useState(false)
  const [insertionPosition, setInsertionPosition] = useState<VisualInsertionPosition | null>(null)
  const [tieSource, setTieSource] = useState('')
  const [expired, setExpired] = useState(false)
  const [measureId, setMeasureId] = useState('')
  const [voiceId, setVoiceId] = useState('')
  const [eventId, setEventId] = useState('-')
  const [busy, setBusy] = useState(false)
  const pending = useRef(false)
  const [error, setError] = useState('')
  const fileHandle = useRef<ScoreFileHandle | null>(null)
  const [filename, setFilename] = useState('concert-score.musicxml')
  const [pendingDownload, setPendingDownload] = useState<SavedScoreFile | null>(null)
  const [saveMessage, setSaveMessage] = useState('')
  const saved = savedFile?.reviewId === review.id && savedFile.revision === review.revision
  const measures = review.score.parts.flatMap((part) => part.measures.map((measure) => ({ part, measure })))
  const current = measures.find((entry) => entry.measure.id === measureId) ?? measures[0]
  const measure = current?.measure
  const voice = measure?.voices.find((item) => item.id === voiceId) ?? measure?.voices[0]
  const event = eventId === '-' ? undefined : voice?.events.find((item) => item.id === eventId) ?? (eventId ? undefined : voice?.events[0])
  const tieTargets = current?.part.measures.flatMap((m) => m.voices.flatMap((v) => v.events.filter((e) => e.kind === 'note')
    .map((e) => ({ id: e.id, label: `Measure ${m.number} · voice ${e.voice} · ${eventLabel(e)}` })))) ?? []
  const selectedId = event?.id
  const selectedIndex = measure?.index
  const selectedOnset = event?.onset ?? null
  const selectedLabel = !advanced ? `A ${event?.kind === 'rest' ? 'rest' : 'note'}` : measure && event ? `${current.part.name || current.part.id}, measure ${measure.number}, voice ${event.voice}, ${eventLabel(event)}` : ''
  const selection: ScoreSelection | null = selectedId && selectedIndex !== undefined ? {
    eventId: selectedId, measureIndex: selectedIndex, onset: selectedOnset, label: selectedLabel,
  } : null

  function selectEvent(id: string) {
    if (busy || expired) return
    if (tieSource) {
      const source = measures.flatMap(({ measure: m }) => m.voices.flatMap((v) => v.events)).find((e) => e.id === tieSource)
      if (source && id !== source.id && measures.some(({ measure: m }) => m.voices.some(v => v.events.some(e => e.id === id && e.kind === 'note' && e.pitch)))) {
        setTieSource('')
        void change(`events/${source.id}`, 'PATCH', { tie_to_event_id: id })
      }
      return
    }
    setAdding(false); setInsertionPosition(null)
    const target = measures.find(({ measure: m }) => m.voices.some((v) => v.events.some((e) => e.id === id)))
    const selected = target?.measure.voices.flatMap((v) => v.events).find((e) => e.id === id)
    if (target && selected) { setMeasureId(target.measure.id); setVoiceId(selected.voice); setEventId(id) }
  }
  const tieTargetIds = tieSource ? measures.flatMap(({ measure: m }) => m.voices.flatMap(v => v.events)).filter(e => e.id !== tieSource && e.kind === 'note' && e.pitch).map(e => e.id) : null

  async function perform(action: () => Promise<ReviewSession | null>, propagate = false) {
    if (pending.current) { if (propagate) throw new Error('Another correction is pending.'); return }
    pending.current = true
    setTieSource('')
    setBusy(true)
    onBusy(true)
    setError('')
    try {
      const updated = await action()
      if (updated) {
        setAdding(false); setInsertionPosition(null)
        const oldIds = new Set(review.score.parts.flatMap((p) => p.measures.flatMap((m) => m.voices.flatMap((v) => v.events.map((e) => e.id)))))
        const entries = updated.score.parts.flatMap((p) => p.measures.flatMap((m) =>
          m.voices.flatMap((v) => v.events.map((e) => ({ measureId: m.id, event: e })))))
        const selected = entries.find(({ event: e }) => !oldIds.has(e.id))
          ?? entries.find(({ event: e }) => e.id === event?.id)
        if (selected) {
          setMeasureId(selected.measureId)
          setVoiceId(selected.event.voice)
          setEventId(selected.event.id)
        } else {
          setEventId('-')
        }
        setExpired(false)
      }
      if (updated && (updated.revision !== review.revision || updated.state !== review.state)) onChange(updated)
    } catch (cause) {
      if (sessionExpired(cause)) setExpired(true)
      setError(cause instanceof Error ? cause.message : 'Correction failed. Reload the review and try again.')
      if (propagate) throw cause
    } finally {
      pending.current = false
      setBusy(false)
      onBusy(false)
    }
  }

  async function checkScore() {
    if (pending.current || expired) return
    pending.current = true; setBusy(true); onBusy(true); setError('')
    try { setMusicCheck(await checkReviewMusic(review)) }
    catch (cause) {
      if (sessionExpired(cause)) setExpired(true)
      setError(cause instanceof Error ? cause.message : 'Unable to check the score. Corrections remain unchanged.')
    } finally { pending.current = false; setBusy(false); onBusy(false) }
  }

  const showingTransposed = !!transposed && rightView === 'transposed'
  const change: Change = (path, method, body) => perform(() => changeReview(review, path, method, body))
  const lyricScope = { reviewId: review.id, revision: review.revision, score: review.score }
  const applyDirectLyric = async (binding: LyricBinding, text: string) => {
    if (busy || expired || showingTransposed || adding || tieSource || !currentLyric(binding, lyricScope))
      throw new Error('This lyric or editing mode changed. Reopen it in the current score.')
    let saved: ReviewSession | null = null
    await perform(async () => {
      saved = await changeReview(review, `lyrics/${binding.lyricId}`, 'PATCH', { text, segment_index: 0 })
      return saved
    }, true)
    const updated = saved as ReviewSession | null
    const lyric = updated?.score.lyrics.find(l => l.id === binding.lyricId && l.event_id === binding.eventId && l.number === binding.originalVerse)
    if (!updated || !lyric) throw new Error('The returned review did not confirm the canonical lyric. Reload review.')
    return { lyric, reviewId: updated.id, revision: updated.revision }
  }
  const selectDirectLyricOwner = (id: string | null) => {
    if (busy || expired || showingTransposed || adding || tieSource) return
    if (id === null) { setEditorTool('lyrics'); setAdvanced(true); return }
    const owners = review.score.lyrics.filter(l => l.id === id)
    if (owners.length !== 1) return
    const target = measures.find(({ measure: m }) => m.voices.some(v => v.events.some(e => e.id === owners[0].event_id)))
    const selected = target?.measure.voices.flatMap(v => v.events).find(e => e.id === owners[0].event_id)
    // Explicit selection only. Never route this action through the pending-tie selectEvent handler.
    if (target && selected) {
      setMeasureId(target.measure.id); setVoiceId(selected.voice); setEventId(selected.id); setEditorTool('lyrics'); setAdvanced(true)
      setError(`Selected canonical lyric ${id}, verse ${owners[0].number}. Use T (Lyric) or Lyrics on selected event in Advanced Review.`)
    }
  }
  const lyricOwner = auxiliaryLyricOwner(review.score, event)
  const selectLyricOwner = () => {
    if (!lyricOwner || !measure || busy || expired || showingTransposed) return
    // This action only selects; it must not complete a pending tie command.
    setTieSource(''); setAdding(false); setInsertionPosition(null)
    setMeasureId(measure.id); setVoiceId(lyricOwner.voice); setEventId(lyricOwner.id)
  }

  async function saveScore(saveAs: boolean) {
    if (busy || expired || pending.current) return
    setPendingDownload(null)
    setSaveMessage('')
    await perform(async () => {
      if (!review.validation.can_verify) {
        const failures = review.validation.diagnostics.filter(issue => issue.blocking).map(issue => issue.message)
        throw new Error(`Cannot save: ${failures.join(' ') || 'Correct the technical score errors shown in Advanced Review.'}`)
      }
      const target = await chooseScoreFile(saveAs, fileHandle.current, filename)
      if (!target) return review
      const validated = review.state === 'VERIFIED' ? review
        : await changeReview(review, 'verify', 'POST', { confirmed_source_comparison: true })
      // Publish validation state even if the subsequent filesystem operation fails.
      if (validated !== review) onChange(validated)
      const blob = await getVerifiedMusicXml(validated.id)
      const snapshot = { reviewId: validated.id, revision: validated.revision, blob, filename: target.filename }
      const result = await writeScoreFile(blob, target, download)
      setFilename(target.filename)
      if (result === 'written') {
        fileHandle.current = target.handle
        onSaved?.(snapshot)
        setSaveMessage(`Saved to ${target.filename}. Save writes this chosen file; Save As chooses another destination.`)
      } else {
        setPendingDownload(snapshot)
        setSaveMessage(`Download requested: ${target.filename}. This browser cannot overwrite a file or confirm download completion. Check your downloads, then confirm below.`)
      }
      return validated
    })
  }

  const contextControls = <div className="editor-context" hidden={editorTool !== 'more' && !advanced}>
    <div className="context-actions" hidden={editorTool !== 'more'}>
      <button aria-pressed={!advanced} onClick={() => { setEditorTool('select'); setAdvanced(false); setTieSource(''); setAdding(false); setInsertionPosition(null) }}>Visual Review</button>
      <button aria-pressed={advanced} onClick={() => { setEditorTool('note'); setAdvanced(true); setTieSource(''); setAdding(false); setInsertionPosition(null) }}>Advanced Review</button>
      <button disabled={busy} onClick={() => void perform(() => getReview(review.id))}>Reload review</button>
      {!resultOnly && <>
      <button disabled={busy || expired} onClick={() => void saveScore(false)}>Save</button>
      <button disabled={busy || expired} onClick={() => void saveScore(true)}>Save As</button>
      <button disabled={busy || !savedFile} onClick={() => {
        if (savedFile) download(savedFile.blob, savedFile.filename)
      }}>Export saved MusicXML</button>
      {savedFile && !saved && <span>Export uses the last saved version. Save to include current edits.</span>}
      <button disabled={busy} onClick={() => { if (!saved && !window.confirm('Close this review and discard unsaved work?')) return; void perform(async () => { await closeReview(review.id); return null }) }}>Close review</button>
      </>}
    </div>
    <details className="review-validation" hidden={editorTool !== 'more'}>
    <summary>Technical score details</summary>
    <ul className="review-diagnostics">{review.validation.diagnostics.filter(issue => issue.blocking).map((issue, index) => <li key={index}>
      {issue.message}{issue.event_id && <button disabled={busy} onClick={() => selectEvent(issue.event_id!)}>Inspect event</button>}
    </li>)}</ul>
    </details>
    <details className="review-music-check" hidden={editorTool !== 'more'}>
      <summary>Optional music check</summary>
      <p>Check score offers musical review suggestions. It never changes notation and is not required before Save.</p>
      <button disabled={busy || expired} onClick={() => void checkScore()}>Check score</button>
      {musicCheck && musicCheck.revision !== review.revision && <p role="status">The score revision changed. Run Check score again for current results.</p>}
      {musicCheck?.revision === review.revision && <div role="status">
        <p>{musicCheck.warning_count} music warnings · {musicCheck.technical_error_count} technical errors. No score changes were made.</p>
        <ul>{musicCheck.diagnostics.filter((issue) => issue.category === 'MUSIC_WARNING').map((issue) => <li key={issue.id ?? `${issue.code}-${issue.event_id}-${issue.measure_id}`}>
          {friendlyDiagnostic(issue.code, issue.message)}
          {issue.can_confirm_source && <SourceDiagnosticConfirmation key={`${review.revision}-${issue.id}`} issue={issue} measureLabel={measures.find(({ measure: m }) => m.id === issue.measure_id)?.measure.number} busy={busy || expired} change={change} />}
        </li>)}</ul>
        {musicCheck.truncated && <p>Additional findings were omitted.</p>}
      </div>}
    </details>
        {editorTool === 'more' && !resultOnly && <div role="toolbar" aria-label="Right pane view">
          <button aria-pressed={!showingTransposed} onClick={() => setRightView('corrected')}>Corrected</button>
          <button disabled={!transposed} aria-pressed={showingTransposed} onClick={() => { setRightView('transposed'); setTieSource(''); setAdding(false); setInsertionPosition(null) }}>Transposed</button>
        </div>}

    {(editorTool === 'note' || editorTool === 'more') && !showingTransposed && <div className="review-fields">
      <button disabled={busy || expired} onClick={() => { setAdding(!adding); setTieSource('') }}>Add at musical position</button>
      <label>Correction measure <select aria-label="Correction measure" disabled={busy} value={measure?.id ?? ''} onChange={(e) => { setMeasureId(e.target.value); setVoiceId(''); setEventId('-'); setPositionStaff(1); setTieSource('') }}>
        {measures.map(({ part, measure: m }) => <option key={m.id} value={m.id}>{part.name || 'Part'} · measure {m.number}</option>)}
      </select></label>
      {adding && <label>Insertion staff <select aria-label="Insertion staff" value={positionStaff} onChange={(e) => setPositionStaff(Number(e.target.value))}>
        {Array.from({ length: measure?.staves ?? 1 }, (_, i) => <option key={i + 1} value={i + 1}>Staff {i + 1}</option>)}
      </select></label>}
    </div>}
    {advanced && (editorTool === 'note' || editorTool === 'more') && !showingTransposed && adding && measure && <MusicalPositionEditor key={`position-${review.revision}-${measure.id}-${positionStaff}`} measure={measure} staff={positionStaff} voices={Array.from(new Set(['1', ...measure.voices.map((v) => v.id)]))} busy={busy || expired} change={change} />}
    {(editorTool === 'note' || editorTool === 'more') && !showingTransposed && event && measure && <details><summary>More note properties</summary><VisualNoteEditor key={`visual-${review.revision}-${event.id}`} event={event} measure={measure} measures={measures.map(({ part, measure: m }) => ({ id: m.id, label: `${part.name || "Part"} · measure ${m.number}`, staves: m.staves }))}
      lyricOwner={lyricOwner} selectLyricOwner={selectLyricOwner}
      lyrics={review.score.lyrics.filter((lyric) => lyric.event_id === event.id)} busy={busy || expired} change={change}
      startTie={() => setTieSource(event.id)} advanced={() => { setEditorTool('note'); setAdvanced(true); setTieSource(''); setAdding(false); setInsertionPosition(null) }} /></details>}

    <details hidden={(editorTool !== 'note' && editorTool !== 'tie' && editorTool !== 'more') || showingTransposed} aria-label="Advanced correction"><summary>{editorTool === 'tie' ? 'Tie endpoints and inserted-note ties' : 'Exact note properties and event navigation'}</summary>
    <div className="review-fields review-navigator">
      <label>Part / measure <select disabled={busy} value={measure?.id ?? ''} onChange={(e) => { setTieSource(''); setMeasureId(e.target.value); setVoiceId(''); setEventId('') }}>
        {measures.map(({ part, measure: m }) => <option key={m.id} value={m.id}>{part.name || part.id} · measure {m.number} ({m.validation_state})</option>)}
      </select></label>
      <label>Voice <select disabled={busy || !voice} value={voice?.id ?? ''} onChange={(e) => { setTieSource(''); setVoiceId(e.target.value); setEventId('') }}>
        {measure?.voices.map((v) => <option key={v.id}>{v.id}</option>)}
      </select></label>
      <label>Event <select disabled={busy || !voice?.events.length} value={event?.id ?? ''} onChange={(e) => { setTieSource(''); setEventId(e.target.value) }}>
        {!event && <option value="">Choose an event</option>}{voice?.events.map((item) => <option key={item.id} value={item.id}>{eventLabel(item)}</option>)}
      </select></label>
    </div>
    {measure && <p>Timing: {measure.actual_duration ?? '?'} / {measure.expected_duration ?? '?'} quarter beats. Divisions: {measure.divisions ?? '?'}. Staff count: {measure.staves}.</p>}
    {event && measure ? <EventInspector key={`${review.revision}-${event.id}`} event={event} measure={measure} tieTargets={tieTargets} busy={busy} change={change} />
      : measure && !measure.voices.some((v) => v.events.length) && <EmptyMeasureAdder key={`${review.revision}-${measure.id}`} measure={measure} busy={busy} change={change} />}
    </details>
    <details hidden={(editorTool !== 'more' && editorTool !== 'lyrics') || showingTransposed}>
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
      {event && (lyricOwner
        ? <AuxiliaryLyricNotice owner={lyricOwner} busy={busy || expired} selectOwner={selectLyricOwner} />
        : <NewLyric key={`${review.revision}-${event.id}`} busy={busy} add={(text, number) => void change(`events/${event.id}/lyrics`, 'POST', { text, number })} />)}
      <h3>Harmony in selected measure</h3>
      {measure && <>
        {review.score.harmonies.filter((h) => h.measure_id === measure.id).map((h) => <HarmonyEditor key={`${review.revision}-${h.id}`} harmony={h} measure={measure} busy={busy} change={change} />)}
        <HarmonyEditor key={`new-harmony-${review.revision}-${measure.id}`} measure={measure} busy={busy} change={change} />
      </>}
    </details>
    {editorTool === 'more' && moreControls}
  </div>

  return <section className="status-card recognition-review">
    {!resultOnly && <form id={`review-save-${review.id}`} onSubmit={event => { event.preventDefault(); void saveScore(false) }} />}
    <p className="save-status" role="status">{busy ? 'Applying changes…' : saved ? `Saved: ${savedFile?.filename}` : 'Unsaved changes'}</p>
    {saveMessage && (saved || pendingDownload?.revision === review.revision) && <p role="status">{saveMessage}</p>}
    {pendingDownload && pendingDownload.reviewId === review.id && pendingDownload.revision === review.revision && <button disabled={busy} onClick={() => {
      onSaved?.(pendingDownload); setPendingDownload(null)
      setSaveMessage('You confirmed that the downloaded MusicXML file was saved locally.')
    }}>I saved the downloaded file</button>}
    {expired && <div role="alert" className="status-error">This editing session expired. Open your saved MusicXML to continue, or download an unvalidated recovery copy of the browser-held edits.
      <button onClick={() => download(review.musicXml, 'unsaved-recovery.musicxml')}>Download recovery copy</button>
    </div>}

    <fieldset disabled={expired} className="visual-review-body">
    <div className={resultOnly ? 'concert-result-editor' : 'review-comparison'}>
      {!resultOnly && (savedFile && !review.source ? <div className="source-viewer musicxml-original">
        <MusicSheetViewer musicXml={savedFile.blob} title="Original" interactive={false} />
      </div> : <SourceViewer review={review} location={null} />)}
      <div className="review-score">
    {error && <div role="alert" className="status-error">{error}{!advanced && <details><summary>Show technical details</summary>{error}</details>}</div>}
        <MusicSheetViewer headerActions={<>
          <button aria-label="Undo" title="Undo" disabled={busy || expired || !review.can_undo} onClick={() => void change('undo', 'POST')}>↶</button>
          <button aria-label="Redo" title="Redo" disabled={busy || expired || !review.can_redo} onClick={() => void change('redo', 'POST')}>↷</button>
        </>} toolbar={<ScoreCorrectionToolbar tieTargets={tieTargets} group={editorTool} onGroup={group => { setEditorTool(group); setAdvanced(group === 'more') }} context={contextControls} key={`tools-${review.revision}-${event?.id ?? 'none'}-${adding}-${insertionPosition?.measureId ?? ''}-${insertionPosition?.staff ?? ''}`} review={review} event={event} measure={measure}
          lyricOwner={lyricOwner} selectLyricOwner={selectLyricOwner}
          anchorPosition={() => { if (event?.onset != null && event?.staff && measure) setInsertionPosition({ measureId: measure.id, onset: event.onset, staff: event.staff }) }}
          position={insertionPosition} adding={adding} tying={!!tieSource} disabled={busy || expired} readOnly={showingTransposed} change={change}
          select={() => { setAdding(false); setInsertionPosition(null); setTieSource('') }}
          add={() => { setAdding(!adding); setInsertionPosition(null); setTieSource('') }}
          tie={() => { setAdding(false); setInsertionPosition(null); setTieSource(tieSource ? '' : event?.id ?? '') }}
          advanced={() => { setEditorTool('note'); setAdvanced(true); setTieSource(''); setAdding(false); setInsertionPosition(null) }} />} lyricScope={lyricScope} onLyricApply={applyDirectLyric} onLyricOwnerSelect={selectDirectLyricOwner} musicXml={showingTransposed ? transposed : review.musicXml} title="My Score" selection={showingTransposed ? null : selection} score={review.score} onSelect={showingTransposed ? undefined : selectEvent} tieTargetIds={showingTransposed ? null : tieTargetIds} interactive={!showingTransposed && !busy && !expired}
          onPitchDrop={(id, pitch) => { if (!busy && !expired && !showingTransposed && !adding && !tieSource) void change(`events/${id}`, 'PATCH', { pitch }) }}
          insertionMode={!showingTransposed && adding} insertionPosition={insertionPosition} onPositionSelect={(position) => {
            if (busy || expired || showingTransposed) return
            setInsertionPosition(position)
            if (position) { setMeasureId(position.measureId); setPositionStaff(position.staff); setError('') }
            else setError('No unique supported musical position here. Click inside an empty measure or near an existing note position; Advanced retains exact placement controls.')
          }} />
        {showingTransposed && <p>Read-only transposition of the verified corrected master. Switch to Corrected to edit.</p>}
      </div>
    </div>
    </fieldset>
  </section>
}

function NewLyric({ busy, add }: { busy: boolean; add: (text: string, number: string) => void }) {
  const [text, setText] = useState('')
  const [number, setNumber] = useState('1')
  return <div className="review-fields"><label>New lyric <input disabled={busy} value={text} onChange={(e) => setText(e.target.value)} /></label>
    <label>Verse <input disabled={busy} value={number} onChange={(e) => setNumber(e.target.value)} /></label>
    <button disabled={busy || !text} onClick={() => add(text, number)}>Add lyric</button></div>
}

export function SourceDiagnosticConfirmation({ issue, measureLabel, busy, change }: { measureLabel?: string; issue: ReviewSession['validation']['diagnostics'][number]; busy: boolean; change: Change }) {
  const [note, setNote] = useState('')
  return <fieldset disabled={busy}>
    <legend>Source comparison{measureLabel && ` — measure ${measureLabel}`}</legend>
    <p>{friendlyDiagnostic(issue.code, issue.message)}</p>
    {issue.source_confirmed ? <p>Confirmed against source: {issue.source_confirmation?.note}</p> : <>
      <label>What matches the original source?<input aria-label="Source confirmation note" value={note} maxLength={2000} onChange={(e) => setNote(e.target.value)} /></label>
      <button disabled={!note.trim() || !issue.id} onClick={() => void change('diagnostics/confirm-source', 'POST', { diagnostic_id: issue.id, note })}>This unusual notation matches the source</button>
    </>}
  </fieldset>
}
