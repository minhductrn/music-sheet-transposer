import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import vm from 'node:vm'
import ts from 'typescript'

function load(path, dependencies = {}, globals = {}) {
  const module = { exports: {} }
  vm.runInNewContext(ts.transpileModule(readFileSync(new URL(path, import.meta.url), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
  }).outputText, { module, exports: module.exports, Blob, Error, Set, Map, console,
    require: name => dependencies[name] ?? { __esModule: true, default: name }, ...globals })
  return module.exports
}
const local = browser => load('../src/utils/localScoreFile.ts', {}, { window: browser })
const xml = new Blob(['<score-partwise><part id="P1"><measure number="1"><note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><tie type="start"/><notations><tied type="start" orientation="over"/></notations><lyric><text>Việt</text></lyric></note></measure></part></score-partwise>'])

test('direct Save reuses only an explicitly chosen handle; Save As selects a new destination', async () => {
  let pickCount = 0, disk = null, closed = false
  const handle = { name: 'chosen.musicxml', createWritable: async () => ({
    write: async data => { disk = data }, close: async () => { closed = true }, abort: async () => {},
  }) }
  const file = local({ showSaveFilePicker: async () => { pickCount++; return handle } })
  const first = await file.chooseScoreFile(false, null, 'concert.musicxml')
  assert.equal(pickCount, 1)
  assert.equal(await file.writeScoreFile(xml, first, () => assert.fail('No download for direct write')), 'written')
  assert.equal(closed, true); assert.equal(await disk.text(), await xml.text())
  await file.chooseScoreFile(false, handle, 'ignored.musicxml'); assert.equal(pickCount, 1)
  await file.chooseScoreFile(true, handle, 'concert.musicxml'); assert.equal(pickCount, 2)
})

test('Firefox fallback only requests a download and Save As supplies a filename', async () => {
  const file = local({ prompt: () => 'My concert score' }), downloads = []
  const target = await file.chooseScoreFile(true, null, 'concert.musicxml')
  assert.equal(target.handle, null); assert.equal(target.filename, 'My concert score.musicxml')
  assert.equal(await file.writeScoreFile(xml, target, (...args) => downloads.push(args)), 'download-requested')
  assert.equal(downloads[0][0], xml)
  assert.equal(downloads[0][1], 'My concert score.musicxml')
  assert.equal(await local({ prompt: () => null }).chooseScoreFile(true, null, 'concert.musicxml'), null)
})

test('cancelled picker and failed writes never report success; failed stream is aborted', async () => {
  const cancelled = local({ showSaveFilePicker: async () => { throw new Error('Picker cancelled') } })
  await assert.rejects(cancelled.chooseScoreFile(true, null, 'concert.musicxml'), /cancelled/)
  let aborted = false
  const handle = { name: 'score.musicxml', createWritable: async () => ({
    write: async () => { throw new Error('Disk full') }, close: async () => assert.fail('No commit'), abort: async () => { aborted = true },
  }) }
  await assert.rejects(local({}).writeScoreFile(xml, { handle, filename: handle.name }, () => assert.fail()), /Disk full/)
  assert.equal(aborted, true)
})

