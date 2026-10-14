import { useEffect, useRef, useState } from 'react'
import MusicSheetViewer from './MusicSheetViewer'
import RecognitionReview from './RecognitionReview'
import type { ReviewSession } from '../types/review'
import { getConcertKey, transposeConcertKey, createReview, closeReview, changeReview, getVerifiedMusicXml } from '../services/api'
import type { ConcertKey, ConcertKeyDetection } from '../services/api'
import { chooseScoreFile, writeScoreFile } from '../utils/localScoreFile'
import type { SavedScoreFile } from '../utils/localScoreFile'

const KEYS = {
  major: ['C♭', 'G♭', 'D♭', 'A♭', 'E♭', 'B♭', 'F', 'C', 'G', 'D', 'A', 'E', 'B', 'F♯', 'C♯'],
  minor: ['A♭', 'E♭', 'B♭', 'F', 'C', 'G', 'D', 'A', 'E', 'B', 'F♯', 'C♯', 'G♯', 'D♯', 'A♯'],
}
const keyName = (key: ConcertKey) => `${KEYS[key.mode][key.fifths + 7]} ${key.mode}`
interface Source { blob: Blob; filename: string; detection: ConcertKeyDetection }
interface Result { blob: Blob; filename: string; label: string }

export default function ConcertTranspose({ sourceFile, disabled, download, onPending, onBusy }: {
  sourceFile: SavedScoreFile
  disabled: boolean
  download: (blob: Blob, filename: string) => void
  onPending: (pending: boolean) => void
  onBusy: (busy: boolean) => void
}) {
  const [source, setSource] = useState<Source | null>(null)
  const [sourceKey, setSourceKey] = useState<ConcertKey | null>(null)
  const [confirmed, setConfirmed] = useState(false)
  const [target, setTarget] = useState(0)
  const [direction, setDirection] = useState<'up' | 'down'>('up')
  const [result, setResult] = useState<Result | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [saveState, setSaveState] = useState<'unsaved' | 'requested' | 'confirmed'>('unsaved')
  const working = useRef(false)
  const [editor, setEditor] = useState<ReviewSession | null>(null)
  const [editorBusy, setEditorBusy] = useState(false)
  const [savedResult, setSavedResult] = useState<SavedScoreFile | null>(null)
  const [requested, setRequested] = useState<SavedScoreFile | null>(null)
  const session = useRef<string | null>(null)
  const unsaved = editor !== null && !(savedResult?.reviewId === editor.id && savedResult.revision === editor.revision)
  useEffect(() => { onPending(unsaved) }, [unsaved, onPending])
  useEffect(() => { onBusy(busy || editorBusy) }, [busy, editorBusy, onBusy])
  useEffect(() => {
    let active = true
    getConcertKey(sourceFile.blob).then(detection => {
      if (!active) return
      setSource({ ...sourceFile, detection }); setSourceKey(detection.suggested); setTarget(detection.fifths)
    }).catch(cause => { if (active) setError(cause instanceof Error ? cause.message : 'Unable to inspect source.') })
    return () => {
      active = false
      if (session.current) void closeReview(session.current).catch(() => {})
    }
  }, [sourceFile])

  function mayReplace() {
    return !unsaved || window.confirm('The unsaved Transposed Concert result will be replaced. Continue?')
  }
  function clearResult() {
    if (session.current) void closeReview(session.current).catch(() => {})
    session.current = null
    setEditor(null); setResult(null); setSavedResult(null); setRequested(null); setSaveState('unsaved')
  }


  async function perform(action: () => Promise<void>) {
    if (disabled || working.current) return
    working.current = true
    setBusy(true); setError('')
    try { await action() }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Unable to process the Concert MusicXML.') }
    finally { working.current = false; setBusy(false) }
  }

  const locked = disabled || busy || editorBusy
  const compatible = sourceKey !== null && sourceKey.fifths === source?.detection.fifths
  return <section className="concert-editor">
    {source && <div className="concert-controls">
      <div className="concert-key-row">
      {sourceKey && <label>Key<select id="concert-target-key" value={target} disabled={locked || !compatible} onChange={event => {
        if (!mayReplace()) return
        clearResult()
        setTarget(Number(event.target.value)); setResult(null); setSaveState('unsaved')
      }}>{KEYS[sourceKey.mode].map((name, index) => <option key={index} value={index - 7}>{name} {sourceKey.mode}</option>)}</select></label>}
        {!sourceKey && <label>Key<select disabled aria-label="Key"><option>Confirm Source Key</option></select></label>}
        <label>Instrument<select aria-label="Instrument" defaultValue="concert" disabled={locked}>
          <option value="concert">Concert (Original pitch)</option>
          <option disabled>Alto Saxophone — unavailable</option>
          <option disabled>Soprano Saxophone — unavailable</option>
          <option disabled>Tenor Saxophone — unavailable</option>
        </select></label>
      </div>
      <details className="source-key-confirmation" open={!confirmed}><summary>Source Key{confirmed && sourceKey ? ` · ${keyName(sourceKey)} confirmed` : ' · confirmation required'}</summary>

      <p>Source: {source.filename} (saved snapshot; later editor changes are excluded).</p>
      <p>Detected key signature: {source.detection.fifths === 0 ? 'No sharps or flats' : `${Math.abs(source.detection.fifths)} ${source.detection.fifths < 0 ? 'flat' : 'sharp'}${Math.abs(source.detection.fifths) === 1 ? '' : 's'}`}.</p>
      {source.detection.suggested
        ? <p>Suggested Source Key from MusicXML: {keyName(source.detection.suggested)}. Confirm or correct it.</p>
        : <p>Mode is not declared. Compatible candidates: {source.detection.candidates.map(keyName).join(' or ')}. Choose and confirm; neither is assumed.</p>}
      <label>Source Key<select id="concert-source-key" value={sourceKey ? `${sourceKey.mode}:${sourceKey.fifths}` : ''} disabled={locked} onChange={event => {
        if (!mayReplace()) return
        clearResult()
        const [mode, fifths] = event.target.value.split(':')
        setSourceKey(mode ? { mode: mode as ConcertKey['mode'], fifths: Number(fifths) } : null)
        setConfirmed(false); setResult(null); setSaveState('unsaved'); setError(''); setTarget(source.detection.fifths)
      }}>
        <option value="">Choose Source Key</option>
        {(['major', 'minor'] as const).flatMap(mode => KEYS[mode].map((name, index) => <option key={`${mode}:${index}`} value={`${mode}:${index - 7}`}>{name} {mode}</option>))}
      </select></label>
      {sourceKey && !compatible && <p role="alert">The selected Source Key is incompatible with the detected key signature. Choose one of: {source.detection.candidates.map(keyName).join(' or ')}.</p>}
      <label><input id="concert-source-confirmed" type="checkbox" checked={confirmed} disabled={locked || !compatible} onChange={event => {
        if (!mayReplace()) return
        clearResult()
        setConfirmed(event.target.checked && compatible); setResult(null); setSaveState('unsaved')
      }} />I confirm the Source Key{sourceKey ? `: ${keyName(sourceKey)}` : ''}</label>
      </details>
      <div className="concert-apply-row">
      <label>Interval direction<select value={direction} disabled={locked} onChange={event => {
        if (!mayReplace()) return
        clearResult()
        setDirection(event.target.value as 'up' | 'down'); setResult(null); setSaveState('unsaved')
      }}><option value="up">Up, within one octave</option><option value="down">Down, within one octave</option></select></label>
      <button disabled={locked || !confirmed || !compatible} onClick={() => void perform(async () => {
        if (!confirmed || !compatible || !sourceKey || !mayReplace()) return
        const blob = await transposeConcertKey(source.blob, target, direction, sourceKey)
        const opened = await createReview(blob)
        clearResult()
        session.current = opened.id
        setEditor(opened)
        const name = keyName({ fifths: target, mode: sourceKey.mode })
        setResult({ blob, label: name, filename: `${source.filename.replace(/\.[^.]+$/, '')}-${name.replaceAll(' ', '-')}.musicxml` })
      })}>Apply</button>
      </div>
    </div>}
    {error && <p role="alert" className="status-error">{error}</p>}
    <div className="concert-workspace">
      <section aria-label="Original Concert" className="concert-panel">
        <MusicSheetViewer musicXml={sourceFile.blob} interactive={false} title="Original"
          headerActions={<span className="panel-key">{sourceKey ? `${keyName(sourceKey)}${confirmed ? '' : ' (unconfirmed)'}` : 'Read-only'}</span>} />
        <p>{sourceFile.filename} · Read-only</p>
      </section>
      <section aria-label="Transposed Concert" className="concert-panel">

        {editor ? <fieldset disabled={locked} className="review-access">
          <RecognitionReview key={editor.id} review={editor} resultOnly savedFile={savedResult} download={download}
            onBusy={setEditorBusy} onChange={updated => { setEditor(updated); setRequested(null); setSaveState('unsaved') }} />
        </fieldset> : <><div className="score-panel-header"><h3>My Score</h3></div><p className="score-placeholder">Confirm Source Key, then Apply.</p></>}
      </section>
    </div>
    {result && editor && <div className="concert-save-controls">
      <p role="status">{unsaved ? 'Unsaved Transposed Concert result' : `You confirmed saving ${savedResult?.filename}.`}</p>
      <button disabled={locked} onClick={() => void perform(async () => {
        if (!editor.validation.can_verify) throw new Error('Correct the technical score errors before saving.')
        const destination = await chooseScoreFile(true, null, result.filename, { prompt: window.prompt.bind(window) })
        if (!destination) return
        if (destination.filename.toLowerCase() === sourceFile.filename.toLowerCase()) {
          throw new Error('Choose a new filename to keep the original Concert score unchanged.')
        }
        const validated = editor.state === 'VERIFIED' ? editor
          : await changeReview(editor, 'verify', 'POST', { confirmed_source_comparison: true })
        setEditor(validated)
        const blob = await getVerifiedMusicXml(validated.id)
        await writeScoreFile(blob, destination, download)
        setResult({ ...result, filename: destination.filename })
        setRequested({ reviewId: validated.id, revision: validated.revision, blob, filename: destination.filename })
        setSaveState('requested')
      })} aria-label="Save Concert MusicXML">Save</button>

      {saveState === 'requested' && requested?.revision === editor.revision && <p role="status">Download requested. Keep the file, then <button disabled={locked} onClick={() => {
        setSavedResult(requested); setSaveState('confirmed')
      }}>I saved the Concert result</button></p>}
    </div>}
  </section>
}
