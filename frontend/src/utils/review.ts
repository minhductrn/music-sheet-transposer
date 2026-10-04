import type { ScoreEvent } from '../types/review'

export function eventLabel(event: ScoreEvent): string {
  const pitch = event.pitch ? `${event.pitch.step}${event.pitch.alter !== '0' ? ` (alter ${event.pitch.alter})` : ''}${event.pitch.octave}` : event.kind
  return `${pitch} · onset ${event.onset ?? '?'} · duration ${event.duration ?? (event.grace ? 'grace' : '?')} · staff ${event.staff ?? '?'} · ${event.display_size}${event.chord_member ? ' · chord' : ''}`
}

export function validDuration(value: string): boolean {
  if (!/^\d+(?:\.\d+|\/\d+)?$/.test(value)) return false
  const [numerator, denominator = '1'] = value.split('/')
  const amount = Number(numerator) / Number(denominator)
  return Number.isFinite(amount) && amount > 0 && amount <= 1024
}
