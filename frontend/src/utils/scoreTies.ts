import type { Score } from './visualReview'
import { scorePoint } from './scoreInsertion'

/** Canonical correction curves only. Raw XML fragments never establish a pair. */
export function drawCorrectionTies(score: Score, targets: { node: HTMLElement; id: string }[], select: (id: string) => void) {
  const nodes = new Map<string, HTMLElement[]>()
  for (const { node, id } of targets) nodes.set(id, [...(nodes.get(id) ?? []), node])
  const cleanup: (() => void)[] = []
  const lanes = new Map<string, number>()
  const positions = new Map(score.parts.flatMap(p => p.measures.flatMap(m => m.voices.flatMap(v =>
    v.events.map(e => [e.id, `${p.id}/${m.id}/${e.staff}/${e.onset}`] as const)))))

  for (const event of score.parts.flatMap(p => p.measures.flatMap(m => m.voices.flatMap(v => v.events)))) {
    const link = event.tie_relationship
    if (!link || link.source_event_id !== event.id) continue
    const sources = nodes.get(event.id), destinations = nodes.get(link.target_event_id)
    if (sources?.length !== 1 || destinations?.length !== 1) continue
    const source = sources[0], target = destinations[0]
    const svg = source.closest('svg') as SVGSVGElement | null
    const targetSvg = target.closest('svg') as SVGSVGElement | null
    if (!svg || !targetSvg) continue
    const a = source.getBoundingClientRect(), b = target.getBoundingClientRect()
    const up = event.tie_direction === 'up'
    const sourceY = up ? a.top - 2 : a.bottom + 2
    const targetY = up ? b.top - 2 : b.bottom + 2
    const start = scorePoint(svg, a.left + a.width / 2, sourceY, 1)
    const end = scorePoint(targetSvg, b.left + b.width / 2, targetY, 1)
    if (!start || !end) continue
    const key = `${positions.get(event.id) ?? event.id}->${positions.get(link.target_event_id) ?? link.target_event_id}`
    const lane = lanes.get(key) ?? 0
    lanes.set(key, lane + 1)
    const headTop = scorePoint(svg, a.left + a.width / 2, a.top, 1)
    const headBottom = scorePoint(svg, a.left + a.width / 2, a.bottom, 1)
    const spacing = headTop && headBottom ? Math.max(1, Math.abs(headBottom.y - headTop.y) * .65) : 0
    const segments = [{ surface: svg, from: start, to: end }]
    if (svg !== targetSvg || (end.x < start.x && end.y > start.y + 30)) {
      const sourceBounds = svg.getBoundingClientRect(), targetBounds = targetSvg.getBoundingClientRect()
      const right = scorePoint(svg, sourceBounds.right, sourceY, 1)
      const left = scorePoint(targetSvg, targetBounds.left, targetY, 1)
      if (!right || !left) continue
      segments.splice(0, 1,
        { surface: svg, from: start, to: { x: Math.max(start.x + 12, right.x - 12), y: start.y } },
        { surface: targetSvg, from: { x: Math.min(end.x - 12, left.x + 12), y: end.y }, to: end })
    }
    for (const { surface, from, to } of segments) {
      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path')
      const bend = (Math.min(22, Math.max(8, Math.abs(to.x - from.x) / 6)) + lane * spacing) * (up ? -1 : 1)
      path.setAttribute('d', `M ${from.x} ${from.y} C ${from.x + (to.x - from.x) / 3} ${from.y + bend} ${to.x - (to.x - from.x) / 3} ${to.y + bend} ${to.x} ${to.y}`)
      path.setAttribute('fill', 'none')
      path.setAttribute('stroke', '#2563eb')
      path.setAttribute('stroke-width', '1.8')
      path.setAttribute('vector-effect', 'non-scaling-stroke')
      path.setAttribute('data-correction-tie', event.id)
      path.setAttribute('role', 'button')
      path.setAttribute('tabindex', '0')
      path.setAttribute('aria-label', 'Select corrected tie source to remove or change this tie')
      const click = () => select(event.id)
      const key = (e: KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); select(event.id) } }
      path.addEventListener('click', click); path.addEventListener('keydown', key)
      surface.appendChild(path)
      cleanup.push(() => { path.removeEventListener('click', click); path.removeEventListener('keydown', key); path.remove() })
    }
  }
  return () => cleanup.forEach(dispose => dispose())
}


/** Replace only owned native curves with the canonical overlay in a viewing clone. */
export function correctionTieDocument(document: Document, score: Score): Document {
  const owned = new Set(score.parts.flatMap(p => p.measures.flatMap(m => m.voices.flatMap(v => v.events.flatMap(e =>
    e.tie_relationship ? [e.tie_relationship.source_visual_id, e.tie_relationship.target_visual_id].filter((id): id is string => Boolean(id)) : [])))))
  const view = document.cloneNode(true) as Document
  for (const node of Array.from(view.getElementsByTagNameNS('*', 'tied'))) {
    if (owned.has(node.getAttribute('id') ?? '')) node.parentNode?.removeChild(node)
  }
  return view
}
