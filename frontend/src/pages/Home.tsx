import type { SavedScoreFile } from '../utils/localScoreFile'
import { useEffect, useState } from 'react'
import MusicSheetViewer from '../components/MusicSheetViewer'
import RecognitionReview from '../components/RecognitionReview'
import ConcertTranspose from '../components/ConcertTranspose'
import {
  closeReview,
  createReview,
  getHealth,
  transposeVerifiedReview,
  recognizeSheetMusic,
  transposeMusicXml,
} from '../services/api'
import type { InputQuality, RecognitionProfile, RecognitionResult } from '../types/recognition'
import type { ReviewSession } from '../types/review'

type ConnectionState = 'loading' | 'success' | 'error'
type TransposeState = 'idle' | 'processing' | 'success' | 'error'

export default function Home() {
  const [connectionState, setConnectionState] =
    useState<ConnectionState>('loading')
  const [statusText, setStatusText] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [semitoneInput, setSemitoneInput] = useState('0')
  const semitones = Number(semitoneInput)
  const validSemitones = /^[+-]?\d+$/.test(semitoneInput) && Number.isSafeInteger(semitones)
  const [transposeState, setTransposeState] =
    useState<TransposeState>('idle')
  const [result, setResult] = useState<Blob | null>(null)
  const [transposeError, setTransposeError] = useState('')
  const [recognized, setRecognized] = useState<RecognitionResult | null>(null)
  const [profile, setProfile] = useState<RecognitionProfile>('VOCAL_SONG')
  const [inputQuality, setInputQuality] = useState<InputQuality | ''>('')
  const [recognitionState, setRecognitionState] =
    useState<'idle' | 'recognizing' | 'success' | 'error'>('idle')
  const [recognitionError, setRecognitionError] = useState('')
  const [reviewSource, setReviewSource] = useState<File | undefined>()
  const [review, setReview] = useState<ReviewSession | null>(null)
  const [reviewBusy, setReviewBusy] = useState(false)
  const [workspaceMode, setWorkspaceMode] = useState<'review' | 'transpose'>('review')
  const [concertSource, setConcertSource] = useState<SavedScoreFile | null>(null)
  const [concertPending, setConcertPending] = useState(false)
  const [concertBusy, setConcertBusy] = useState(false)
  const [savedFile, setSavedFile] = useState<SavedScoreFile | null>(null)
  const currentSaved = savedFile?.reviewId === review?.id && savedFile?.revision === review?.revision
  const isMusicXml = file ? /\.(musicxml|xml)$/i.test(file.name) : false
  const busy = recognitionState === 'recognizing' || transposeState === 'processing' || reviewBusy || concertBusy

  function mayReplace() {
    return (!(review && !currentSaved) && !concertPending) || window.confirm('Unsaved score work will be replaced. Continue?')
  }

  useEffect(() => {
    if (!(review && !currentSaved) && !concertPending) return
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = '' }
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [review, currentSaved, concertPending])

  function clearRecognition() {
    if (review) void closeReview(review.id).catch(() => { /* Server expiry also releases abandoned sessions. */ })
    setReview(null)
    setConcertSource(null)
    setConcertPending(false)
    setConcertBusy(false)
    setWorkspaceMode('review')
    setSavedFile(null)
    setRecognized(null)
    setResult(null)
    setRecognitionState('idle')
    setRecognitionError('')
    setTransposeState('idle')
  }

  async function handleRecognize() {
    if (!file || busy || !mayReplace()) return
    setRecognitionState('recognizing')
    setRecognitionError('')
    setRecognized(null)
    setResult(null)
    setTransposeState('idle')
    try {
      if (review) await closeReview(review.id)
      setReview(null)
      const draft = await recognizeSheetMusic(file, profile, inputQuality || undefined)
      setRecognized(draft)
      setReview(await createReview(draft.baselineMusicXml ?? draft.musicXml, file, draft.omrArtifact, draft.semanticEvidenceArtifact))
      setRecognitionState('success')
    } catch (error) {
      setRecognitionError(error instanceof Error ? error.message : 'Recognition failed.')
      setRecognitionState('error')
    }
  }

  useEffect(() => {
    let cancelled = false

    getHealth()
      .then((health) => {
        if (cancelled) return
        setStatusText(health.status)
        setConnectionState('success')
      })
      .catch(() => {
        if (cancelled) return
        setConnectionState('error')
      })

    return () => {
      cancelled = true
    }
  }, [])

  async function handleTranspose() {
    if (!file || busy || !validSemitones || ((review || !isMusicXml) && (review?.state !== 'VERIFIED' || !review || !currentSaved))) return

    setTransposeState('processing')
    setTransposeError('')
    setResult(null)

    try {
      const transposedFile = review
        ? await transposeVerifiedReview(review, semitones)
        : await transposeMusicXml(file, semitones)

      setResult(transposedFile)
      setTransposeState('success')
    } catch (error) {
      setTransposeError(error instanceof Error ? error.message : 'Unable to transpose the MusicXML file.')
      setTransposeState('error')
    }
  }

  function download(blob: Blob, filename: string) {
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')

    link.href = url
    link.download = filename

    document.body.appendChild(link)
    link.click()
    link.remove()

    URL.revokeObjectURL(url)
  }

  const importSettings = <div className="import-settings">
        {!review && <details><summary>Optional comparison source for MusicXML</summary>
          <p>This separate file is used for comparison when opening MusicXML. It does not replace the recognition input.</p>
          <label htmlFor="comparison-source">Comparison PDF / Image (optional)<input id="comparison-source" type="file" accept=".pdf,.png,.jpg,.jpeg,.webp" disabled={busy}
          onChange={event => setReviewSource(event.target.files?.[0])} /></label>
        </details>}
        {file && !isMusicXml && (
          <>
            <p>
              <label htmlFor="recognition-profile">Recognition profile: </label>
              <select id="recognition-profile" value={profile} disabled={busy} onChange={(event) => {
                if (!mayReplace()) return
                setProfile(event.target.value as RecognitionProfile)
                clearRecognition()
              }}>
                <option value="VOCAL_SONG">Vocal song</option>
                <option value="SATB">SATB choir</option>
                <option value="PIANO">Piano</option>
                <option value="GENERAL">General</option>
                <option value="ORCHESTRAL">Orchestral</option>
              </select>
            </p>
            <p>
              <label htmlFor="input-quality">Source quality: </label>
              <select id="input-quality" value={inputQuality} disabled={busy} onChange={(event) => {
                if (!mayReplace()) return
                setInputQuality(event.target.value as InputQuality | '')
                clearRecognition()
              }}>
                <option value="">Profile default</option>
                <option value="Synthetic">Clean digital score</option>
                <option value="Standard">Scan or photograph</option>
                <option value="Poor">Poor-quality scan</option>
              </select>
            </p>
            <button type="button" disabled={busy} onClick={handleRecognize}>
              {recognitionState === 'recognizing' ? 'Recognizing…' : 'Recognize Sheet Music'}
            </button>
          </>
        )}
  </div>
  const recognitionControls = <>{recognized && (
        <details className="recognition-details"><summary>Recognition details</summary>

          <dl>
            <dt>Recognition profile</dt><dd>{recognized.profile.replaceAll('_', ' ')}</dd>
            <dt>Provider</dt><dd>{recognized.provider}</dd>
            <dt>Current review status</dt><dd>{review?.state.replaceAll('_', ' ') ?? 'Review not open'}</dd>
          </dl>
          {recognized.review_required && (
            <p role="status">Compare pitches, note sizes, rhythms, and lyrics with the original before transposing.</p>
          )}
          {recognized.warnings.length > 0 && (
            <details>
              <summary>Recognition checks ({recognized.warnings.length})</summary>
              <ul>{recognized.warnings.map((warning, index) => (
                <li key={`${warning.code}-${index}`}>
                  {warning.part_id && `Part ${warning.part_id}: `}
                  {warning.measure && `Measure ${warning.measure}: `}
                  {warning.message}
                </li>
              ))}</ul>
            </details>
          )}
          <button type="button" onClick={() => download(recognized.baselineMusicXml ?? recognized.musicXml, 'recognition-baseline.musicxml')}>
            Download Original Draft MusicXML
          </button>
          {recognized.omrArtifact && (
            <button type="button" onClick={() => recognized.omrArtifact && download(recognized.omrArtifact, 'recognized.omr')}>
              Download Audiveris Project
            </button>
          )}
          {!review && file && <button type="button" disabled={busy} onClick={async () => {
            setReviewBusy(true)
            setRecognitionError('')
            try { setReview(await createReview(recognized.baselineMusicXml ?? recognized.musicXml, file, recognized.omrArtifact, recognized.semanticEvidenceArtifact)) }
            catch (error) { setRecognitionError(error instanceof Error ? error.message : 'Unable to open review.') }
            finally { setReviewBusy(false) }
          }}>Open Recognition Review</button>}
        </details>
      )}</>
  const secondaryControls = <>{importSettings}{workspaceMode === 'review' && <details>
        <summary>Interval transposition</summary>
        <div id="transposition-controls">
          <label htmlFor="semitones">
            Semitones:
          </label>

          <input
            id="semitones"
            type="number"
            step="1"
            disabled={busy}
            value={semitoneInput}
            onChange={(event) => {
              setSemitoneInput(event.target.value)
              setResult(null)
              setTransposeState('idle')
            }}
          />
        </div>

        <button
          type="button"
          disabled={!file || busy || ((review || !isMusicXml) && (review?.state !== 'VERIFIED' || !review || !currentSaved)) || !validSemitones}
          onClick={handleTranspose}
        >
          {transposeState === 'processing'
            ? 'Transposing…'
            : 'Transpose by semitones'}
        </button>
        {review && !currentSaved && <p>Save the current Working Score before transposing. For downloads, confirm the file was saved locally.</p>}

        {transposeState === 'success' && (
          <>
            <p className="status-success">
              MusicXML transposed successfully.
            </p>

            <button
              type="button"
              onClick={() => result && download(result, `${file?.name.replace(/\.[^.]+$/, '') || 'score'}-transposed-${semitones}.musicxml`)}
              disabled={!result}
            >
              Download Transposed MusicXML
            </button>
          </>
        )}

        {transposeState === 'error' && (
          <p className="status-error" role="alert">{transposeError}</p>
        )}
        </details>}{recognitionControls}</>

  const landing = !file && !review && !concertSource
  const fileActions = <>
        <label className="file-action" htmlFor="sheet-upload">{file && !isMusicXml && !review && !concertSource ? 'Change File' : 'Import PDF / Image'}
          <input
          id="sheet-upload"
          type="file"
          accept=".pdf,.png,.jpg,.jpeg,.webp"
          disabled={busy}
          onChange={(event) => {
            const selected = event.target.files?.[0]
            if (!selected) return
            if (!mayReplace()) { event.target.value = ''; return }
            setFile(selected)
            clearRecognition()
            setReviewSource(undefined)
          }}
        />
        </label>
        <label className="file-action" htmlFor="musicxml-open">Open MusicXML
          <input id="musicxml-open" type="file" accept=".musicxml,.xml" disabled={busy} onChange={async event => {
          const selected = event.target.files?.[0]
          event.target.value = ''
          if (!selected || !mayReplace()) return
          setReviewBusy(true); setRecognitionError('')
          try {
            const opened = await createReview(selected, reviewSource)
            clearRecognition()
            setFile(selected); setReview(opened)
            const snapshot = { reviewId: opened.id, revision: opened.revision, blob: selected, filename: selected.name }
            setSavedFile(snapshot); setConcertSource(snapshot)
          } catch (error) { setRecognitionError(error instanceof Error ? error.message : 'Unable to open MusicXML.') }
          finally { setReviewBusy(false) }
        }} />
        </label>
  </>

  return (
    <section className="workspace-shell">
      <header className="workspace-header">
        <h1>Music Sheet Transposer</h1>
        {!landing && fileActions}
        {review && workspaceMode === 'review' && <button className="primary-action" type="submit" form={`review-save-${review.id}`} disabled={busy}>Save</button>}
        <span className={`connection-indicator connection-${connectionState}`} role="status" title={connectionState === 'success' ? `Backend: ${statusText}` : connectionState === 'error' ? 'Backend unavailable' : 'Connecting'} aria-label={connectionState === 'success' ? 'Backend connected' : connectionState === 'error' ? 'Backend unavailable' : 'Connecting'} />
      </header>
      {landing && <section className="landing-welcome" aria-labelledby="welcome-title">
        <h2 id="welcome-title">Your music, your way.</h2>
        <p>Import a score or open a saved MusicXML to get started.</p>
        <div className="landing-actions">{fileActions}</div>
      </section>}
      <div className="workspace-meta">
        {file && <span>{file.name}</span>}
        {concertSource && <div className="workspace-modes" aria-label="Concert workspace mode">
          <button disabled={busy} aria-pressed={workspaceMode === 'review'} onClick={() => setWorkspaceMode('review')}>Review</button>
          <button disabled={busy} aria-pressed={workspaceMode === 'transpose'} onClick={() => setWorkspaceMode('transpose')}>Transpose</button>
        </div>}
        {review && <span role="status">{workspaceMode === 'review' ? currentSaved ? 'Saved' : 'Unsaved changes' : concertPending ? 'Unsaved result' : 'Saved source'}</span>}
      </div>
      {!review && !concertSource && <div className="empty-import-state">
        {file && !isMusicXml && <p role="status"><strong>Recognition input: {file.name}</strong> — ready to recognize. You do not need to select it again.</p>}
        {file ? importSettings : <details><summary>More</summary>{importSettings}
          <p>Backend: {connectionState === 'success' ? statusText : connectionState === 'error' ? 'Unavailable' : 'Connecting'}</p>
        </details>}
        {recognitionControls}
      </div>}
      {connectionState === 'error' && <p role="alert" className="status-error">Backend unavailable. Import and score operations require a connection.</p>}
      {recognitionError && <p role="alert" className="status-error">{recognitionError}</p>}
      {review && <fieldset hidden={workspaceMode !== 'review'} className="review-access" disabled={busy}>
        <RecognitionReview moreControls={secondaryControls} key={review.id} review={review} savedFile={savedFile} onSaved={setSavedFile} transposed={result} onBusy={setReviewBusy} download={download} onChange={(updated) => {
          setReview(updated)
          if (!updated) setSavedFile(null)
          setResult(null)
          setTransposeState('idle')
        }} />
      </fieldset>}
      {result && !review && <MusicSheetViewer musicXml={result} />}
      {concertSource && <div hidden={workspaceMode !== 'transpose'}>
        <ConcertTranspose key={`${concertSource.reviewId}:${concertSource.revision}`} sourceFile={concertSource}
          disabled={reviewBusy} download={download} onPending={setConcertPending} onBusy={setConcertBusy} />
      </div>}

    </section>
  )
}
