import { Pitch, type OpenSheetMusicDisplay, type Note } from 'opensheetmusicdisplay'
import type { Lyric } from '../types/review'
import { mappedEvent, type Score } from './visualReview'

export interface LyricBinding {
  reviewId: string
  revision: number
  renderGeneration: number
  lyricId: string | null
  eventId: string | null
  originalVerse: string
  node: SVGGraphicsElement
  owners: Lyric[]
  reason: string | null
  valid: () => boolean
}
export interface LyricScope { reviewId: string; revision: number; score: Score }
export function lyricOwner(score: Score, ids: (string | null)[], verse: string): Lyric[] {
  if (!ids.length || ids.some(id => id === null)) return []
  return score.lyrics.filter(l => ids.includes(l.event_id) && l.number === verse)
}
export function currentLyric(binding: LyricBinding, scope: LyricScope): Lyric | null {
  if (binding.reviewId !== scope.reviewId || binding.revision !== scope.revision || !binding.valid()) return null
  const matches = scope.score.lyrics.filter(l => l.id === binding.lyricId)
  return matches.length === 1 && matches[0].event_id === binding.eventId && matches[0].number === binding.originalVerse ? matches[0] : null
}
export function overlapping(a: DOMRect, b: DOMRect): boolean {
  return Math.min(a.right, b.right) > Math.max(a.left, b.left) && Math.min(a.bottom, b.bottom) > Math.max(a.top, b.top)
}

