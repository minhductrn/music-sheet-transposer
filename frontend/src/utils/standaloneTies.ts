/** Read-only compatibility for explicitly owned ties that OSMD did not parse. */
import { Pitch as OsmdPitch, type OpenSheetMusicDisplay, type VexFlowGraphicalNote } from 'opensheetmusicdisplay'
import { drawCorrectionTies } from './scoreTies'
import { mappedEvent, type Score } from './visualReview'

const children = (node: Element, name: string) => Array.from(node.children).filter(n => n.localName === name)
const child = (node: Element, name: string) => children(node, name)[0]
const text = (node: Element, name: string) => child(node, name)?.textContent?.trim()

/** Ephemeral view identities use the existing review e-N document-order convention. */
export function standaloneTieScore(document: Document): Score | null {
  const endpoints: { node: Element; event: Record<string, unknown>; part: number }[] = []
  let serial = 0
  const parts = children(document.documentElement, 'part').map((part, partIndex) => {
    let divisions = NaN
    const measures = children(part, 'measure').map((measure, index) => {
      let cursor = 0, previous = 0, valid = true
      const events: Record<string, unknown>[] = []
      for (const node of Array.from(measure.children)) {
        if (node.localName === 'attributes') {
          const value = text(node, 'divisions')
          if (value !== undefined) divisions = Number(value)
        } else if (node.localName === 'backup' || node.localName === 'forward') {
          cursor += (node.localName === 'backup' ? -1 : 1) * Number(text(node, 'duration')) / divisions
          if (!Number.isFinite(cursor) || cursor < 0) valid = false
        } else if (node.localName === 'note') {
          const grace = Boolean(child(node, 'grace'))
          const chord = Boolean(child(node, 'chord'))
          const onset = chord ? previous : cursor
          const duration = grace ? 0 : Number(text(node, 'duration')) / divisions
          const pitch = child(node, 'pitch')
          const event = { id: `e-${++serial}`, staff: Number(text(node, 'staff') ?? '1'),
            voice: text(node, 'voice') ?? '1', onset: String(onset), duration: String(duration), grace,
            kind: pitch ? 'note' : child(node, 'rest') ? 'rest' : 'unpitched',
            pitch: pitch ? { step: text(pitch, 'step'), octave: Number(text(pitch, 'octave')), alter: text(pitch, 'alter') ?? '0' } : null,
          }
          if (!Number.isFinite(onset) || !Number.isFinite(duration) || (!grace && duration <= 0)) valid = false
          events.push(event)
          for (const notation of children(node, 'notations')) for (const tied of children(notation, 'tied'))
            endpoints.push({ node: tied, event, part: partIndex })
          previous = onset
          if (!chord && !grace) cursor += duration
        }
      }
      // Unresolvable timing must not acquire a guessed graphical identity.
      if (!valid) for (const event of events) event.onset = null
      return { id: `m-${partIndex}-${index}`, index, voices: [{ events }] }
    })
    return { id: part.getAttribute('id') ?? String(partIndex), measures }
  })
  const ids = new Map<string, typeof endpoints>()
  for (const endpoint of endpoints) {
    const id = endpoint.node.getAttribute('id')
    if (id) ids.set(id, [...(ids.get(id) ?? []), endpoint])
  }
  let pairs = 0
  for (const [id, starts] of ids) {
    if (!/^review-tie-[0-9a-f]{32}-s[01]-t[01]-start$/.test(id) || starts.length !== 1) continue
    const stops = ids.get(id.slice(0, -6) + '-stop')
    if (stops?.length !== 1) continue
    const source = starts[0], target = stops[0]
    const number = source.node.getAttribute('number')
    if (source.part !== target.part || source.event === target.event || source.node.getAttribute('type') !== 'start'
      || target.node.getAttribute('type') !== 'stop' || !number || !/^(?:[2-9]|1[0-6])$/.test(number)
      || target.node.getAttribute('number') !== number || source.event.grace || target.event.grace
      || source.event.onset === null || target.event.onset === null || !source.event.pitch || !target.event.pitch) continue
    const a = source.event.pitch as { step: string; octave: number; alter: string }
    const b = target.event.pitch as typeof a
    if (a.step !== b.step || a.octave !== b.octave || Number(a.alter) !== Number(b.alter)) continue
    const orientations: Record<string, string> = { over: 'up', under: 'down' }
    const placements: Record<string, string> = { above: 'up', below: 'down' }
    const direction = (node: Element) => orientations[node.getAttribute('orientation') ?? '']
      ?? placements[node.getAttribute('placement') ?? '']
    const startDirection = direction(source.node), stopDirection = direction(target.node)
    if (startDirection && stopDirection && startDirection !== stopDirection) continue
    // Multiple owned relationships from one event cannot be silently collapsed.
    if (source.event.tie_relationship) { source.event.ambiguous = true; continue }
    source.event.tie_relationship = { source_event_id: source.event.id, target_event_id: target.event.id,
      source_visual_id: id, target_visual_id: id.slice(0, -6) + '-stop', origin: 'EXPORTED_CORRECTION' }
    source.event.tie_direction = startDirection ?? stopDirection
    pairs++
  }
  for (const part of parts) for (const measure of part.measures) for (const voice of measure.voices)
    for (const event of voice.events) if (event.ambiguous) delete event.tie_relationship
  // Only fields consumed by mappedEvent/drawCorrectionTies; never a canonical review session.
  return pairs ? { parts } as unknown as Score : null
}

