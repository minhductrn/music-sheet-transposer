import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import vm from 'node:vm'
import ts from 'typescript'

function load(path, dependencies = {}, globals = {}) {
  const module = { exports: {} }
  vm.runInNewContext(ts.transpileModule(readFileSync(new URL(path, import.meta.url), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
  }).outputText, { module, exports: module.exports, Blob, File, Error, FormData, String, console,
    require: name => dependencies[name] ?? { __esModule: true, default: name }, ...globals })
  return module.exports
}
function find(tree, predicate) {
  if (!tree || typeof tree !== 'object') return null
  if (predicate(tree)) return tree
  for (const child of [tree.props?.children, tree.props?.headerActions, tree.props?.toolbar, tree.props?.context, tree.props?.moreControls].flat(Infinity)) { const result = find(child, predicate); if (result) return result }
  return null
}
const button = (tree, label) => find(tree, e => e.type === 'button' && e.props.children === label)
const text = tree => !tree || typeof tree !== 'object' ? String(tree ?? '') : [tree.props?.children, tree.props?.headerActions, tree.props?.toolbar, tree.props?.context, tree.props?.moreControls].flat(Infinity).map(text).join(' ')
const tick = () => new Promise(setImmediate)

const original = new Blob(['saved concert XML'])
const transposed = new Blob(['transposed XML'])
function hooks() {
  const states = [], effects = []; let slot = 0
  return {
    react: {
      useState(initial) { const i = slot++; if (!(i in states)) states[i] = initial; return [states[i], value => { states[i] = typeof value === 'function' ? value(states[i]) : value }] },
      useRef(initial) { const i = slot++; if (!(i in states)) states[i] = { current: initial }; return states[i] },
      useEffect(effect, deps) { const i = slot++; if (!(i in states) || deps.some((v, n) => states[i][n] !== v)) { states[i] = deps; effects.push(effect) } },
    },
    render(component, props) { slot = 0; const tree = component(props); effects.splice(0).forEach(effect => effect()); return tree },
  }
}
const jsx = (type, props) => ({ type, props })
function harness({ mode = null, fifths = -1, invalid = false } = {}) {
  const hook = hooks(), calls = [], downloads = [], pending = []
  let allow = true, filename = 'independent.musicxml', current
  const props = { sourceFile: { reviewId: 'source', revision: 1, blob: original, filename: 'source.musicxml' },
    disabled: false, download: (...args) => downloads.push(args), onPending: value => pending.push(value), onBusy() {} }
  const component = load('../src/components/ConcertTranspose.tsx', {
    react: hook.react, 'react/jsx-runtime': { jsx, jsxs: jsx },
    '../services/api': {
      getConcertKey: async blob => { calls.push(['inspect', blob]); if (invalid) throw new Error('Source mode will not be guessed.'); return { fifths, mode, suggested: mode ? { fifths, mode } : null, candidates: ['major', 'minor'].map(mode => ({ fifths, mode })) } },
      transposeConcertKey: async (...args) => { calls.push(['transpose', ...args]); return transposed },
      createReview: async blob => { calls.push(['open', blob]); current = { id: `result-${calls.length}`, revision: 1, state: 'DRAFT', musicXml: blob, validation: { can_verify: true } }; return current },
      closeReview: async id => calls.push(['close', id]),
      changeReview: async review => { calls.push(['verify', review]); current = { ...review, state: 'VERIFIED' }; return current },
      getVerifiedMusicXml: async id => { calls.push(['export', id]); return current.musicXml },
    }, '../utils/localScoreFile': load('../src/utils/localScoreFile.ts'),
  }, { window: { confirm: () => allow, prompt: () => filename } }).default
  const render = () => hook.render(component, props)
  return { render, calls, downloads, pending, allow(value) { allow = value }, name(value) { filename = value },
    edit(blob) { const editor = find(render(), e => e.type === './RecognitionReview'); current = { ...editor.props.review, revision: editor.props.review.revision + 1, musicXml: blob, state: 'DRAFT' }; editor.props.onChange(current) } }
}
const control = (view, id) => find(view.render(), e => e.props?.id === id)
async function start(view, mode = 'major') {
  view.render(); await tick()
  control(view, 'concert-source-key').props.onChange({ target: { value: `${mode}:-1` } })
  control(view, 'concert-source-confirmed').props.onChange({ target: { checked: true } })
  button(view.render(), 'Apply').props.onClick(); await tick()
}
for (const mode of ['major', 'minor']) {
  test(`one-flat missing mode requires explicit ${mode} selection and confirmation`, async () => {
    const view = harness(); view.render(); await tick()
    assert.match(text(view.render()), /F major or D minor/)
    assert.equal(control(view, 'concert-source-key').props.value, '')
    assert.equal(button(view.render(), 'Apply').props.disabled, true)
    await start(view, mode)
    assert.equal(view.calls.find(c => c[0] === 'transpose')[1], original)
    assert.equal(view.calls.find(c => c[0] === 'transpose')[4].mode, mode)
    assert.equal(find(view.render(), e => e.type === 'input' && e.props.type === 'file'), null)
  })
}
test('explicit suggestion still requires confirmation; incompatible keys cannot reach engine', async () => {
  const view = harness({ mode: 'major' }); view.render(); await tick()
  assert.match(text(view.render()), /Suggested Source Key from MusicXML:\s+F major/)
  assert.equal(button(view.render(), 'Apply').props.disabled, true)
  control(view, 'concert-source-key').props.onChange({ target: { value: 'major:1' } })
  assert.match(text(view.render()), /incompatible/)
  control(view, 'concert-source-confirmed').props.onChange({ target: { checked: true } })
  button(view.render(), 'Apply').props.onClick(); await tick()
  assert.equal(view.calls.filter(c => c[0] === 'transpose').length, 0)
})
test('inspection failure is actionable and prevents transposition', async () => {
  const view = harness({ invalid: true }); view.render(); await tick()
  assert.match(text(view.render()), /will not be guessed/)
  assert.equal(button(view.render(), 'Apply'), null)
})
test('Original is read-only, result uses accepted editor, latest edits are exported independently', async () => {
  const view = harness(); await start(view)
  const left = find(view.render(), e => e.props?.['aria-label'] === 'Original Concert')
  assert.equal(find(left, e => e.type === './MusicSheetViewer').props.musicXml, original)
  assert.equal(find(left, e => e.type === './RecognitionReview'), null)
  const right = find(view.render(), e => e.props?.['aria-label'] === 'Transposed Concert')
  assert.equal(find(right, e => e.type === './RecognitionReview').props.resultOnly, true)
  const edited = new Blob(['edited lyrics pitch small notes ties'])
  view.edit(edited)
  view.name('source.musicxml')
  button(view.render(), 'Save').props.onClick(); await tick()
  assert.equal(view.downloads.length, 0)
  assert.match(text(view.render()), /Choose a new filename/)
  view.name('new.musicxml')
  button(view.render(), 'Save').props.onClick(); await tick()
  assert.equal(view.downloads[0][0], edited)
  assert.equal(view.downloads[0][1], 'new.musicxml')
  assert.equal(view.pending.at(-1), true)
  button(view.render(), 'I saved the Concert result').props.onClick(); view.render()
  assert.equal(view.pending.at(-1), false)
  assert.equal(await original.text(), 'saved concert XML')
  view.edit(new Blob(['later changes']))
  assert.equal(button(view.render(), 'I saved the Concert result'), null)
  assert.equal(view.pending.at(-1), true)
})
for (const id of ['concert-source-key', 'concert-target-key', 'concert-source-confirmed', 'direction', 'retranspose']) {
  test(`unsaved result blocks cancelled ${id}; approved replacement invalidates prior save`, async () => {
    const view = harness(); await start(view); view.edit(new Blob(['pending']))
    const action = () => {
      if (id === 'retranspose') button(view.render(), 'Apply').props.onClick()
      else if (id === 'direction') find(view.render(), e => e.type === 'select' && e.props.value === 'up').props.onChange({ target: { value: 'down' } })
      else control(view, id).props.onChange({ target: { value: id === 'concert-source-key' ? 'minor:-1' : '-3', checked: false } })
    }
    view.allow(false); action(); await tick()
    assert.equal(find(view.render(), e => e.type === './RecognitionReview').props.review.revision, 2)
    assert.equal(view.calls.filter(c => c[0] === 'transpose').length, 1)
    view.allow(true); action(); await tick()
    const editor = find(view.render(), e => e.type === './RecognitionReview')
    if (id === 'retranspose') assert.equal(editor.props.review.revision, 1)
    else assert.equal(editor, null)
    if (id === 'concert-source-key') assert.equal(control(view, 'concert-source-confirmed').props.checked, false)
  })
}
function homeHarness({ recognition = false } = {}) {
  const hook = hooks(), calls = []; let allow = true
  const Home = load('../src/pages/Home.tsx', {
    react: hook.react, 'react/jsx-runtime': { jsx, jsxs: jsx },
    '../services/api': { getHealth: async () => ({ status: 'ok' }),
      createReview: async blob => { calls.push(['open', blob]); return { id: `r${calls.length}`, revision: 1, musicXml: blob, state: 'DRAFT' } },
      closeReview: async id => calls.push(['close', id]), recognizeSheetMusic: async (...args) => { if (!recognition) assert.fail('MusicXML must bypass OMR'); calls.push(['recognize', ...args]); return { musicXml: original, profile: 'VOCAL_SONG', warnings: [] } } },
  }, { window: { confirm: () => allow, addEventListener() {}, removeEventListener() {} } }).default
  const render = () => hook.render(Home)
  return { render, calls, allow(value) { allow = value }, async open(file) {
    await control({ render }, 'musicxml-open').props.onChange({ target: { files: [file], value: file.name } })
  } }
}
test('one MusicXML open supplies both modes; review edits and switching never replace saved source', async () => {
  const view = homeHarness(), file = new File([original], 'source.musicxml')
  await view.open(file)
  const editor = () => find(view.render(), e => e.type === '../components/RecognitionReview')
  const panel = () => find(view.render(), e => e.type === '../components/ConcertTranspose')
  editor().props.onChange({ ...editor().props.review, revision: 2, musicXml: new Blob(['review edits']) })
  button(view.render(), 'Transpose').props.onClick()
  assert.equal(panel().props.sourceFile.blob, file)
  assert.equal(view.calls.filter(c => c[0] === 'open').length, 1)
  button(view.render(), 'Review').props.onClick()
  assert.equal(editor().props.review.revision, 2)
  view.allow(false); await view.open(new File(['replacement'], 'other.musicxml'))
  assert.equal(editor().props.review.revision, 2)
  assert.equal(panel().props.sourceFile.blob, file)
  view.allow(true); await view.open(new File(['downloaded edited result'], 'result.musicxml'))
  assert.equal(await editor().props.review.musicXml.text(), 'downloaded edited result')
  assert.equal(panel().props.sourceFile.filename, 'result.musicxml')
  assert.equal(await file.text(), 'saved concert XML')
})
test('pending result prevents replacing source via MusicXML or PDF entry', async () => {
  const view = homeHarness(); await view.open(new File([original], 'source.musicxml'))
  find(view.render(), e => e.type === '../components/ConcertTranspose').props.onPending(true)
  view.allow(false); await view.open(new File(['other'], 'other.musicxml'))
  control(view, 'sheet-upload').props.onChange({ target: { files: [new File(['pdf'], 'score.pdf')], value: 'score.pdf' } })
  assert.equal(view.calls.filter(c => c[0] === 'open').length, 1)
  assert.match(text(view.render()), /source.musicxml/)
})
test('central API sends saved bytes, target spelling and direction and surfaces backend errors', async () => {
  const calls = []
  const api = load('../src/services/api.ts', {}, { fetch: async (url, options) => {
    calls.push([url, options])
    return url.endsWith('/transpose/concert-key') ? new Response(transposed) : Response.json({ fifths: 0, mode: 'minor' })
  } })
  assert.equal((await api.getConcertKey(original)).mode, 'minor')
  assert.equal(await (await api.transposeConcertKey(original, -3, 'down', { fifths: 0, mode: 'minor' })).text(), await transposed.text())
  assert.equal(calls[1][0], '/api/v1/transpose/concert-key')
  assert.equal(await calls[1][1].body.get('file').text(), await original.text())
  assert.equal(calls[1][1].body.get('target_fifths'), '-3')
  assert.equal(calls[1][1].body.get('direction'), 'down')
  assert.equal(calls[1][1].body.get('source_fifths'), '0')
  assert.equal(calls[1][1].body.get('source_mode'), 'minor')
  assert.equal(calls[1][1].body.get('source_confirmed'), 'true')
  const rejected = load('../src/services/api.ts', {}, { fetch: async () => Response.json({ detail: 'Repair source pitch' }, { status: 422 }) })
  await assert.rejects(rejected.transposeConcertKey(original, 0, 'up', { fifths: 0, mode: 'major' }), /Repair source pitch/)
})


