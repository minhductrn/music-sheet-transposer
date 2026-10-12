import type { Measure, Pitch, ReviewSession, ScoreEvent } from '../types/review'

export const durations = [
  ['1/4', '𝅘𝅥𝅯', 'Sixteenth'], ['1/2', '♪', 'Eighth'], ['1', '♩', 'Quarter'],
  ['3/2', '♩·', 'Dotted quarter'], ['2', '𝅗𝅥', 'Half'], ['3', '𝅗𝅥·', 'Dotted half'], ['4', '𝅝', 'Whole'],
] as const

export function amount(value: string | null): number {
  if (value === null) return NaN
  const [n, d = '1'] = value.split('/')
  return Number(n) / Number(d)
}

export function durationChoices(divisions: string | null, supported?: string[]) {
  const scale = amount(divisions)
  return durations.filter(([value]) => Number.isInteger(amount(value) * scale) && scale > 0 && (supported === undefined || supported.includes(value)))
}

// Semantic diatonic movement works independently of clef or screen geometry.
// Use the destination key spelling; explicit accidental controls remain available.
export function movePitch(pitch: ScoreEvent['pitch'], direction: number, measure: Measure, staff: number | null): Pitch | null {
  if (!pitch || pitch.step === null || pitch.octave === null) return null
  const steps = 'CDEFGAB'
  const index = steps.indexOf(pitch.step)
  if (index < 0 || !Number.isInteger(pitch.octave)) return null
  const absolute = pitch.octave * 7 + index + direction
  const octave = Math.floor(absolute / 7)
  if (octave < 0 || octave > 9) return null
  const step = steps[((absolute % 7) + 7) % 7]
  const key = measure.key_signature?.find((k) => k.staff === String(staff)) ?? measure.key_signature?.find((k) => k.staff === null)
  if (key && (key.fifths === null || !/^-?[0-7]$/.test(key.fifths))) return null
  const fifths = Number(key?.fifths ?? 0)
  const altered = (fifths > 0 ? 'FCGDAEB' : 'BEADGCF').slice(0, Math.abs(fifths)).includes(step)
  return { step, octave, alter: altered ? (fifths > 0 ? '1' : '-1') : '0' }
}

export function insertion(event: ScoreEvent, measure: Measure, pitch: Pitch, duration: string, position: string) {
  return { measure_id: measure.id, kind: 'note', pitch, duration, grace: false,
    ...(position === 'simultaneous' ? { same_onset_id: event.id } : position === 'before' ? { before_event_id: event.id } : { after_event_id: event.id }) }
}

export function friendlyDiagnostic(code: string, message: string): string {
  if (code === 'measure_overfilled') return 'This measure has notes extending beyond the expected barline. Compare with the source; faithful unusual notation can be explicitly confirmed.'
  if (code === 'voice_overlap') return 'Some notes overlap in time. Check their placement against the source or use Advanced review.'
  if (code === 'voice_underfilled' || code === 'measure_duration_mismatch') return 'This measure may have missing notes or be an intentional partial measure. Compare it with the source.'
  if (code === 'empty_measure') return 'This measure is empty. Compare it with the source before adding notes or rests.'
  if (code.includes('tie')) return message
  return message
}

export function sessionExpired(error: unknown): boolean {
  return error instanceof Error && /Review session was not found or has expired/i.test(error.message)
}

export type Score = ReviewSession['score']

// A local, single-voice mixed-size chord with an authoritative lyrical anchor.
// Size alone, coincident notes, or a missing lyric cannot establish this relation.
export function auxiliaryLyricOwner(score: Score, event?: ScoreEvent): ScoreEvent | null {
  if (!event || event.kind !== 'note' || event.display_size !== 'small' || event.grace || event.cue
    || !event.chord_member || !event.chord_id || event.staff !== 1
    || event.lyric_ids.length || score.lyrics.some(l => l.event_id === event.id)
    || score.parts.length !== 1) return null
  const measure = score.parts[0].measures.find(m => m.voices.some(v => v.events.includes(event)))
  if (!measure || measure.staves !== 1 || measure.rhythm_status === 'STRUCTURALLY_AMBIGUOUS') return null
  const events = measure.voices.flatMap(v => v.events)
  const chord = events.filter(e => e.chord_id === event.chord_id)
  const owner = chord.find(e => e.id === event.chord_id)
  const onset = amount(event.onset), duration = amount(event.duration)
  if (chord.length !== 2 || !owner || owner.id === event.id || owner.chord_member
    || owner.kind !== 'note' || owner.display_size !== 'normal' || owner.grace || owner.cue
    || owner.staff !== event.staff || owner.voice !== event.voice
    || !Number.isFinite(onset) || onset < 0 || !Number.isFinite(duration) || duration <= 0
    || amount(owner.onset) !== onset || amount(owner.duration) !== duration
    || !score.lyrics.some(l => l.event_id === owner.id)) return null
  // A separate concurrent voice may represent an independent singer. Unknown
  // timing is also insufficient evidence for the auxiliary interpretation.
  if (events.some(e => !chord.includes(e) && e.kind !== 'rest' && (
    !Number.isFinite(amount(e.onset)) || !Number.isFinite(amount(e.duration))
    || (amount(e.onset) < onset + duration && amount(e.onset) + amount(e.duration) > onset)
    || (e.grace && amount(e.onset) >= onset && amount(e.onset) < onset + duration)
  ))) return null
  return owner
}

export interface RenderedIdentity {
  partIndex: number; measureIndex: number; staff: number; voice: string
  onset: number; duration: number; grace: boolean; kind: string
  step: string | null; octave: number | null; alter: number
}

// Resolve only a unique semantic match; never assign XML order to graphical order.
export function mappedEvent(score: Score, identity: RenderedIdentity): ScoreEvent | null {
  const measure = score.parts[identity.partIndex]?.measures.find((m) => m.index === identity.measureIndex)
  const candidates = measure?.voices.flatMap((v) => v.events).filter((e) =>
    e.staff === identity.staff && e.voice === identity.voice && e.kind === identity.kind && e.grace === identity.grace
    && Math.abs(amount(e.onset) - identity.onset) < 1e-7
    && (e.grace || Math.abs(amount(e.duration) - identity.duration) < 1e-7)
    && (e.kind !== 'note' || (e.pitch?.step === identity.step && e.pitch.octave === identity.octave && Number(e.pitch.alter) === identity.alter))) ?? []
  return candidates.length === 1 ? candidates[0] : null
}
