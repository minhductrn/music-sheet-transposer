import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import vm from 'node:vm'
import ts from 'typescript'

function load(path, dependencies = {}) {
  const module = { exports: {} }
  const source = ts.transpileModule(readFileSync(new URL(path, import.meta.url), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
  }).outputText
  vm.runInNewContext(source, {
    module, exports: module.exports, console, Error, Set, Map,
    require(name) { return dependencies[name] ?? { __esModule: true, default: name } },
  })
  return module.exports
}
const helpers = load('../src/utils/visualReview.ts')
function harness(path, props, dependencies = {}, exportName = 'default') {
  const states = []; let slot = 0
  const jsx = (type, props, key) => ({ type, props, key })
  const hooks = {
    useState(initial) {
      const index = slot++
      if (!(index in states)) states[index] = initial
      return [states[index], (value) => { states[index] = value }]
    },
    useRef(initial) {
      const index = slot++
      if (!(index in states)) states[index] = { current: initial }
      return states[index]
    },
  }
  const component = load(path, {
    react: hooks, 'react/jsx-runtime': { jsx, jsxs: jsx }, '../utils/visualReview': helpers,
    '../utils/review': { eventLabel: (e) => e.id, validDuration: () => true }, ...dependencies,
  })
  return { render(next = props) { props = next; slot = 0; return component[exportName](props) }, component, hooks, jsx }
}
function find(tree, predicate) {
  if (!tree || typeof tree !== 'object') return null
  if (predicate(tree)) return tree
  const children = tree.props?.children
  for (const child of Array.isArray(children) ? children.flat(Infinity) : [children]) {
    const found = find(child, predicate)
    if (found) return found
  }
  return null
}
const button = (tree, label) => find(tree, (e) => e.type === 'button' && e.props.children === label)
const field = (tree, name) => find(tree, (e) => e.props?.['aria-label'] === name)
const plain = (value) => JSON.parse(JSON.stringify(value))
const event = { id: 'note', kind: 'note', pitch: { step: 'A', alter: '0', octave: 4 }, onset: '0', duration: '2', divisions: '4', voice: '2', staff: 1, grace: false, ties: [], lyric_ids: [], tie_target_ids: ['target'], tie_target_id: null }
const measure = { id: 'measure', index: 0, number: '5', divisions: '4', staves: 1, key_signature: [], voices: [{ id: '2', events: [event] }] }
const score = { metadata: { title: '', credits: [] }, parts: [{ id: 'part', name: 'Singer', measures: [measure] }], lyrics: [], harmonies: [] }
const review = { id: 'review', revision: 1, state: 'VERIFIED', musicXml: {}, score, expires_at: 9999999999, can_undo: true, can_redo: true, review_issues: [], validation: { can_verify: true, unresolved_issue_count: 0, error_count: 0, warning_count: 0, diagnostics: [] } }
function editor(overrides = {}) {
  const requests = []
  const props = { event, measure, lyrics: [], busy: false, change: async (...args) => requests.push(args), startTie() {}, advanced() {}, ...overrides }
  return { ...harness('../src/components/VisualNoteEditor.tsx', props), requests, props }
}
function recognition(initial = review, fail = false) {
  let current = initial; let response = initial
  const requests = []; const downloads = []
  const view = harness('../src/components/RecognitionReview.tsx', {}, { '../services/api': {
    changeReview: async (r, ...args) => { requests.push({ revision: r.revision, args }); if (fail) throw new Error('Review session was not found or has expired. Import the source again.'); return response },
  } })
  // Legacy selection regressions begin by explicitly clicking their source event.
  const first = initial.score.parts.flatMap((p) => p.measures.flatMap((m) => m.voices.flatMap((v) => v.events)))[0]
  if (first) find(view.render({ review: current, onChange() {}, onBusy() {}, download() {} }), (e) => e.type === './MusicSheetViewer').props.onSelect(first.id)
  return { requests, downloads, setResponse(value) { response = value }, render() {
    return view.render({ review: current, onChange: (value) => { current = value }, onBusy() {}, download: (...args) => downloads.push(args) })
  } }
}

