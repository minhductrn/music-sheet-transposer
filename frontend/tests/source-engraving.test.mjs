import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import vm from 'node:vm'
import ts from 'typescript'

const module = { exports: {} }
vm.runInNewContext(ts.transpileModule(readFileSync(new URL('../src/utils/sourceEngraving.ts', import.meta.url), 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS },
}).outputText, { module, exports: module.exports })
const { trustedSourceGroups, engraveSourceGroups, renderedSourceGroups, sourceEngravingWidth } = module.exports
const plain = (v) => JSON.parse(JSON.stringify(v))
function fixture(counts = [5, 5, 7]) {
  let index = 0
  const groups = counts.map((count) => Array.from({ length: count }, () => index++))
  const score = { validation: { error_count: 1, conflicts: ['overfill'] }, parts: [{ id: 'p', measures: Array.from({ length: index }, (_, i) => ({ id: `m${i + 1}`, index: i, validation_state: 'OVERFILLED', voices: [{ events: [{ pitch: 'A4', duration: '2', onset: '0', ties: ['start'], lyrics: ['Unicode đây'], staff: 1, voice: '1' }] }] })) }],
    layout: { mode: 'SOURCE_REVIEW', origin: 'MUSICXML_PRINT', systems: groups.map((g) => ({ part_id: 'p', measure_ids: g.map((i) => `m${i + 1}`), explicit_break_measure_id: `m${g[0] + 1}` })) } }
  return { groups, score }
}
// A controlled renderer boundary, not a claim of browser/OSMD acceptance.
// Its reported first graph reproduces the real observed extra split.
function renderer(groups, minimumWidth = 1800) {
  const source = Array.from({ length: groups.flat().length }, () => ({}))
  let width = 0; let renders = 0
  const osmd = { Sheet: { SourceMeasures: source }, GraphicSheet: { MusicPages: [] }, updateGraphic() {}, render() {
    renders++
    const actual = width >= minimumWidth ? groups : [groups[0].slice(0, -1), groups[0].slice(-1), ...groups.slice(1)]
    osmd.GraphicSheet.MusicPages = [{ MusicSystems: actual.map((g) => ({ StaffLines: [{ Measures: g.map((i) => ({ parentSourceMeasure: source[i] })) }] })) }]
  } }
  return { osmd, setWidth: (value) => { width = value }, get renders() { return renders } }
}

test('complete trusted variable groups are derived from ownership, not a fixed measure count', () => {
  for (const counts of [[5, 5, 7], [2, 8, 3], [1, 1, 1]]) {
    const { score, groups } = fixture(counts)
    assert.deepEqual(plain(trustedSourceGroups(score)), groups)
  }
})
test('absence, partial, duplicate, unknown and incompatible part ownership fail safely', () => {
  assert.equal(trustedSourceGroups(), null)
  for (const mutate of [
    (s) => { s.layout.mode = 'RESPONSIVE' },
    (s) => { s.layout.origin = 'UNKNOWN' },
    (s) => { s.layout.systems[0].measure_ids.pop() },
    (s) => { s.layout.systems[1].measure_ids[0] = 'm1' },
    (s) => { s.layout.systems[0].explicit_break_measure_id = 'm2' },
    (s) => { s.parts.push({ id: 'other', measures: s.parts[0].measures }) },
  ]) {
    const { score } = fixture(); mutate(score); assert.equal(trustedSourceGroups(score), null)
  }
})
test('extra split in groups 1–5 / 6–10 / 11–17 triggers measured widening, independent of narrow pane', () => {
  const { score, groups } = fixture(); const before = JSON.stringify(score)
  const engine = renderer(groups); const widths = []
  const result = engraveSourceGroups(engine.osmd, trustedSourceGroups(score), (width) => { widths.push(width); engine.setWidth(width) }, 960)
  assert.equal(result.matched, true)
  assert.deepEqual(widths, [960, 1920])
  assert.deepEqual(plain(renderedSourceGroups(engine.osmd)), groups)
  assert.equal(JSON.stringify(score), before) // Includes untouched conflicts, duration, onset and musical properties.
})
test('explicit variable breaks remain separate even on a generous surface', () => {
  const { groups } = fixture([3, 2, 6]); const engine = renderer(groups, 500)
  assert.equal(engraveSourceGroups(engine.osmd, groups, engine.setWidth, 960).matched, true)
  assert.deepEqual(plain(renderedSourceGroups(engine.osmd)), groups)
  assert.equal(engine.renders, 1)
})
test('unrepresentable renderer ownership is bounded and reported instead of silently accepted', () => {
  const { groups } = fixture(); const engine = renderer(groups, Infinity)
  const result = engraveSourceGroups(engine.osmd, groups, engine.setWidth, 960)
  assert.equal(result.matched, false)
  assert.equal(engine.renders, 6)
  assert.equal(result.width, 30720)
})
test('multi-staff graphical rows deduplicate source measures without using display numbering', () => {
  const { groups } = fixture(); const engine = renderer(groups, 500)
  engraveSourceGroups(engine.osmd, groups, engine.setWidth, 960)
  for (const s of engine.osmd.GraphicSheet.MusicPages[0].MusicSystems) s.StaffLines.push(s.StaffLines[0])
  assert.deepEqual(plain(renderedSourceGroups(engine.osmd)), groups)
})


