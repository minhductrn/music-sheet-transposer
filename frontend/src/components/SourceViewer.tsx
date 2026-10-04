import { useEffect, useState } from 'react'
import { getReviewSource } from '../services/api'
import type { ReviewSession } from '../types/review'

export default function SourceViewer({ review }: { review: ReviewSession }) {
  const [page, setPage] = useState(1)
  const [zoom, setZoom] = useState(100)
  const [source, setSource] = useState<{ id: string; url: string; error?: string } | null>(null)
  const hasSource = Boolean(review.source)

  useEffect(() => {
    if (!hasSource) return
    const controller = new AbortController()
    let url: string | null = null
    getReviewSource(review.id, controller.signal).then((blob) => {
      if (controller.signal.aborted) return
      url = URL.createObjectURL(blob)
      setSource({ id: review.id, url })
    }).catch((error) => {
      if (!controller.signal.aborted) setSource({ id: review.id, url: '', error: String(error.message) })
    })
    return () => {
      controller.abort()
      if (url) URL.revokeObjectURL(url)
    }
  }, [review.id, hasSource])

  const active = source?.id === review.id ? source : null
  const pdf = review.source?.media_type === 'application/pdf'
  return (
    <section className="source-viewer" aria-label="Original source">
      <h3>Original source</h3>
      {!review.source && <p>No source retained for this session.</p>}
      {active?.error && <p role="alert">{active.error}</p>}
      {review.source && !active && <p>Loading original source…</p>}
      {active?.url && <>
        <div className="review-toolbar">
          {pdf && <label>Page <input type="number" min={1} max={review.source?.pages} value={page}
            onChange={(e) => setPage(Math.max(1, Math.min(review.source?.pages ?? 1, Number(e.target.value) || 1)))} /> / {review.source?.pages}</label>}
          <label>Zoom <select value={zoom} onChange={(e) => setZoom(Number(e.target.value))}>
            {[50, 75, 100, 125, 150, 200, 300].map((value) => <option key={value} value={value}>{value}%</option>)}
          </select></label>
          <a href={active.url} target="_blank" rel="noreferrer">Open source</a>
        </div>
        <div className="source-scroll">
          {pdf ? <iframe title={`Original PDF, page ${page}`} src={`${active.url}#page=${page}&zoom=${zoom}`} />
            : <img alt="Original uploaded music sheet" src={active.url} style={{ width: `${zoom}%` }} />}
        </div>
        {pdf && <p className="review-hint">PDF controls depend on your browser’s PDF viewer. Use Open source if embedded navigation is unavailable.</p>}
      </>}
    </section>
  )
}
