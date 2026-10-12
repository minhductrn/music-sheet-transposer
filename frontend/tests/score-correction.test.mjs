import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import vm from 'node:vm'
import ts from 'typescript'

function load(path, dependencies = {}, globals = {}) {
  const module = { exports: {} }
  vm.runInNewContext(ts.transpileModule(readFileSync(new URL(path, import.meta.url), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
  }).outputText, { module, exports: module.exports, require: name => dependencies[name] ?? { __esModule: true, default: name }, ...globals })
  return module.exports
}
const helpers = load('../src/utils/visualReview.ts')
const geometry = load('../src/utils/scoreInsertion.ts', { './visualReview': helpers })
const plain = value => JSON.parse(JSON.stringify(value))
function find(tree, predicate) {
  if (!tree || typeof tree !== 'object') return null
  if (predicate(tree)) return tree
  for (const child of [tree.props?.children].flat(Infinity)) { const result = find(child, predicate); if (result) return result }
  return null
}
function harness(path, props, dependencies = {}) {
  const states = []; let slot = 0
  const jsx = (type, props, key) => ({ type, props, key })
  const module = load(path, {
    react: {
      useState(initial) { const i = slot++; if (!(i in states)) states[i] = initial; return [states[i], value => { states[i] = value }] },
      useRef(initial) { const i = slot++; if (!(i in states)) states[i] = { current: initial }; return states[i] },
    }, 'react/jsx-runtime': { jsx, jsxs: jsx }, '../utils/visualReview': helpers,
    '../utils/review': { eventLabel: e => e.id, validDuration: () => true }, ...dependencies,
  })
  return { render(next = props) { props = next; slot = 0; return module.default(props) } }
}
const field = (tree, label) => find(tree, e => e.props?.['aria-label'] === label)
const button = (tree, label) => find(tree, e => e.type === 'button' && (e.props['aria-label'] === label || e.props.children === label))
const note = { id: 'a', kind: 'note', voice: '1', staff: 1, pitch: { step: 'A', octave: 4, alter: '0' }, duration: '2', onset: '0', divisions: '4', display_size: 'normal', grace: false, tie_target_ids: ['next'], lyric_ids: [] }
const measure = { id: 'm1', index: 0, number: '1', staves: 1, divisions: '4', voices: [{ id: '1', events: [note] }] }
const score = { parts: [{ id: 'p', measures: [measure] }], lyrics: [], harmonies: [], metadata: { credits: [] } }
const review = { id: 'review', revision: 1, state: 'DRAFT', expires_at: 9999999999, score, can_undo: true, can_redo: true, review_issues: [], validation: { diagnostics: [], unresolved_issue_count: 0, error_count: 0, warning_count: 0 } }
function toolbar(overrides = {}) {
  const calls = []; const actions = []
  const props = { review, event: note, measure, position: null, adding: false, tying: false, disabled: false, readOnly: false,
    change: async (...args) => calls.push(args), select: () => actions.push('select'), add: () => actions.push('add'), tie: () => actions.push('tie'), advanced: () => actions.push('advanced'), ...overrides }
  return { ...harness('../src/components/ScoreCorrectionToolbar.tsx', props), calls, actions, props }
}

test('toolbar has labeled icon actions and disables unrelated edits without selection', () => {
  const view = toolbar({ event: undefined }); const tree = view.render()
  for (const label of ['Select', 'Add note', 'Delete selected notation', 'Pitch', 'Duration', 'Accidental', 'Normal / Small', 'Duration-bearing / Grace', 'Tie', 'Lyric', 'Undo', 'Redo', 'More / Advanced']) {
    const action = button(tree, label); assert.ok(action); assert.equal(action.props.title, label)
  }
  assert.equal(button(tree, 'Select').props.disabled, false)
  assert.equal(button(tree, 'Add note').props.disabled, false)
  for (const label of ['Delete selected notation', 'Pitch', 'Duration', 'Accidental', 'Normal / Small', 'Duration-bearing / Grace', 'Tie', 'Lyric']) assert.equal(button(tree, label).props.disabled, true)
  button(tree, 'Add note').props.onClick(); assert.deepEqual(view.actions, ['add'])
})

