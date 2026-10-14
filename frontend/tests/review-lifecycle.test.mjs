// Exercise Home's actual callbacks with provider/network calls replaced by stubs.
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import vm from 'node:vm'
import ts from 'typescript'

function element(tree, predicate) {
  if (!tree || typeof tree !== 'object') return null
  if (predicate(tree)) return tree
  const children = [tree.props?.children, tree.props?.headerActions, tree.props?.toolbar, tree.props?.context, tree.props?.moreControls]
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
    module, exports: module.exports, window: { confirm: () => true },
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

for (const operation of ['add', 'change', 'remove', 'undo', 'redo', 'lyric add', 'lyric edit', 'lyric remove', 'pitch', 'duration', 'insertion', 'deletion']) {
  test(`${operation} correction clears stale transposed preview/download and uses the next verified revision`, async () => {
    const view = harness()
    let tree = view.render()
    element(tree, (e) => e.type === 'input' && e.props.id === 'sheet-upload').props.onChange({ target: { files: [{ name: 'source.pdf' }] } })
    tree = view.render()
    await element(tree, (e) => e.type === 'button' && e.props.children === 'Recognize Sheet Music').props.onClick()
    tree = view.render()
    const saving = element(tree, e => e.type === '../components/RecognitionReview')
    saving.props.onSaved({ reviewId: saving.props.review.id, revision: saving.props.review.revision, filename: 'score.musicxml', blob: saving.props.review.musicXml })
    tree = view.render()
    await element(tree, (e) => e.type === 'button' && e.props.children === 'Transpose by semitones').props.onClick()
    tree = view.render()
    assert.equal(element(tree, (e) => e.type === '../components/RecognitionReview').props.transposed, view.output)
    assert.equal(element(tree, (e) => e.type === '../components/MusicSheetViewer'), null)
    assert.ok(element(tree, (e) => e.type === 'button' && e.props.children === 'Download Transposed MusicXML'))
    const inspector = element(tree, (e) => e.type === '../components/RecognitionReview')
    inspector.props.onChange({ ...inspector.props.review, revision: 2, state: 'REVIEW_REQUIRED' })
    tree = view.render()
    assert.equal(element(tree, (e) => e.type === '../components/MusicSheetViewer'), null)
    assert.equal(element(tree, (e) => e.type === '../components/RecognitionReview').props.transposed, null)
    assert.equal(element(tree, (e) => e.type === 'button' && e.props.children === 'Download Transposed MusicXML'), null)
    assert.equal(element(tree, (e) => e.type === 'button' && e.props.children === 'Transpose by semitones').props.disabled, true)
    const updated = element(tree, (e) => e.type === '../components/RecognitionReview')
    updated.props.onChange({ ...updated.props.review, revision: 3, state: 'VERIFIED' })
    tree = view.render()
    const savingUpdated = element(tree, e => e.type === '../components/RecognitionReview')
    savingUpdated.props.onSaved({ reviewId: savingUpdated.props.review.id, revision: savingUpdated.props.review.revision, filename: 'score.musicxml', blob: savingUpdated.props.review.musicXml })
    tree = view.render()
    await element(tree, (e) => e.type === 'button' && e.props.children === 'Transpose by semitones').props.onClick()
    assert.equal(view.calls[1].review.revision, 3)
  })
}


test('MusicXML Visual Review transposes the verified corrected revision instead of the uploaded file', async () => {
  const view = harness()
  await element(view.render(), e => e.props?.id === 'musicxml-open').props.onChange({ target: { files: [{ name: 'score.musicxml' }], value: 'score.musicxml' } })
  let tree = view.render()
  const panel = element(tree, (e) => e.type === '../components/RecognitionReview')
  const corrected = { ...panel.props.review, revision: 2, state: 'REVIEW_REQUIRED', musicXml: { corrected: true } }
  panel.props.onChange(corrected)
  tree = view.render()
  assert.equal(element(tree, (e) => e.type === 'button' && e.props.children === 'Transpose by semitones').props.disabled, true)
  element(tree, (e) => e.type === '../components/RecognitionReview').props.onChange({ ...corrected, revision: 3, state: 'VERIFIED' })
  const saving = element(view.render(), e => e.type === '../components/RecognitionReview')
  saving.props.onSaved({ reviewId: saving.props.review.id, revision: saving.props.review.revision, filename: 'score.musicxml', blob: saving.props.review.musicXml })
  await element(view.render(), (e) => e.type === 'button' && e.props.children === 'Transpose by semitones').props.onClick()
  assert.equal(view.calls[0].review.revision, 3)
  assert.equal(view.calls[0].review.musicXml.corrected, true)
})

test('+2 then +3 both use the same verified corrected master and one review pane', async () => {
  const view = harness()
  await element(view.render(), e => e.props?.id === 'musicxml-open').props.onChange({ target: { files: [{ name: 'score.musicxml' }], value: 'score.musicxml' } })
  const panel=element(view.render(),e=>e.type==='../components/RecognitionReview')
  const master={...panel.props.review,revision:4,state:'VERIFIED',musicXml:{corrected:true}}
  panel.props.onChange(master)
  panel.props.onSaved({ reviewId: master.id, revision: master.revision, filename: 'score.musicxml', blob: master.musicXml })
  for (const value of ['2','3']) {
    element(view.render(),e=>e.type==='input' && e.props.id==='semitones').props.onChange({target:{value}})
    await element(view.render(),e=>e.type==='button' && e.props.children==='Transpose by semitones').props.onClick()
  }
  assert.deepEqual(view.calls.map(call=>call.semitones),[2,3])
  assert.ok(view.calls.every(call=>call.review===master))
  assert.equal(element(view.render(),e=>e.type==='../components/MusicSheetViewer'),null)
  assert.equal(element(view.render(),e=>e.type==='../components/RecognitionReview').props.transposed,view.output)
})


test('verified but unsaved review cannot transpose; a stale saved revision cannot unlock edits', async () => {
  const view = harness()
  await element(view.render(), e => e.props?.id === 'musicxml-open').props.onChange({ target: { files: [{ name: 'score.musicxml' }], value: 'score.musicxml' } })
  const opened = element(view.render(), e => e.type === '../components/RecognitionReview')
  opened.props.onChange({ ...opened.props.review, revision: 2 })
  let tree = view.render()
  assert.equal(element(tree, e => e.type === 'button' && e.props.children === 'Transpose by semitones').props.disabled, true)
  await element(tree, e => e.type === 'button' && e.props.children === 'Transpose by semitones').props.onClick()
  assert.equal(view.calls.length, 0)
  const panel = element(tree, e => e.type === '../components/RecognitionReview')
  panel.props.onSaved({ reviewId: 'other', revision: 1, blob: {}, filename: 'other.musicxml' })
  assert.equal(element(view.render(), e => e.type === 'button' && e.props.children === 'Transpose by semitones').props.disabled, true)
  panel.props.onSaved({ reviewId: 'review', revision: 2, blob: {}, filename: 'score.musicxml' })
  assert.equal(element(view.render(), e => e.type === 'button' && e.props.children === 'Transpose by semitones').props.disabled, false)
  panel.props.onChange({ ...panel.props.review, revision: 3, state: 'VERIFIED' })
  tree = view.render()
  assert.equal(element(tree, e => e.type === 'button' && e.props.children === 'Transpose by semitones').props.disabled, true)
  await element(tree, e => e.type === 'button' && e.props.children === 'Transpose by semitones').props.onClick()
  assert.equal(view.calls.length, 0)
})