test('UX-01 Stage 1 header Save targets the existing editor form and Concert controls stay mode-specific', async () => {
  const view = homeHarness()
  assert.equal(find(view.render(), node => node.type === '../components/RecognitionReview'), null)
  assert.equal(find(view.render(), node => node.type === '../components/ConcertTranspose'), null)
  await view.open(new File([original], 'concert.musicxml'))
  const editor = find(view.render(), node => node.type === '../components/RecognitionReview')
  const header = find(view.render(), node => node.type === 'header')
  assert.equal(button(header, 'Save').props.form, `review-save-${editor.props.review.id}`)
  assert.equal(button(header, 'Save').props.type, 'submit')
  assert.equal(find(header, node => node.type === 'select'), null)
  button(view.render(), 'Transpose').props.onClick()
  assert.equal(button(find(view.render(), node => node.type === 'header'), 'Save'), null)
  assert.ok(find(view.render(), node => node.type === '../components/ConcertTranspose'))
})

test('UX-02A landing has exactly two central file actions and no duplicate header actions', () => {
  const view = homeHarness(), tree = view.render()
  const welcome = find(tree, n => n.props?.className === 'landing-welcome')
  assert.match(text(welcome), /Your music, your way/)
  assert.match(text(welcome), /Import a score or open a saved MusicXML to get started\./)
  const actions = find(welcome, n => n.props?.className === 'landing-actions')
  const ids = []
  function collect(node) {
    if (!node || typeof node !== 'object') return
    if (node.type === 'input' && node.props.type === 'file') ids.push(node.props.id)
    for (const child of [node.props?.children].flat(Infinity)) collect(child)
  }
  collect(actions)
  assert.deepEqual(ids, ['sheet-upload', 'musicxml-open'])
  const header = find(tree, n => n.type === 'header')
  assert.equal(find(header, n => n.props?.id === 'sheet-upload'), null)
  assert.equal(find(header, n => n.props?.id === 'musicxml-open'), null)
  assert.match(text(header), /Music Sheet Transposer/)
  assert.equal(text(tree).includes('Open MusicXML or import a PDF / image.'), false)
})