/** SVG is a revision-scoped handle, never the owner of a lyric. */
export function bindLyrics(osmd: OpenSheetMusicDisplay, root: HTMLElement, scope: LyricScope, renderGeneration: number,
  latest: () => LyricScope | null, enabled: () => boolean, open: (binding: LyricBinding) => void) {
  let disposed = false
  const sources = new Map<Note, string | null>()
  for (const row of osmd.GraphicSheet.MeasureList) for (const m of row) {
    if (!m) continue
    for (const entry of m.staffEntries) for (const voice of entry.graphicalVoiceEntries) for (const graphical of voice.notes) {
      const n = graphical.sourceNote, staff = n?.ParentStaff, pitch = n?.Pitch
      if (!staff?.ParentInstrument || !n.ParentVoiceEntry || m.parentSourceMeasure !== n.SourceMeasure) continue
      sources.set(n, mappedEvent(scope.score, {
        partIndex: osmd.Sheet.Instruments.indexOf(staff.ParentInstrument),
        measureIndex: osmd.Sheet.SourceMeasures.indexOf(n.SourceMeasure),
        staff: staff.ParentInstrument.Staves.indexOf(staff) + 1, voice: String(n.ParentVoiceEntry.ParentVoice.VoiceId),
        onset: n.ParentVoiceEntry.Timestamp.RealValue * 4, duration: n.Length.RealValue * 4,
        grace: n.IsGraceNote, kind: n.isRest() ? 'rest' : pitch ? 'note' : 'unpitched',
        step: pitch ? Pitch.getNoteEnumString(pitch.FundamentalNote) : null,
        octave: pitch ? pitch.Octave + Pitch.OctaveXmlDifference : null, alter: pitch?.AccidentalHalfTones ?? 0,
      })?.id ?? null)
    }
  }
  const byNode = new Map<SVGGraphicsElement, LyricBinding[]>()
  for (const row of osmd.GraphicSheet.MeasureList) for (const m of row) {
    if (!m) continue
    for (const entry of m.staffEntries) for (const g of entry.LyricsEntries ?? []) {
      const node = g.GraphicalLabel?.SVGNode as SVGGraphicsElement | undefined
      if (!node?.getBoundingClientRect || !root.contains(node)) continue
      const verse = String(g.LyricsEntry.VerseNumber), notes = g.LyricsEntry.Parent?.Notes ?? []
      const ids = notes.map(n => n.SourceMeasure === m.parentSourceMeasure && n.ParentStaff === m.ParentStaff ? sources.get(n) ?? null : null)
      // Incomplete mappings cannot activate directly, but mapped owners remain available for explicit selection.
      const owners = scope.score.lyrics.filter(l => ids.includes(l.event_id) && l.number === verse)
      const unique = lyricOwner(scope.score, ids, verse)
      const lyric = unique.length === 1 && scope.score.lyrics.filter(l => l.id === unique[0].id).length === 1 ? unique[0] : null
      const binding: LyricBinding = { reviewId: scope.reviewId, revision: scope.revision, renderGeneration,
        lyricId: lyric?.id ?? null, eventId: lyric?.event_id ?? null, originalVerse: verse, node, owners,
        reason: !lyric ? 'This label has ambiguous or incomplete ownership. Select a canonical owner below, or use Advanced Review.'
          : lyric.segments.length !== 1 ? 'This lyric has multiple text segments. Use the existing editor to choose a segment.' : null,
        valid: () => !disposed && node.isConnected && root.contains(node) && latest()?.reviewId === scope.reviewId && latest()?.revision === scope.revision,
      }
      const bindings = byNode.get(node) ?? []; bindings.push(binding); byNode.set(node, bindings)
    }
  }
  const bindings = [...byNode.values()].flat()
  for (const rows of byNode.values()) if (rows.length > 1) for (const row of rows) row.reason = 'This SVG label is shared. Use the existing canonical-owner editor.'
  const activePointers = new Set<number>()
  const track = (e: PointerEvent) => { if ((e.target as Element)?.closest?.('[data-review-event]')) activePointers.add(e.pointerId) }
  const release = (e: PointerEvent) => activePointers.delete(e.pointerId)
  const intercept = (e: Event) => {
    const rows = e.composedPath().flatMap(n => byNode.get(n as SVGGraphicsElement) ?? [])
    if (!rows.length) return
    // Both initial clicks must be isolated from insertion/tie/note handlers, even when activation is refused.
    e.stopPropagation(); e.preventDefault()
    if (e.type !== 'dblclick' || !enabled() || activePointers.size || root.querySelector('[data-pitch-preview]')) return
    const binding = rows[0]
    if (!binding.valid()) return
    const box = binding.node.getBoundingClientRect()
    const overlap = bindings.some(other => other.node !== binding.node && other.node.isConnected && overlapping(box, other.node.getBoundingClientRect()))
    open(overlap ? { ...binding, reason: 'These lyric labels overlap. Select a canonical owner explicitly; direct editing is unavailable.',
      owners: [...new Map(bindings.filter(other => other.node === binding.node || overlapping(box, other.node.getBoundingClientRect())).flatMap(b => b.owners).map(l => [l.id, l])).values()] } : binding)
  }
  const oldStyles = [...byNode.keys()].map(node => ({ node, userSelect: node.style.userSelect }))
  for (const { node } of oldStyles) node.style.userSelect = 'none'
  const events = ['pointerdown', 'mousedown', 'pointerup', 'click', 'dblclick']
  for (const type of events) root.addEventListener(type, intercept, true)
  root.addEventListener('pointerdown', track, true)
  document.addEventListener('pointerup', release, true); document.addEventListener('pointercancel', release, true)
  return { bindings,
    canEdit(binding: LyricBinding) {
      return enabled() && !activePointers.size && !root.querySelector('[data-pitch-preview]') && binding.valid() && !binding.reason
        && !bindings.some(other => other.node !== binding.node && other.node.isConnected && overlapping(binding.node.getBoundingClientRect(), other.node.getBoundingClientRect()))
    },
    dispose() {
    disposed = true
    for (const type of events) root.removeEventListener(type, intercept, true)
    root.removeEventListener('pointerdown', track, true)
    document.removeEventListener('pointerup', release, true); document.removeEventListener('pointercancel', release, true)
    for (const { node, userSelect } of oldStyles) node.style.userSelect = userSelect
  } }
}