function find(tree, predicate) {
  if (!tree || typeof tree !== 'object') return null
  if (predicate(tree)) return tree
  for (const child of [tree.props?.children].flat(Infinity)) { const result = find(child, predicate); if (result) return result }
  return null
}
const button = (tree, label) => find(tree, e => e.type === 'button' && e.props.children === label)
const text = tree => !tree || typeof tree !== 'object' ? String(tree ?? '') : [tree.props?.children].flat(Infinity).map(text).join(' ')
function editor({ invalid = false, writeFails = false, direct = false } = {}) {
  const file = local(direct ? { showSaveFilePicker: async () => ({ name: 'chosen.musicxml', createWritable: async () => ({
    write: async () => { if (writeFails) throw new Error('Disk full') }, close: async () => {}, abort: async () => {},
  }) }) } : { prompt: () => 'new.musicxml' })
  const calls = [], downloads = [], saves = [], states = []; let slot = 0
  let props = { review: { id: 'r', revision: 1, state: 'DRAFT', expires_at: 9999999999, musicXml: xml,
    score: { parts: [], lyrics: [], harmonies: [], metadata: { title: '', credits: [] } },
    validation: { can_verify: !invalid, error_count: invalid ? 1 : 0, diagnostics: invalid ? [{ blocking: true, message: 'Repair the missing duration.' }] : [] } },
    onBusy() {}, download: (...args) => downloads.push(args),
    onChange: review => { props = { ...props, review } },
    onSaved: savedFile => { saves.push(savedFile); props = { ...props, savedFile } },
  }
  const jsx = (type, props) => ({ type, props })
  const component = load('../src/components/RecognitionReview.tsx', {
    react: { useState(initial) { const i = slot++; if (!(i in states)) states[i] = initial; return [states[i], value => { states[i] = value }] },
      useRef(initial) { const i = slot++; if (!(i in states)) states[i] = { current: initial }; return states[i] } },
    'react/jsx-runtime': { jsx, jsxs: jsx }, '../utils/localScoreFile': file,
    '../utils/visualReview': load('../src/utils/visualReview.ts'),
    '../utils/review': { eventLabel: () => '', validDuration: () => true },
    '../services/api': {
      changeReview: async (review, ...args) => { calls.push(args); return { ...review, state: 'VERIFIED', revision: review.revision + 1 } },
      getVerifiedMusicXml: async () => xml,
    },
  }).default
  return { calls, downloads, saves,
    render() { slot = 0; return component(props) },
    edit() { props = { ...props, review: { ...props.review, revision: props.review.revision + 1, state: 'REVIEW_REQUIRED' } } },
  }
}
const tick = () => new Promise(setImmediate)

test('Save explicitly validates; fallback waits for user acknowledgement and exports the saved snapshot', async () => {
  const view = editor()
  assert.match(text(view.render()), /Unsaved changes/)
  button(view.render(), 'Save').props.onClick(); await tick()
  assert.equal(view.saves.length, 0); assert.equal(view.downloads[0][0], xml)
  assert.deepEqual(JSON.parse(JSON.stringify(view.calls)), [['verify', 'POST', { confirmed_source_comparison: true }]])
  assert.match(text(view.render()), /cannot overwrite a file or confirm download completion/)
  button(view.render(), 'I saved the downloaded file').props.onClick()
  assert.equal(view.saves.length, 1); assert.match(text(view.render()), /Saved: concert-score.musicxml/)
  view.edit()
  assert.match(text(view.render()), /Unsaved changes/)
  assert.equal(view.saves.length, 1)
  button(view.render(), 'Export saved MusicXML').props.onClick()
  assert.equal(view.downloads.at(-1)[0], xml)
  assert.match(text(view.render()), /Export uses the last saved version/)
})

test('stale download acknowledgement disappears after an edit', async () => {
  const view = editor()
  button(view.render(), 'Save').props.onClick(); await tick(); view.edit()
  assert.equal(button(view.render(), 'I saved the downloaded file'), null)
  assert.equal(view.saves.length, 0)
})

test('direct Save reports success only after write/close; Save As uses another selection', async () => {
  const view = editor({ direct: true })
  button(view.render(), 'Save').props.onClick(); await tick()
  assert.equal(view.saves.length, 1); assert.equal(view.downloads.length, 0)
  button(view.render(), 'Save As').props.onClick(); await tick()
  assert.equal(view.saves.length, 2)
})

test('technical corruption or disk failure displays an actionable error without a saved marker', async () => {
  for (const options of [{ invalid: true }, { direct: true, writeFails: true }]) {
    const view = editor(options)
    button(view.render(), 'Save').props.onClick(); await tick()
    assert.equal(view.saves.length, 0); assert.equal(view.downloads.length, 0)
    assert.match(text(find(view.render(), e => e.props?.role === 'alert')), options.invalid ? /Repair the missing duration/ : /Disk full/)
    if (options.invalid) assert.equal(view.calls.length, 0)
  }
})