test('UX-02A central Import enters existing recognition setup and restores compact actions', () => {
  const view = homeHarness(), file = new File(['pdf'], 'scan.pdf')
  control(view, 'sheet-upload').props.onChange({ target: { files: [file], value: file.name } })
  const tree = view.render()
  assert.equal(find(tree, n => n.props?.className === 'landing-welcome'), null)
  assert.match(text(tree), /scan.pdf/)
  assert.ok(button(tree, 'Recognize Sheet Music'))
  assert.ok(find(tree, n => n.props?.id === 'recognition-profile'))
  const header = find(tree, n => n.type === 'header')
  assert.ok(find(header, n => n.props?.id === 'sheet-upload'))
  assert.ok(find(header, n => n.props?.id === 'musicxml-open'))
  assert.equal(view.calls.length, 0)
})

test('UX-02A central Open enters existing Review and retains both loaded workspace headers', async () => {
  const view = homeHarness(), file = new File([original], 'concert.musicxml')
  await view.open(file)
  assert.equal(view.calls[0][1], file)
  assert.equal(find(view.render(), n => n.props?.className === 'landing-welcome'), null)
  for (const mode of ['Review', 'Transpose']) {
    button(view.render(), mode).props.onClick()
    const header = find(view.render(), n => n.type === 'header')
    assert.ok(find(header, n => n.props?.id === 'sheet-upload'))
    assert.ok(find(header, n => n.props?.id === 'musicxml-open'))
    assert.equal(Boolean(button(header, 'Save')), mode === 'Review')
    assert.ok(find(view.render(), n => n.type === '../components/RecognitionReview'))
    assert.ok(find(view.render(), n => n.type === '../components/ConcertTranspose'))
  }
})