test('Visual Review defaults to simple controls with Advanced inspector hidden', () => {
  const view = recognition(); let tree = view.render()
  assert.equal(button(tree, 'Visual Review').props['aria-pressed'], true)
  assert.ok(find(tree, (e) => e.type === './ScoreCorrectionToolbar'))
  assert.equal(find(tree, (e) => e.type === './VisualNoteEditor'), null)
  assert.ok(find(tree, (e) => e.type === 'div' && e.props.hidden === true && find(e, (n) => n.type === './EventInspector')))
  button(tree, 'Advanced Review').props.onClick(); tree = view.render()
  assert.equal(button(tree, 'Advanced Review').props['aria-pressed'], true)
  assert.ok(find(tree, (e) => e.type === './VisualNoteEditor'))
})
for (const [label, step] of [['↑ One staff step up', 'B'], ['↓ One staff step down', 'G']]) {
  test(`visual ${label} submits semantic pitch through existing endpoint`, () => {
    const view = editor(); button(view.render(), label).props.onClick()
    assert.deepEqual(plain(view.requests[0]), ['events/note', 'PATCH', { pitch: { step, octave: 4, alter: '0' } }])
  })
}
test('staff steps handle octave boundaries, key signature and unsupported keys safely', () => {
  assert.deepEqual(plain(helpers.movePitch({ step: 'B', octave: 4, alter: '0' }, 1, measure, 1)), { step: 'C', octave: 5, alter: '0' })
  assert.equal(helpers.movePitch({ step: 'C', octave: 0, alter: '0' }, -1, measure, 1), null)
  assert.equal(helpers.movePitch({ step: 'B', octave: 9, alter: '0' }, 1, measure, 1), null)
  const keyed = { ...measure, key_signature: [{ staff: null, fifths: '1' }] }
  assert.equal(helpers.movePitch({ step: 'E', octave: 4, alter: '0' }, 1, keyed, 1).alter, '1')
  assert.equal(helpers.movePitch(event.pitch, 1, { ...keyed, key_signature: [{ staff: null, fifths: null }] }, 1), null)
})
test('duration picker filters unrepresentable choices and submits existing duration patch', () => {
  assert.equal(helpers.durationChoices('1').some(([value]) => value === '1/2'), false)
  const view = editor(); button(view.render(), 'Duration').props.onClick()
  find(view.render(), (e) => typeof e.type === 'function' && e.type.name === 'DurationPicker').props.onChange('1/2')
  assert.deepEqual(plain(view.requests[0]), ['events/note', 'PATCH', { duration: '1/2', duration_scope: 'note', preserve_onsets: true }])
})
for (const [position, anchor] of [['before', 'before_event_id'], ['after', 'after_event_id'], ['simultaneous', 'same_onset_id']]) {
  test(`visual ${position} insertion retains semantic measure and inherits voice/staff`, () => {
    const view = editor(); button(view.render(), 'Add note').props.onClick()
    field(view.render(), 'Placement').props.onChange({ target: { value: position } })
    button(view.render(), 'Apply new note').props.onClick()
    const body = view.requests[0][2]
    assert.equal(body[anchor], 'note'); assert.equal(body.measure_id, 'measure'); assert.equal(body.grace, false)
    assert.equal(body.voice, undefined); assert.equal(body.staff, undefined); assert.equal(body.onset, undefined)
  })
}
test('direct selection synchronizes visual/advanced editing and deletion clears selection', async () => {
  const second = { ...event, id: 'second', onset: '2', duration: '1/2' }
  const current = { ...review, score: { ...score, parts: [{ ...score.parts[0], measures: [{ ...measure, voices: [{ id: '2', events: [event, second] }] }] }] } }
  const view = recognition(current)
  find(view.render(), (e) => e.type === './MusicSheetViewer').props.onSelect('second')
  let tree = view.render()
  assert.equal(find(tree, (e) => e.type === './ScoreCorrectionToolbar').props.event.id, 'second')
  assert.equal(find(tree, (e) => e.type === './EventInspector').props.event.id, 'second')
  view.setResponse(review)
  await find(tree, (e) => e.type === './ScoreCorrectionToolbar').props.change('events/second', 'DELETE')
  tree = view.render()
  assert.equal(find(tree, (e) => e.type === './MusicSheetViewer').props.selection, null)
  assert.equal(find(tree, (e) => e.type === './VisualNoteEditor'), null)
})
test('adjacent additions remain separate and the second new note becomes a tie target', async () => {
  const view = recognition()
  const first = { ...event, id: 'new-1' }; const second = { ...event, id: 'new-2', onset: '2', duration: '1/2' }
  const updated = (revision, events) => ({ ...review, revision, state: 'REVIEW_REQUIRED', score: { ...score, parts: [{ ...score.parts[0], measures: [{ ...measure, voices: [{ id: '2', events }] }] }] } })
  view.setResponse(updated(2, [event, first]))
  await find(view.render(), (e) => e.type === './ScoreCorrectionToolbar').props.change('events', 'POST', {})
  assert.equal(find(view.render(), (e) => e.type === './ScoreCorrectionToolbar').props.event.id, 'new-1')
  view.setResponse(updated(3, [event, { ...first, tie_target_ids: ['new-2'] }, second]))
  await find(view.render(), (e) => e.type === './ScoreCorrectionToolbar').props.change('events', 'POST', {})
  assert.equal(find(view.render(), (e) => e.type === './ScoreCorrectionToolbar').props.event.id, 'new-2')
  find(view.render(), (e) => e.type === './MusicSheetViewer').props.onSelect('new-1')
  find(view.render(), (e) => e.type === './ScoreCorrectionToolbar').props.tie()
  const tree = view.render()
  assert.deepEqual(plain(find(tree, (e) => e.type === './MusicSheetViewer').props.tieTargetIds), ['note', 'new-2'])
  find(tree, (e) => e.type === './MusicSheetViewer').props.onSelect('missing'); assert.equal(view.requests.length, 2)
  find(tree, (e) => e.type === './MusicSheetViewer').props.onSelect('new-2'); await new Promise(setImmediate)
  assert.equal(view.requests[2].revision, 3)
  assert.deepEqual(plain(view.requests[2].args), ['events/new-1', 'PATCH', { tie_to_event_id: 'new-2' }])
})
test('visual tie removal uses explicit null', () => {
  const view = editor({ event: { ...event, tie_target_id: 'target' } }); button(view.render(), 'Remove tie').props.onClick()
  assert.deepEqual(plain(view.requests[0]), ['events/note', 'PATCH', { tie_to_event_id: null }])
})
test('Delete submits the existing deletion endpoint', () => {
  const view = editor(); button(view.render(), 'Delete note').props.onClick()
  assert.deepEqual(plain(view.requests[0]), ['events/note', 'DELETE'])
})
for (const direction of ['Undo', 'Redo']) {
  test(`${direction} rerenders authoritative score and invalidates visible verification`, async () => {
    const view = recognition(); const changed = { ...review, revision: 2, state: 'REVIEW_REQUIRED', musicXml: {} }
    view.setResponse(changed); button(view.render(), direction).props.onClick(); await new Promise(setImmediate)
    const tree = view.render()
    assert.equal(find(tree, (e) => e.type === './MusicSheetViewer').props.musicXml, changed.musicXml)
    assert.match(find(tree, (e) => e.type === './ScoreCorrectionToolbar').key, /^tools-2-note-/)
    assert.equal(button(tree, 'Export saved MusicXML').props.disabled, true)
  })
}
test('expired session retains browser XML download and disables visual corrections', async () => {
  const view = recognition(review, true); button(view.render(), 'Undo').props.onClick(); await new Promise(setImmediate)
  const tree = view.render()
  assert.ok(find(tree, (e) => e.props?.role === 'alert' && String(e.props.children).includes('expired')))
  assert.equal(find(tree, (e) => e.type === './ScoreCorrectionToolbar').props.disabled, true)
  button(tree, 'Download recovery copy').props.onClick(); assert.equal(view.downloads[0][0], review.musicXml)
})
test('technical malformed pitch keeps verification blocked and technical details accessible', () => {
  const invalid = { ...review, state: 'REVIEW_REQUIRED', validation: { ...review.validation, can_verify: false, error_count: 1, diagnostics: [{ code: 'invalid_pitch', category: 'TECHNICAL_ERROR', severity: 'ERROR', blocking: true, message: 'Malformed pitch.' }] } }
  const tree = recognition(invalid).render()
  assert.ok(find(tree, (e) => e.type === 'li' && String(e.props.children).includes('Malformed pitch.')))
  assert.ok(find(tree, (e) => e.type === 'summary' && e.props.children === 'Technical score details'))
  assert.ok(button(tree, 'Save'))
})
test('semantic mapping refuses duplicate, wrong-measure and wrong-pitch identities', () => {
  const identity = { partIndex: 0, measureIndex: 0, voice: '2', staff: 1, onset: 0, duration: 2, kind: 'note', step: 'A', octave: 4, alter: 0, grace: false }
  assert.equal(helpers.mappedEvent(score, identity).id, 'note')
  assert.equal(helpers.mappedEvent(score, { ...identity, step: 'C' }), null)
  assert.equal(helpers.mappedEvent(score, { ...identity, measureIndex: 1 }), null)
  const duplicate = { ...score, parts: [{ measures: [{ ...measure, voices: [{ events: [event, { ...event, id: 'duplicate' }] }] }] }] }
  assert.equal(helpers.mappedEvent(duplicate, identity), null)
})
test('SVG binding selects semantic chord head after Fit scaling, highlights targets, supports keyboard and cleans up', () => {
  const nodes = Array.from({ length: 2 }, () => ({ dataset: {}, attributes: {}, listeners: {}, classes: new Set(),
    setAttribute(key, value) { this.attributes[key] = value }, removeAttribute(key) { delete this.attributes[key]; if (key === 'data-review-event') delete this.dataset.reviewEvent }, addEventListener(key, fn) { this.listeners[key] = fn }, removeEventListener(key) { delete this.listeners[key] },
    get classList() { return { toggle: (name, enabled) => enabled ? this.classes.add(name) : this.classes.delete(name) } },
  }))
  const instrument = { Staves: [] }; const staff = { ParentInstrument: instrument }; instrument.Staves.push(staff)
  const sourceMeasure = {}
  const note = (step) => ({ ParentStaff: staff, SourceMeasure: sourceMeasure, ParentVoiceEntry: { ParentVoice: { VoiceId: 2 }, Timestamp: { RealValue: 0 } }, Length: { RealValue: .5 }, IsGraceNote: false, Pitch: { FundamentalNote: step, Octave: 1, AccidentalHalfTones: 0 }, isRest: () => false })
  const osmd = { Sheet: { Instruments: [instrument], SourceMeasures: [sourceMeasure] }, GraphicSheet: { MeasureList: [[{ parentSourceMeasure: sourceMeasure, staffEntries: [{ graphicalVoiceEntries: [{ notes: [
    { sourceNote: note('A'), vfnote: [{}, 0], getNoteheadSVGs: () => nodes }, { sourceNote: note('C'), vfnote: [{}, 1], getNoteheadSVGs: () => nodes },
  ] }] }] }]] } }
  const chord = { ...event, id: 'chord', pitch: { step: 'C', octave: 4, alter: '0' } }
  const mappedScore = { ...score, parts: [{ measures: [{ ...measure, voices: [{ events: [event, chord] }] }] }] }
  const selected = []
  const adapter = load('../src/utils/scoreInteraction.ts', { './scoreTies': { drawCorrectionTies: () => () => {} }, './visualReview': helpers, opensheetmusicdisplay: { Pitch: { getNoteEnumString: (s) => s, OctaveXmlDifference: 3 } } })
  const binding = adapter.bindScore(osmd, mappedScore, (id) => selected.push(id))
  for (const scale of [.25, .5, 1, 2]) {
    nodes.forEach((node) => { node.style = { transform: `scale(${scale})` } })
    nodes[1].listeners.click({ clientX: 100 * scale, clientY: 50 * scale })
    assert.equal(selected.at(-1), 'chord')
  }
  selected.length = 0
  // DOM click target identity survives CSS transforms; no screen-coordinate pitch inference.
  for (const scale of [.25, .5, 2]) {
    nodes[1].setAttribute('transform', `scale(${scale})`)
    nodes[1].listeners.click(); assert.equal(selected.at(-1), 'chord')
  }
  selected.splice(0)
  nodes[1].listeners.click(); assert.deepEqual(selected, ['chord'])
  nodes[0].listeners.keydown({ key: 'Enter', preventDefault() {} }); assert.deepEqual(selected, ['chord', 'note'])
  binding.highlight('note', ['chord'])
  assert.ok(nodes[0].classes.has('score-note-selected')); assert.ok(nodes[1].classes.has('score-tie-target'))
  assert.equal(nodes[1].attributes.tabindex, '0'); binding.dispose(); assert.equal(nodes[1].listeners.click, undefined); assert.equal(nodes[1].attributes.tabindex, undefined); assert.equal(nodes[1].classes.size, 0)
  osmd.GraphicSheet.MeasureList[0][0].parentSourceMeasure = {}
  adapter.bindScore(osmd, mappedScore, (id) => selected.push(id))
  assert.equal(nodes[0].listeners.click, undefined) // A rendered continuation in another measure is not an insertion anchor.
})