test('contextual pitch duration accidental size timing delete and history use existing commands', () => {
  const view = toolbar()
  button(view.render(), 'Pitch').props.onClick()
  field(view.render(), 'Note pitch').props.onChange({ target: { value: 'C' } })
  field(view.render(), 'Note octave').props.onChange({ target: { value: '5' } })
  button(view.render(), 'Apply pitch').props.onClick()
  assert.deepEqual(plain(view.calls[0]), ['events/a', 'PATCH', { pitch: { step: 'C', octave: 5, alter: '0' } }])
  button(view.render(), 'Duration').props.onClick()
  button(view.render(), 'Eighth note').props.onClick()
  assert.deepEqual(plain(view.calls[1]), ['events/a', 'PATCH', { duration: '1/2', duration_scope: 'note', preserve_onsets: true }])
  button(view.render(), 'Accidental').props.onClick()
  button(view.render(), 'Sharp').props.onClick()
  button(view.render(), 'Apply accidental').props.onClick()
  assert.deepEqual(plain(view.calls[2][2]), { pitch: { step: 'A', octave: 4, alter: '1' }, written_accidental: 'sharp' })
  button(view.render(), 'Normal / Small').props.onClick()
  field(view.render(), 'Selected note size').props.onChange({ target: { value: 'small' } })
  assert.deepEqual(plain(view.calls[3]), ['events/a', 'PATCH', { display_size: 'small' }])
  button(view.render(), 'Duration-bearing / Grace').props.onClick()
  field(view.render(), 'Selected note timing').props.onChange({ target: { value: 'grace' } })
  assert.deepEqual(plain(view.calls[4]), ['events/a', 'PATCH', { grace: true }])
  button(view.render(), 'Delete selected notation').props.onClick()
  assert.deepEqual(plain(view.calls[5]), ['events/a', 'DELETE'])
  button(view.render(), 'Undo').props.onClick(); button(view.render(), 'Redo').props.onClick()
  assert.deepEqual(plain(view.calls.slice(6)), [['undo', 'POST'], ['redo', 'POST']])
})

test('Add consumes visual position with C5 Half Small duration-bearing; no offset input', () => {
  const position = { measureId: 'm1', staff: 1, onset: '0' }
  const view = toolbar({ adding: true, position })
  let tree = view.render()
  assert.equal(button(tree, 'Add note').props['aria-pressed'], true)
  assert.equal(button(tree, 'Pitch').props.disabled, true)
  for (const [label, value] of [['Note pitch','C'], ['Note octave','5'], ['New note size','small'], ['New note voice','secondary']]) field(view.render(), label).props.onChange({ target: { value } })
  button(view.render(), 'Half note').props.onClick()
  tree = view.render()
  assert.equal(field(tree, 'New note timing').props.value, 'duration-bearing')
  assert.equal(find(tree, e => e.type === 'input'), null)
  button(tree, 'Add').props.onClick()
  assert.deepEqual(plain(view.calls[0]), ['events','POST',{ measure_id: 'm1', onset: '0', staff: 1, voice: '2', kind: 'note', pitch: { step: 'C', octave: 5, alter: '0' }, duration: '2', display_size: 'small', grace: false, written_accidental: null }])
  const noPosition = toolbar({ adding: true })
  assert.equal(button(noPosition.render(), 'Add').props.disabled, true)
})

test('ambiguous voice requires a musical choice and does not guess ownership', () => {
  const poly = { ...measure, voices: [...measure.voices, { id: '2', events: [{ ...note, id: 'b', voice: '2' }] }] }
  const view = toolbar({ adding: true, position: { measureId: 'm1', staff: 1, onset: '0' }, review: { ...review, score: { ...score, parts: [{ id: 'p', measures: [poly] }] } } })
  assert.equal(button(view.render(), 'Add').props.disabled, true)
  field(view.render(), 'New note voice').props.onChange({ target: { value: '2' } })
  assert.equal(button(view.render(), 'Add').props.disabled, false)
})

test('tie mode and removal are explicit, lyrics and Advanced remain accessible', () => {
  const view = toolbar({ tying: true, event: { ...note, tie_target_id: 'next' } })
  assert.equal(button(view.render(), 'Cancel tie').props['aria-pressed'], true)
  button(view.render(), 'Cancel tie').props.onClick(); assert.deepEqual(view.actions, ['tie'])
  button(view.render(), 'Remove tie').props.onClick()
  assert.deepEqual(plain(view.calls[0]), ['events/a', 'PATCH', { tie_to_event_id: null }])
  const normal = toolbar(); button(normal.render(), 'Lyric').props.onClick()
  assert.ok(find(normal.render(), e => e.type === './VisualNoteEditor' || e.props?.lyrics))
  button(normal.render(), 'More / Advanced').props.onClick(); assert.deepEqual(normal.actions, ['advanced'])
})