test('engraving seed comes from variable source grouping and XML geometry without mutating XML', () => {
  const widths = [200, 350, 180, 420, 220]
  const document = { documentElement: { children: [{ localName: 'part', children: widths.map((width) =>
    ({ localName: 'measure', getAttribute: () => String(width) })) }] } }
  assert.equal(sourceEngravingWidth(document, [[0, 1], [2, 3, 4]]), 940)
  assert.equal(sourceEngravingWidth(document, [[0, 1, 2, 3, 4]]), 1490)
  assert.deepEqual(widths, [200, 350, 180, 420, 220])
})

test('engraving seed follows longest trusted XML group across parts without pane dimensions', () => {
  const { sourceEngravingWidth } = module.exports
  const measure = (width) => ({ localName: 'measure', getAttribute: () => width })
  const doc = { documentElement: { children: [{ localName: 'part', children: [200, 300, 400, 500].map(measure) }] } }
  const before = JSON.stringify(doc)
  assert.equal(sourceEngravingWidth(doc, [[0, 1], [2, 3]]), 1020)
  assert.equal(sourceEngravingWidth(doc, [[0, 1, 2], [3]]), 1020)
  assert.equal(sourceEngravingWidth(doc, [[0, 1, 2, 3]]), 1520)
  assert.equal(JSON.stringify(doc), before)
})
test('missing XML measure widths still get measured; huge seed renders within bounded capacity', () => {
  const { sourceEngravingWidth } = module.exports
  const { groups } = fixture([2, 3])
  const doc = { documentElement: { children: [{ localName: 'part', children: Array.from({ length: 5 }, () => ({ localName: 'measure', getAttribute: () => null })) }] } }
  const seed = sourceEngravingWidth(doc, groups)
  assert.equal(seed, 600)
  const engine = renderer(groups, 1100)
  assert.equal(engraveSourceGroups(engine.osmd, groups, engine.setWidth, seed).matched, true)
  const bounded = renderer(groups, Infinity)
  const result = engraveSourceGroups(bounded.osmd, groups, bounded.setWidth, 100000)
  assert.equal(bounded.renders, 1)
  assert.equal(result.width, 32760)
  assert.equal(result.matched, false)
})