for (const operation of ['add', 'edit', 'remove']) {
  test(`visual lyric ${operation} preserves Unicode and targets only the selected verse`, () => {
    const requests = []
    const lyrics = operation === 'add' ? [] : [{ id: 'verse1', number: '1', segments: ['khế“ịp', 'đây'] }, { id: 'verse2', number: '2', segments: ['khác'] }]
    const view = harness('../src/components/VisualNoteEditor.tsx', { event, lyrics, busy: false, change: async (...args) => requests.push(args) }, {}, 'LyricEditor')
    if (operation === 'remove') button(view.render(), 'Delete lyric').props.onClick()
    else { field(view.render(), 'Lyric text').props.onChange({ target: { value: 'khắp' } }); button(view.render(), 'Apply lyric').props.onClick() }
    const args = plain(requests[0])
    assert.equal(args[0], operation === 'add' ? 'events/note/lyrics' : 'lyrics/verse1')
    assert.equal(args[1], operation === 'add' ? 'POST' : operation === 'edit' ? 'PATCH' : 'DELETE')
    if (operation !== 'remove') assert.equal(args[2].text, 'khắp')
    if (operation === 'edit') assert.equal(args[2].segment_index, 0)
  })
}
test('lyric verse/segment selection never overwrites another verse', () => {
  const requests = []
  const lyrics = [{ id: 'verse1', number: '1', segments: ['one', 'two'] }, { id: 'verse2', number: '2', segments: ['khác'] }]
  const view = harness('../src/components/VisualNoteEditor.tsx', { event, lyrics, busy: false, change: async (...args) => requests.push(args) }, {}, 'LyricEditor')
  field(view.render(), 'Lyric verse').props.onChange({ target: { value: 'verse2' } })
  assert.equal(field(view.render(), 'Lyric text').props.value, 'khác')
  field(view.render(), 'Lyric text').props.onChange({ target: { value: 'đây' } })
  button(view.render(), 'Apply lyric').props.onClick()
  assert.deepEqual(plain(requests[0]), ['lyrics/verse2', 'PATCH', { text: 'đây', segment_index: 0 }])
})

