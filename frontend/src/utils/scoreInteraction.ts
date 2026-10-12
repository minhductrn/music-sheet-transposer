import { Pitch as OsmdPitch, type OpenSheetMusicDisplay, type VexFlowGraphicalNote } from 'opensheetmusicdisplay'
import { drawCorrectionTies } from './scoreTies'
import { bindPitchDrag, clefBottom, type PitchStaff } from './pitchDrag'
import type { Pitch, ScoreEvent, Measure } from '../types/review'
import { mappedEvent, type Score } from './visualReview'

// VexFlow's rendered head metadata is not exposed by OSMD's StemmableNote type.
// Fail closed if a renderer version no longer supplies these fields.
type RenderedHeads = {
  isDisplaced?: () => boolean
  note_heads?: { glyph_code?: string; custom_glyph?: boolean; isDisplaced?: () => boolean }[]
  getKeyProps?: () => { line: number }[]
}

function supportedMatrix(m: DOMMatrix | null): m is DOMMatrix {
  return Boolean(m && [m.a, m.b, m.c, m.d, m.e, m.f].every(Number.isFinite)
    && m.a > 0 && m.d > 0 && Math.abs(m.b) < 1e-9 && Math.abs(m.c) < 1e-9
    && Math.abs(m.a - m.d) < 1e-9)
}