for (const mode of ['visible', 'initially hidden', 'hidden during load', 'cancelled while hidden']) test(`viewer lifecycle: ${mode}; initializes once at positive width`, async () => {
  const { score, groups } = fixture()
  const before = JSON.stringify(score)
  const states = []; const effects = []; let slot = 0; let instance; let resizeObservers = 0; const observers = []; let finishLoad
  const container = { innerHTML: '', style: {}, clientWidth: mode === 'initially hidden' || mode === 'cancelled while hidden' ? 0 : 250, get offsetWidth() { return mode === 'initially hidden' ? this.clientWidth ? Number.parseFloat(this.style.width) || 0 : 0 : this.clientWidth }, closest() { const container = this; return mode === 'initially hidden' ? { querySelector: () => ({ get clientWidth() { return container.clientWidth } }) } : null } }
  const jsx = (type, props) => ({ type, props })
  const find = (tree, predicate) => {
    if (!tree || typeof tree !== 'object') return null
    if (predicate(tree)) return tree
    for (const child of [tree.props?.children, tree.props?.headerActions, tree.props?.toolbar, tree.props?.context, tree.props?.moreControls].flat(Infinity)) { const found = find(child, predicate); if (found) return found }
    return null
  }
  class Engine {
    constructor() {
      const simulated = renderer(groups)
      instance = this
      this.renders = 0
      this.Sheet = simulated.osmd.Sheet; this.GraphicSheet = simulated.osmd.GraphicSheet
      this.cursor = { hide() {} }
      this.updateGraphic = simulated.osmd.updateGraphic
      this.render = () => { this.renders++; simulated.setWidth(Number.parseFloat(container.style.width)); simulated.osmd.render() }
    }
    async load() { if (mode === 'hidden during load') { container.clientWidth = 0; await new Promise(resolve => { finishLoad = resolve }) } }
  }
  const bindingGroups = []
  const dependencies = {
    react: {
      useRef(initial) { const i = slot++; states[i] ??= { current: initial }; return states[i] },
      useState(initial) { const i = slot++; if (!(i in states)) states[i] = initial; return [states[i], (value) => { states[i] = value }] },
      useEffect(fn) { const i = slot++; if (!(i in states)) { states[i] = true; effects.push(fn) } },
    },
    'react/jsx-runtime': { jsx, jsxs: jsx },
    opensheetmusicdisplay: { OpenSheetMusicDisplay: Engine },
    '../utils/sourceEngraving': { ...module.exports, sourceEngravingWidth: () => 1000 },
    '../utils/scoreRenderer': { rendererOptions: () => ({}), reviewDocument: (doc) => doc,
      bindRenderer: (osmd) => { bindingGroups.push(plain(renderedSourceGroups(osmd))); return { highlight() {}, dispose() {} } } },
    './ReviewScoreViewport': { __esModule: true, default: 'Viewport' },
  }
  const component = { exports: {} }
  vm.runInNewContext(ts.transpileModule(readFileSync(new URL('../src/components/MusicSheetViewer.tsx', import.meta.url), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
  }).outputText, { module: component, exports: component.exports, require: (name) => dependencies[name], console,
    DOMParser: class { parseFromString(xml) { return { xml } } },
    ResizeObserver: class { constructor(fn) { resizeObservers++; this.notify = fn; observers.push(this) } observe() {} disconnect() { this.disconnected = true } },
  })
  const xml = Object.freeze({ text: async () => '<score-partwise>untouched</score-partwise>' })
  const props = { musicXml: xml, score, onSelect() {} }
  let tree = component.exports.default(props)
  find(tree, (e) => e.props?.ref).props.ref.current = container
  const cleanups = effects.map(fn => fn())
  await new Promise(setImmediate)
  if (mode === 'cancelled while hidden') {
    assert.equal(instance, undefined)
    cleanups.forEach(fn => fn?.())
    assert.equal(observers[0].disconnected, true)
    container.clientWidth = 250; observers[0].notify()
    await new Promise(setImmediate)
    assert.equal(instance, undefined)
    return
  }
  if (mode === 'hidden during load') { finishLoad(); await new Promise(setImmediate) }
  if (mode !== 'visible') {
    assert.deepEqual(bindingGroups, [])
    assert.equal(instance?.renders ?? 0, 0)
    if (mode === 'initially hidden') assert.equal(instance, undefined)
    observers[0].notify(); await new Promise(setImmediate)
    assert.deepEqual(bindingGroups, [])
    assert.equal(instance?.renders ?? 0, 0)
    container.clientWidth = 250
    observers[0].notify(); observers[0].notify()
    await new Promise(setImmediate)
    assert.equal(observers[0].disconnected, true)
  }
  assert.deepEqual(bindingGroups, [groups])
  assert.equal(resizeObservers, mode === 'visible' ? 0 : 1)
  assert.equal(container.style.width, '2000px')
  const initializedInstance = instance
  container.clientWidth = 0; observers[0]?.notify()
  container.clientWidth = 125; observers[0]?.notify()
  slot = 0; tree = component.exports.default(props)
  assert.equal(find(tree, (e) => e.type === 'Viewport').props.engravingWidth, 2000)
  assert.deepEqual(plain(renderedSourceGroups(instance)), groups)
  assert.equal(instance, initializedInstance)
  assert.equal(bindingGroups.length, 1)
  assert.equal(JSON.stringify(score), before)
  assert.equal(await xml.text(), '<score-partwise>untouched</score-partwise>')
})

test('saved XML preview reads compatible explicit systems without mutating XML', () => {
  const measure = (split = false) => ({ localName: 'measure', children: split ? [{ localName: 'print', getAttribute: name => name === 'new-system' ? 'yes' : null }] : [] })
  const part = () => ({ localName: 'part', children: [measure(), measure(), measure(true), measure()] })
  const doc = { documentElement: { children: [part(), part()] } }
  assert.deepEqual(plain(module.exports.xmlSourceGroups(doc)), [[0, 1], [2, 3]])
  assert.equal(doc.documentElement.children[0].children.length, 4)
  doc.documentElement.children[1].children[2] = measure()
  assert.equal(module.exports.xmlSourceGroups(doc), null)
})