test('backend-restricted duration choices and per-event key context reach visual controls', () => {
  assert.deepEqual(plain(helpers.durationChoices('4', ['1', '2']).map(([v]) => v)), ['1', '2'])
  const view = editor({ event: { ...event, pitch: { step: 'E', octave: 4, alter: '0' }, key_signature: [{ staff: null, fifths: '1' }], duration_options: ['1', '2'] } })
  button(view.render(), '↑ One staff step up').props.onClick()
  assert.equal(view.requests[0][2].pitch.alter, '1')
  button(view.render(), 'Duration').props.onClick()
  assert.deepEqual(plain(find(view.render(), (e) => typeof e.type === 'function' && e.type.name === 'DurationPicker').props.supported), ['1', '2'])
})

test('OSMD refresh discards late loads, rebuilds bindings and refreshes highlight on resize', async () => {
  const states = []; const effects = []; let slot = 0; const scheduled = []
  const instances = []; const highlights = []; let resize
  const jsx = (type, props) => ({ type, props })
  class Renderer {
    constructor() {
      instances.push(this); this.renders = 0
      this.cursor = { hide() {}, show() {}, reset() {}, next() {}, iterator: { EndReached: false, CurrentMeasureIndex: 0, CurrentRelativeInMeasureTimestamp: { RealValue: 0 } } }
    }
    load() { return new Promise((resolve) => { this.finish = resolve }) }
    render() { this.renders++ }
    updateGraphic() {}
  }
  const module = { exports: {} }
  vm.runInNewContext(ts.transpileModule(readFileSync(new URL('../src/components/MusicSheetViewer.tsx', import.meta.url), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
  }).outputText, {
    module, exports: module.exports, console,
    DOMParser: class { parseFromString(xml) { return { xml } } },
    ResizeObserver: class { constructor(fn) { resize = fn } observe() {} disconnect() {} },
    require(name) {
      if (name === 'react/jsx-runtime') return { jsx, jsxs: jsx }
      if (name === 'opensheetmusicdisplay') return { OpenSheetMusicDisplay: Renderer }
      if (name === '../utils/sourceEngraving') return { initialEngravingWidth: 1000, trustedSourceGroups: () => null }
      if (name === '../utils/scoreRenderer') return { rendererOptions: () => ({}), reviewDocument: (doc) => doc, bindRenderer: () => ({ highlight: (...args) => highlights.push(args), dispose() {} }) }
      if (name === 'react') return {
        useRef(initial) { const i = slot++; states[i] ??= { current: initial }; return states[i] },
        useState(initial) { const i = slot++; if (!(i in states)) states[i] = initial; return [states[i], (value) => { states[i] = value }] },
        useEffect(fn, deps) {
          const i = slot++; const old = effects[i]
          if (!old || deps.some((dep, j) => dep !== old.deps[j])) scheduled.push(() => { old?.cleanup?.(); effects[i] = { deps, cleanup: fn() } })
        },
      }
      return {}
    },
  })
  const container = { innerHTML: '', clientWidth: 600, style: {} }
  function render(blob, id = 'note', targets = null) {
    slot = 0
    const tree = module.exports.default({ musicXml: blob, score, selection: { eventId: id, measureIndex: 0, onset: '0', label: 'note' }, onSelect() {}, tieTargetIds: targets })
    find(tree, (e) => e.props?.ref).props.ref.current = container
    scheduled.splice(0).forEach((fn) => fn())
  }
  const first = { text: async () => 'old' }; const second = { text: async () => 'corrected' }
  render(first); await new Promise(setImmediate)
  render(second); await new Promise(setImmediate)
  instances[0].finish(); await new Promise(setImmediate)
  assert.equal(instances[0].renders, 0)
  instances[1].finish(); await new Promise(setImmediate)
  assert.equal(instances[1].renders, 1)
  render(second, 'target', ['note'])
  assert.deepEqual(plain(highlights.at(-1)), ['target', ['note']])
  resize([{ contentRect: { width: 700 } }])
  assert.equal(instances[1].renders, 2)
  assert.deepEqual(plain(highlights.at(-1)), ['target', ['note']])
})

