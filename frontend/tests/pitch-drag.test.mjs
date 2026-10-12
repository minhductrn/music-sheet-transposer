import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import vm from 'node:vm'
import ts from 'typescript'
function load(path, dependencies = {}, globals = {}) {
  const module = { exports: {} }
  vm.runInNewContext(ts.transpileModule(readFileSync(new URL(path, import.meta.url), 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText,
    { module, exports: module.exports, require: n => dependencies[n], ...globals })
  return module.exports
}
const helpers = load('../src/utils/visualReview.ts')
const geometry = load('../src/utils/scoreInsertion.ts', { './visualReview': helpers })
const document = { createElementNS: (namespaceURI) => ({ namespaceURI, setAttribute() {}, appendChild() {}, remove() {} }) }
const drag = load('../src/utils/pitchDrag.ts', { './visualReview': helpers, './scoreInsertion': geometry }, { document })
const clef = (sign = 'G', line = '2', shift) => ({ fields: [{ name: 'sign', text: sign }, { name: 'line', text: line }, ...(shift ? [{ name: 'clef-octave-change', text: shift }] : [])] })
const event = { id: 'same', kind: 'note', pitch: { step: 'C', octave: 4, alter: '0' }, clef: clef(), staff: 1, accidental: { text: null } }
const measure = { key_signature: [] }
const staff = { top: 20, spacing: 1, minY: 17, maxY: 27 }
const plain = v => JSON.parse(JSON.stringify(v))
for (const [y, step, octave] of [[25,'C',4],[24.5,'D',4],[24,'E',4],[21.5,'C',5],[26,'A',3]]) test(`treble Y=${y} snaps to ${step}${octave}`, () => {
  assert.deepEqual(plain(drag.resolveDragPitch(event, measure, staff, y)), { step, octave, alter: '0' })
})
test('effective bass, alto, tenor and octave clefs', () => {
  for (const [sign,line,bottom] of [['F','4',18],['C','3',24],['C','4',22],['G','2',30]]) assert.equal(drag.clefBottom(clef(sign,line)),bottom)
  assert.equal(drag.clefBottom(clef('G','2','-1')),23)
  assert.equal(drag.resolveDragPitch({ ...event, clef: clef('F','4') }, measure, staff,24).step,'G')
})
test('missing/ambiguous context, outside staff and overlapping staff fail safely', () => {
  for (const context of [null,clef('percussion'),{ fields: [...clef().fields, ...clef().fields] }]) assert.equal(drag.resolveDragPitch({...event,clef:context},measure,staff,22),null)
  assert.equal(drag.resolveDragPitch(event,measure,staff,100),null)
  assert.equal(drag.resolveDragPitch(event,measure,staff,22,[staff]),null)
  assert.equal(drag.resolveDragPitch(event,measure,{...staff,spacing:0},22),null)
})
test('NONE follows destination key; explicit natural/sharp/flat carry alteration', () => {
  const keyed = { key_signature: [{ staff:null, fifths:'1' }] }
  assert.equal(drag.resolveDragPitch(event,keyed,staff,23.5).alter,'1') // F4
  for (const [text,alter] of [['natural','0'],['sharp','1'],['flat','-1']]) {
    const e = {...event,accidental:{text},pitch:{...event.pitch,alter}}
    assert.equal(drag.resolveDragPitch(e,keyed,staff,23.5).alter,alter)
    assert.equal(e.accidental.text,text)
  }
  assert.equal(event.accidental.text,null)
})
function harness(scale = 1) {
  const handlers = new Map(), commits = [], selected = []
  let captured = false, enabled = true
  const node = { style:{touchAction:''}, addEventListener(n,f){ handlers.set(n,f) }, removeEventListener(n){handlers.delete(n)}, setPointerCapture(){captured=true},hasPointerCapture(){return captured},releasePointerCapture(){captured=false} }
  const svg = { getScreenCTM: () => ({inverse: () => ({scale})}), createSVGPoint(){return {x:0,y:0,matrixTransform(m){return {x:this.x / m.scale,y:this.y / m.scale}}}},appendChild(){} }
  const before = JSON.stringify(event)
  const cleanup = drag.bindPitchDrag(node,svg,10,event,measure,staff,[],10,{enabled:()=>enabled,select:()=>selected.push(event.id),commit:p=>commits.push(plain(p))})
  function send(type,y,x=100) { handlers.get(type)?.({type,clientY:y,clientX:x,pointerId:1,isPrimary:true,button:0,preventDefault(){},stopImmediatePropagation(){}}) }
  return {send,commits,selected,cleanup,disable:()=>{enabled=false},before}
}
test('click, threshold, horizontal movement and no-op produce no edits', () => {
  for (const [y,x] of [[250,100],[254,100],[250,900]]) { const h=harness();h.send('pointerdown',250);h.send('pointermove',y,x);h.send('pointerup',y,x);assert.equal(h.commits.length,0);h.cleanup() }
  const h=harness();h.send('pointerdown',250);h.send('pointermove',215);h.send('pointerup',250);assert.equal(h.commits.length,0)
})
for (const scale of [.65,1,1.5]) test(`Fit/zoom ${scale} emits one C5 edit, independent of horizontal displacement`, () => {
  const h=harness(scale);h.send('pointerdown',250*scale)
  for (const y of [245,235,225,215]) h.send('pointermove',y*scale,900)
  assert.equal(h.commits.length,0)
  h.send('pointerup',215*scale,1200)
  assert.deepEqual(h.commits,[{step:'C',octave:5,alter:'0'}]);assert.equal(h.selected.length,1)
  assert.equal(JSON.stringify(event),h.before);h.cleanup()
})
test('invalid release, cancellation, lost capture and disabled interaction never patch', () => {
  for (const type of ['pointercancel','lostpointercapture','pointerup']) { const h=harness();h.send('pointerdown',250);h.send('pointermove',215);h.send(type,500);assert.equal(h.commits.length,0);h.cleanup() }
  const h=harness();h.send('pointerdown',250);h.send('pointermove',215);h.disable();h.send('pointerup',215);assert.equal(h.commits.length,0)
})

test('renderer adapter binds drag to the same uniquely mapped canonical event and staff geometry', () => {
  const handlers = new Map(), commits = []
  let captured = false
  const svg = { getScreenCTM:()=>({inverse:()=>({scale:1})}),createSVGPoint(){return {x:0,y:0,matrixTransform(){return {x:this.x,y:this.y}}}},appendChild(){} }
  const node = { style:{touchAction:''},dataset:{},closest:()=>svg,setAttribute(){},removeAttribute(){},classList:{toggle(){}},
    addEventListener(n,f,capture){handlers.set(`${n}-${!!capture}`,f)},removeEventListener(){},setPointerCapture(){captured=true},hasPointerCapture(){return captured},releasePointerCapture(){captured=false} }
  const adapter = load('../src/utils/scoreInteraction.ts', { './scoreTies': { drawCorrectionTies: () => () => {} }, './pitchDrag':drag,'./visualReview':helpers,opensheetmusicdisplay:{Pitch:{getNoteEnumString:s=>s,OctaveXmlDifference:3}} })
  const instrument={Staves:[]}, sourceStaff={ParentInstrument:instrument,isTab:false,StafflineCount:5};instrument.Staves.push(sourceStaff)
  const sourceMeasure={}
  const staffLine={ParentStaff:sourceStaff,StaffLines:Array.from({length:5},(_,i)=>({Start:{y:i},End:{y:i}})),PositionAndShape:{AbsolutePosition:{y:20}},ParentMusicSystem:{Parent:{PageNumber:1}}}
  const note={ParentStaff:sourceStaff,ParentVoiceEntry:{ParentVoice:{VoiceId:1},Timestamp:{RealValue:0}},SourceMeasure:sourceMeasure,Pitch:{FundamentalNote:'C',Octave:1,AccidentalHalfTones:0},Length:{RealValue:.5},IsGraceNote:false,isRest:()=>false}
  const graphical={sourceNote:note,PositionAndShape:{AbsolutePosition:{x:10,y:25}},getNoteheadSVGs:()=>[node],vfnoteIndex:0}
  const gMeasure={ParentStaffLine:staffLine,parentSourceMeasure:sourceMeasure,staffEntries:[{graphicalVoiceEntries:[{notes:[graphical]}]}]}
  const e={...event,voice:'1',onset:'0',duration:'2',grace:false}
  const m={...measure,id:'m',index:0,voices:[{events:[e]}]}
  const osmd={Sheet:{Instruments:[instrument],SourceMeasures:[sourceMeasure]},GraphicSheet:{MeasureList:[[gMeasure]]},Drawer:{calculatePixelDistance:()=>10}}
  const binding=adapter.bindScore(osmd,{parts:[{measures:[m]}]},()=>{}, {enabled:()=>true,commit:(id,pitch)=>commits.push({id,pitch:plain(pitch)})})
  const send=(type,y)=>handlers.get(`${type}-false`)?.({type,pointerId:1,isPrimary:true,button:0,clientX:999,clientY:y,preventDefault(){}})
  send('pointerdown',250);send('pointermove',215);send('pointerup',215)
  assert.deepEqual(commits,[{id:'same',pitch:{step:'C',octave:5,alter:'0'}}])
  assert.equal(node.dataset.reviewEvent,'same');binding.dispose()
  // A graphical note inconsistent with canonical clef/pitch is selectable but not draggable.
  handlers.clear();graphical.PositionAndShape.AbsolutePosition.y=22
  adapter.bindScore(osmd,{parts:[{measures:[m]}]},()=>{}, {enabled:()=>true,commit(){throw Error('unsafe edit')}})
  assert.equal(handlers.has('pointerdown-false'),false)
  assert.equal(handlers.has('click-false'),true)
})

test('unsupported explicit accidental fails safely and a return to original position retains sounding pitch', () => {
  assert.equal(drag.resolveDragPitch({...event,accidental:{text:'quarter-sharp'},pitch:{...event.pitch,alter:'1/2'}},measure,staff,21.5),null)
  assert.equal(drag.resolveDragPitch({...event,pitch:{...event.pitch,alter:'1'}},measure,staff,25).alter,'1')
})