/** Only ordinary, untied, non-displaced up-stem heads have verified attachment geometry. */
function stemPivot(vf: VexFlowGraphicalNote, head: SVGGraphicsElement, box: DOMRect, tied: boolean): number | null {
  try {
    const note = vf.sourceNote, rendered = vf.vfnote?.[0]
    const index = vf.vfnote?.[1] ?? vf.vfnoteIndex
    const metadata = rendered as unknown as RenderedHeads
    const renderedHead = metadata?.note_heads?.[index]
    const entry = vf.parentVoiceEntry?.parentStaffEntry
    if (tied || note.isRest() || note.IsGraceNote || note.IsCueNote || !note.PrintObject
      || !('NoteTie' in note) || note.NoteTie || !Array.isArray(note.NoteSlurs) || note.NoteSlurs.length
      || note.CustomNoteheadVFCode || note.Notehead
      || vf.getTieSVGs?.().length !== 0 || vf.getSlurSVGs?.().length !== 0
      || rendered?.getStemDirection?.() !== 1 || metadata.isDisplaced?.() !== false
      || renderedHead?.glyph_code !== 'vb' || renderedHead.custom_glyph
      || renderedHead.isDisplaced?.() !== false || note.sharesNoteheadWithVisibleUnisonNote?.() !== false
      || !entry || entry.graphicalLink || note.ParentStaffEntry?.Link
      || entry.parentMeasure?.ParentStaff !== note.ParentStaff
      || !note.ParentVoiceEntry.Notes?.length
      || !note.ParentVoiceEntry.Notes.every(n => n.ParentStaff === note.ParentStaff)
      || !vf.parentVoiceEntry.notes.every(g => g.sourceNote.ParentStaff === note.ParentStaff)) return null
    const keys = metadata.getKeyProps?.()
    if (!keys?.length || keys.some(k => !Number.isFinite(k.line)) || new Set(keys.map(k => k.line)).size !== keys.length) return null

    const headPaths = head.querySelectorAll('path')
    if (headPaths.length !== 1) return null
    const stem = vf.getStemSVG?.() as unknown as SVGGraphicsElement | null
    const svg = head.ownerSVGElement
    if (!svg || !stem || stem.tagName.toLowerCase() !== 'path' || stem.ownerSVGElement !== svg) return null
    // Resolve by renderer identity, never by pitch or nearest-stem distance.
    const groups = Array.from(svg.querySelectorAll('[id]')).filter(n => n.id === `vf-${vf.getSVGId()}-stem`)
    if (groups.length !== 1) return null
    const paths = groups[0].querySelectorAll('path')
    if (paths.length !== 1 || paths[0] !== stem) return null
    const view = head.ownerDocument.defaultView
    if (!view) return null
    const painted = (color: string) => /^(?:#[\da-f]{3}(?:[\da-f]{3})?|rgb\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\))$/i.test(color)
    const fill = view.getComputedStyle(headPaths[0])
    if (!painted(fill.fill) || !(Number(fill.fillOpacity) > 0) || fill.stroke !== 'none') return null
    for (const element of [head, headPaths[0], stem]) {
      if (!supportedMatrix(element.getScreenCTM())) return null
      for (let n: Element | null = element; n; n = n.parentElement) {
        const style = view.getComputedStyle(n)
        if (style.display === 'none' || style.visibility !== 'visible' || !(Number(style.opacity) > 0)
          || style.vectorEffect !== 'none') return null
        if (n === svg) break
      }
    }
    const style = view.getComputedStyle(stem)
    const width = Number.parseFloat(style.strokeWidth)
    if (!(width > 0) || !Number.isFinite(width) || !painted(style.stroke)
      || !(Number(style.strokeOpacity) > 0) || style.strokeDasharray !== 'none') return null
    const hm = head.getScreenCTM(), sm = stem.getScreenCTM()
    if (!supportedMatrix(hm) || !supportedMatrix(sm)) return null
    const relative = hm.inverse().multiply(sm)
    if (!supportedMatrix(relative)) return null
    // Accept only the renderer's single absolute vertical line, not a curve or multi-segment stem.
    const number = '([-+]?(?:\\d*\\.?\\d+)(?:[eE][-+]?\\d+)?)'
    const line = new RegExp(`^\\s*M\\s*${number}[ ,]+${number}\\s*L\\s*${number}[ ,]+${number}\\s*$`).exec(stem.getAttribute('d') ?? '')
    if (!line) return null
    const [x1, y1, x2, y2] = line.slice(1).map(Number)
    const x = relative.a * x1 + relative.e
    const bottom = relative.d * y1 + relative.f, top = relative.d * y2 + relative.f
    const halfStroke = width * relative.a / 2, centerY = box.y + box.height / 2
    if (![x1, y1, x2, y2, x, top, bottom, halfStroke].every(Number.isFinite)
      || Math.abs(x1 - x2) > 1e-9 || top >= bottom || !(box.width > 0 && box.height > 0)
      || box.x + box.width / 2 >= x
      || box.x + box.width < x - halfStroke || box.x + box.width > x + halfStroke + 1e-3
      || centerY < top - halfStroke || centerY > bottom + halfStroke) return null
    return x
  } catch {
    // Detached SVG nodes or unsupported renderer APIs retain the existing center scaling.
    return null
  }
}

/** SVG nodes are view-only handles. Identity is resolved from OSMD's source semantics. */
export function bindScore(osmd: OpenSheetMusicDisplay, score: Score, select: (id: string) => void, drag?: { enabled: () => boolean; commit: (id: string, pitch: Pitch) => void }) {
  const tiedIds = new Set<string>()
  const relationshipEvents = score.parts.flatMap(p => p.measures.flatMap(m => m.voices.flatMap(v => v.events)))
  const eventIds = new Set(relationshipEvents.map(e => e.id))
  let ambiguousRelationships = eventIds.size !== relationshipEvents.length
  const excludePair = (source: string, target: string) => {
    if (typeof source !== 'string' || typeof target !== 'string' || source === target
      || !eventIds.has(source) || !eventIds.has(target)) ambiguousRelationships = true
    else { tiedIds.add(source); tiedIds.add(target) }
  }
  for (const event of relationshipEvents) {
    // tie_target_ids are picker candidates, never established relationships.
    // Minimal view inputs may omit ties only with explicit null relationship fields;
    // stemPivot also requires parsed source/rendered evidence of no ties or slurs.
    if (!Array.isArray(event.ties)
      && !(event.ties === undefined && event.tie_target_id === null && event.tie_relationship === null)) tiedIds.add(event.id)
    if (event.ties?.length || event.tie_correction_error || event.tie_source_editable === false) tiedIds.add(event.id)
    if (event.tie_target_id !== undefined && event.tie_target_id !== null) excludePair(event.id, event.tie_target_id)
    if (event.tie_relationship !== undefined && event.tie_relationship !== null) {
      const link = event.tie_relationship
      excludePair(link.source_event_id, link.target_event_id)
      if (event.id !== link.source_event_id && event.id !== link.target_event_id) ambiguousRelationships = true
    }
  }
  // A malformed explicit pair cannot establish which other endpoint is affected.
  if (ambiguousRelationships) for (const id of eventIds) tiedIds.add(id)
  const renderedNotes = new Map<HTMLElement, Set<VexFlowGraphicalNote>>()
  const contexts = new Map<HTMLElement, { event: ScoreEvent; measure: Measure; staff: PitchStaff; line: object; page: number; x: number }>()
  const staffs = new Map<object, { staff: PitchStaff; page: number }>()
  for (const row of osmd.GraphicSheet.MeasureList) for (const m of row) {
    const line = m?.ParentStaffLine
    if (!line || staffs.has(line) || line.ParentStaff.isTab || line.ParentStaff.StafflineCount !== 5 || line.StaffLines.length !== 5) continue
    const lines = line.StaffLines
    const spacing = (lines[4].Start.y - lines[0].Start.y) / 4
    if (!lines.every((l, i) => Number.isFinite(l.Start.y) && Math.abs(l.Start.y - l.End.y) < 1e-7 && Math.abs(l.Start.y - lines[0].Start.y - i * spacing) < 1e-7)) continue
    const top = line.PositionAndShape.AbsolutePosition.y + lines[0].Start.y
    if (Number.isFinite(top) && Number.isFinite(spacing) && spacing > 0)
      staffs.set(line, { staff: { top, spacing, minY: top - 3 * spacing, maxY: top + 7 * spacing }, page: line.ParentMusicSystem.Parent.PageNumber })
  }
  const bindings = new Map<HTMLElement, Set<string>>()
  for (const measures of osmd.GraphicSheet.MeasureList) for (const measure of measures) {
    if (!measure) continue
    for (const entry of measure.staffEntries) for (const voice of entry.graphicalVoiceEntries) for (const graphical of voice.notes) {
      const note = graphical.sourceNote
      const staff = note?.ParentStaff
      if (!staff?.ParentInstrument || !note.ParentVoiceEntry || !note.SourceMeasure) continue
      if (measure.parentSourceMeasure !== note.SourceMeasure) continue // Never bind a renderer-generated continuation across a barline.
      const pitch = note.Pitch
      const event = mappedEvent(score, {
        partIndex: osmd.Sheet.Instruments.indexOf(staff.ParentInstrument),
        measureIndex: osmd.Sheet.SourceMeasures.indexOf(note.SourceMeasure),
        staff: staff.ParentInstrument.Staves.indexOf(staff) + 1,
        voice: String(note.ParentVoiceEntry.ParentVoice.VoiceId),
        onset: note.ParentVoiceEntry.Timestamp.RealValue * 4,
        duration: note.Length.RealValue * 4, grace: note.IsGraceNote,
        kind: note.isRest() ? 'rest' : pitch ? 'note' : 'unpitched',
        step: pitch ? OsmdPitch.getNoteEnumString(pitch.FundamentalNote) : null,
        octave: pitch ? pitch.Octave + OsmdPitch.OctaveXmlDifference : null,
        alter: pitch?.AccidentalHalfTones ?? 0,
      })
      if (!event) continue
      const vf = graphical as VexFlowGraphicalNote
      const heads = vf.getNoteheadSVGs?.() ?? []
      // getNoteheadSVGs returns the entire chord; VexFlow's semantic key index
      // selects this particular head, even when graphical notes are pitch-sorted.
      const head = heads[vf.vfnote?.[1] ?? vf.vfnoteIndex]
      if (!head) continue
      const geometry = staffs.get(measure.ParentStaffLine)
      const canonicalMeasure = score.parts[osmd.Sheet.Instruments.indexOf(staff.ParentInstrument)]?.measures.find((m) => m.index === osmd.Sheet.SourceMeasures.indexOf(note.SourceMeasure))
      const bottom = geometry ? clefBottom(event.clef) : null
      const y = graphical.PositionAndShape?.AbsolutePosition.y ?? NaN
      const expectedY = geometry && event.pitch?.step && event.pitch.octave !== null && bottom !== null
        ? geometry.staff.top + 4 * geometry.staff.spacing - (event.pitch.octave * 7 + 'CDEFGAB'.indexOf(event.pitch.step) - bottom) * geometry.staff.spacing / 2 : NaN
      // Reject unsupported octave shifts/renderer geometry rather than guess.
      if (geometry && canonicalMeasure && event.kind === 'note' && Math.abs(y - expectedY) < geometry.staff.spacing / 4)
        contexts.set(head, { event, measure: canonicalMeasure, ...geometry, line: measure.ParentStaffLine, x: graphical.PositionAndShape.AbsolutePosition.x })
      if (!renderedNotes.has(head)) renderedNotes.set(head, new Set())
      renderedNotes.get(head)!.add(vf)
      if (!bindings.has(head)) bindings.set(head, new Set())
      bindings.get(head)!.add(event.id)
    }
  }
  const cleanups: (() => void)[] = []
  const targets: { node: HTMLElement; id: string }[] = []
  for (const [node, ids] of bindings) {
    if (ids.size !== 1) continue // Shared unison heads must never select an arbitrary voice.
    const id = [...ids][0]
    node.dataset.reviewEvent = id
    node.setAttribute('role', 'button')
    node.setAttribute('tabindex', '0')
    const owner = score.parts.flatMap((part) => part.measures).find((m) => m.voices.some((v) => v.events.some((e) => e.id === id)))
    const events = owner?.voices.flatMap((v) => v.events) ?? []
    const index = events.findIndex((e) => e.id === id)
    node.setAttribute('aria-label', `Select ${events[index]?.kind === 'rest' ? 'rest' : 'note'} ${index + 1}, measure ${owner?.number ?? ''}`)
    const canonical = events[index]
    if (canonical?.display_size === 'small' && !canonical.grace && !canonical.cue) {
      const head = node as unknown as SVGGraphicsElement
      const box = head.getBBox?.()
      if (box && [box.x, box.y, box.width, box.height].every(Number.isFinite)) {
        const old = node.getAttribute('transform')
        const candidates = renderedNotes.get(node)
        const vf = candidates?.size === 1 ? [...candidates][0] : null
        const anchored = canonical.kind === 'note' && vf ? stemPivot(vf, head, box, tiedIds.has(id)) : null
        const x = anchored ?? box.x + box.width / 2, y = box.y + box.height / 2
        // Supported heads keep contact with their own rendered stem; all others retain center scaling.
        node.setAttribute('transform', `${old ?? ''} translate(${x} ${y}) scale(.65) translate(${-x} ${-y})`)
        cleanups.push(() => { if (old === null) node.removeAttribute('transform'); else node.setAttribute('transform', old) })
      }
    }
    const context = contexts.get(node)
    const svg = drag && context ? node.closest('svg') as SVGSVGElement | null : null
    if (drag && context && svg) cleanups.push(bindPitchDrag(node, svg, osmd.Drawer.calculatePixelDistance(1),
      context.event, context.measure, context.staff,
      [...staffs.entries()].filter(([line, g]) => line !== context.line && g.page === context.page).map(([, g]) => g.staff),
      context.x, { enabled: drag.enabled, select: () => select(id), commit: (pitch) => drag.commit(id, pitch) }))
    const click = () => select(id)
    const key = (event: KeyboardEvent) => {
      if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); select(id) }
    }
    node.addEventListener('click', click)
    node.addEventListener('keydown', key)
    targets.push({ node, id })
    cleanups.push(() => {
      node.removeEventListener('click', click); node.removeEventListener('keydown', key)
      for (const name of ['data-review-event', 'role', 'tabindex', 'aria-label', 'aria-pressed', 'aria-disabled']) node.removeAttribute(name)
      node.classList.toggle('score-note-selected', false)
      node.classList.toggle('score-tie-target', false)
    })
  }
  cleanups.push(drawCorrectionTies(score, targets, select))
  return {
    highlight(selected: string | null, validTargets: string[] | null) {
      for (const { node, id } of targets) {
        node.classList.toggle('score-note-selected', id === selected)
        node.classList.toggle('score-tie-target', Boolean(validTargets?.includes(id)))
        node.setAttribute('aria-pressed', String(id === selected))
        node.setAttribute('aria-disabled', String(validTargets !== null && !validTargets.includes(id)))
      }
    },
    dispose() { cleanups.forEach((cleanup) => cleanup()) },
  }
}