test('changing review mode cancels stale tie-target interaction without changing selection', () => {
  const withTarget = { ...review, score: { ...score, parts: [{ ...score.parts[0], measures: [{ ...measure, voices: [{ id: '2', events: [event, { ...event, id: 'target' }] }] }] }] } }
  const view = recognition(withTarget)
  find(view.render(), (e) => e.type === './ScoreCorrectionToolbar').props.tie()
  assert.deepEqual(plain(find(view.render(), (e) => e.type === './MusicSheetViewer').props.tieTargetIds), ['target'])
  button(view.render(), 'Advanced Review').props.onClick()
  assert.equal(find(view.render(), (e) => e.type === './MusicSheetViewer').props.tieTargetIds, null)
  assert.equal(find(view.render(), (e) => e.type === './EventInspector').props.event.id, 'note')
})

test('normal position workflow is available in an empty measure', () => {
  const empty = { ...measure, voices: [] }
  const view = recognition({ ...review, score: { ...score, parts: [{ ...score.parts[0], measures: [empty] }] } })
  find(view.render(), (e) => e.type === './ScoreCorrectionToolbar').props.add()
  const tree = view.render()
  const pane = find(tree, (e) => e.type === './MusicSheetViewer')
  assert.equal(pane.props.insertionMode, true)
  assert.equal(find(tree, (e) => e.type === './MusicalPositionEditor'), null)
  pane.props.onPositionSelect({ measureId: empty.id, staff: 1, onset: '0' })
  assert.deepEqual(plain(find(view.render(), (e) => e.type === './ScoreCorrectionToolbar').props.position), { measureId: empty.id, staff: 1, onset: '0' })
})

test('position command sends C5 Half Small duration-bearing without IDs in user fields', () => {
  const calls = []
  const view = harness('../src/components/MusicalPositionEditor.tsx', { measure, staff: 1, voices: ['1','2'], busy: false, change: async (...args) => calls.push(args) })
  assert.equal(button(view.render(), 'Apply note at position').props.disabled, true)
  for (const [label, value] of [['Musical position','0'],['Insertion voice','2'],['Insertion pitch','C'],['Insertion octave','5'],['Insertion display size','small']]) field(view.render(), label).props.onChange({ target: { value } })
  find(view.render(), (e) => e.props?.onChange && e.props?.divisions === '4').props.onChange('2')
  assert.equal(field(view.render(), 'Insertion timing').props.value, 'duration-bearing')
  button(view.render(), 'Apply note at position').props.onClick()
  assert.deepEqual(plain(calls[0]), ['events','POST',{ measure_id:'measure',staff:1,onset:'0',voice:'2',kind:'note',duration:'2',display_size:'small',grace:false,pitch:{step:'C',octave:5,alter:'0'},written_accidental:null }])
})

test('small property is independent and measure ownership is an explicit command', () => {
  const view = editor({ event: { ...event, display_size: 'normal' }, measures: [{id:'measure',label:'Measure 5',staves:1},{id:'next',label:'Measure 6',staves:2}] })
  field(view.render(), 'Display size').props.onChange({ target: { value: 'small' } })
  assert.deepEqual(plain(view.requests[0]), ['events/note','PATCH',{display_size:'small'}])
  for (const [label,value] of [['Destination measure','next'],['Destination voice','3'],['Destination staff','2']]) field(view.render(),label).props.onChange({target:{value}})
  button(view.render(),'Apply explicit ownership').props.onClick()
  assert.deepEqual(plain(view.requests[1]), ['events/note/ownership','POST',{measure_id:'next',onset:'0',voice:'3',staff:2}])
})

test('right pane switches read-only Transposed and keeps original source visible', () => {
  const transposed = {derived:true}
  const view = harness('../src/components/RecognitionReview.tsx', {review,transposed,onChange(){},onBusy(){},download(){}})
  assert.equal(find(view.render(),e=>e.type==='./MusicSheetViewer').props.musicXml,review.musicXml)
  button(view.render(),'Transposed').props.onClick()
  let tree=view.render(); const pane=find(tree,e=>e.type==='./MusicSheetViewer')
  assert.equal(pane.props.musicXml,transposed); assert.equal(pane.props.interactive,false)
  assert.equal(pane.props.onSelect,undefined); assert.equal(pane.props.selection,null)
  assert.equal(pane.props.score,score)
  assert.ok(find(tree,e=>e.type==='./SourceViewer'))
  assert.equal(find(tree,e=>e.type==='./VisualNoteEditor'),null)
  button(tree,'Corrected').props.onClick(); tree=view.render()
  assert.equal(find(tree,e=>e.type==='./MusicSheetViewer').props.musicXml,review.musicXml)
  assert.equal(find(tree,e=>e.type==='./ScoreCorrectionToolbar').props.readOnly, false)
})

test('source comparison requires a handling note and submits a scoped decision', () => {
  const calls=[]
  const issue={id:'diagnostic',code:'measure_overfilled',message:'Overfill',can_confirm_source:true,source_confirmed:false}
  const view=harness('../src/components/RecognitionReview.tsx',{issue,busy:false,change:async(...args)=>calls.push(args)}, {}, 'SourceDiagnosticConfirmation')
  assert.equal(button(view.render(),'This unusual notation matches the source').props.disabled,true)
  field(view.render(),'Source confirmation note').props.onChange({target:{value:'Checked the printed long measure'}})
  button(view.render(),'This unusual notation matches the source').props.onClick()
  assert.deepEqual(plain(calls[0]),['diagnostics/confirm-source','POST',{diagnostic_id:'diagnostic',note:'Checked the printed long measure'}])
})

test('single verse lyric correction hides verse controls until adding another verse', () => {
  const calls=[]
  const view=harness('../src/components/VisualNoteEditor.tsx',{event,lyrics:[{id:'verse1',number:'1',segments:['Chúa']}],busy:false,change:async(...args)=>calls.push(args)},{},'LyricEditor')
  assert.equal(field(view.render(),'Lyric verse'),null)
  assert.equal(field(view.render(),'New verse'),null)
  assert.equal(field(view.render(),'Lyric text').props.value,'Chúa')
  button(view.render(),'Add another verse').props.onClick()
  assert.equal(field(view.render(),'New verse').props.value,'2')
  field(view.render(),'Lyric text').props.onChange({target:{value:'Người'}})
  button(view.render(),'Apply lyric').props.onClick()
  assert.deepEqual(plain(calls[0]),['events/note/lyrics','POST',{text:'Người',number:'2'}])
})

