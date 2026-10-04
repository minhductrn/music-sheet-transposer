import type { ScoreEvent } from '../types/review'

export function eventLabel(event: ScoreEvent): string {
  const pitch = event.pitch ? `${event.pitch.step}${event.pitch.alter !== '0' ? ` (alter ${event.pitch.alter})` : ''}${event.pitch.octave}` : event.kind
  return `${pitch} · onset ${event.onset ?? '?'} · duration ${event.duration ?? (event.grace ? 'grace' : '?')} · staff ${event.staff ?? '?'} · ${event.display_size}${event.chord_member ? ' · chord' : ''}`
}