for (const name of ['cungdemTinMung.pdf', 'score.png']) test(`UX-02A-FIX ${name}: selection persists and recognition uses the main file`, async () => {
  const view = homeHarness({ recognition: true }), file = new File(['score'], name)
  control(view, 'sheet-upload').props.onChange({ target: { files: [file], value: name } })
  assert.match(text(view.render()), new RegExp(name.replace('.', '\\.')))
  assert.match(text(view.render()), /Recognition input:/)
  const change = find(view.render(), n => n.type === 'label' && n.props.htmlFor === 'sheet-upload')
  assert.match(text(change), /Change File/)
  const comparison = new File(['comparison'], 'reference.jpg')
  control(view, 'comparison-source').props.onChange({ target: { files: [comparison] } })
  control(view, 'recognition-profile').props.onChange({ target: { value: 'PIANO' } })
  control(view, 'input-quality').props.onChange({ target: { value: 'Poor' } })
  assert.match(text(view.render()), /does not replace the recognition input/)
  await button(view.render(), 'Recognize Sheet Music').props.onClick()
  const request = view.calls.find(c => c[0] === 'recognize')
  assert.equal(request[1], file)
  assert.equal(request[2], 'PIANO')
  assert.equal(request[3], 'Poor')
})

test('UX-02A-FIX Change File replaces active input; cancellation retains it', async () => {
  const view = homeHarness({ recognition: true })
  const first = new File(['first'], 'first.pdf'), replacement = new File(['second'], 'second.jpg')
  const choose = files => control(view, 'sheet-upload').props.onChange({ target: { files, value: '' } })
  choose([first]); choose([])
  assert.match(text(view.render()), /Recognition input:.*first.pdf/)
  choose([replacement]); choose([])
  assert.match(text(view.render()), /Recognition input:.*second.jpg/)
  await button(view.render(), 'Recognize Sheet Music').props.onClick()
  assert.equal(view.calls.find(c => c[0] === 'recognize')[1], replacement)
})