/** Pair-level native evidence, never a chord-wide getTieSVGs() result. */
export function nativeTieState(source: VexFlowGraphicalNote['sourceNote'], target: VexFlowGraphicalNote['sourceNote']): 'present' | 'missing' | 'unknown' {
  if (!('NoteTie' in source) || !('NoteTie' in target)) return 'unknown'
  const ties = [source.NoteTie, target.NoteTie].filter(Boolean)
  for (const tie of ties) {
    const notes = tie.Notes
    if (!Array.isArray(notes)) return 'unknown'
    if (notes.some((note, index) => note === source && notes[index + 1] === target)) return 'present'
  }
  return ties.length ? 'unknown' : 'missing'
}

export function drawStandaloneTies(osmd: OpenSheetMusicDisplay, score: Score): () => void {
  const mappings = new Map<string, { note: VexFlowGraphicalNote['sourceNote']; head: HTMLElement }[]>()
  for (const row of osmd.GraphicSheet.MeasureList) for (const measure of row) for (const entry of measure.staffEntries)
    for (const voice of entry.graphicalVoiceEntries) for (const graphical of voice.notes) {
      const note = graphical.sourceNote, staff = note.ParentStaff, pitch = note.Pitch
      if (!staff || !pitch) continue
      const event = mappedEvent(score, { partIndex: osmd.Sheet.Instruments.indexOf(staff.ParentInstrument),
        measureIndex: osmd.Sheet.SourceMeasures.indexOf(note.SourceMeasure),
        staff: staff.ParentInstrument.Staves.indexOf(staff) + 1, voice: String(note.ParentVoiceEntry.ParentVoice.VoiceId),
        onset: note.ParentVoiceEntry.Timestamp.RealValue * 4, duration: note.Length.RealValue * 4,
        grace: note.IsGraceNote, kind: 'note', step: OsmdPitch.getNoteEnumString(pitch.FundamentalNote),
        octave: pitch.Octave + OsmdPitch.OctaveXmlDifference, alter: pitch.AccidentalHalfTones ?? 0 })
      if (!event) continue
      const vf = graphical as VexFlowGraphicalNote
      const head = vf.getNoteheadSVGs?.()[vf.vfnote?.[1] ?? vf.vfnoteIndex] as unknown as HTMLElement | undefined
      if (head) mappings.set(event.id, [...(mappings.get(event.id) ?? []), { note, head }])
    }
  const events = score.parts.flatMap(p => p.measures.flatMap(m => m.voices.flatMap(v => v.events)))
  const missing = new Set<string>()
  for (const event of events) {
    const link = event.tie_relationship
    if (!link) continue
    const sources = mappings.get(event.id), targets = mappings.get(link.target_event_id)
    if (sources?.length !== 1 || targets?.length !== 1) continue
    if (sources[0].head === targets[0].head) continue
    // Shared unison heads are not a unique source or destination mapping.
    if ([...mappings.values()].flat().filter(m => m.head === sources[0].head || m.head === targets[0].head).length !== 2) continue
    if (nativeTieState(sources[0].note, targets[0].note) === 'missing') missing.add(event.id)
  }
  const view = { ...score, parts: score.parts.map(p => ({ ...p, measures: p.measures.map(m => ({ ...m,
    voices: m.voices.map(v => ({ ...v, events: v.events.map(e => ({ ...e,
      tie_relationship: missing.has(e.id) ? e.tie_relationship : null })) })) })) })) }
  return drawCorrectionTies(view, [...mappings].flatMap(([id, values]) => values.map(m => ({ id, node: m.head }))), () => {})
}
