import { useEffect, useState } from 'react'
import { getReviewSource } from '../services/api'
import type { ReviewSession, SourceLocation } from '../types/review'

export default function SourceViewer({ review, location }: { review: ReviewSession; location: SourceLocation | null }) {
  const selectionKey = location ? JSON.stringify(location) : ''
  const [navigation, setNavigation] = useState({ selectionKey: '', page: 1 })
  const page = navigation.selectionKey === selectionKey ? navigation.page : location?.page ?? 1
  const [imageSize, setImageSize] = useState<{ id: string; width: number; height: number } | null>(null)
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
  const box = location?.bounds
  const width = location?.width
  const height = location?.height
  const highlight = !pdf && location?.page === 1 && box && width && height && width > 0 && height > 0
    && box.every(Number.isFinite) && box[0] >= 0 && box[1] >= 0 && box[2] > 0 && box[3] > 0
    && box[0] + box[2] <= width && box[1] + box[3] <= height
    && imageSize?.id === review.id && Math.abs(imageSize.width / imageSize.height - width / height) < 0.01
    ? { left: `${box[0] / width * 100}%`, top: `${box[1] / height * 100}%`,
        width: `${box[2] / width * 100}%`, height: `${box[3] / height * 100}%` } : null
  return (
    <section className="source-viewer" aria-label="Original source">
      <h3>Original source</h3>
      {location ? <p role="status">Selected evidence: page {location.page}{box ? ` · box ${box.join(', ')}` : ' · geometry unavailable'}.
        {pdf ? ' PDF page navigation is coordinated; the native PDF viewer does not support a box overlay.' : !highlight ? ' A source highlight is unavailable until compatible image geometry is present.' : ''}</p>
        : <p>No source geometry is available for this event.</p>}
      {!review.source && <p>No source retained for this session.</p>}
      {active?.error && <p role="alert">{active.error}</p>}
      {review.source && !active && <p>Loading original source…</p>}
      {active?.url && <>
        <div className="review-toolbar">
          {pdf && <label>Page <input type="number" min={1} max={review.source?.pages} value={page}
            onChange={(e) => setNavigation({ selectionKey, page: Math.max(1, Math.min(review.source?.pages ?? 1, Number(e.target.value) || 1)) })} /> / {review.source?.pages}</label>}
          <label>Zoom <select value={zoom} onChange={(e) => setZoom(Number(e.target.value))}>
            {[50, 75, 100, 125, 150, 200, 300].map((value) => <option key={value} value={value}>{value}%</option>)}
          </select></label>
          <a href={active.url} target="_blank" rel="noreferrer">Open source</a>
        </div>
        <div className="source-scroll">
          {pdf ? <iframe title={`Original PDF, page ${page}`} src={`${active.url}#page=${page}&zoom=${zoom}`} />
            : <div className="source-image" style={{ width: `${zoom}%` }}>
              <img alt="Original uploaded music sheet" src={active.url} style={{ width: '100%' }}
                onLoad={(event) => setImageSize({ id: review.id, width: event.currentTarget.naturalWidth, height: event.currentTarget.naturalHeight })} />
              {highlight && <div aria-label="Selected recognition evidence location" className="source-highlight" style={highlight} />}
            </div>}
        </div>
        {pdf && <p className="review-hint">PDF controls depend on your browser’s PDF viewer. Use Open source if embedded navigation is unavailable.</p>}
      </>}
    </section>
  )
}
