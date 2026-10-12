import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import vm from 'node:vm'
import ts from 'typescript'

function load(path, dependencies = {}, globals = {}) {
  const module = { exports: {} }
  vm.runInNewContext(ts.transpileModule(readFileSync(new URL(path, import.meta.url), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
  }).outputText, { module, exports: module.exports, require: (name) => dependencies[name] ?? { default: name, __esModule: true }, ...globals })
  return module.exports
}
const zoom = load('../src/utils/reviewZoom.ts')
function find(tree, predicate) {
  if (!tree || typeof tree !== 'object') return null
  if (predicate(tree)) return tree
  const children = tree.props?.children
  for (const child of Array.isArray(children) ? children.flat(Infinity) : [children]) {
    const result = find(child, predicate)
    if (result) return result
  }
  return null
}

test('fit uses a proportional scale; manual zoom and limits affect only presentation', () => {
  assert.equal(zoom.reviewScale(null, 500, 1000), .5)
  assert.equal(zoom.reviewScale(null, 500, 1200), 500 / 1200)
  assert.equal(zoom.reviewScale(null, 0, 0), 1)
  assert.equal(zoom.reviewScale(100, 500, 1000), 1)
  assert.equal(zoom.nextReviewZoom(.5, 1), 60)
  assert.equal(zoom.nextReviewZoom(.25, -1), 25)
  assert.equal(zoom.nextReviewZoom(3, 1), 300)
})

function viewport(sourceReview = true, engravingWidth = 1000) {
  const states = []; const effects = []; let slot = 0
  const observations = []; const cleanup = []
  const jsx = (type, props) => ({ type, props })
  const component = load('../src/components/ReviewScoreViewport.tsx', {
    '../utils/reviewZoom': zoom,
    '../utils/sourceEngraving': { initialEngravingWidth: 1000 },
    'react/jsx-runtime': { jsx, jsxs: jsx },
    react: {
      useRef(initial) { const i = slot++; states[i] ??= { current: initial }; return states[i] },
      useState(initial) {
        const i = slot++; if (!(i in states)) states[i] = initial
        return [states[i], (value) => { states[i] = typeof value === 'function' ? value(states[i]) : value }]
      },
      useEffect(fn) { const i = slot++; if (!(i in states)) { states[i] = true; effects.push(fn) } },
    },
  }, {
    ResizeObserver: class { constructor(fn) { observations.push(fn) } observe() {} disconnect() { cleanup.push('resize') } },
    MutationObserver: class { constructor(fn) { observations.push(fn) } observe() {} disconnect() { cleanup.push('mutation') } },
  }).default
  const pane = { clientWidth: 500 }
  const surface = { clientWidth: 1000, scrollWidth: 1000, scrollHeight: 2000 }
  const children = Object.freeze({ type: 'svg', props: Object.freeze({ semanticBytes: '<score-partwise/>' }) })
  function render() {
    slot = 0
    const tree = component({ sourceReview, engravingWidth, children })
    find(tree, (e) => e.props?.className === 'review-score-scroll').props.ref.current = pane
    find(tree, (e) => e.props?.className === 'review-score-surface').props.ref.current = surface
    return tree
  }
  render(); const dispose = effects.map((fn) => fn())
  return { render, pane, surface, observations, children, dispose, cleanup }
}

test('review defaults to Fit; zoom and resize retain engraving width and rendered children', () => {
  const view = viewport()
  let tree = view.render()
  const surface = () => find(tree, (e) => e.props?.className === 'review-score-surface')
  assert.equal(surface().props.style.transform, 'scale(0.5)')
  assert.equal(surface().props.style.width, 1000)
  assert.equal(surface().props.children, view.children)
  assert.equal(find(tree, (e) => e.props?.className === 'review-score-stage').props.style.height, 1000)
  find(tree, (e) => e.props?.children === '100%').props.onClick()
  tree = view.render()
  assert.equal(surface().props.style.transform, 'scale(1)')
  assert.equal(surface().props.style.width, 1000)
  find(tree, (e) => e.props?.['aria-label'] === 'Zoom score in').props.onClick()
  tree = view.render()
  assert.equal(surface().props.style.transform, 'scale(1.1)')
  find(tree, (e) => e.props?.children === 'Fit').props.onClick()
  view.pane.clientWidth = 400; view.observations[0]()
  tree = view.render()
  assert.equal(surface().props.style.transform, 'scale(0.4)')
  assert.equal(surface().props.children, view.children)
  view.surface.scrollHeight = 3000; view.observations[1]()
  tree = view.render()
  assert.equal(find(tree, (e) => e.props?.className === 'review-score-stage').props.style.height, 1200)
  view.dispose.forEach((fn) => fn())
  assert.deepEqual(view.cleanup, ['resize', 'mutation'])
})

test('responsive review zoom does not alter the pane-based engraving width', () => {
  const view = viewport(false)
  let tree = view.render()
  const surface = () => find(tree, (e) => e.props?.className === 'review-score-surface')
  assert.equal(surface().props.style.width, 500)
  find(tree, (e) => e.props?.children === '100%').props.onClick()
  tree = view.render()
  assert.equal(surface().props.style.width, 500)
})

