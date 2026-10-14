import type { OpenSheetMusicDisplay } from 'opensheetmusicdisplay'
import type { Score } from './visualReview'

// No paper width is assigned until trusted layout has supplied an engraving seed.
export const initialEngravingWidth = 0

/** Require complete, ordered and compatible ownership across all parts. */
export function trustedSourceGroups(score?: Score): number[][] | null {
  const layout = score?.layout
  if (!score || layout?.mode !== 'SOURCE_REVIEW' ||
      !['MUSICXML_PRINT', 'OMR_ORDERED_MEASURES'].includes(layout.origin ?? '') || !score.parts.length) return null
  let common: number[][] | undefined
  for (const part of score.parts) {
    const groups = layout.systems.filter((g) => g.part_id === part.id)
    if (!groups.length || !part.measures.length) return null
    const indices: number[][] = []
    for (const group of groups) {
      if (!group.measure_ids.length || group.explicit_break_measure_id !== group.measure_ids[0]) return null
      const row = group.measure_ids.map((id) => part.measures.find((m) => m.id === id)?.index ?? -1)
      indices.push(row)
    }
    const flat = indices.flat()
    if (flat.length !== part.measures.length || flat.some((index, i) => index !== i)) return null
    if (common && JSON.stringify(common) !== JSON.stringify(indices)) return null
    common = indices
  }
  return common ?? null
}

/** XML widths seed engraving capacity; the rendered graph verifies sufficiency. */
export function sourceEngravingWidth(document: Document, groups: number[][]): number {
  const parts = Array.from(document.documentElement.children).filter((e) => e.localName === 'part')
  const widths = parts.map((p) => Array.from(p.children).filter((e) => e.localName === 'measure')
    .map((m) => Number(m.getAttribute('width'))))
  return Math.ceil(Math.max(...groups.map((g) => g.reduce((sum, index) =>
    sum + Math.max(160, ...widths.map((w) => Number.isFinite(w[index]) ? w[index] : 0)), 120))))
}

/** Read source identity, never OSMD's display numbering or screen coordinates. */
export function renderedSourceGroups(osmd: OpenSheetMusicDisplay): number[][] {
  return osmd.GraphicSheet.MusicPages.flatMap((page) => page.MusicSystems.map((system) => {
    const indices = new Set<number>()
    for (const staff of system.StaffLines) for (const measure of staff.Measures)
      indices.add(osmd.Sheet.SourceMeasures.indexOf(measure.parentSourceMeasure))
    return [...indices].sort((a, b) => a - b)
  }))
}

/** Bounded deterministic measurement using the completed renderer graph.
 * No pane/zoom input, no score mutation, no private OSMD layout patch.
 * Explicit breaks remain enabled throughout; widening only removes extra breaks.
 */
export function engraveSourceGroups(osmd: OpenSheetMusicDisplay, groups: number[][],
  setWidth: (width: number) => void, seedWidth: number): { width: number; matched: boolean } {
  let width = Math.min(32760, Math.max(1, Math.ceil(seedWidth)))
  for (let attempt = 0; attempt < 8 && width <= 32760; attempt++) {
    setWidth(width)
    osmd.updateGraphic()
    osmd.render()
    if (JSON.stringify(renderedSourceGroups(osmd)) === JSON.stringify(groups)) return { width, matched: true }
    if (attempt < 7 && width * 2 <= 32760) width *= 2
    else break
  }
  return { width, matched: false }
}

/** Saved preview uses the same explicit MusicXML system boundaries as Review. */
export function xmlSourceGroups(document: Document): number[][] | null {
  const parts = Array.from(document.documentElement.children).filter(e => e.localName === 'part')
  let common: number[][] | undefined
  for (const part of parts) {
    const measures = Array.from(part.children).filter(e => e.localName === 'measure')
    if (!measures.length) return null
    const groups: number[][] = [[]]
    let explicit = false
    measures.forEach((measure, index) => {
      const print = Array.from(measure.children).find(e => e.localName === 'print')
      if (index && (print?.getAttribute('new-system') === 'yes' || print?.getAttribute('new-page') === 'yes')) {
        groups.push([]); explicit = true
      }
      groups[groups.length - 1].push(index)
    })
    if (!explicit || (common && JSON.stringify(common) !== JSON.stringify(groups))) return null
    common = groups
  }
  return common ?? null
}
