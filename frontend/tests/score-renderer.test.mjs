import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import vm from 'node:vm'
import ts from 'typescript'

const module = { exports: {} }
vm.runInNewContext(ts.transpileModule(readFileSync(new URL('../src/utils/scoreRenderer.ts', import.meta.url), 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS },
}).outputText, { module, exports: module.exports, require: () => ({ bindScore: () => 'binding' }) })
const adapter = module.exports
const plain = (v) => JSON.parse(JSON.stringify(v))

for (const source of [true, false]) test(`${source ? 'source' : 'responsive'} renderer mode has explicit layout and no invented rests`, () => {
  const options = adapter.rendererOptions(source)
  assert.equal(options.newSystemFromXML, source)
  assert.equal(options.newPageFromXML, source)
  assert.equal(options.newSystemFromNewPageInXML, source)
  assert.equal(options.fillEmptyMeasuresWithWholeRest, 0)
  assert.equal(options.autoGenerateMultipleRestMeasuresFromRestMeasures, false)
  assert.equal(options.pageFormat, source ? 'Endless' : undefined)
})

function documentFixture() {
  const make = (localName, children = [], attributes = {}) => ({ localName, children, attributes,
    setAttribute(k, v) { this.attributes[k] = v },
    insertBefore(node) { this.children.unshift(node) },
    get firstChild() { return this.children[0] },
  })
  const notes = [make('note', [], { duration: '14', pitch: 'A4' }), make('note', [], { duration: '8', rest: 'true' })]
  const measures = notes.map((n) => make('measure', [n]))
  const original = { documentElement: { namespaceURI: 'urn:test', children: [make('part', measures)] } }
  original.cloneNode = () => {
    const copy = (node) => make(node.localName, node.children.map(copy), { ...node.attributes })
    return { documentElement: { namespaceURI: original.documentElement.namespaceURI, children: original.documentElement.children.map(copy) }, createElementNS: (_, name) => make(name) }
  }
  return original
}

test('OMR grouping adds view-only breaks without changing notes, rests, ties or original document', () => {
  const original = documentFixture()
  const before = plain(original)
  const score = { parts: [{ id: 'p', measures: [{ id: 'm1', index: 0 }, { id: 'm2', index: 1 }] }],
    layout: { origin: 'OMR_ORDERED_MEASURES', systems: [{ part_id: 'p', explicit_break_measure_id: 'm2', new_page: true }] } }
  const view = adapter.reviewDocument(original, score)
  assert.deepEqual(plain(original), before)
  const [m1, m2] = view.documentElement.children[0].children
  assert.equal(m1.children[0].attributes.duration, '14')
  assert.equal(m2.children[0].localName, 'print')
  assert.deepEqual(plain(m2.children[0].attributes), { 'new-system': 'yes', 'new-page': 'yes' })
  assert.equal(m2.children[1].attributes.duration, '8')
  assert.equal(m2.children[1].attributes.rest, 'true')
})

test('absent evidence does not fabricate print instructions', () => {
  const original = documentFixture()
  assert.deepEqual(plain(adapter.reviewDocument(original)), plain(original))
})

test('measure bounds map to semantic ownership and ambiguous/invalid hits fail safely', () => {
  const instrument = { Staves: [] }; const staff = { ParentInstrument: instrument }; instrument.Staves.push(staff)
  const sourceMeasure = {}
  const osmd = { Sheet: { Instruments: [instrument], SourceMeasures: [sourceMeasure] }, GraphicSheet: { MeasureList: [[{
    ParentStaff: staff, parentSourceMeasure: sourceMeasure,
    PositionAndShape: { AbsolutePosition: { x: 10, y: 20 }, BorderLeft: 0, BorderRight: 30, BorderTop: 0, BorderBottom: 10 },
  }]] } }
  const score = { parts: [{ measures: [{ id: 'm1', index: 0 }] }] }
  const regions = adapter.measureRegions(osmd, score)
  assert.equal(regions[0].coordinateSpace, 'OSMD_UNITS')
  assert.equal(adapter.hitMeasure(regions, { x: 12, y: 22 }).measureId, 'm1')
  assert.equal(adapter.hitMeasure([...regions, ...regions], { x: 12, y: 22 }), null)
  assert.equal(adapter.hitMeasure(regions, { x: 40, y: 22 }), null)
  assert.deepEqual(plain(adapter.measureRegions(osmd, { parts: [] })), [])
})


test('XML-origin rendering clone retains existing breaks and every authoritative musical field', () => {
  const original = documentFixture()
  const second = original.documentElement.children[0].children[1]
  second.children.unshift({ localName: 'print', attributes: { 'new-system': 'yes', 'new-page': 'yes' }, children: [] })
  const note = original.documentElement.children[0].children[0].children[0]
  Object.assign(note.attributes, { tie: 'start', lyric: 'đây', harmony: 'F7', voice: '2', staff: '1', onset: '0', time: '2/4', key: '-1', barline: 'regular' })
  const before = plain(original)
  const view = adapter.reviewDocument(original, { layout: { origin: 'MUSICXML_PRINT' } })
  assert.notEqual(view, original)
  assert.deepEqual(plain(view), before)
  assert.deepEqual(plain(original), before)
})

test('duration-bearing small display uses rhythmic renderer path while true cue/grace and canonical XML survive',()=>{
  function doc() {
    const make=(grace=false,cue=false)=>{
      const type={localName:'type',attrs:{size:'cue'},getAttribute(k){return this.attrs[k]},removeAttribute(k){delete this.attrs[k]}}
      const head={localName:'notehead',getAttribute:()=> 'small'}
      return {children:[type,head,{localName:'duration'},...(grace?[{localName:'grace'}]:[]),...(cue?[{localName:'cue'}]:[])],type}
    }
    const notes=[make(),make(true),make(false,true)]
    return {notes,documentElement:{children:[]},getElementsByTagNameNS:()=>notes,cloneNode:()=>doc()}
  }
  const original=doc(), view=adapter.reviewDocument(original,undefined,true)
  assert.equal(view.notes[0].type.attrs.size,undefined)
  assert.equal(view.notes[1].type.attrs.size,'cue')
  assert.equal(view.notes[2].type.attrs.size,'cue')
  assert.equal(original.notes[0].type.attrs.size,'cue')
  assert.equal(adapter.reviewDocument(original).notes[0].type.attrs.size,'cue')
})
