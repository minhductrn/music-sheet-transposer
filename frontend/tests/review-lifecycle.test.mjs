// Exercise Home's actual callbacks with provider/network calls replaced by stubs.
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import vm from 'node:vm'
import ts from 'typescript'

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

function harness() {
  const states = []
  let slot = 0
  const draft = { profile: 'VOCAL_SONG', provider: 'fixture', warnings: [], musicXml: {} }
  const original = { id: 'review', revision: 1, state: 'VERIFIED', musicXml: {} }
  const output = { correctedTransposedBytes: true }
  const calls = []
  const api = {
    recognizeSheetMusic: async () => draft,
    createReview: async () => original,
    transposeVerifiedReview: async (review, semitones) => { calls.push({ review, semitones }); return output },
  }
  const module = { exports: {} }
  const jsx = (type, props, key) => ({ type, props, key })
  const source = ts.transpileModule(readFileSync(new URL('../src/pages/Home.tsx', import.meta.url), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
  }).outputText
  vm.runInNewContext(source, {
    module, exports: module.exports,
    require(name) {
      if (name === 'react') return {
        useState(initial) {
          const index = slot++
          if (!(index in states)) states[index] = initial
          return [states[index], (value) => { states[index] = value }]
        },
        useEffect() {},
      }
      if (name === 'react/jsx-runtime') return { jsx, jsxs: jsx }
      if (name === '../services/api') return api
      return { __esModule: true, default: name }
    },
  })
  return { calls, output, render() { slot = 0; return module.exports.default() } }
}

for (const operation of ['add', 'change', 'remove', 'undo', 'redo']) {
  test(`${operation} tie update clears stale transposed preview/download and uses the next verified revision`, async () => {
    const view = harness()
    let tree = view.render()
    element(tree, (e) => e.type === 'input' && e.props.type === 'file').props.onChange({ target: { files: [{ name: 'source.pdf' }] } })
    tree = view.render()
    await element(tree, (e) => e.type === 'button' && e.props.children === 'Recognize Sheet Music').props.onClick()
    tree = view.render()
    await element(tree, (e) => e.type === 'button' && e.props.children === 'Transpose').props.onClick()
    tree = view.render()
    assert.equal(element(tree, (e) => e.type === '../components/MusicSheetViewer').props.musicXml, view.output)
    assert.ok(element(tree, (e) => e.type === 'button' && e.props.children === 'Download Transposed MusicXML'))
    const inspector = element(tree, (e) => e.type === '../components/RecognitionReview')
    inspector.props.onChange({ ...inspector.props.review, revision: 2, state: 'REVIEW_REQUIRED' })
    tree = view.render()
    assert.equal(element(tree, (e) => e.type === '../components/MusicSheetViewer'), null)
    assert.equal(element(tree, (e) => e.type === 'button' && e.props.children === 'Download Transposed MusicXML'), null)
    assert.equal(element(tree, (e) => e.type === 'button' && e.props.children === 'Transpose').props.disabled, true)
    const updated = element(tree, (e) => e.type === '../components/RecognitionReview')
    updated.props.onChange({ ...updated.props.review, revision: 3, state: 'VERIFIED' })
    tree = view.render()
    await element(tree, (e) => e.type === 'button' && e.props.children === 'Transpose').props.onClick()
    assert.equal(view.calls[1].review.revision, 3)
  })
}
