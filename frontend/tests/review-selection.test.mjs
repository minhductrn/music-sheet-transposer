// Focused component regression using built-in Node tools and the existing TS compiler.
// This checks selection state; DOM engraving remains a manual browser acceptance item.
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import vm from 'node:vm'
import ts from 'typescript'

function componentHarness(initialReview) {
  const states = []
  let slot = 0
  let review = initialReview
  let response
  const requests = []
  const jsx = (type, props, key) => ({ type, props, key })
  const api = {
    changeReview: async (current, path, method, body) => {
      requests.push({ revision: current.revision, path, method, body })
      return response
    },
  }
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
  const module = { exports: {} }
  const source = ts.transpileModule(readFileSync(new URL('../src/components/RecognitionReview.tsx', import.meta.url), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
  }).outputText
  vm.runInNewContext(source, {
    module, exports: module.exports,
    require(name) {
      if (name === 'react') return hooks
      if (name === 'react/jsx-runtime') return { jsx, jsxs: jsx }
      if (name === '../services/api') return api
      if (name === '../utils/review') return { eventLabel: (e) => e.id, validDuration: () => true }
      return { __esModule: true, default: name }
    },
  })
  return {
    requests,
    setResponse(value) { response = value },
    render() {
      slot = 0
      return module.exports.default({ review, onChange: (value) => { review = value }, onBusy() {}, download() {} })
    },
  }
}

function element(tree, predicate) {
  if (!tree || typeof tree !== 'object') return null
  if (predicate(tree)) return tree
  const children = tree.props?.children
  for (const child of Array.isArray(children) ? children.flat(Infinity) : [children]) {
    const found = element(child, predicate)
    if (found) return found
  }
  return null
}

function review(revision, restored = false) {
  const event = (id, voice) => ({ id, voice, onset: '0', duration: '1', pitch: null, ties: [], kind: 'rest', provenance: { origin: 'musicxml_import', manual_fields: [], evidence_ids: [] } })
  return {
    id: 'review', revision, state: 'REVIEW_REQUIRED', expires_at: 9999999999,
    can_undo: true, can_redo: true, review_issues: [],
    validation: { unresolved_issue_count: 0, error_count: 0, warning_count: 0, diagnostics: [] },
    score: { metadata: { credits: [] }, lyrics: [], harmonies: [], parts: [{ id: 'p-1', measures: [
      { id: 'm-1', index: 0, number: '1', voices: [{ id: '1', events: [event('e-1', '1')] }] },
      { id: 'm-2', index: 1, number: '2', voices: [{ id: '2', events: restored ? [event('e-2', '2')] : [] }] },
    ] }] },
  }
}

for (const direction of ['undo', 'redo']) {
  test(`${direction} selects a restored event together with its measure and voice`, async () => {
    const harness = componentHarness(review(3))
    const tree = harness.render()
    harness.setResponse(review(4, true))
    const button = element(tree, (e) => e.type === 'button' && e.props.children === (direction === 'undo' ? 'Undo' : 'Redo'))
    button.props.onClick()
    await new Promise(setImmediate)
    const refreshed = harness.render()
    const inspector = element(refreshed, (e) => e.type === './EventInspector')
    assert.equal(inspector.props.event.id, 'e-2')
    assert.equal(inspector.props.measure.id, 'm-2')
    assert.equal(inspector.props.event.voice, '2')
    assert.equal(harness.requests[0].revision, 3)
    const nextButton = element(refreshed, (e) => e.type === 'button' && e.props.children === 'Undo')
    harness.setResponse(review(5, true))
    nextButton.props.onClick()
    await new Promise(setImmediate)
    assert.equal(harness.requests[1].revision, 4)
  })
}

test('ordinary correction retains the selected event and its measure', async () => {
  const harness = componentHarness(review(1, true))
  const tree = harness.render()
  const inspector = element(tree, (e) => e.type === './EventInspector')
  const updated = review(2, true)
  updated.score.parts[0].measures[0].voices[0].events[0].display_size = 'small'
  harness.setResponse(updated)
  await inspector.props.change('events/e-1', 'PATCH', { display_size: 'small' })
  const selected = element(harness.render(), (e) => e.type === './EventInspector')
  assert.equal(selected.props.event.id, 'e-1')
  assert.equal(selected.props.measure.id, 'm-1')
  assert.equal(selected.props.event.display_size, 'small')
})

function tiedReview(revision, tied) {
  const result = review(revision)
  const measure = result.score.parts[0].measures[0]
  measure.voices[0].events[0] = { ...measure.voices[0].events[0], kind: 'note', pitch: { step: 'A', alter: '0', octave: 4 }, ties: tied ? ['start'] : [], tie_target_id: tied ? 'target' : null, tie_target_ids: ['target'] }
  measure.voices[0].events.push({ ...measure.voices[0].events[0], id: 'target', onset: '2', duration: '1/2', ties: tied ? ['stop'] : [], tie_target_id: null, tie_target_ids: [] })
  return result
}

for (const direction of ['undo', 'redo']) {
  test(`${direction} refreshes inspector tie state and remount key`, async () => {
    const harness = componentHarness(tiedReview(2, direction === 'undo'))
    const before = harness.render()
    const first = element(before, (e) => e.type === './EventInspector')
    harness.setResponse(tiedReview(3, direction === 'redo'))
    element(before, (e) => e.type === 'button' && e.props.children === (direction === 'undo' ? 'Undo' : 'Redo')).props.onClick()
    await new Promise(setImmediate)
    const next = element(harness.render(), (e) => e.type === './EventInspector')
    assert.equal(next.props.event.tie_target_id, direction === 'redo' ? 'target' : null)
    assert.ok(next.props.tieTargets.some((t) => t.id === 'target'))
    assert.notEqual(next.key, first.key)
    assert.equal(next.props.event.id, 'e-1')
  })
}
