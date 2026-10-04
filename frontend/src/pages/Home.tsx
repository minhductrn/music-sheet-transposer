import { useEffect, useState } from 'react'
import MusicSheetViewer from '../components/MusicSheetViewer'
import RecognitionReview from '../components/RecognitionReview'
import {
  closeReview,
  createReview,
  getHealth,
  getVerifiedMusicXml,
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
  const [semitones, setSemitones] = useState(0)
  const [transposeState, setTransposeState] =
    useState<TransposeState>('idle')
  const [result, setResult] = useState<Blob | null>(null)
  const [recognized, setRecognized] = useState<RecognitionResult | null>(null)
  const [profile, setProfile] = useState<RecognitionProfile>('VOCAL_SONG')
  const [inputQuality, setInputQuality] = useState<InputQuality | ''>('')
  const [recognitionState, setRecognitionState] =
    useState<'idle' | 'recognizing' | 'success' | 'error'>('idle')
  const [recognitionError, setRecognitionError] = useState('')
  const [review, setReview] = useState<ReviewSession | null>(null)
  const [reviewBusy, setReviewBusy] = useState(false)
  const isMusicXml = file ? /\.(musicxml|xml)$/i.test(file.name) : false
  const busy = recognitionState === 'recognizing' || transposeState === 'processing' || reviewBusy

  function clearRecognition() {
    if (review) void closeReview(review.id).catch(() => { /* Server expiry also releases abandoned sessions. */ })
    setReview(null)
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
      setReview(await createReview(draft.musicXml, file))
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
    if (!file || busy || (!isMusicXml && review?.state !== 'VERIFIED')) return

    setTransposeState('processing')
    setResult(null)

    try {
      const inputFile = isMusicXml ? file : new File([await getVerifiedMusicXml(review!.id)], 'verified.musicxml', {
        type: 'application/vnd.recordare.musicxml+xml',
      })
      const transposedFile = await transposeMusicXml(
        inputFile,
        semitones,
      )

      setResult(transposedFile)
      setTransposeState('success')
    } catch {
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
      <p>
        Import, view, and transpose music sheets.
      </p>

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
          Select MusicXML, PDF, PNG, JPEG or WEBP. Recognize, review and verify PDF/images before transposing.
        </p>

        <input
          type="file"
          accept=".musicxml,.xml,.pdf,.png,.jpg,.jpeg,.webp"
          disabled={busy}
          onChange={(event) => {
            setFile(event.target.files?.[0] ?? null)
            clearRecognition()
          }}
        />

        {file && <p>Selected: {file.name}</p>}
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

        <div>
          <label htmlFor="semitones">
            Semitones:
          </label>

          <input
            id="semitones"
            type="number"
            step="1"
            disabled={busy}
            value={semitones}
            onChange={(event) => {
              setSemitones(Number(event.target.value))
              setResult(null)
              setTransposeState('idle')
            }}
          />
        </div>

        <button
          type="button"
          disabled={!file || busy || (!isMusicXml && review?.state !== 'VERIFIED') || !Number.isInteger(semitones)}
          onClick={handleTranspose}
        >
          {transposeState === 'processing'
            ? 'Transposing…'
            : 'Transpose'}
        </button>
        {recognized && review?.state !== 'VERIFIED' && <p>Review and mark the corrected score VERIFIED to enable transposition.</p>}

        {transposeState === 'success' && (
          <>
            <p className="status-success">
              MusicXML transposed successfully.
            </p>

            <button
              type="button"
              onClick={() => result && download(result, 'transposed.musicxml')}
              disabled={!result}
            >
              Download Transposed MusicXML
            </button>
          </>
        )}

        {transposeState === 'error' && (
          <p className="status-error">
            Unable to transpose the MusicXML file.
          </p>
        )}
      </div>

      {recognized && (
        <div className="status-card">
          <h2>Recognition draft</h2>
          <dl>
            <dt>Recognition profile</dt><dd>{recognized.profile.replaceAll('_', ' ')}</dd>
            <dt>Provider</dt><dd>{recognized.provider}</dd>
            <dt>Review status</dt><dd>DRAFT — review required</dd>
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
          <button type="button" onClick={() => download(recognized.musicXml, 'recognized.musicxml')}>
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
            try { setReview(await createReview(recognized.musicXml, file)) }
            catch (error) { setRecognitionError(error instanceof Error ? error.message : 'Unable to open review.') }
            finally { setReviewBusy(false) }
          }}>Open Recognition Review</button>}
        </div>
      )}
      {review && <fieldset className="review-access" disabled={busy}>
        <RecognitionReview review={review} onBusy={setReviewBusy} download={download} onChange={(updated) => {
          setReview(updated)
          setResult(null)
          setTransposeState('idle')
        }} />
      </fieldset>}
      {result && <MusicSheetViewer musicXml={result} />}
    </section>
  )
}