test('visible Tie Up and Tie Down use only direction PATCH and reflect canonical state', () => {
  const selected = { ...note, tie_target_id: 'next', tie_direction_editable: true, tie_direction: 'up' }
  const view = toolbar({ event: selected })
  assert.equal(button(view.render(), 'Tie Up').props['aria-pressed'], true)
  for (const [label, direction] of [['Tie Down', 'down'], ['Tie Up', 'up']]) {
    button(view.render(), label).props.onClick()
    assert.deepEqual(plain(view.calls.at(-1)), ['events/a', 'PATCH', { tie_direction: direction }])
  }
  const tree = view.render({ ...view.props, event: { ...selected, id: 'new-1', tie_direction: 'down' } })
  assert.equal(button(tree, 'Tie Down').props['aria-pressed'], true)
  button(tree, 'Tie Up').props.onClick()
  assert.deepEqual(plain(view.calls.at(-1)), ['events/new-1', 'PATCH', { tie_direction: 'up' }])
  button(tree, 'Tie Down').props.onClick()
  assert.deepEqual(plain(view.calls.at(-1)), ['events/new-1', 'PATCH', { tie_direction: 'down' }])
})

test('direction buttons stay visible without eligibility metadata and defer identity validation to backend', () => {
  for (const eligibility of [undefined, false, true]) {
    const view = toolbar({ event: { ...note, tie_target_id: 'next', tie_direction_editable: eligibility } })
    for (const label of ['Tie Up', 'Tie Down']) {
      const control = button(view.render(), label)
      assert.equal(control.props.disabled, false)
      control.props.onClick()
    }
    assert.deepEqual(plain(view.calls), [
      ['events/a', 'PATCH', { tie_direction: 'up' }], ['events/a', 'PATCH', { tie_direction: 'down' }],
    ])
  }
  for (const props of [{ event: undefined }, { event: { ...note, kind: 'rest', pitch: null } },
    { adding: true }, { tying: true }, { disabled: true }, { readOnly: true }]) {
    const tree = toolbar(props).render()
    for (const label of ['Tie Up', 'Tie Down']) assert.equal(button(tree, label).props.disabled, true)
  }
  assert.equal(field(toolbar().render(), 'Temporary tie toolbar diagnostic'), null)
})

test('Transposed and busy states disable mutations and hide corrected-property popovers', () => {
  const view = toolbar(); button(view.render(), 'Pitch').props.onClick()
  const tree = view.render({ ...view.props, readOnly: true })
  for (const label of ['Add note', 'Delete selected notation', 'Pitch', 'Duration', 'Accidental', 'Normal / Small', 'Duration-bearing / Grace', 'Tie', 'Lyric', 'Undo', 'Redo', 'More / Advanced']) assert.equal(button(tree, label).props.disabled, true)
  assert.equal(field(tree, 'Note pitch'), null)
  assert.equal(button(toolbar({ disabled: true }).render(), 'Select').props.disabled, true)
})

function renderer(empty = false, page = 1) {
  const instrument = { Staves: [] }; const staff = { ParentInstrument: instrument }; instrument.Staves.push(staff)
  const source = {}
  const entry = (x, time) => ({ PositionAndShape: { AbsolutePosition: { x, y: 20 } }, relInMeasureTimestamp: { RealValue: time / 4 }, graphicalVoiceEntries: [{ notes: [{ sourceNote: { SourceMeasure: source } }] }] })
  const graphical = { ParentStaff: staff, parentSourceMeasure: source, ParentMusicSystem: { Parent: { PageNumber: page } },
    beginInstructionsWidth: 2, endInstructionsWidth: 0, PositionAndShape: { AbsolutePosition: { x: 10, y: 20 }, BorderLeft: 0, BorderRight: 20 }, staffEntries: empty ? [] : [entry(15,0), entry(25,2)] }
  const osmd = { Sheet: { Instruments: [instrument], SourceMeasures: [source] }, EngravingRules: { StaffHeight: 4 }, GraphicSheet: { MeasureList: [[graphical]] } }
  const semantic = empty ? { ...measure, voices: [] } : { ...measure, voices: [{ id: '1', events: [note, { ...note, id: 'next', onset: '2' }] }] }
  return { osmd, score: { parts: [{ measures: [semantic] }] }, graphical }
}