test('workspace CSS bounds independent source/score scroll panes and proportional scaled overflow', () => {
  const css = readFileSync(new URL('../src/index.css', import.meta.url), 'utf8')
  assert.match(css, /grid-template-columns: minmax\(0, 1fr\) minmax\(0, 1fr\)/)
  assert.match(css, /\.source-viewer\s*\{[^}]*min-width: 0;[^}]*max-width: 100%/)
  assert.match(css, /\.review-score\s*\{[^}]*min-width: 0;[^}]*max-width: 100%/)
  assert.match(css, /\.source-scroll\s*\{[^}]*overflow: auto/)
  assert.match(css, /\.review-score-scroll\s*\{[^}]*max-width: 100%;[^}]*overflow: auto/)
  assert.match(css, /\.review-score-stage\s*\{[^}]*overflow: hidden/)
  assert.match(css, /\.review-score-surface\s*\{[^}]*transform-origin: top left/)
  assert.match(css, /@media \(max-width: 900px\)[\s\S]*grid-template-columns: 1fr/)
})

test('technical integrity is in Advanced; optional music check and source controls remain', () => {
  const source = readFileSync(new URL('../src/components/RecognitionReview.tsx', import.meta.url), 'utf8')
  assert.ok(source.indexOf('className="review-validation"') < source.indexOf('className="review-comparison"'))
  assert.equal((source.match(/<summary>Technical score details/g) ?? []).length, 1)
  assert.match(source, /className="review-validation" hidden=\{!advanced\}/)
  assert.match(source, />Advanced Review<\/button>/)
  assert.match(source, /<VisualNoteEditor/)
  const pdf = readFileSync(new URL('../src/components/SourceViewer.tsx', import.meta.url), 'utf8')
  assert.match(pdf, /Open source/)
  assert.match(pdf, /#page=\$\{page\}&zoom=\$\{zoom\}/)
})

test('viewer passes explicit source-break options and its rendering document to OSMD', async () => {
  const effects = []; const cleanups = []; const captures = []
  const jsx = (type, props) => ({ type, props })
  const renderingDocument = Object.freeze({ print: 'new-system=yes', semanticBytes: '<score-partwise/>' })
  const sourceDocument = Object.freeze({ semanticBytes: '<score-partwise/>' })
  const score = Object.freeze({ layout: Object.freeze({ mode: 'SOURCE_REVIEW' }) })
  const before = JSON.stringify(score)
  const component = load('../src/components/MusicSheetViewer.tsx', {
    react: { useState: (value) => [value, () => {}], useRef: (value) => ({ current: value }), useEffect: (fn) => effects.push(fn) },
    'react/jsx-runtime': { jsx, jsxs: jsx },
    opensheetmusicdisplay: { OpenSheetMusicDisplay: class {
      constructor(_, options) { captures.push({ options }); this.cursor = { hide() {} } }
      async load(document) { captures[0].document = document }
      render() { captures[0].rendered = true }
    } },
    '../utils/sourceEngraving': { initialEngravingWidth: 0, trustedSourceGroups: () => [[0]], sourceEngravingWidth: () => 720, engraveSourceGroups(osmd, groups, setWidth, seed) { setWidth(seed); osmd.render(); return { width: seed, matched: true } } },
    '../utils/scoreRenderer': {
      rendererOptions(sourceReview) { return { newSystemFromXML: sourceReview, newPageFromXML: sourceReview } },
      reviewDocument(document, suppliedScore) { assert.equal(document, sourceDocument); assert.equal(suppliedScore, score); return renderingDocument },
      bindRenderer() { return { highlight() {}, dispose() {} } },
    },
  }, {
    console,
    DOMParser: class { parseFromString() { return sourceDocument } },
    ResizeObserver: class { observe() {} disconnect() {} },
  }).default
  const tree = component({ musicXml: { text: async () => '<score-partwise/>' }, score, onSelect() {} })
  find(tree, (e) => e.props?.ref).props.ref.current = { innerHTML: '', clientWidth: 320, style: {} }
  for (const fn of effects) { const dispose = fn(); if (dispose) cleanups.push(dispose) }
  await new Promise(setImmediate)
  assert.deepEqual(captures[0].options, { newSystemFromXML: true, newPageFromXML: true })
  assert.equal(captures[0].document, renderingDocument)
  assert.equal(captures[0].rendered, true)
  assert.equal(JSON.stringify(score), before)
  cleanups.forEach((fn) => fn())
})


test('measured engraving surface stays fixed across narrow pane changes and Fit/zoom', () => {
  const view = viewport(true, 2400)
  view.surface.clientWidth = 2400; view.surface.scrollWidth = 2400; view.observations[0]()
  let tree = view.render()
  const surface = () => find(tree, (e) => e.props?.className === 'review-score-surface')
  assert.equal(surface().props.style.width, 2400)
  assert.equal(surface().props.style.transform, `scale(${500 / 2400})`)
  view.pane.clientWidth = 250; view.observations[0](); tree = view.render()
  assert.equal(surface().props.style.width, 2400)
  assert.equal(surface().props.style.transform, `scale(${250 / 2400})`)
  find(tree, (e) => e.props?.children === '100%').props.onClick(); tree = view.render()
  assert.equal(surface().props.style.width, 2400)
  assert.equal(surface().props.style.transform, 'scale(1)')
  assert.equal(surface().props.children, view.children)
})
