/** Safe visual placement: geometry chooses among canonical positions, never invents time. */
import type { OpenSheetMusicDisplay } from 'opensheetmusicdisplay'
import type { ReviewSession } from '../types/review'
import { amount } from './visualReview'

export interface VisualInsertionPosition { measureId: string; staff: number; onset: string }
export interface InsertionLane extends VisualInsertionPosition {
  page: number; x: number; top: number; bottom: number; left: number; right: number
}

// Vite replaces this expression in browser builds; the guard also tolerates test hosts.
declare const process: { env: { NODE_ENV: string } }
export function insertionDiagnosticsEnabled(): boolean {
  try {
    return process.env.NODE_ENV === 'development' && localStorage.getItem('mst_debug_insertion') === '1'
  } catch { return false }
}

export function logInsertionDiagnostic(input: {
  targetCategory: 'note event' | 'score SVG' | 'other'
  svgResolved: boolean; pageMatches: number; page: number | null
  client: { x: number; y: number }; point: { x: number; y: number } | null
  conversionFailure: string | null; lanes: InsertionLane[]
}) {
  const hits = input.point && input.page !== null ? input.lanes.filter((p) =>
    p.page === input.page && input.point!.x >= p.left && input.point!.x <= p.right
    && input.point!.y >= p.top && input.point!.y <= p.bottom) : []
  const positionKeys = Array.from(new Set(hits.map((p) => JSON.stringify([p.measureId, p.staff, p.onset]))))
  const result = input.targetCategory === 'note event' ? 'event-intercepted'
    : input.conversionFailure ? 'coordinate-failure'
      : !hits.length ? 'zero-hit' : hits.length === 1 ? 'resolved'
        : positionKeys.length === 1 ? 'equivalent-multiple-hit' : 'ambiguous-multiple-hit'
  console.debug('[mst insertion]', {
    targetCategory: input.targetCategory,
    svg: { resolved: input.svgResolved },
    page: { matches: input.pageMatches, resolved: input.page },
    client: input.client, score: input.point, conversionFailure: input.conversionFailure,
    laneCount: input.lanes.length, hitCount: hits.length, positionKeys, result,
  })
}

export function insertionLanes(osmd: OpenSheetMusicDisplay, score: ReviewSession['score']): InsertionLane[] {
  const lanes: InsertionLane[] = []
  for (const row of osmd.GraphicSheet.MeasureList) for (const graphical of row) {
    const instrument = graphical?.ParentStaff?.ParentInstrument
    if (!instrument || graphical.IsExtraGraphicalMeasure) continue
    const part = score.parts[osmd.Sheet.Instruments.indexOf(instrument)]
    const measure = part?.measures.find((m) => m.index === osmd.Sheet.SourceMeasures.indexOf(graphical.parentSourceMeasure))
    const staff = instrument.Staves.indexOf(graphical.ParentStaff) + 1
    const page = graphical.ParentMusicSystem?.Parent?.PageNumber
    const box = graphical.PositionAndShape
    if (!measure || staff < 1 || !box || !page) continue
    const left = box.AbsolutePosition.x + box.BorderLeft
    const right = box.AbsolutePosition.x + box.BorderRight
    // Staff lines, not lyric/title bounds. The staff box is the drawing's origin.
    const top = box.AbsolutePosition.y - .5
    const bottom = top + (osmd.EngravingRules.StaffHeight ?? 4) + 1
    if (![left, right, top, bottom].every(Number.isFinite) || right <= left || bottom <= top) continue
    const playableLeft = left + Math.max(0, graphical.beginInstructionsWidth) + .8
    const playableRight = right - Math.max(0, graphical.endInstructionsWidth) - .8
    if (!Number.isFinite(playableLeft + playableRight) || playableRight <= playableLeft) continue
    const events = measure.voices.flatMap((v) => v.events).filter((e) => e.staff === staff)
    const known = Array.from(new Set(events.flatMap((e) => e.onset === null ? [] : [e.onset])))
    const positions: { onset: string; x: number }[] = []
    if (!measure.voices.some((v) => v.events.length)) {
      // One position in an empty measure: its explicit start, independent of meter.
      positions.push({ onset: '0', x: (playableLeft + playableRight) / 2 })
    } else {
      for (const entry of graphical.staffEntries) {
        const time = entry.relInMeasureTimestamp?.RealValue * 4
        const matches = known.filter((onset) => Math.abs(amount(onset) - time) < 1e-7)
        if (matches.length !== 1 || !entry.graphicalVoiceEntries.some((v) => v.notes.some((n) => n.sourceNote?.SourceMeasure === graphical.parentSourceMeasure))) continue
        const x = entry.PositionAndShape.AbsolutePosition.x
        if (Number.isFinite(x) && x >= playableLeft && x <= playableRight) positions.push({ onset: matches[0], x })
      }
      // Start in a sparse staff is explicit, not a meter-completion inference.
      if (!positions.some((p) => amount(p.onset) === 0) && events.every((e) => e.onset !== null && amount(e.onset) > 0))
        positions.push({ onset: '0', x: playableLeft })
    }
    const ordered = positions.sort((a, b) => a.x - b.x)
    for (let i = 0; i < ordered.length; i++) {
      const p = ordered[i]
      // Duplicate renderer lanes or coincident different onsets deliberately stay ambiguous.
      const singleEmpty = !measure.voices.some((v) => v.events.length)
      lanes.push({ measureId: measure.id, staff, onset: p.onset, page, x: p.x, top, bottom,
        left: singleEmpty ? playableLeft : Math.max(playableLeft, p.x - 2, i ? (ordered[i - 1].x + p.x) / 2 : playableLeft),
        right: singleEmpty ? playableRight : Math.min(playableRight, p.x + 2, i + 1 < ordered.length ? (ordered[i + 1].x + p.x) / 2 : playableRight) })
    }
  }
  return lanes
}