test('empty-measure hit resolves only explicit start, independent of meter and width', () => {
  const fixture = renderer(true); const before = plain(fixture.score)
  const lanes = geometry.insertionLanes(fixture.osmd, fixture.score)
  assert.equal(lanes.length, 1); assert.equal(lanes[0].onset, '0')
  const hit = geometry.hitInsertion(lanes, 1, { x: 23, y: 22 })
  assert.equal(hit.measureId, 'm1'); assert.equal(hit.staff, 1)
  assert.equal(geometry.hitInsertion(lanes, 2, { x: 23, y: 22 }), null)
  assert.equal(geometry.hitInsertion(lanes, 1, { x: 11, y: 22 }), null) // clef/instruction area
  assert.equal(geometry.hitInsertion(lanes, 1, { x: 23, y: 32 }), null) // lyrics
  assert.deepEqual(plain(fixture.score), before)
})

test('populated hits use canonical rendered onsets and reject gaps and overlapping ownership', () => {
  const fixture = renderer(); const lanes = geometry.insertionLanes(fixture.osmd, fixture.score)
  assert.deepEqual(plain(lanes.map(l => l.onset)), ['0','2'])
  assert.equal(geometry.hitInsertion(lanes,1,{x:25,y:22}).onset,'2')
  assert.equal(geometry.hitInsertion(lanes,1,{x:20,y:22}),null)
  assert.equal(geometry.hitInsertion([...lanes,...lanes],1,{x:25,y:22}),null)
  fixture.graphical.staffEntries[1].relInMeasureTimestamp.RealValue=3/4 // renderer timing not in canonical model
  assert.deepEqual(plain(geometry.insertionLanes(fixture.osmd,fixture.score).map(l=>l.onset)), ['0'])
})

test('SVG point conversion inverts Fit zoom viewBox offset and scroll', () => {
  for (const scale of [.25,.5,1,2]) {
    const svg = { getScreenCTM: () => ({ inverse: () => ({ scale, x: 130, y: -70 }) }), createSVGPoint: () => ({ x:0,y:0,matrixTransform(m) { return { x:(this.x-m.x)/m.scale, y:(this.y-m.y)/m.scale } } }) }
    assert.deepEqual(plain(geometry.scorePoint(svg,130+250*scale,-70+220*scale,10)), {x:25,y:22})
  }
  assert.equal(geometry.scorePoint({getScreenCTM:()=>null},1,1,10),null)
})

test('insertion marker lives in the same SVG, is UI-only and is removable', () => {
  const nodes=[]
  const document = { createElementNS(namespaceURI,name) { const node={namespaceURI,name,attributes:{},children:[],setAttribute(k,v){this.attributes[k]=v},appendChild(n){this.children.push(n)},remove(){this.removed=true}};nodes.push(node);return node } }
  const adapter=load('../src/utils/scoreInsertion.ts',{'./visualReview':helpers},{document})
  const svg={children:[],appendChild(n){this.children.push(n)}}
  const lane=geometry.insertionLanes(renderer(true).osmd,renderer(true).score)[0]
  const remove=adapter.drawInsertionMarker(svg,lane,10)
  assert.equal(svg.children[0].attributes['data-insertion-marker'],'true')
  assert.equal(svg.children[0].attributes['pointer-events'],'none')
  assert.match(nodes[1].attributes.d,/V 245/)
  remove();assert.equal(svg.children[0].removed,true)
  const css=readFileSync(new URL('../src/index.css',import.meta.url),'utf8')
  assert.match(css,/\.score-insertion-caret\s*\{[^}]*vector-effect: non-scaling-stroke/)
})

