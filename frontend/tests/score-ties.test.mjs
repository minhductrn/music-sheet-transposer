import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import vm from 'node:vm'
import ts from 'typescript'
function load(file, dependencies={}, globals={}) {
  const module={exports:{}}
  vm.runInNewContext(ts.transpileModule(readFileSync(new URL(file,import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText,
    {module,exports:module.exports,require:n=>dependencies[n],...globals})
  return module.exports
}
const geometry=load('../src/utils/scoreInsertion.ts')
function fixture(scale=1) {
  const paths=[]
  const document={createElementNS(){return {attributes:{},handlers:{},setAttribute(k,v){this.attributes[k]=v},addEventListener(k,f){this.handlers[k]=f},removeEventListener(k){delete this.handlers[k]},remove(){paths.splice(paths.indexOf(this),1)}}}}
  const svg={getScreenCTM:()=>({inverse:()=>({})}),createSVGPoint(){return{x:0,y:0,matrixTransform(){return{x:(this.x-100)/scale,y:(this.y-50)/scale}}}},appendChild:p=>paths.push(p)}
  const node=x=>({closest:()=>svg,getBoundingClientRect:()=>({left:100+x*scale,width:10*scale,bottom:50+40*scale-2})})
  const source={id:'a',tie_relationship:{source_event_id:'a',target_event_id:'b',origin:'USER_CORRECTION'}}
  const score={parts:[{measures:[{voices:[{events:[source,{id:'b'}]}]}]}]}
  const targets=[{id:'a',node:node(20)},{id:'b',node:node(90)}]
  return{...load('../src/utils/scoreTies.ts',{'./scoreInsertion':geometry},{document}),paths,score,targets}
}
for(const scale of [.5,1,1.5])test(`canonical correction renders exact endpoints at zoom ${scale} and disposes without XML changes`,()=>{
  const f=fixture(scale), selected=[];const before=JSON.stringify(f.score)
  const dispose=f.drawCorrectionTies(f.score,f.targets,id=>selected.push(id))
  assert.equal(f.paths.length,1)
  assert.match(f.paths[0].attributes.d,/^M 25 40 C .* 95 40$/)
  f.paths[0].handlers.click();assert.deepEqual(selected,['a'])
  f.paths[0].handlers.keydown({key:'Enter',preventDefault(){}});assert.deepEqual(selected,['a','a'])
  dispose();assert.equal(f.paths.length,0);assert.equal(JSON.stringify(f.score),before)
})
test('raw fragments and inferred target never create a canonical correction curve',()=>{
  const f=fixture();f.score.parts[0].measures[0].voices[0].events[0]={id:'a',ties:['start'],tie_target_id:'b'}
  f.drawCorrectionTies(f.score,f.targets,()=>{});assert.equal(f.paths.length,0)
})
test('unmapped or multiply mapped heads cannot draw a guessed relationship',()=>{
  for(const targets of [[],[...fixture().targets,{id:'a',node:{}}]]){
    const f=fixture();f.drawCorrectionTies(f.score,targets,()=>{});assert.equal(f.paths.length,0)
  }
})

test('viewing clone suppresses only owned native curves and preserves raw distinct markers and source XML',()=>{
  const f=fixture()
  f.score.parts[0].measures[0].voices[0].events[0].tie_relationship.source_visual_id='owned-start'
  f.score.parts[0].measures[0].voices[0].events[0].tie_relationship.target_visual_id='owned-stop'
  function doc(ids){
    const nodes=ids.map(id=>({getAttribute:()=>id}))
    const parent={removeChild:n=>nodes.splice(nodes.indexOf(n),1)}
    nodes.forEach(n=>n.parentNode=parent)
    return {nodes,getElementsByTagNameNS:()=>nodes,cloneNode:()=>doc(ids)}
  }
  const original=doc(['raw-number-2','owned-start','owned-stop'])
  const view=f.correctionTieDocument(original,f.score)
  assert.deepEqual(view.nodes.map(n=>n.getAttribute()),['raw-number-2'])
  assert.equal(original.nodes.length,3)
})

test('page-spanning explicit relationship renders removable endpoint continuation segments',()=>{
  const f=fixture(), extra=[]
  const svg={getBoundingClientRect:()=>({left:100,right:300}),getScreenCTM:()=>({inverse:()=>({})}),createSVGPoint(){return{x:0,y:0,matrixTransform(){return{x:this.x-100,y:this.y-50}}}},appendChild:p=>extra.push(p)}
  const originalSvg=f.targets[0].node.closest();originalSvg.getBoundingClientRect=()=>({left:100,right:300})
  f.targets[1].node.closest=()=>svg
  f.drawCorrectionTies(f.score,f.targets,()=>{})
  assert.equal(f.paths.length,1);assert.equal(extra.length,1)
  assert.equal(f.paths[0].attributes['data-correction-tie'],extra[0].attributes['data-correction-tie'])
  assert.match(f.paths[0].attributes.d,/^M 25 40 C .* 188 40$/)
  assert.match(extra[0].attributes.d,/^M 12 40 C .* 95 40$/)
})

test('two explicitly authored simultaneous ties have independent selectable curves and no inferred third tie',()=>{
  const f=fixture(), events=f.score.parts[0].measures[0].voices[0].events
  events[0].onset='0';events[0].staff=1;events[1].onset='1';events[1].staff=1
  events.push({...events[0],id:'c',tie_relationship:{source_event_id:'c',target_event_id:'d'}},
    {...events[1],id:'d'}, {id:'unlinked',onset:'0',staff:1})
  f.targets.push({id:'c',node:f.targets[0].node},{id:'d',node:f.targets[1].node})
  // Coincident heads are the worst collision case; actual heads supply scalable clearance.
  for(const target of f.targets){
    const bounds=target.node.getBoundingClientRect
    target.node.getBoundingClientRect=()=>({...bounds(),top:80})
  }
  const selected=[]
  const dispose=f.drawCorrectionTies(f.score,f.targets,id=>selected.push(id))
  assert.equal(f.paths.length,2)
  assert.notEqual(f.paths[0].attributes.d,f.paths[1].attributes.d)
  f.paths[1].handlers.click();assert.deepEqual(selected,['c'])
  dispose();assert.equal(f.paths.length,0)
})

for(const scale of [.5,1,1.5])for(const direction of ['up','down'])test(`explicit ${direction} geometry at zoom ${scale} preserves identity and selection`,()=>{
  const f=fixture(scale),selected=[]
  f.score.parts[0].measures[0].voices[0].events[0].tie_direction=direction
  for(const target of f.targets){
    const bounds=target.node.getBoundingClientRect
    target.node.getBoundingClientRect=()=>({...bounds(),top:50+30*scale+2})
  }
  const before=JSON.stringify(f.score)
  const dispose=f.drawCorrectionTies(f.score,f.targets,id=>selected.push(id))
  const values=f.paths[0].attributes.d.match(/-?\d+(?:\.\d+)?/g).map(Number)
  const y=direction==='up'?30:40
  assert.equal(values[1],y);assert.equal(values[7],y)
  assert.ok(direction==='up'?values[3]<y&&values[5]<y:values[3]>y&&values[5]>y)
  f.paths[0].handlers.click();assert.deepEqual(selected,['a'])
  assert.equal(JSON.stringify(f.score),before)
  dispose();assert.equal(f.paths.length,0)
})

test('Up uses above-head endpoints on both page continuation segments',()=>{
  const f=fixture(),extra=[]
  f.score.parts[0].measures[0].voices[0].events[0].tie_direction='up'
  for(const target of f.targets){const bounds=target.node.getBoundingClientRect;target.node.getBoundingClientRect=()=>({...bounds(),top:82})}
  const svg={getBoundingClientRect:()=>({left:100,right:300}),getScreenCTM:()=>({inverse:()=>({})}),
    createSVGPoint(){return{x:0,y:0,matrixTransform(){return{x:this.x-100,y:this.y-50}}}},appendChild:p=>extra.push(p)}
  f.targets[0].node.closest().getBoundingClientRect=()=>({left:100,right:300})
  f.targets[1].node.closest=()=>svg
  f.drawCorrectionTies(f.score,f.targets,()=>{})
  for(const path of [f.paths[0],extra[0]]){
    const values=path.attributes.d.match(/-?\d+(?:\.\d+)?/g).map(Number)
    assert.equal(values[1],30);assert.equal(values[7],30)
    assert.ok(values[3]<30&&values[5]<30)
  }
})
