import { useEffect, useState } from 'react'
import {
  getHealth,
  transposeMusicXml,
} from '../services/api'

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
    if (!file) return

    setTransposeState('processing')
    setResult(null)

    try {
      const transposedFile = await transposeMusicXml(
        file,
        semitones,
      )

      setResult(transposedFile)
      setTransposeState('success')
    } catch {
      setTransposeState('error')
    }
  }

  function handleDownload() {
    if (!result) return

    const url = URL.createObjectURL(result)
    const link = document.createElement('a')

    link.href = url
    link.download = 'transposed.musicxml'

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
        <h2>Transpose MusicXML</h2>

        <p>
          Select a MusicXML file and transpose it by semitones.
        </p>

        <input
          type="file"
          accept=".musicxml,.xml"
          onChange={(event) => {
            setFile(event.target.files?.[0] ?? null)
            setResult(null)
            setTransposeState('idle')
          }}
        />

        <div>
          <label htmlFor="semitones">
            Semitones:
          </label>

          <input
            id="semitones"
            type="number"
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
          disabled={!file || transposeState === 'processing'}
          onClick={handleTranspose}
        >
          {transposeState === 'processing'
            ? 'Transposing…'
            : 'Transpose'}
        </button>

        {transposeState === 'success' && (
          <>
            <p className="status-success">
              MusicXML transposed successfully.
            </p>

            <button
              type="button"
              onClick={handleDownload}
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
    </section>
  )
}