test('normal workspace starts unselected; toolbar precedes score inside right pane; Advanced survives', () => {
  const view=harness('../src/components/RecognitionReview.tsx',{review,onChange(){},onBusy(){},download(){}})
  let tree=view.render();const pane=find(tree,e=>e.props?.className==='review-score')
  assert.ok(pane)
  const tools=find(pane,e=>e.type==='./ScoreCorrectionToolbar')
  assert.equal(tools.props.event,undefined)
  assert.equal(find(pane,e=>e.type==='./MusicSheetViewer').props.selection,null)
  assert.equal(find(tree,e=>e.type==='./VisualNoteEditor'),null)
  assert.ok(find(tree,e=>e.type==='./SourceViewer'))
  tools.props.add();tree=view.render()
  const viewer=find(tree,e=>e.type==='./MusicSheetViewer')
  assert.equal(viewer.props.insertionMode,true)
  viewer.props.onPositionSelect({measureId:'m1',staff:1,onset:'0'})
  assert.equal(find(view.render(),e=>e.type==='./ScoreCorrectionToolbar').props.position.onset,'0')
  find(view.render(),e=>e.type==='./ScoreCorrectionToolbar').props.select()
  assert.equal(find(view.render(),e=>e.type==='./MusicSheetViewer').props.insertionPosition,null)
  find(view.render(),e=>e.type==='./MusicSheetViewer').props.onSelect('a')
  find(view.render(),e=>e.type==='./ScoreCorrectionToolbar').props.advanced()
  assert.equal(find(view.render(),e=>e.type==='./VisualNoteEditor').props.event.id,'a')
})

test('SVG backend canvas wrapper resolves the actual drawing and its page identity', () => {
  const svg = { localName: 'svg' }
  const osmd = { Drawer: { Backends: [{ graphicalMusicPage: { PageNumber: 3 }, getCanvas: () => ({ localName: 'div', querySelector: name => { assert.equal(name,'svg'); return svg } }) }] } }
  const pages = geometry.renderedScorePages(osmd)
  assert.equal(pages[0].svg,svg); assert.equal(pages[0].page,3)
  assert.deepEqual(plain(geometry.renderedScorePages({ Drawer:{ Backends:[{ graphicalMusicPage:{PageNumber:1},getCanvas:()=>({localName:'div',querySelector:()=>null}) }] } })),[])
})

