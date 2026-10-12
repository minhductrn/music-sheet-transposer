import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import vm from 'node:vm'
import ts from 'typescript'
import test from 'node:test'
function load(path, dependencies = {}, globals = {}) {
  const module = { exports: {} }
  const source = ts.transpileModule(readFileSync(new URL(path, import.meta.url), 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX } }).outputText
  vm.runInNewContext(source, { module, exports: module.exports, console, Error, Map, Set, document: doc, ...globals, require: n => dependencies[n] ?? {} })
  return module.exports
}
const doc = { addEventListener() {}, removeEventListener() {} }
const visual = load('../src/utils/visualReview.ts')
const helpers = load('../src/utils/lyricInteraction.ts', { './visualReview': visual, opensheetmusicdisplay: { Pitch: { getNoteEnumString: () => 'A', OctaveXmlDifference: 3 } } })
const lyric = { id: 'l-2', event_id: 'e-4', number: '1', text: 'cũng', segments: ['cũng'] }
const event = { id: 'e-4', kind: 'note', staff: 1, voice: '1', onset: '0', duration: '1', grace: false, pitch: { step: 'A', octave: 4, alter: '0' } }
const score = { lyrics: [lyric], parts: [{ measures: [{ index: 0, voices: [{ events: [event] }] }] }] }
const plain = x => JSON.parse(JSON.stringify(x))
test('canonical ownership requires all source notes and exactly one owner; ignores text', () => {
  assert.deepEqual(plain(helpers.lyricOwner(score, ['e-4', 'aux'], '1')), [lyric])
  assert.equal(helpers.lyricOwner(score, ['e-4', null], '1').length, 0)
  assert.equal(helpers.lyricOwner(score, ['e-4'], '2').length, 0)
  assert.equal(helpers.lyricOwner({ ...score, lyrics: [lyric, { ...lyric, id: 'other', event_id: 'aux' }] }, ['e-4', 'aux'], '1').length, 2)
})
test('revision, review and canonical IDs must all agree', () => {
  const binding = { reviewId: 'r', revision: 2, lyricId: 'l-2', eventId: 'e-4', originalVerse: '1', valid: () => true }
  const scope = { reviewId: 'r', revision: 2, score }
  assert.equal(helpers.currentLyric(binding, scope), lyric)
  for (const change of [{ revision: 3 }, { reviewId: 'new' }]) assert.equal(helpers.currentLyric(binding, { ...scope, ...change }), null)
  for (const change of [{ eventId: 'aux' }, { originalVerse: '2' }, { valid: () => false }]) assert.equal(helpers.currentLyric({ ...binding, ...change }, scope), null)
  assert.equal(helpers.currentLyric(binding, { ...scope, score: { ...score, lyrics: [lyric, lyric] } }), null)
})
function fixture(extra = false) {
  const listeners = {}, opens = [], box = { left: 0, top: 0, right: 30, bottom: 20 }
  const node = { style: { userSelect: '' }, isConnected: true, getBoundingClientRect: () => box }
  const other = { ...node, style: { userSelect: '' } }
  const root = { contains: () => true, querySelector: () => null, addEventListener(n, fn) { (listeners[n] ??= []).push(fn) }, removeEventListener() {} }
  const staff = { ParentInstrument: { Staves: [] } }; staff.ParentInstrument.Staves = [staff]
  const sourceMeasure = {}, note = { ParentStaff: staff, Pitch: { FundamentalNote: 9, Octave: 1, AccidentalHalfTones: 0 }, Length: { RealValue: .25 }, IsGraceNote: false, isRest: () => false, SourceMeasure: sourceMeasure }
  note.ParentVoiceEntry = { ParentVoice: { VoiceId: 1 }, Timestamp: { RealValue: 0 }, Notes: [note] }
  const g = n => ({ LyricsEntry: { VerseNumber: '1', Parent: note.ParentVoiceEntry }, GraphicalLabel: { SVGNode: n } })
  const osmd = { Sheet: { Instruments: [staff.ParentInstrument], SourceMeasures: [sourceMeasure] }, GraphicSheet: { MeasureList: [[{ parentSourceMeasure: sourceMeasure, ParentStaff: staff, staffEntries: [{ graphicalVoiceEntries: [{ notes: [{ sourceNote: note }] }], LyricsEntries: extra ? [g(node), g(other)] : [g(node)] }] }]] } }
  let enabled = true, scope = { reviewId: 'r', revision: 1, score }
  const bound = helpers.bindLyrics(osmd, root, scope, 9, () => scope, () => enabled, x => opens.push(x))
  function dispatch(type, target = node) { let stopped = false, prevented = false; const e = { type, target, pointerId: 1, composedPath: () => [target, root], stopPropagation() { stopped = true }, preventDefault() { prevented = true } }; for (const f of listeners[type] ?? []) f(e); return { stopped, prevented } }
  return { bound, dispatch, opens, node, setEnabled: v => enabled = v, setScope: v => scope = v }
}
test('initial clicks are isolated, double-click opens exact owner without selection', () => {
  const f = fixture(); assert.deepEqual(f.dispatch('click'), { stopped: true, prevented: true }); assert.equal(f.opens.length, 0)
  f.dispatch('dblclick'); assert.equal(f.opens[0].lyricId, 'l-2'); assert.equal(f.opens[0].eventId, 'e-4'); assert.equal(f.opens[0].renderGeneration, 9)
  assert.equal(f.node.style.userSelect, 'none'); f.bound.dispose(); assert.equal(f.node.style.userSelect, ''); assert.equal(f.opens[0].valid(), false)
})
test('blocked modes, stale and detached nodes refuse activation', () => {
  const f = fixture(); f.setEnabled(false); f.dispatch('dblclick'); assert.equal(f.opens.length, 0)
  f.setEnabled(true); f.setScope({ reviewId: 'r', revision: 2, score }); f.dispatch('dblclick'); assert.equal(f.opens.length, 0)
  const d = fixture(); d.node.isConnected = false; d.dispatch('dblclick'); assert.equal(d.opens.length, 0)
})
test('overlap presents explicit owners, never a direct editor', () => {
  const f = fixture(true); f.dispatch('dblclick'); assert.match(f.opens[0].reason, /overlap/); assert.equal(f.opens[0].owners.length, 1)
})
test('active note pointer blocks lyric activation', () => {
  const f = fixture(); f.dispatch('pointerdown', { closest: () => true }); f.dispatch('dblclick'); assert.equal(f.opens.length, 0)
})
function editorHarness(overrides = {}) {
  const states = []; let slot = 0
  const hooks = { useState(initial) { const i = slot++; if (!(i in states)) states[i] = initial; return [states[i], v => { states[i] = v }] },
    useRef(initial) { const i = slot++; if (!(i in states)) states[i] = { current: initial }; return states[i] }, useEffect() {} }
  const jsx = (type, props) => ({ type, props })
  const C = load('../src/components/DirectLyricEditor.tsx', { react: hooks, 'react/jsx-runtime': { jsx, jsxs: jsx }, 'react-dom': { createPortal: child => child } }).default
  const saves = [], selected = []; let closed = 0
  const props = { binding: { valid: () => true, reason: null, originalVerse: '1', owners: [lyric] }, lyric, events: [event], enabled: true,
    apply: async text => { saves.push(text) }, selectOwner: id => selected.push(id), close: () => { closed++ }, ...overrides }
  function render() { slot = 0; return C(props) }
  return { render, props, saves, selected, closed: () => closed }
}
function find(tree, predicate) {
  if (!tree || typeof tree !== 'object') return null
  if (predicate(tree)) return tree
  const c = tree.props?.children
  for (const child of Array.isArray(c) ? c.flat(Infinity) : [c]) { const found = find(child, predicate); if (found) return found }
  return null
}
const inputOf = t => find(t, n => n.type === 'input')
const applyOf = t => find(t, n => n.type === 'button' && n.props.children === 'Apply lyric directly')
const tick = () => new Promise(resolve => setImmediate(resolve))
test('IME Enter is ignored, post-composition Enter applies exact decomposed Unicode once', async () => {
  const h = editorHarness(); let t = h.render(), input = inputOf(t)
  input.props.onCompositionStart(); input.props.onChange({ target: { value: 'cùng Việt' } }); t = h.render()
  const e = { key: 'Enter', target: null, nativeEvent: { isComposing: true }, stopPropagation() {}, preventDefault() {} }
  t.props.onKeyDown(e); assert.equal(h.saves.length, 0)
  inputOf(t).props.onCompositionEnd(); t = h.render()
  t.props.onKeyDown({ ...e, nativeEvent: { isComposing: false } }); await tick()
  assert.deepEqual(h.saves, ['cùng Việt']); assert.equal(h.closed(), 1)
})
test('Escape cancels, Tab does not commit, explicit Apply works', async () => {
  const h = editorHarness(); const t = h.render()
  const key = key => ({ key, nativeEvent: {}, stopPropagation() {}, preventDefault() {} })
  t.props.onKeyDown(key('Tab')); assert.equal(h.saves.length, 0); assert.equal(h.closed(), 0)
  t.props.onKeyDown(key('Escape')); assert.equal(h.closed(), 1)
  const a = editorHarness(); applyOf(a.render()).props.onClick(); await tick(); assert.deepEqual(a.saves, ['cũng'])
})
test('PATCH failure retains draft, reports error and does not close or claim success', async () => {
  const h = editorHarness({ apply: async () => { throw Error('Revision conflict') } }); let t = h.render()
  inputOf(t).props.onChange({ target: { value: 'Việt mới' } }); t = h.render(); applyOf(t).props.onClick(); await tick(); t = h.render()
  assert.equal(inputOf(t).props.value, 'Việt mới'); assert.equal(h.closed(), 0)
  assert.match(find(t, n => n.props?.role === 'alert').props.children, /Revision conflict.*Draft retained/)
})
test('stale or disabled editor sends no patch; overlap only offers explicit selection', async () => {
  for (const overrides of [{ enabled: false }, { binding: { valid: () => false } }]) {
    const h = editorHarness(overrides); applyOf(h.render()).props.onClick(); await tick(); assert.equal(h.saves.length, 0)
  }
  const h = editorHarness({ binding: { valid: () => true, reason: 'overlap', owners: [lyric] } }); const t = h.render()
  assert.equal(inputOf(t), null); assert.equal(applyOf(t), null); assert.equal(h.selected.length, 0)
  find(t, n => n.type === 'button' && Array.isArray(n.props.children)).props.onClick(); assert.deepEqual(h.selected, ['l-2'])
})