// Browser-independent binding checks use renderer metadata, not pitch/voice size guesses.
function stemBindingFixture(change = () => {}) {
  const matrix = (a = 1, d = a, e = 0, f = 0, b = 0, c = 0) => ({ a, b, c, d, e, f,
    inverse() { return matrix(1 / a, 1 / d, -e / a, -f / d) },
    multiply(m) { return matrix(a * m.a, d * m.d, a * m.e + e, d * m.f + f, b, c) },
  })
  const svg = { querySelectorAll: () => [stemGroup] }
  const style = { display: 'inline', visibility: 'visible', opacity: '1', stroke: '#000', strokeWidth: '1.5', strokeOpacity: '1', vectorEffect: 'none', strokeDasharray: 'none', fill: '#000', fillOpacity: '1' }
  const view = { getComputedStyle: (n) => ({ ...style, ...n.css }) }
  const node = (tagName, parentElement = svg) => ({ tagName, parentElement, ownerSVGElement: svg, ownerDocument: { defaultView: view }, dataset: {}, attributes: {}, listeners: {}, classes: new Set(), css: {},
    setAttribute(k, v) { this.attributes[k] = v }, getAttribute(k) { return this.attributes[k] ?? null },
    removeAttribute(k) { delete this.attributes[k] }, addEventListener(k, f) { this.listeners[k] = f }, removeEventListener(k) { delete this.listeners[k] },
    getScreenCTM: () => matrix(), closest: () => svg,
    get classList() { return { toggle: (n, enabled) => enabled ? this.classes.add(n) : this.classes.delete(n) } },
  })
  Object.assign(svg, node('svg', null), { querySelectorAll: () => [stemGroup] })
  const stemGroup = node('g'); stemGroup.id = 'vf-rendered-stem'
  const stem = node('path', stemGroup); stem.attributes.d = 'M20 45L20 5'
  stemGroup.querySelectorAll = () => [stem]
  const heads = [node('g'), node('g')]
  heads.forEach((h, i) => {
    h.getBBox = () => ({ x: 8.75, y: 40 - i * 10, width: 12, height: 10 })
    const path = node('path', h); path.css.stroke = 'none'; h.querySelectorAll = () => [path]
  })
  const instrument = { Staves: [] }; const staff = { ParentInstrument: instrument }; instrument.Staves.push(staff)
  const sourceMeasure = {}, staffEntry = { Link: undefined }
  const sourceVoice = { ParentVoice: { VoiceId: 2 }, Timestamp: { RealValue: 0 }, Notes: [] }
  const note = (step) => ({ ParentStaff: staff, ParentStaffEntry: staffEntry, SourceMeasure: sourceMeasure, ParentVoiceEntry: sourceVoice,
    Length: { RealValue: .5 }, IsGraceNote: false, IsCueNote: false, PrintObject: true, NoteSlurs: [], NoteTie: undefined,
    Pitch: { FundamentalNote: step, Octave: 1, AccidentalHalfTones: 0 }, isRest: () => false, sharesNoteheadWithVisibleUnisonNote: () => false })
  const sourceNotes = [note('A'), note('C')]; sourceVoice.Notes = sourceNotes
  const vfNote = { getStemDirection: () => 1, isDisplaced: () => false, getKeyProps: () => [{ line: 1 }, { line: 2 }],
    note_heads: heads.map(() => ({ glyph_code: 'vb', custom_glyph: false, isDisplaced: () => false })),
  }
  const m = { parentSourceMeasure: sourceMeasure, ParentStaff: staff, staffEntries: [] }
  const parentVoiceEntry = { parentStaffEntry: { parentMeasure: m, graphicalLink: undefined }, notes: [] }
  const graphical = sourceNotes.map((sourceNote, i) => ({ sourceNote, parentVoiceEntry, vfnote: [vfNote, i], getNoteheadSVGs: () => heads,
    getStemSVG: () => stem, getSVGId: () => 'rendered', getTieSVGs: () => [], getSlurSVGs: () => [] }))
  parentVoiceEntry.notes = graphical
  m.staffEntries = [{ graphicalVoiceEntries: [{ notes: graphical }] }]
  const lower = { ...event, ties: [], tie_target_ids: [], tie_relationship: null, display_size: 'normal' }
  const upper = { ...lower, id: 'upper', pitch: { step: 'C', octave: 4, alter: '0' }, display_size: 'small' }
  const mappedScore = { ...score, parts: [{ measures: [{ ...measure, voices: [{ events: [lower, upper] }] }] }] }
  const osmd = { Sheet: { Instruments: [instrument], SourceMeasures: [sourceMeasure] }, GraphicSheet: { MeasureList: [[m]] } }
  const fixture = { heads, stem, stemGroup, svg, upper, lower, sourceNotes, vfNote, graphical, mappedScore, matrix, m }
  change(fixture)
  const adapter = load('../src/utils/scoreInteraction.ts', { './scoreTies': { drawCorrectionTies: () => () => {} }, './visualReview': helpers,
    opensheetmusicdisplay: { Pitch: { getNoteEnumString: (s) => s, OctaveXmlDifference: 3 } } })
  fixture.selected = []
  fixture.bind = () => adapter.bindScore(osmd, mappedScore, (id) => fixture.selected.push(id))
  return fixture
}

test('supported filled up-stem small head uses stem X and its own vertical center; partner, stem and identity stay unchanged', () => {
  const f = stemBindingFixture(); const original = JSON.stringify(f.mappedScore), stemPath = f.stem.getAttribute('d')
  const b = f.bind()
  assert.equal(f.heads[1].getAttribute('transform'), ' translate(20 35) scale(.65) translate(-20 -35)')
  assert.equal(f.heads[0].getAttribute('transform'), null); assert.equal(f.stem.getAttribute('d'), stemPath); assert.equal(f.stem.getAttribute('transform'), null)
  f.heads[1].listeners.click(); f.heads[0].listeners.click(); assert.deepEqual(f.selected, ['upper', 'note'])
  assert.equal(JSON.stringify(f.mappedScore), original); b.dispose()
})