test('viewer click connects real page wrapper geometry to marker, suppresses note edits in Add and clears on mode changes', async () => {
  const fixture = renderer(true)
  const nodes = []; const hits = []; const selections = []; const highlights = []
  const document = { createElementNS(namespaceURI,name) { const node = { namespaceURI,name,attributes:{},children:[],setAttribute(k,v){this.attributes[k]=v},appendChild(n){this.children.push(n)},remove(){this.removed=true} }; nodes.push(node); return node } }
  let scale=.5
  const svg={localName:'svg',children:[],appendChild(n){this.children.push(n)},getScreenCTM:()=>({inverse:()=>({scale,x:100,y:50})}),createSVGPoint:()=>({x:0,y:0,matrixTransform(m){return {x:(this.x-m.x)/m.scale,y:(this.y-m.y)/m.scale}}})}
  const wrapper={localName:'div',querySelector:()=>svg}
  let diagnostics=false
  const records=[]
  const adapters=load('../src/utils/scoreInsertion.ts',{'./visualReview':helpers},{document,
    process:{env:{NODE_ENV:'development'}},localStorage:{getItem:()=>diagnostics?'1':null},
    console:{debug:(label,record)=>records.push({label,...plain(record)})}})
  const states=[];const effects=[];const scheduled=[];let slot=0, renderCount=0, selectHead
  const jsx=(type,props)=>({type,props})
  const module=load('../src/components/MusicSheetViewer.tsx',{
    react:{
      useState(initial){const i=slot++;if(!(i in states))states[i]=initial;return [states[i],v=>{states[i]=v}]},
      useRef(initial){const i=slot++;if(!(i in states))states[i]={current:initial};return states[i]},
      useEffect(fn,deps){const i=slot++;const previous=effects[i];if(!previous||deps.some((d,j)=>d!==previous.deps[j]))scheduled.push(()=>{previous?.cleanup?.();effects[i]={deps,cleanup:fn()}})},
    },'react/jsx-runtime':{jsx,jsxs:jsx},
    opensheetmusicdisplay:{OpenSheetMusicDisplay:class{
      constructor(){Object.assign(this,fixture.osmd);this.Drawer={Backends:[{graphicalMusicPage:{PageNumber:1},getCanvas:()=>wrapper}],calculatePixelDistance:()=>10};this.cursor={hide(){},reset(){},iterator:{EndReached:true}}}
      async load(){} render(){renderCount++} updateGraphic(){}
    }},
    '../utils/sourceEngraving':{initialEngravingWidth:1000,trustedSourceGroups:()=>[[0]],sourceEngravingWidth:()=>1000,engraveSourceGroups(osmd,groups,width,seed){width(seed);osmd.render();return {width:seed,matched:true}}},
    '../utils/scoreRenderer':{rendererOptions:()=>({}),reviewDocument:d=>d,bindRenderer(osmd,score,select){selectHead=select;return {highlight:(...args)=>highlights.push(args),dispose(){}}}},
    '../utils/scoreInsertion':adapters,
    '../utils/visualReview':helpers,
  },{console,DOMParser:class{parseFromString(){return {}}},ResizeObserver:class{observe(){}disconnect(){}}})
  const blob={text:async()=>'<score-partwise/>'};const container={innerHTML:'',clientWidth:1000,style:{}}
  const onSelect=id=>selections.push(id),onPositionSelect=p=>hits.push(p)
  function render(mode=true,position=null,interactive=true){
    slot=0
    const tree=module.default({musicXml:blob,score:fixture.score,onSelect,onPositionSelect,insertionMode:mode,insertionPosition:position,interactive,selection:{eventId:'a',measureIndex:0,onset:'0',label:'Selected A'}})
    find(tree,e=>e.props?.ref).props.ref.current=container
    scheduled.splice(0).forEach(fn=>fn())
    return tree
  }
  render();await new Promise(setImmediate)
  assert.equal(renderCount,1)
  let tree=render()
  const click=find(tree,e=>e.props?.onClick && e.props?.ref)
  click.props.onClick({target:{closest:selector=>selector==='svg'?svg:null},clientX:100+230*scale,clientY:50+220*scale})
  assert.deepEqual(plain(hits[0]),{measureId:'m1',staff:1,onset:'0'})
  tree=render(true,hits[0])
  assert.ok(nodes.some(n=>n.attributes['data-insertion-marker']==='true'&&!n.removed))
  assert.deepEqual(plain(highlights.at(-1)),['a',null]) // Marker coexists with existing-note highlight.
  selectHead('a');assert.deepEqual(selections,[])
  scale=2
  find(tree,e=>e.props?.onClick && e.props?.ref).props.onClick({target:{closest:selector=>selector==='svg'?svg:null},clientX:100+230*scale,clientY:50+220*scale})
  assert.deepEqual(plain(hits[1]),plain(hits[0]))
  render(false,null);selectHead('a');assert.deepEqual(selections,['a'])
  assert.ok(nodes.filter(n=>n.attributes['data-insertion-marker']).every(n=>n.removed))
  const count=hits.length
  tree=render(true,null,false)
  find(tree,e=>e.props?.onClick && e.props?.ref).props.onClick({target:{closest:()=>svg},clientX:560,clientY:490})
  assert.equal(hits.length,count)
  assert.equal(renderCount,1) // Modes/markers/zoom do not change source engraving.

  // P0.6A.3: exact canonical anchor, independent of screen coordinates and lanes.
  const anchored={...note,id:'clicked',onset:'3/2',voice:'2',lyric_ids:['lyric'],tie_target_ids:['target']}
  fixture.score.parts[0].measures[0].voices=[{id:'2',events:[anchored]}]
  const before=JSON.stringify(fixture.score)
  const eventClick=(id,x=-999,y=-999)=>({target:{closest:selector=>selector==='[data-review-event]'
    ? {getAttribute:()=>id} : selector==='svg'?svg:null},clientX:x,clientY:y})
  const invoke=(event)=>find(tree,e=>e.props?.onClick && e.props?.ref).props.onClick(event)
  tree=render(true)
  invoke(eventClick('clicked'))
  assert.deepEqual(plain(hits.at(-1)),{measureId:'m1',staff:1,onset:'3/2'})
  assert.equal(records.length,0)
  assert.deepEqual(selections,['a']) // No note selection or edit callback in Add mode.
  assert.equal(JSON.stringify(fixture.score),before) // Pitch, duration, lyrics, ties unchanged.
  assert.equal(renderCount,1)

  diagnostics=true
  const prior=hits.length
  invoke(eventClick('clicked'))
  assert.equal(hits.length,prior+1)
  assert.deepEqual(plain(hits.at(-1)),{measureId:'m1',staff:1,onset:'3/2'})
  assert.equal(records.length,1)
  assert.equal(records[0].targetCategory,'note event')
  assert.equal(records[0].result,'event-intercepted') // Existing diagnostic classification retained.
  assert.equal(records[0].hitCount,0)
  diagnostics=false

  invoke(eventClick('missing'));assert.equal(hits.at(-1),null)
  fixture.score.parts[0].measures[0].voices.push({id:'3',events:[{...anchored,voice:'3'}]})
  invoke(eventClick('clicked'));assert.equal(hits.at(-1),null) // Duplicate canonical identity.
  fixture.score.parts[0].measures[0].voices.pop()
  anchored.onset=null
  invoke(eventClick('clicked'));assert.equal(hits.at(-1),null)
  anchored.onset='3/2';anchored.staff=null
  invoke(eventClick('clicked'));assert.equal(hits.at(-1),null)
  anchored.staff=1

  // Non-pitched events retain the whitespace path, including empty measures.
  fixture.score.parts[0].measures[0].voices=[{id:'1',events:[{...note,id:'rest',kind:'rest',pitch:null}]}]
  const populated=renderer()
  fixture.graphical.staffEntries=populated.graphical.staffEntries
  fixture.graphical.parentSourceMeasure=populated.graphical.parentSourceMeasure
  fixture.osmd.Sheet.SourceMeasures=[populated.graphical.parentSourceMeasure]
  invoke(eventClick('rest',100+150*scale,50+220*scale))
  assert.deepEqual(plain(hits.at(-1)),{measureId:'m1',staff:1,onset:'0'})
  const populatedHit=plain(hits.at(-1))
  invoke({target:{closest:selector=>selector==='svg'?svg:null},clientX:100+150*scale,clientY:50+220*scale})
  assert.deepEqual(plain(hits.at(-1)),populatedHit)

  tree=render(false)
  const selectCount=hits.length
  invoke(eventClick('rest'))
  assert.equal(hits.length,selectCount)
  selectHead('clicked')
  assert.deepEqual(selections,['a','clicked'])
  effects.forEach(effect=>effect?.cleanup?.())
})

