import { useEffect, useRef, useState, type ReactNode } from 'react'
import { initialEngravingWidth } from '../utils/sourceEngraving'
import { nextReviewZoom, reviewScale } from '../utils/reviewZoom'

/** Keep engraving width independent of display zoom to preserve source grouping. */
export default function ReviewScoreViewport({ sourceReview, children, engravingWidth = initialEngravingWidth, title, headerActions, toolbar }: { title?: string; headerActions?: ReactNode; toolbar?: ReactNode; sourceReview: boolean; children: ReactNode; engravingWidth?: number }) {
  const viewportRef = useRef<HTMLDivElement | null>(null)
  const surfaceRef = useRef<HTMLDivElement | null>(null)
  const [zoom, setZoom] = useState<number | null>(null)
  const [size, setSize] = useState({ pane: 0, width: 0, height: 0 })

  useEffect(() => {
    const viewport = viewportRef.current
    const surface = surfaceRef.current
    if (!viewport || !surface) return
    const measure = () => {
      const next = { pane: viewport.clientWidth, width: Math.max(surface.clientWidth, surface.scrollWidth), height: surface.scrollHeight }
      setSize((old) => old.pane === next.pane && old.width === next.width && old.height === next.height ? old : next)
    }
    const observer = new ResizeObserver(measure)
    observer.observe(viewport)
    observer.observe(surface)
    // SVG width can overflow without changing the surface's border box.
    const changes = new MutationObserver(measure)
    changes.observe(surface, { childList: true, subtree: true, attributes: true, attributeFilter: ['width', 'height', 'viewBox'] })
    measure()
    return () => { observer.disconnect(); changes.disconnect() }
  }, [])

  const scale = reviewScale(zoom, size.pane, size.width)
  const previousScale = useRef(scale)
  useEffect(() => {
    const viewport = viewportRef.current
    if (viewport && previousScale.current > 0) {
      const ratio = scale / previousScale.current
      viewport.scrollLeft *= ratio
      viewport.scrollTop *= ratio
    }
    previousScale.current = scale
  }, [scale])
  return <div className="review-score-viewport">
    <div className="score-panel-header" role="toolbar" aria-label="Score zoom">
      {title && <h3>{title}</h3>}
      {headerActions}
      <button aria-pressed={zoom === null} onClick={() => setZoom(null)}>Fit</button>
      <button aria-label="Zoom score out" disabled={scale <= .25} onClick={() => setZoom(nextReviewZoom(scale, -1))}>−</button>
      <button aria-label="Reset score zoom to 100%" aria-pressed={zoom === 100} onClick={() => setZoom(100)}>{Math.round(scale * 100)}%</button>
      <button aria-label="Zoom score in" disabled={scale >= 3} onClick={() => setZoom(nextReviewZoom(scale, 1))}>+</button>

    </div>
    {toolbar}
    <div className="review-score-scroll" ref={viewportRef} aria-label="Score pane" tabIndex={0}>
      <div className="review-score-stage" style={{ width: size.width ? Math.ceil(size.width * scale) : '100%', height: Math.max(1, Math.ceil(size.height * scale)) }}>
        <div className="review-score-surface" ref={surfaceRef} style={{ width: sourceReview ? engravingWidth || 'max-content' : size.pane || '100%', transform: `scale(${scale})` }}>
          {children}
        </div>
      </div>
    </div>
  </div>
}
