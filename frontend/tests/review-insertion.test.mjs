// Focused component regression using built-in Node tools and the existing TS compiler.
// This checks insertion controls; DOM engraving remains a manual browser acceptance item.
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import vm from 'node:vm'
import ts from 'typescript'

function componentHarness(props) {
  const states = []
  let slot = 0
  const requests = []
  const jsx = (type, props) => ({ type, props })
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
  const source = ts.transpileModule(readFileSync(new URL('../src/components/EventInspector.tsx', import.meta.url), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
  }).outputText
  vm.runInNewContext(source, {
    module, exports: module.exports,
    require(name) {
      if (name === 'react') return hooks
      if (name === 'react/jsx-runtime') return { jsx, jsxs: jsx }
      if (name === '../utils/review') return { eventLabel: (e) => e.id, validDuration: () => true }
      return { __esModule: true, default: name }
    },
  })
  return {
    requests,
    setProps(value) { props = value; states.length = 0 },
    render() {
      slot = 0
      return module.exports.default({ ...props, change: async (path, method, body) => { requests.push({ path, method, body }) } })
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


function text(node) {
  if (node == null || typeof node === 'boolean') return ''
  if (typeof node !== 'object') return String(node)
  const children = node.props?.children
  return (Array.isArray(children) ? children.flat(Infinity) : [children]).map(text).join('')
}

function inspector() {
  return componentHarness({
    event: { id: 'following', kind: 'note', ties: [], pitch: { step: 'A', alter: '0', octave: 4 }, duration: '1', voice: '2', staff: 2, display_size: 'normal', grace: false, provenance: { origin: 'musicxml_import', manual_fields: [] } },
    measure: { id: 'm-1', number: '1', staves: 2 }, busy: false,
    tieTargets: [{ id: 'following', label: 'Following A' }],
  })
}

function input(tree, label) {
  const parent = element(tree, (e) => e.type === 'label' && text(e).startsWith(label))
  return element(parent, (e) => e.type === 'input' || e.type === 'select')
}

test('missing note controls send duration-bearing insertion with explicit tie target', async () => {
  const harness = inspector()
  let tree = harness.render()
  input(tree, 'Duration (quarter beats)').props.onChange({ target: { value: '2' } })
  input(tree, 'Tie inserted note to').props.onChange({ target: { value: 'following' } })
  tree = harness.render()
  const button = element(tree, (e) => e.type === 'button' && e.props.children === 'Add before selected')
  assert.equal(button.props.disabled, false)
  button.props.onClick()
  await new Promise(setImmediate)
  const { path, method, body } = harness.requests[0]
  assert.equal(path, 'events'); assert.equal(method, 'POST')
  assert.equal(body.before_event_id, 'following')
  assert.equal(body.tie_to_event_id, 'following')
  assert.equal(body.pitch.step, 'A'); assert.equal(body.duration, '2')
  assert.equal(body.voice, '2'); assert.equal(body.staff, 2); assert.equal(body.grace, false)
})

for (const invalid of ['rest']) {
  test(`tied insertion is disabled for ${invalid}`, () => {
    const harness = inspector()
    let tree = harness.render()
    input(tree, 'Tie inserted note to').props.onChange({ target: { value: 'following' } })
    if (invalid === 'grace') input(tree, ' Grace timing').props.onChange({ target: { checked: true } })
    else input(tree, 'Add ').props.onChange({ target: { value: 'rest' } })
    tree = harness.render()
    for (const label of ['Add before selected', 'Add after selected', 'Add simultaneous note']) {
      assert.equal(element(tree, (e) => e.type === 'button' && e.props.children === label).props.disabled, true)
    }
  })
}

test('tie target is exclusive to insertion and is not sent in ordinary patch', async () => {
  const harness = inspector()
  let tree = harness.render()
  input(tree, 'Tie inserted note to').props.onChange({ target: { value: 'following' } })
  input(tree, 'Display size').props.onChange({ target: { value: 'small' } })
  tree = harness.render()
  element(tree, (e) => e.type === 'button' && e.props.children === 'Apply correction').props.onClick()
  await new Promise(setImmediate)
  assert.equal(harness.requests[0].method, 'PATCH')
  assert.deepEqual(JSON.parse(JSON.stringify(harness.requests[0].body)), { display_size: 'small' })
})

function existingInspector(target = null) {
  return {
    event: { id: 'source', kind: 'note', ties: target ? ['start'] : [], tie_target_id: target, tie_target_ids: ['following'], pitch: { step: 'A', alter: '0', octave: 4 }, duration: '2', voice: '1', staff: 1, display_size: 'normal', grace: false, provenance: { origin: 'musicxml_import', manual_fields: [] } },
    measure: { id: 'm-5', number: '5', staves: 1 }, busy: false,
    tieTargets: [{ id: 'following', label: 'Measure 5 · Voice 1 · A4 · onset 2 · duration 1/2' }, { id: 'wrong', label: 'Incompatible B4' }],
  }
}

test('existing-note tie selector offers matching targets without manual ID entry', async () => {
  const harness = componentHarness(existingInspector())
  let tree = harness.render()
  const select = input(tree, 'Tie to')
  assert.equal(select.type, 'select')
  assert.equal(select.props.value, '')
  assert.ok(element(select, (e) => e.type === 'option' && e.props.value === 'following'))
  assert.equal(element(select, (e) => e.type === 'option' && e.props.value === 'wrong'), null)
  select.props.onChange({ target: { value: 'following' } })
  tree = harness.render()
  const button = element(tree, (e) => e.type === 'button' && e.props.children === 'Apply correction')
  assert.equal(button.props.disabled, false)
  button.props.onClick()
  await new Promise(setImmediate)
  assert.equal(harness.requests[0].path, 'events/source')
  assert.equal(harness.requests[0].method, 'PATCH')
  assert.deepEqual(JSON.parse(JSON.stringify(harness.requests[0].body)), { tie_to_event_id: 'following' })
  // React remounts the inspector by revision, resetting its draft selection.
  harness.setProps(existingInspector('following'))
  assert.equal(input(harness.render(), 'Tie to').props.value, 'following')
})

test('existing tie displays its target and No tie sends explicit null removal', async () => {
  const harness = componentHarness(existingInspector('following'))
  let tree = harness.render()
  assert.equal(input(tree, 'Tie to').props.value, 'following')
  input(tree, 'Tie to').props.onChange({ target: { value: '' } })
  tree = harness.render()
  element(tree, (e) => e.type === 'button' && e.props.children === 'Apply correction').props.onClick()
  await new Promise(setImmediate)
  assert.deepEqual(JSON.parse(JSON.stringify(harness.requests[0].body)), { tie_to_event_id: null })
  harness.setProps(existingInspector())
  assert.equal(input(harness.render(), 'Tie to').props.value, '')
})

test('changing existing tie target sends only the new relationship', async () => {
  const props = existingInspector('following')
  props.event.tie_target_ids.push('alternative')
  props.tieTargets.push({ id: 'alternative', label: 'Matching chord peer' })
  const harness = componentHarness(props)
  let tree = harness.render()
  input(tree, 'Tie to').props.onChange({ target: { value: 'alternative' } })
  tree = harness.render()
  element(tree, (e) => e.type === 'button' && e.props.children === 'Apply correction').props.onClick()
  await new Promise(setImmediate)
  assert.deepEqual(JSON.parse(JSON.stringify(harness.requests[0].body)), { tie_to_event_id: 'alternative' })
})


test('a user-selected tie target does not prevent grace-note insertion', async () => {
  const harness = inspector()
  input(harness.render(), 'Tie inserted note to').props.onChange({ target: { value: 'following' } })
  input(harness.render(), ' Grace timing').props.onChange({ target: { checked: true } })
  const tree = harness.render()
  const add = element(tree, (e) => e.type === 'button' && e.props.children === 'Add before selected')
  assert.equal(add.props.disabled, false)
  await add.props.onClick()
  assert.equal(harness.requests[0].body.grace, true)
  assert.equal(harness.requests[0].body.tie_to_event_id, 'following')
})