test('musical value symbols map to exact durations for Add and selected-note correction', () => {
  for (const [label, duration] of [['Eighth note','1/2'], ['Quarter note','1'], ['Half note','2'], ['Whole note','4']]) {
    const add = toolbar({ adding:true, position:{measureId:'m1',staff:1,onset:'0'} })
    assert.equal(field(add.render(), 'Note duration'), null)
    const symbol = button(add.render(),label)
    assert.equal(symbol.props.title,label)
    symbol.props.onClick()
    assert.equal(button(add.render(),label).props['aria-pressed'],true)
    button(add.render(),'Add').props.onClick()
    assert.equal(add.calls[0][2].duration,duration)
    const edit = toolbar()
    button(edit.render(),'Duration').props.onClick()
    button(edit.render(),label).props.onClick()
    assert.deepEqual(plain(edit.calls[0]),['events/a','PATCH',{duration,duration_scope:'note',preserve_onsets:true}])
  }
})

test('no explicit accidental follows B-flat key; symbols toggle printed signs independently', () => {
  const keyed = {...measure,key_signature:[{staff:null,fifths:'-1'}]}
  for (const [step,alter] of [['A','0'],['B','-1']]) {
    const view=toolbar({adding:true,position:{measureId:'m1',staff:1,onset:'0'},review:{...review,score:{...score,parts:[{measures:[keyed]}]}}})
    field(view.render(),'Note pitch').props.onChange({target:{value:step}})
    assert.equal(field(view.render(),'Note accidental').type,'div')
    for (const label of ['Double flat','Flat','Natural','Sharp','Double sharp']) assert.equal(button(view.render(),label).props['aria-pressed'],false)
    button(view.render(),'Add').props.onClick()
    assert.deepEqual(plain(view.calls.at(-1)[2].pitch),{step,octave:4,alter})
    assert.equal(view.calls.at(-1)[2].written_accidental,null)
    for (const [label,spelling,value] of [['Double flat','flat-flat','-2'],['Flat','flat','-1'],['Natural','natural','0'],['Sharp','sharp','1'],['Double sharp','double-sharp','2']]) {
      button(view.render(),label).props.onClick()
      button(view.render(),'Add').props.onClick()
      assert.equal(view.calls.at(-1)[2].written_accidental,spelling)
      assert.equal(view.calls.at(-1)[2].pitch.alter,value)
      button(view.render(),label).props.onClick()
      button(view.render(),'Add').props.onClick()
      assert.equal(view.calls.at(-1)[2].written_accidental,null)
      assert.equal(view.calls.at(-1)[2].pitch.alter,alter)
    }
  }
})