export function hitInsertion(lanes: InsertionLane[], page: number, point: { x: number; y: number }): InsertionLane | null {
  const hits = lanes.filter((p) => p.page === page && point.x >= p.left && point.x <= p.right && point.y >= p.top && point.y <= p.bottom)
  return hits.length === 1 ? hits[0] : null
}

/** SVG CTM includes viewBox, CSS Fit/zoom, page offsets and scroll. */
export function scorePoint(svg: SVGSVGElement, clientX: number, clientY: number, pixelsPerUnit: number): { x: number; y: number } | null {
  const matrix = svg.getScreenCTM()
  if (!matrix || !Number.isFinite(pixelsPerUnit) || pixelsPerUnit <= 0) return null
  try {
    const point = svg.createSVGPoint(); point.x = clientX; point.y = clientY
    const local = point.matrixTransform(matrix.inverse())
    const result = { x: local.x / pixelsPerUnit, y: local.y / pixelsPerUnit }
    return Object.values(result).every(Number.isFinite) ? result : null
  } catch { return null }
}

export function drawInsertionMarker(svg: SVGSVGElement, lane: InsertionLane, pixelsPerUnit: number): () => void {
  const group = document.createElementNS('http://www.w3.org/2000/svg', 'g')
  group.setAttribute('data-insertion-marker', 'true')
  group.setAttribute('aria-label', 'Selected note insertion position')
  group.setAttribute('role', 'img')
  group.setAttribute('pointer-events', 'none')
  const line = document.createElementNS(group.namespaceURI, 'path')
  const x = lane.x * pixelsPerUnit, top = lane.top * pixelsPerUnit, bottom = lane.bottom * pixelsPerUnit
  line.setAttribute('d', `M ${x - 5} ${top} H ${x + 5} M ${x} ${top} V ${bottom} M ${x - 5} ${bottom} H ${x + 5}`)
  line.setAttribute('class', 'score-insertion-caret')
  group.appendChild(line); svg.appendChild(group)
  return () => group.remove()
}

/** OSMD's SVG backend exposes a DIV canvas wrapper, not the SVG itself. */
export function renderedScorePages(osmd: OpenSheetMusicDisplay): { page: number; svg: SVGSVGElement }[] {
  return osmd.Drawer.Backends.flatMap((backend) => {
    const canvas = backend.getCanvas()
    const svg = canvas?.localName === 'svg' ? canvas as unknown as SVGSVGElement : canvas?.querySelector<SVGSVGElement>('svg')
    const page = backend.graphicalMusicPage?.PageNumber
    return svg && page ? [{ page, svg }] : []
  })
}