test('stale detached overlays retain their anchor and clamp after warning growth and resize', () => {
  const states = []; let slot = 0, effect, valid = true, height = 160
  const callbacks = {}, observers = []
  const panel = { getBoundingClientRect: () => ({ width: 340, height }), querySelector: () => null }
  const node = { isConnected: true, closest: () => null, getBoundingClientRect: () => ({ left: 900, bottom: 650 }) }
  const globals = { innerWidth: 1000, innerHeight: 800,
    window: { addEventListener: (name, fn) => { callbacks[name] = fn }, removeEventListener() {} },
    ResizeObserver: class { constructor(fn) { observers.push(fn) } observe() {} disconnect() {} },
    MutationObserver: class { observe() {} disconnect() {} } }
  const hooks = {
    useState(initial) { const i = slot++; if (!(i in states)) states[i] = initial; return [states[i], v => { states[i] = v }] },
    useRef(initial) { const i = slot++; if (!(i in states)) states[i] = { current: initial }; return states[i] },
    useEffect(fn) { effect = fn }
  }
  const jsx = (type, props) => ({ type, props })
  const C = load('../src/components/DirectLyricEditor.tsx', { react: hooks, 'react/jsx-runtime': { jsx, jsxs: jsx }, 'react-dom': { createPortal: x => x } }, globals).default
  const props = { binding: { node, valid: () => valid, owners: [] }, lyric, events: [], enabled: true }
  const render = () => { slot = 0; return C(props) }
  let tree = render(); tree.props.ref.current = panel; effect(); tree = render()
  assert.equal(tree.props.style.left, 652); assert.equal(tree.props.style.top, 632)
  valid = false; node.isConnected = false; height = 300; observers[0](); tree = render()
  assert.equal(tree.props.style.top, 492); assert.equal(applyOf(tree).props.disabled, true)
  assert.equal(inputOf(tree).props.value, 'cũng')
  // Resize while detached must still reposition; the retained anchor cannot keep Cancel offscreen.
  height = 400; callbacks.resize(); tree = render()
  assert.equal(tree.props.style.top, 392)
  assert.equal(tree.props.style.maxHeight, 'calc(100dvh - 16px)')
  const cancel = find(tree, n => n.type === 'button' && n.props.children === 'Cancel lyric editing')
  assert.equal(cancel.props.disabled, false)
  assert.equal(tree.props.children[1].props.style.flexShrink, 0)
})