test('stem pivot converts into original head coordinates and cleanup prevents cumulative rebinding', () => {
  const f = stemBindingFixture(({ heads, stem, matrix }) => {
    heads[1].attributes.transform = 'translate(2 0)'
    heads[1].getBBox = () => ({ x: 6.75, y: 30, width: 12, height: 10 })
    heads[1].getScreenCTM = () => matrix(2, 2, 4, 0)
    stem.getScreenCTM = () => matrix(2)
  })
  for (let i = 0; i < 3; i++) {
    const b = f.bind()
    assert.equal(f.heads[1].getAttribute('transform'), 'translate(2 0) translate(18 35) scale(.65) translate(-18 -35)')
    b.dispose(); assert.equal(f.heads[1].getAttribute('transform'), 'translate(2 0)'); assert.equal(f.heads[1].listeners.click, undefined)
  }
})

for (const [name, change] of [
  ['missing stem', f => { f.graphical[1].getStemSVG = () => null }],
  ['ambiguous stem', f => { f.svg.querySelectorAll = () => [f.stemGroup, f.stemGroup] }],
  ['down-stem', f => { f.vfNote.getStemDirection = () => -1 }],
  ['displaced head', f => { f.vfNote.note_heads[1].isDisplaced = () => true }],
  ['displaced chord', f => { f.vfNote.isDisplaced = () => true }],
  ['open head', f => { f.vfNote.note_heads[1].glyph_code = 'v53' }],
  ['custom head', f => { f.vfNote.note_heads[1].custom_glyph = true }],
  ['canonical sound tie', f => { f.upper.ties = ['start'] }],
  ['source tie', f => { f.sourceNotes[1].NoteTie = {} }],
  ['canonical outgoing tie', f => { f.upper.tie_target_id = 'note' }],
  ['canonical incoming tie', f => { f.lower.tie_target_id = 'upper' }],
  ['explicit outgoing pair', f => { f.upper.tie_relationship = { source_event_id: 'upper', target_event_id: 'note', origin: 'USER_CORRECTION' } }],
  ['explicit incoming pair', f => { f.lower.tie_relationship = { source_event_id: 'note', target_event_id: 'upper', origin: 'USER_CORRECTION' } }],
  ['imported stop', f => { f.upper.ties = ['stop'] }],
  ['missing canonical relationship evidence', f => { delete f.upper.ties; delete f.upper.tie_target_id; delete f.upper.tie_relationship }],
  ['missing parsed tie evidence', f => { delete f.sourceNotes[1].NoteTie }],
  ['missing parsed slur evidence', f => { delete f.sourceNotes[1].NoteSlurs }],
  ['malformed relationship scalar', f => { f.upper.tie_relationship = false }],
  ['ambiguous explicit pair', f => { f.lower.tie_relationship = { source_event_id: 'note' } }],
  ['dangling actual target', f => { f.lower.tie_target_id = 'missing-event' }],
  ['ambiguous source endpoint', f => { f.upper.tie_correction_error = 'Distinct endpoint markings' }],
  ['source slur', f => { f.sourceNotes[1].NoteSlurs = [{}] }],
  ['rendered slur', f => { f.graphical[1].getSlurSVGs = () => [{}] }],
  ['cross-staff', f => { f.m.ParentStaff = {} }],
  ['linked staff', f => { f.sourceNotes[1].ParentStaffEntry.Link = {} }],
  ['ambiguous unison', f => { f.vfNote.getKeyProps = () => [{ line: 1 }, { line: 1 }] }],
  ['hidden stem', f => { f.stemGroup.css.display = 'none' }],
  ['zero stroke', f => { f.stem.css.strokeWidth = '0' }],
  ['non-scaling stroke', f => { f.stem.css.vectorEffect = 'non-scaling-stroke' }],
  ['skew', f => { f.stem.getScreenCTM = () => f.matrix(1, 1, 0, 0, .1) }],
  ['singular transform', f => { f.stem.getScreenCTM = () => f.matrix(0) }],
  ['transparent stem', f => { f.stem.css.stroke = 'rgba(0, 0, 0, 0)' }],
  ['unfilled SVG head', f => { f.heads[1].querySelectorAll()[0].css.fill = 'none' }],
  ['rotated transform', f => { f.stem.getScreenCTM = () => f.matrix(0, 0, 0, 0, 1, -1) }],
  ['nonuniform scale', f => { f.stem.getScreenCTM = () => f.matrix(1, 2) }],
  ['nonfinite dimensions', f => { f.heads[1].getBBox = () => ({ x: NaN, y: 30, width: 12, height: 10 }) }],
  ['semantic cue', f => { f.upper.cue = true }],
  ['grace', f => { f.upper.grace = true; f.sourceNotes[1].IsGraceNote = true }],
  ['curved stem', f => { f.stem.attributes.d = 'M20 45Q20 25 20 5' }],
]) test(`small head keeps center-scaling fallback for ${name}`, () => {
  const f = stemBindingFixture(change), b = f.bind()
  assert.equal(f.heads[1].getAttribute('transform'), ['nonfinite dimensions', 'semantic cue', 'grace'].includes(name) ? null : ' translate(14.75 35) scale(.65) translate(-14.75 -35)')
  b.dispose(); assert.equal(f.heads[1].getAttribute('transform'), null)
})


test('minimal untied binding input may omit ties without disabling supported stem anchoring', () => {
  const f = stemBindingFixture(({ upper, lower }) => { delete upper.ties; delete lower.ties })
  const b = f.bind()
  assert.equal(f.heads[1].getAttribute('transform'), ' translate(20 35) scale(.65) translate(-20 -35)')
  b.dispose()
})


