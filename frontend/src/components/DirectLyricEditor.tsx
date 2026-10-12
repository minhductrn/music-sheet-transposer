import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import type { LyricBinding } from '../utils/lyricInteraction'
import type { Lyric, ScoreEvent } from '../types/review'

interface Props {
  binding: LyricBinding
  lyric: Lyric | null
  events: ScoreEvent[]
  enabled: boolean
  apply: (text: string) => Promise<void>
  selectOwner: (id: string | null) => void
  close: () => void
}
export default function DirectLyricEditor({ binding, lyric, events, enabled, apply, selectOwner, close }: Props) {
  const [text, setText] = useState(lyric?.segments[0] ?? '')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [position, setPosition] = useState({ left: 0, top: 0 })
  const panel = useRef<HTMLDivElement>(null)
  const input = useRef<HTMLInputElement>(null)
  const composing = useRef(false)
  const pending = useRef(false)
  const stale = !binding.valid()
  useEffect(() => {
    // Geometry remains usable after revision changes and SVG replacement.
    let anchor = { left: 8, bottom: 8 }
    const reposition = () => {
      if (!binding.valid()) setError('The score view or revision changed. Copy your draft, cancel, then reopen the lyric.')
      if (binding.node.isConnected) anchor = binding.node.getBoundingClientRect()
      const b = anchor, p = panel.current?.getBoundingClientRect()
      setPosition({ left: Math.max(8, Math.min(innerWidth - (p?.width ?? 320) - 8, b.left)),
        top: Math.max(8, Math.min(innerHeight - (p?.height ?? 180) - 8, b.bottom + 6)) })
    }
    reposition(); (input.current ?? panel.current?.querySelector('button'))?.focus()
    const resize = new ResizeObserver(reposition)
    if (panel.current) resize.observe(panel.current)
    const pane = binding.node.closest('.review-score-scroll')
    if (pane) resize.observe(pane)
    const mutation = new MutationObserver(reposition)
    const surface = binding.node.closest('.review-score-surface')
    if (surface) mutation.observe(surface, { attributes: true, childList: true, subtree: true, attributeFilter: ['style', 'width', 'height'] })
    window.addEventListener('scroll', reposition, true); window.addEventListener('resize', reposition)
    return () => { resize.disconnect(); mutation.disconnect(); window.removeEventListener('scroll', reposition, true); window.removeEventListener('resize', reposition) }
  }, [binding])
  async function save() {
    if (pending.current || composing.current || !enabled || !binding.valid() || binding.reason) return
    pending.current = true; setSaving(true); setError('')
    try { await apply(text); close() }
    catch (cause) { setError(`${cause instanceof Error ? cause.message : 'Unable to apply lyric.'} Draft retained. Reload review if needed, then reopen the lyric.`) }
    finally { pending.current = false; setSaving(false) }
  }
  return createPortal(<div ref={panel} role="dialog" aria-label="Edit visible lyric" aria-describedby="direct-lyric-help"
    style={{ position: 'fixed', zIndex: 1000, ...position, width: 'min(340px, calc(100vw - 16px))', boxSizing: 'border-box', maxHeight: 'calc(100dvh - 16px)', display: 'flex', flexDirection: 'column', padding: 12, background: 'white', color: '#111', border: '2px solid #155e75', borderRadius: 6, boxShadow: '0 3px 12px #0004' }}
    onKeyDown={e => {
      e.stopPropagation()
      if (composing.current || e.nativeEvent.isComposing || e.keyCode === 229) return
      if (e.key === 'Escape' && !saving) { e.preventDefault(); close() }
      if (e.key === 'Enter' && e.target === input.current) { e.preventDefault(); void save() }
    }}>
    <div style={{ overflowY: 'auto', minHeight: 0 }}>
    <p id="direct-lyric-help">{binding.reason ?? `Edit verse ${binding.originalVerse}. Enter applies; Escape cancels.`}</p>
    {!binding.reason && <label>Lyric text<input ref={input} aria-label="Direct lyric text" value={text} disabled={saving} readOnly={stale || !enabled}
      onCompositionStart={() => { composing.current = true }} onCompositionEnd={() => { composing.current = false }}
      onChange={e => setText(e.target.value)} /></label>}
    {(error || stale) && <p role="alert">{error || 'This lyric binding is stale. Cancel and reopen it in the current score.'}</p>}
    </div>
    <div style={{ flexShrink: 0, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
    {!binding.reason && <button type="button" disabled={saving || !enabled || stale} onClick={() => void save()}>Apply lyric directly</button>}
    <button type="button" disabled={saving} onClick={close}>Cancel lyric editing</button>
    </div>
    <div style={{ overflowY: 'auto', minHeight: 0 }}>
    {binding.reason && <button type="button" disabled={!enabled} onClick={() => { selectOwner(null); close() }}>Open Advanced Review</button>}
    {binding.reason && binding.owners.map(owner => { const event = events.find(e => e.id === owner.event_id)
      return <button type="button" key={owner.id} disabled={!enabled || stale} onClick={() => { selectOwner(owner.id); close() }}>
        Select {owner.event_id}, voice {event?.voice ?? '?'}, staff {event?.staff ?? '?'}, verse {owner.number} in existing editor
      </button>
    })}
    </div>
  </div>, document.body)
}