test('selected source accidental is active and clearing returns pitch to key context', () => {
  const view=toolbar({event:{...note,pitch:{step:'B',octave:4,alter:'0'},accidental:{text:'natural'}},measure:{...measure,key_signature:[{staff:null,fifths:'-1'}]}})
  button(view.render(),'Accidental').props.onClick()
  assert.equal(button(view.render(),'Natural').props['aria-pressed'],true)
  button(view.render(),'Natural').props.onClick()
  button(view.render(),'Apply accidental').props.onClick()
  assert.deepEqual(plain(view.calls[0][2]),{pitch:{step:'B',octave:4,alter:'-1'},written_accidental:null})
})

test('existing sharp can be explicitly cleared after Apply and palette remount without selecting natural', () => {
  const key = [{staff:null,fifths:'-1'}]
  for (const [step,followAlter] of [['A','0'],['B','-1']]) {
    const selectedNote={...note,pitch:{step,octave:4,alter:followAlter},accidental:{text:null},key_signature:key}
    const initial=toolbar({event:selectedNote})
    button(initial.render(),'Accidental').props.onClick()
    button(initial.render(),'Sharp').props.onClick()
    button(initial.render(),'Apply accidental').props.onClick()
    assert.deepEqual(plain(initial.calls[0][2]),{pitch:{step,octave:4,alter:'1'},written_accidental:'sharp'})
    // Applying a correction increments the revision and remounts the toolbar in the workspace.
    const appliedNote={...selectedNote,pitch:initial.calls[0][2].pitch,accidental:{text:'sharp'}}
    const applied=toolbar({event:appliedNote,review:{...review,revision:2}})
    button(applied.render(),'Accidental').props.onClick()
    assert.equal(button(applied.render(),'Sharp').props['aria-pressed'],true)
    assert.equal(button(applied.render(),'Clear accidental').props.disabled,false)
    button(applied.render(),'Clear accidental').props.onClick()
    for (const sign of ['Double flat','Flat','Natural','Sharp','Double sharp']) assert.equal(button(applied.render(),sign).props['aria-pressed'],false)
    assert.ok(find(applied.render(),e=>e.props?.role==='status' && e.props.children==='Follow key context'))
    button(applied.render(),'Apply accidental').props.onClick()
    assert.deepEqual(plain(applied.calls[0][2]),{pitch:{step,octave:4,alter:followAlter},written_accidental:null})
    const cleared=toolbar({event:{...selectedNote,pitch:applied.calls[0][2].pitch},review:{...review,revision:3}})
    button(cleared.render(),'Accidental').props.onClick()
    assert.ok(find(cleared.render(),e=>e.props?.role==='status' && e.props.children==='Follow key context'))
    assert.equal(button(cleared.render(),'Clear accidental').props.disabled,true)
    if (step==='B') {
      button(cleared.render(),'Natural').props.onClick()
      button(cleared.render(),'Apply accidental').props.onClick()
      assert.deepEqual(plain(cleared.calls[0][2]),{pitch:{step:'B',octave:4,alter:'0'},written_accidental:'natural'})
    }
  }
})

test('clear action leaves Add note accidentals and default key semantics working', () => {
  const view=toolbar({adding:true,position:{measureId:'m1',staff:1,onset:'0'}})
  button(view.render(),'Sharp').props.onClick()
  button(view.render(),'Add').props.onClick()
  assert.equal(view.calls[0][2].written_accidental,'sharp')
  button(view.render(),'Clear accidental').props.onClick()
  button(view.render(),'Add').props.onClick()
  assert.equal(view.calls[1][2].written_accidental,null)
  assert.equal(view.calls[1][2].pitch.alter,'0')
})

test('add-note exact anchor is explicit and retains duration, size and voice choices',async()=>{
  let anchored=0
  const view=toolbar({adding:true,anchorPosition:()=>anchored++})
  button(view.render(),'Use selected note’s exact onset').props.onClick()
  assert.equal(anchored,1)
  const position={measureId:measure.id,staff:note.staff,onset:'1/3'}
  let tree=view.render({...view.props,position})
  field(tree,'New note size').props.onChange({target:{value:'small'}})
  button(tree,'Eighth note').props.onClick()
  tree=view.render()
  await button(tree,'Add').props.onClick()
  const body=view.calls[0][2]
  assert.equal(body.onset,'1/3')
  assert.equal(body.voice,note.voice)
  assert.equal(body.duration,'1/2')
  assert.equal(body.display_size,'small')
  assert.equal(body.grace,false)
})