test('nonempty tie picker candidates do not exclude either untied endpoint', () => {
  const f = stemBindingFixture(({ upper, lower }) => {
    upper.tie_target_ids = ['note']; lower.tie_target_ids = ['upper']
  })
  const b = f.bind()
  assert.equal(f.heads[1].getAttribute('transform'), ' translate(20 35) scale(.65) translate(-20 -35)')
  assert.equal(f.heads[0].getAttribute('transform'), null)
  b.dispose()
})

function lyricChord() {
  const normal = { id: 'e-2', kind: 'note', pitch: { step: 'A', octave: 4, alter: '0' },
    display_size: 'normal', staff: 1, voice: '1', onset: '1/2', duration: '1/2',
    chord_id: 'e-2', chord_member: false, grace: false, cue: false, lyric_ids: ['l-1'] }
  const small = { ...normal, id: 'e-3', pitch: { step: 'C', octave: 5, alter: '0' }, display_size: 'small', chord_member: true, lyric_ids: [] }
  const measure = { id: 'm-1', staves: 1, voices: [{ id: '1', events: [normal, small] }] }
  const score = { parts: [{ id: 'p-1', measures: [measure] }], lyrics: [{ id: 'l-1', event_id: normal.id, number: '1', segments: ['ta'], text: 'ta' }] }
  return { normal, small, measure, score }
}

test('mixed-size lyrical chord resolves the normal owner without changing score or selection', () => {
  const f = lyricChord(), before = JSON.stringify(f.score)
  assert.equal(helpers.auxiliaryLyricOwner(f.score, f.small), f.normal)
  assert.equal(helpers.auxiliaryLyricOwner(f.score, f.normal), null)
  // A disjoint recognition voice at the preceding beat does not compete here.
  f.measure.voices.push({ id: '2', events: [{ ...f.normal, id: 'opening', voice: '2', onset: '0', chord_id: null }] })
  assert.equal(helpers.auxiliaryLyricOwner(f.score, f.small), f.normal)
  f.measure.voices.pop()
  assert.equal(JSON.stringify(f.score), before)
})

for (const [name, change] of [
  ['small note already owns a canonical lyric', f => f.score.lyrics.push({ id: 'authored', event_id: f.small.id, number: '1', text: 'Việt', segments: ['Việt'] })],
  ['small note has an unresolved lyric reference', f => f.small.lyric_ids.push('retained')],
  ['size alone without chord membership', f => { f.small.chord_member = false }],
  ['coincident independent voice', f => { f.small.voice = '2' }],
  ['independent concurrent vocal voice', f => f.measure.voices.push({ id: '2', events: [{ ...f.normal, id: 'singer', voice: '2', chord_id: null }] })],
  ['overlapping separate entry in the same voice', f => f.measure.voices[0].events.push({ ...f.normal, id: 'other', chord_id: null })],
  ['two possible normal chord owners', f => f.measure.voices[0].events.push({ ...f.normal, id: 'other' })],
  ['unknown onset', f => { f.small.onset = null }],
  ['different durations', f => { f.normal.duration = '1' }],
  ['no authoritative normal lyric', f => { f.score.lyrics = [] }],
  ['cross-staff chord', f => { f.normal.staff = 2 }],
  ['multiple staves', f => { f.measure.staves = 2 }],
  ['independent parts', f => f.score.parts.push({ id: 'p-2', measures: [] })],
  ['explicit cue', f => { f.small.cue = true }],
  ['grace', f => { f.small.grace = true }],
  ['structurally ambiguous measure', f => { f.measure.rhythm_status = 'STRUCTURALLY_AMBIGUOUS' }],
]) test(`auxiliary lyric guard leaves ${name} editable and unchanged`, () => {
  const f = lyricChord(); change(f); const before = JSON.stringify(f.score)
  assert.equal(helpers.auxiliaryLyricOwner(f.score, f.small), null)
  assert.equal(JSON.stringify(f.score), before)
})

test('auxiliary notice replaces Add lyric and selects owner only on explicit action', () => {
  const f = lyricChord(), calls = [], selected = []
  const view = harness('../src/components/VisualNoteEditor.tsx', {
    event: f.small, lyrics: [], busy: false, lyricOwner: f.normal,
    selectLyricOwner: () => selected.push(f.normal.id), change: async (...args) => calls.push(args),
  }, {}, 'LyricEditor')
  const element = view.render(), tree = element.type(element.props)
  assert.equal(button(tree, 'Apply lyric'), null)
  assert.equal(find(tree, e => e.type === 'input'), null)
  assert.deepEqual(selected, [])
  button(tree, 'Select normal-note lyric owner').props.onClick()
  assert.deepEqual(selected, ['e-2'])
  assert.deepEqual(calls, [])
})

test('existing small-note lyric remains editable even if a stale guard was supplied', () => {
  const f = lyricChord(), calls = []
  const view = harness('../src/components/VisualNoteEditor.tsx', {
    event: f.small, lyrics: [{ id: 'authored', number: '1', segments: ['Tiếng Việt'] }],
    busy: false, lyricOwner: f.normal, selectLyricOwner: () => assert.fail('silent redirection'),
    change: async (...args) => calls.push(args),
  }, {}, 'LyricEditor')
  button(view.render(), 'Apply lyric').props.onClick()
  assert.deepEqual(JSON.parse(JSON.stringify(calls)), [['lyrics/authored', 'PATCH', { text: 'Tiếng Việt', segment_index: 0 }]])
})


test('recognition ambiguity has no issue workflow or redundant verification controls', () => {
  const pending = { ...review, state: 'REVIEW_REQUIRED', semantic_recovery: { review_required: 1 } }
  const view = harness('../src/components/RecognitionReview.tsx', { review: pending, onChange() {}, onBusy() {}, download() {} })
  const tree = view.render()
  assert.equal(find(tree, e => e.type === 'summary' && String(e.props.children).includes('Review issues')), null)
  assert.equal(button(tree, 'Mark VERIFIED'), null)
  assert.equal(find(tree, e => e.type === 'input' && e.props.type === 'checkbox'), null)
  assert.equal(button(tree, 'Save').props.disabled, false)
  assert.ok(button(tree, 'Save As'))
})
