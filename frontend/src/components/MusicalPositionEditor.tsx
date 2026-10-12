import { useState } from 'react'
import type { Measure, Pitch } from '../types/review'
import { amount, movePitch } from '../utils/visualReview'
import { DurationPicker } from './VisualNoteEditor'

type Change = (path: string, method: 'POST' | 'PATCH' | 'DELETE', body?: unknown) => Promise<void>
export default function MusicalPositionEditor({ measure, staff, voices, busy, change }: {
  measure: Measure; staff: number; voices: string[]; busy: boolean; change: Change
}) {
  const [position, setPosition] = useState('')
  const [customPosition, setCustomPosition] = useState('0')
  const [voice, setVoice] = useState('')
  const [newVoice, setNewVoice] = useState('')
  const [pitch, setPitch] = useState<Pitch>({ step: 'C', octave: 4, alter: '0' })
  const [explicitAccidental, setExplicitAccidental] = useState('')
  const followPitch = movePitch(pitch, 0, measure, staff)
  const effectivePitch = explicitAccidental ? pitch : followPitch
  const [duration, setDuration] = useState('1')
  const [display, setDisplay] = useState('normal')
  const [grace, setGrace] = useState(false)
  const [kind, setKind] = useState('note')
  const onsets = Array.from(new Set(['0', ...measure.voices.flatMap((v) => v.events.flatMap((e) => e.onset === null ? [] : [e.onset]))]))
  const onset = position === 'custom' ? customPosition : position
  const selectedVoice = voice === 'new' ? newVoice.trim() : voice
  const validPosition = /^[+]?[0-9]+(?:\.[0-9]+|\/[0-9]+)?$/.test(onset) && Number.isFinite(amount(onset)) && amount(onset) >= 0 && amount(onset) <= 1024
  const validVoice = /^\S{1,32}$/.test(selectedVoice)
  return <fieldset disabled={busy} className="review-fields" aria-label="Insert at musical position">
    <legend>Add missing notation — measure {measure.number}, staff {staff}</legend>
    <label>Musical position <select aria-label="Musical position" value={position} onChange={(e) => setPosition(e.target.value)}>
      <option value="">Choose position</option>{onsets.map((value) => <option key={value} value={value}>{value === '0' ? 'Measure start' : `${value} quarter-note units from start`}</option>)}
      <option value="custom">Other position</option>
    </select></label>
    {position === 'custom' && <label>Position from measure start (quarter-note units)<input aria-label="Position from measure start" value={customPosition} onChange={(e) => setCustomPosition(e.target.value)} /></label>}
    <label>Voice <select aria-label="Insertion voice" value={voice} onChange={(e) => setVoice(e.target.value)}>
      <option value="">Choose voice</option>{voices.map((value) => <option key={value} value={value}>Voice {value}</option>)}<option value="new">New secondary voice</option>
    </select></label>
    {voice === 'new' && <label>Secondary voice label<input aria-label="Secondary voice label" value={newVoice} maxLength={32} onChange={(e) => setNewVoice(e.target.value)} /></label>}
    <label>Notation <select value={kind} onChange={(e) => { setKind(e.target.value); if (e.target.value === 'rest') setGrace(false) }}><option value="note">Note</option><option value="rest">Rest</option></select></label>
    {kind === 'note' && <>
      <label>Pitch <select aria-label="Insertion pitch" value={pitch.step} onChange={(e) => setPitch({ ...pitch, step: e.target.value })}>{'CDEFGAB'.split('').map((step) => <option key={step}>{step}</option>)}</select></label>
      <label>Octave <select aria-label="Insertion octave" value={pitch.octave} onChange={(e) => setPitch({ ...pitch, octave: Number(e.target.value) })}>{Array.from({ length: 10 }, (_, i) => <option key={i}>{i}</option>)}</select></label>
      <label>Accidental <select aria-label="Insertion accidental" value={explicitAccidental} onChange={(e) => { setExplicitAccidental(e.target.value); if (e.target.value) setPitch({ ...pitch, alter: e.target.value }) }}><option value="">Follow key context</option><option value="-1">Flat</option><option value="0">Natural</option><option value="1">Sharp</option></select></label>
    </>}
    <DurationPicker value={duration} divisions={measure.divisions} disabled={busy} onChange={setDuration} />
    <label>Display size <select aria-label="Insertion display size" value={display} onChange={(e) => setDisplay(e.target.value)}><option value="normal">Normal</option><option value="small">Small</option></select></label>
    <label>Timing <select aria-label="Insertion timing" value={grace ? 'grace' : 'duration-bearing'} disabled={kind === 'rest'} onChange={(e) => setGrace(e.target.value === 'grace')}><option value="duration-bearing">Duration-bearing</option><option value="grace">Grace</option></select></label>
    <p>Existing notes keep their positions. A matching position and rhythm in the same voice adds a chord member; choose a secondary voice for independent timing. Placement stays in this measure even if it exceeds the displayed meter.</p>
    <button disabled={!validPosition || !validVoice || !duration || (kind === 'note' && !effectivePitch)} onClick={() => void change('events', 'POST', {
      measure_id: measure.id, staff, onset, voice: selectedVoice, kind, duration, display_size: display, grace,
      ...(kind === 'note' ? { pitch: effectivePitch, written_accidental: explicitAccidental ? { '-1': 'flat', '0': 'natural', '1': 'sharp' }[explicitAccidental] : null } : {}),
    })}>Apply note at position</button>
  </fieldset>
}
