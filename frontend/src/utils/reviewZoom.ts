/** Presentation-only geometry; no score state or renderer layout changes. */
export function reviewScale(zoom: number | null, paneWidth: number, scoreWidth: number): number {
  if (zoom !== null) return Math.max(0.25, Math.min(3, zoom / 100))
  return paneWidth > 0 && scoreWidth > 0 ? Math.min(1, paneWidth / scoreWidth) : 1
}

export function nextReviewZoom(scale: number, direction: number): number {
  return Math.max(25, Math.min(300, Math.round(scale * 100) + direction * 10))
}
