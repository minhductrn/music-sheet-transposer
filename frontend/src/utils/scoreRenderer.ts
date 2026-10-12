/** Renderer boundary: layout and graphical hints never mutate canonical score bytes. */
import type { IOSMDOptions, OpenSheetMusicDisplay } from 'opensheetmusicdisplay'
import { bindScore } from './scoreInteraction'
import type { Score } from './visualReview'

export function rendererOptions(sourceReview: boolean): IOSMDOptions {
  return { autoResize: false, backend: 'svg', drawTitle: true, disableCursor: false,
    fillEmptyMeasuresWithWholeRest: 0, autoGenerateMultipleRestMeasuresFromRestMeasures: false,
    newSystemFromXML: sourceReview, newSystemFromNewPageInXML: sourceReview,
    newPageFromXML: sourceReview, ...(sourceReview ? { pageFormat: 'Endless' } : {}) }
}

export function reviewDocument(document: Document, score?: Score, rhythmicSmallNotes = false): Document {
  // View-only clone. The uploaded/exported Blob remains unchanged.
  const view = document.cloneNode(true) as Document
  // OSMD interprets type@size=cue as IsCueNote and constructs VexFlow GraceNote.
  // Duration-bearing small display must instead enter ordinary rhythmic engraving.
  for (const note of Array.from(rhythmicSmallNotes ? view.getElementsByTagNameNS?.('*', 'note') ?? [] : [])) {
    const children = Array.from(note.children)
    const type = children.find(e => e.localName === 'type')
    const head = children.find(e => e.localName === 'notehead')
    if (type?.getAttribute('size') === 'cue' && head?.getAttribute('font-size') === 'small'
      && children.some(e => e.localName === 'duration')
      && !children.some(e => e.localName === 'grace' || e.localName === 'cue')) type.removeAttribute('size')
  }
  if (score?.layout?.origin !== 'OMR_ORDERED_MEASURES') return view
  const ns = view.documentElement.namespaceURI
  const parts = Array.from(view.documentElement.children).filter((e) => e.localName === 'part')
  for (const group of score.layout.systems) {
    const partIndex = score.parts.findIndex((p) => p.id === group.part_id)
    const semantic = score.parts[partIndex]?.measures.find((m) => m.id === group.explicit_break_measure_id)
    const measures = Array.from(parts[partIndex]?.children ?? []).filter((e) => e.localName === 'measure')
    const measure = semantic ? measures[semantic.index] : undefined
    if (!measure) continue
    let print = Array.from(measure.children).find((e) => e.localName === 'print')
    if (!print) { print = view.createElementNS(ns, 'print'); measure.insertBefore(print, measure.firstChild) }
    print.setAttribute('new-system', 'yes')
    if (group.new_page) print.setAttribute('new-page', 'yes')
  }
  return view
}

export function bindRenderer(osmd: OpenSheetMusicDisplay, score: Score, select: (id: string) => void, drag?: Parameters<typeof bindScore>[3]) {
  return bindScore(osmd, score, select, drag)
}

export interface MeasureHitRegion {
  measureId: string
  staff: number
  bounds: { left: number; top: number; right: number; bottom: number }
  coordinateSpace: 'OSMD_UNITS'
}

/** Derived geometry is an ephemeral hit hint, never source evidence or an onset. */
export function measureRegions(osmd: OpenSheetMusicDisplay, score: Score): MeasureHitRegion[] {
  const regions: MeasureHitRegion[] = []
  for (const row of osmd.GraphicSheet.MeasureList) for (const graphical of row) {
    if (!graphical?.ParentStaff?.ParentInstrument) continue
    const partIndex = osmd.Sheet.Instruments.indexOf(graphical.ParentStaff.ParentInstrument)
    const measureIndex = osmd.Sheet.SourceMeasures.indexOf(graphical.parentSourceMeasure)
    const measure = score.parts[partIndex]?.measures.find((m) => m.index === measureIndex)
    const staff = graphical.ParentStaff.ParentInstrument.Staves.indexOf(graphical.ParentStaff) + 1
    const box = graphical.PositionAndShape
    if (!measure || staff < 1 || !box) continue
    const bounds = { left: box.AbsolutePosition.x + box.BorderLeft, right: box.AbsolutePosition.x + box.BorderRight,
      top: box.AbsolutePosition.y + box.BorderTop, bottom: box.AbsolutePosition.y + box.BorderBottom }
    if (Object.values(bounds).every(Number.isFinite) && bounds.left < bounds.right && bounds.top < bounds.bottom)
      regions.push({ measureId: measure.id, staff, bounds, coordinateSpace: 'OSMD_UNITS' })
  }
  return regions
}

export function hitMeasure(regions: MeasureHitRegion[], point: { x: number; y: number }): MeasureHitRegion | null {
  const hits = regions.filter(({ bounds: b }) => point.x >= b.left && point.x < b.right && point.y >= b.top && point.y < b.bottom)
  return hits.length === 1 ? hits[0] : null
}
