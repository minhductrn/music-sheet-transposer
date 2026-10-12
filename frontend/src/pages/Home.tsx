import type { SavedScoreFile } from '../utils/localScoreFile'
import { useEffect, useState } from 'react'
import MusicSheetViewer from '../components/MusicSheetViewer'
import RecognitionReview from '../components/RecognitionReview'
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
  const [savedFile, setSavedFile] = useState<SavedScoreFile | null>(null)
  const currentSaved = savedFile?.reviewId === review?.id && savedFile?.revision === review?.revision
  const isMusicXml = file ? /\.(musicxml|xml)$/i.test(file.name) : false
  const busy = recognitionState === 'recognizing' || transposeState === 'processing' || reviewBusy

  function clearRecognition() {
    if (review) void closeReview(review.id).catch(() => { /* Server expiry also releases abandoned sessions. */ })
    setReview(null)
    setSavedFile(null)
    setRecognized(null)
    setResult(null)
    setRecognitionState('idle')
    setRecognitionError('')
    setTransposeState('idle')
  }

  async function handleRecognize() {
    if (!file || busy) return
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

  return (
    <section>
      <p>Import → Review → Correct → Verify → Transpose → Export</p>

      <div className="status-card" role="status">
        <h2>Backend connection</h2>

        {connectionState === 'loading' && (
          <p>Checking backend connection…</p>
        )}

        {connectionState === 'success' && (
          <p className="status-success">
            Connected - backend status: {statusText}
          </p>
        )}

        {connectionState === 'error' && (
          <p className="status-error">
            Unable to reach the backend.
          </p>
        )}
      </div>

      <div className="status-card">
        <h2>Import Sheet Music</h2>

        <p>
          Select MusicXML, PDF, PNG, JPEG or WEBP. Import, edit, and save PDF/images before transposing. Open a saved MusicXML file directly without recognition.
        </p>

        <label htmlFor="sheet-upload">Sheet music file</label>
        <input
          id="sheet-upload"
          type="file"
          accept=".musicxml,.xml,.pdf,.png,.jpg,.jpeg,.webp"
          disabled={busy}
          onChange={(event) => {
            setFile(event.target.files?.[0] ?? null)
            clearRecognition()
            setReviewSource(undefined)
          }}
        />

        {file && <p>Selected: {file.name}</p>}
        {file && isMusicXml && !review && <div className="review-fields">
          <label>Original source for comparison (optional)<input type="file" accept=".pdf,.png,.jpg,.jpeg,.webp" disabled={busy}
            onChange={(event) => setReviewSource(event.target.files?.[0])} /></label>
          <button disabled={busy} onClick={async () => {
            setReviewBusy(true); setRecognitionError(''); setResult(null); setTransposeState('idle')
            try { setReview(await createReview(file, reviewSource)) }
            catch (error) { setRecognitionError(error instanceof Error ? error.message : 'Unable to open review.') }
            finally { setReviewBusy(false) }
          }}>Open MusicXML</button>
        </div>}
        {file && !isMusicXml && (
          <>
            <p>
              <label htmlFor="recognition-profile">Recognition profile: </label>
              <select id="recognition-profile" value={profile} disabled={busy} onChange={(event) => {
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
        {recognitionError && <p role="alert" className="status-error">{recognitionError}</p>}

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
            : 'Transpose'}
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
      </div>

      {recognized && (
        <div className="status-card">
          <h2>Recognition draft</h2>
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
        </div>
      )}
      {review && <fieldset className="review-access" disabled={busy}>
        <RecognitionReview key={review.id} review={review} savedFile={savedFile} onSaved={setSavedFile} transposed={result} onBusy={setReviewBusy} download={download} onChange={(updated) => {
          setReview(updated)
          if (!updated) setSavedFile(null)
          setResult(null)
          setTransposeState('idle')
        }} />
      </fieldset>}
      {result && !review && <MusicSheetViewer musicXml={result} />}
    </section>
  )
}
