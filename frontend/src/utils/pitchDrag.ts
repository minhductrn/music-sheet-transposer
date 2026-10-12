/** UI-only vertical preview. Completed safe gestures emit exactly one pitch edit. */
import type { Pitch, ScoreEvent, Measure } from '../types/review'
import { movePitch } from './visualReview'
import { scorePoint } from './scoreInsertion'
export const PITCH_DRAG_THRESHOLD = 5
export interface PitchStaff { top: number; spacing: number; minY: number; maxY: number }
export function clefBottom(clef: ScoreEvent['clef']): number | null {
  const fields = clef?.fields as { name: string; text: string | null }[] | undefined
  if (!Array.isArray(fields)) return null
  const field = (name: string) => fields.filter((f) => f.name === name)
  if (field('sign').length !== 1 || field('line').length !== 1 || field('clef-octave-change').length > 1) return null
  const sign = field('sign')[0].text, line = Number(field('line')[0].text)
  const shift = Number(field('clef-octave-change')[0]?.text ?? 0)
  const reference = sign === 'G' ? 32 : sign === 'F' ? 24 : sign === 'C' ? 28 : null
  return reference !== null && Number.isInteger(line) && line >= 1 && line <= 5 && Number.isInteger(shift) && Math.abs(shift) <= 2
    ? reference - (line - 1) * 2 + shift * 7 : null
}
export function resolveDragPitch(event: ScoreEvent, measure: Measure, staff: PitchStaff, y: number, otherStaffs: PitchStaff[] = []): Pitch | null {
  const bottom = clefBottom(event.clef)
  if (bottom === null || !event.pitch?.step || event.pitch.octave === null || !Number.isFinite(y) ||
      !Object.values(staff).every(Number.isFinite) || staff.spacing <= 0 || staff.minY >= staff.maxY ||
      y < staff.minY || y > staff.maxY || otherStaffs.some((s) => y >= s.minY && y <= s.maxY)) return null
  const absolute = bottom + Math.round((staff.top + 4 * staff.spacing - y) / (staff.spacing / 2))
  const start = event.pitch.octave * 7 + 'CDEFGAB'.indexOf(event.pitch.step)
  const explicit = event.accidental?.text
  const supported: Record<string, string> = { natural: '0', sharp: '1', flat: '-1', 'double-sharp': '2', 'flat-flat': '-2' }
  // Unsupported signs cannot safely round-trip through the existing pitch patcher.
  if (explicit && (supported[explicit] === undefined || Number(supported[explicit]) !== Number(event.pitch.alter))) return null
  if (absolute === start) return { step: event.pitch.step, octave: event.pitch.octave, alter: event.pitch.alter }
  const target = movePitch(event.pitch, absolute - start, event.key_signature ? { ...measure, key_signature: event.key_signature } : measure, event.staff)
  if (target && event.accidental?.text) target.alter = event.pitch.alter
  return target
}
export interface DragCallbacks { enabled: () => boolean; select: () => void; commit: (pitch: Pitch) => void }
export function bindPitchDrag(node: HTMLElement, svg: SVGSVGElement, pixelsPerUnit: number,
  event: ScoreEvent, measure: Measure, staff: PitchStaff, otherStaffs: PitchStaff[], x: number, callbacks: DragCallbacks) {
  let gesture: { id: number; startY: number; dragging: boolean; pitch: Pitch | null } | null = null
  let marker: SVGGElement | null = null
  let suppressClick = false
  const oldTouchAction = node.style.touchAction
  node.style.touchAction = 'none'
  const clear = () => { marker?.remove(); marker = null }
  const down = (e: PointerEvent) => {
    if (e.button !== 0 || !e.isPrimary || gesture || !callbacks.enabled()) return
    gesture = { id: e.pointerId, startY: e.clientY, dragging: false, pitch: null }
    suppressClick = false; node.setPointerCapture(e.pointerId)
  }
  const move = (e: PointerEvent) => {
    if (!gesture || gesture.id !== e.pointerId) return
    if (!gesture.dragging && Math.abs(e.clientY - gesture.startY) < PITCH_DRAG_THRESHOLD) return
    if (!gesture.dragging) { gesture.dragging = true; callbacks.select() }
    e.preventDefault(); clear()
    const point = scorePoint(svg, e.clientX, e.clientY, pixelsPerUnit)
    gesture.pitch = callbacks.enabled() && point ? resolveDragPitch(event, measure, staff, point.y, otherStaffs) : null
    marker = document.createElementNS('http://www.w3.org/2000/svg', 'g')
    marker.setAttribute('pointer-events', 'none'); marker.setAttribute('data-pitch-preview', 'true')
    const text = document.createElementNS(marker.namespaceURI, 'text')
    const pitch = gesture.pitch, bottom = clefBottom(event.clef)
    const y = pitch && bottom !== null ? staff.top + 4 * staff.spacing - (pitch.octave * 7 + 'CDEFGAB'.indexOf(pitch.step) - bottom) * staff.spacing / 2 : point?.y ?? staff.top
    text.setAttribute('x', String((x + 1) * pixelsPerUnit)); text.setAttribute('y', String(y * pixelsPerUnit))
    text.setAttribute('fill', pitch ? '#155e75' : '#b91c1c'); text.setAttribute('font-size', '14')
    text.textContent = pitch ? `● ${pitch.step}${pitch.octave}` : 'Invalid pitch target — release to cancel'
    marker.appendChild(text); svg.appendChild(marker)
  }
  const finish = (e: PointerEvent) => {
    if (!gesture || gesture.id !== e.pointerId) return
    if (e.type === 'pointerup' && gesture.dragging) move(e)
    const completed = gesture
    gesture = null; clear(); suppressClick = completed.dragging
    if (node.hasPointerCapture(e.pointerId)) node.releasePointerCapture(e.pointerId)
    if (e.type === 'pointerup' && completed.dragging && completed.pitch && callbacks.enabled() &&
        (completed.pitch.step !== event.pitch?.step || completed.pitch.octave !== event.pitch?.octave || completed.pitch.alter !== event.pitch?.alter)) callbacks.commit(completed.pitch)
  }
  const click = (e: MouseEvent) => { if (suppressClick) { e.preventDefault(); e.stopImmediatePropagation(); suppressClick = false } }
  node.addEventListener('pointerdown', down); node.addEventListener('pointermove', move)
  node.addEventListener('pointerup', finish); node.addEventListener('pointercancel', finish); node.addEventListener('lostpointercapture', finish)
  node.addEventListener('click', click, true)
  return () => {
    if (gesture && node.hasPointerCapture(gesture.id)) node.releasePointerCapture(gesture.id)
    gesture = null; clear(); node.style.touchAction = oldTouchAction
    node.removeEventListener('pointerdown', down); node.removeEventListener('pointermove', move)
    node.removeEventListener('pointerup', finish); node.removeEventListener('pointercancel', finish); node.removeEventListener('lostpointercapture', finish)
    node.removeEventListener('click', click, true)
  }
}
