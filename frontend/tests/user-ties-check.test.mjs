import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import vm from 'node:vm'
import ts from 'typescript'
function load(path, deps={}, globals={}) {
  const module={exports:{}}
  vm.runInNewContext(ts.transpileModule(readFileSync(new URL(path,import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX}}).outputText,
    {module,exports:module.exports,require:n=>deps[n]??{__esModule:true,default:n},...globals})
  return module.exports
}
const utils=load('../src/utils/visualReview.ts')
function harness(path,initial,dependencies={}) {
  let props=initial,slot=0;const states=[]
  const jsx=(type,props,key)=>({type,props,key})
  const react={useState(value){const i=slot++;if(!(i in states))states[i]=value;return[states[i],v=>{states[i]=v}]},useRef(value){const i=slot++;if(!(i in states))states[i]={current:value};return states[i]}}
  const component=load(path,{react,'react/jsx-runtime':{jsx,jsxs:jsx},'../utils/visualReview':utils,'../utils/review':{eventLabel:e=>e.id,validDuration:()=>true},...dependencies}).default
  return{render(next=props){props=next;slot=0;return component(props)}}
}
function find(tree,match){if(!tree||typeof tree!=='object')return null;if(match(tree))return tree;for(const child of [tree.props?.children, tree.props?.headerActions, tree.props?.toolbar, tree.props?.context, tree.props?.moreControls].flat(Infinity)){const r=find(child,match);if(r)return r}return null}
const button=(tree,label)=>find(tree,e=>e.type==='button'&&(e.props.children===label||e.props['aria-label']===label))
const child=(tree,name)=>find(tree,e=>e.type===name)
const plain=v=>JSON.parse(JSON.stringify(v))
const note={id:'source',kind:'note',pitch:{step:'C',octave:4,alter:'0'},onset:'0',duration:'2',voice:'1',staff:1,grace:false,display_size:'normal',ties:[],lyric_ids:[],tie_target_id:null,tie_target_ids:['chosen','other'],divisions:'4'}
const target={...note,id:'chosen',pitch:{step:'G',octave:5,alter:'1'},onset:'3',voice:'2',tie_target_ids:['source'],tie_target_id:null}
const other={...target,id:'other'}
const measure={id:'measure',number:'1',index:0,divisions:'4',staves:1,key_signature:[],voices:[{id:'1',events:[note]},{id:'2',events:[target,other]}]}
const review={id:'review',revision:1,state:'REVIEW_REQUIRED',expires_at:9999999999,musicXml:{},can_undo:false,can_redo:false,review_issues:[],score:{parts:[{id:'p',name:'Part',measures:[measure]}],lyrics:[],harmonies:[],metadata:{credits:[]}},validation:{can_verify:true,error_count:0,warning_count:1,unresolved_issue_count:0,diagnostics:[{code:'measure_overfilled',category:'MUSIC_WARNING',severity:'WARNING',message:'Unusual measure.',blocking:false}]}}
function view(initial=review){const edits=[],changes=[],checks=[];let result={revision:initial.revision,diagnostics:initial.validation.diagnostics,warning_count:1,technical_error_count:0,truncated:false}
  const h=harness('../src/components/RecognitionReview.tsx',{review:initial,onChange:v=>changes.push(v),onBusy(){},download(){}},{'../services/api':{changeReview:async(r,...args)=>{edits.push({id:r.id,revision:r.revision,args:plain(args)});return {...r,revision:r.revision+1}},checkReviewMusic:async r=>{checks.push(r);return result}}})
  return{...h,edits,changes,checks,setResult:v=>{result=v},props:r=>({review:r,onChange:v=>changes.push(v),onBusy(){},download(){}})}
}
test('select source → Tie → explicit target makes exactly one relationship-only request',async()=>{
  const h=view();const before=JSON.stringify(review)
  child(h.render(),'./MusicSheetViewer').props.onSelect('source')
  child(h.render(),'./ScoreCorrectionToolbar').props.tie()
  let tree=h.render();const viewer=child(tree,'./MusicSheetViewer')
  assert.equal(viewer.props.selection.eventId,'source')
  assert.deepEqual(plain(viewer.props.tieTargetIds),['chosen','other'])
  viewer.props.onSelect('chosen')
  await new Promise(resolve=>setTimeout(resolve,0))
  assert.deepEqual(h.edits,[{id:'review',revision:1,args:['events/source','PATCH',{tie_to_event_id:'chosen'}]}])
  assert.equal(h.changes.length,1);assert.equal(JSON.stringify(review),before)
  assert.equal(child(h.render(),'./MusicSheetViewer').props.tieTargetIds,null)
})
test('Cancel tie makes no edit; unsafe/unlisted target cannot substitute an endpoint',()=>{
  const h=view();child(h.render(),'./MusicSheetViewer').props.onSelect('source');child(h.render(),'./ScoreCorrectionToolbar').props.tie()
  child(h.render(),'./MusicSheetViewer').props.onSelect('missing')
  assert.equal(h.edits.length,0)
  child(h.render(),'./ScoreCorrectionToolbar').props.select()
  assert.equal(child(h.render(),'./MusicSheetViewer').props.tieTargetIds,null)
  assert.equal(h.edits.length,0)
})
test('Tie toolbar eligibility uses backend technical capabilities, independent of music warnings',()=>{
  const calls=[]
  const props={review,event:note,measure,position:null,adding:false,tying:false,disabled:false,readOnly:false,change:async(...args)=>calls.push(plain(args)),select(){},add(){},tie(){calls.push('tie')},advanced(){}}
  const h=harness('../src/components/ScoreCorrectionToolbar.tsx',{...props,group:'tie'})
  assert.equal(button(h.render(),'Add tie').props.disabled,false)
  button(h.render(),'Add tie').props.onClick();assert.deepEqual(calls,['tie'])
  const unsafe={...props,event:{...note,tie_correction_error:'Distinct tie markings cannot be selected safely.',tie_target_ids:[]}}
  assert.equal(button(h.render({...unsafe,group:'tie'}),'Add tie').props.disabled,false)
  assert.ok(find(h.render(),e=>e.type==='p'&&String(e.props.children).includes('Distinct tie markings')))
})
test('Remove tie sends only explicit null; cancel stays available for a source without candidates',()=>{
  const calls=[];const h=harness('../src/components/ScoreCorrectionToolbar.tsx',{group:'tie',review,event:{...note,tie_target_id:'chosen',tie_target_ids:[]},measure,position:null,adding:false,tying:true,disabled:false,readOnly:false,change:async(...args)=>calls.push(plain(args)),select(){},add(){},tie(){},advanced(){}})
  assert.equal(button(h.render(),'Cancel tie').props.disabled,false)
  button(h.render(),'Remove tie').props.onClick()
  assert.deepEqual(calls,[['events/source','PATCH',{tie_to_event_id:null}]])
})
test('music check is invoked only on demand and does not call correction/onChange',async()=>{
  const h=view({...review,state:'VERIFIED'})
  const tree=h.render();assert.equal(h.checks.length,0)
  assert.equal(find(tree,e=>e.type==='li'&&e.props.children==='Unusual measure.'),null)
  await button(tree,'Check score').props.onClick()
  await new Promise(resolve=>setTimeout(resolve,0))
  assert.equal(h.checks.length,1);assert.equal(h.edits.length,0);assert.equal(h.changes.length,0)
  assert.ok(find(h.render(),e=>e.type==='li'&&String(e.props.children).includes('barline')))
  assert.equal(button(h.render(),'Save').props.disabled,false) // Checking never changes save state.
  const stale=h.render(h.props({...review,revision:2}))
  assert.ok(find(stale,e=>e.type==='p'&&String(e.props.children).includes('Run Check score again')))
  assert.equal(find(stale,e=>e.type==='li'&&String(e.props.children).includes('barline')),null)
})
test('music warnings do not require Check before explicit Save',()=>{
  const h=view()
  assert.equal(button(h.render(),'Save').props.disabled,false)
  assert.equal(h.checks.length,0)
})
test('technical diagnostics remain available internally while Save provides actionable errors',()=>{
  const bad={...review,validation:{...review.validation,can_verify:false,error_count:1,diagnostics:[{code:'invalid_pitch',category:'TECHNICAL_ERROR',severity:'ERROR',blocking:true,message:'Malformed pitch.'}]}}
  const h=view(bad)
  assert.ok(button(h.render(),'Save'))
  assert.ok(find(h.render(),e=>e.type==='li'&&String(e.props.children).includes('Malformed pitch.')))
  assert.ok(find(h.render(),e=>e.type==='details'&&e.props.className==='review-validation').props.hidden)
})

test('an existing target remains explicitly selectable for duplicate correction', async () => {
  const tied = {...note, tie_target_id:'chosen'}
  const r = {...review, score:{...review.score,parts:[{id:'p',measures:[{...measure,voices:[{id:'1',events:[tied]},{id:'2',events:[target]}]}]}]}}
  const h=view(r)
  child(h.render(),'./MusicSheetViewer').props.onSelect('source')
  child(h.render(),'./ScoreCorrectionToolbar').props.tie()
  assert.ok(child(h.render(),'./MusicSheetViewer').props.tieTargetIds.includes('chosen'))
  child(h.render(),'./MusicSheetViewer').props.onSelect('chosen')
  await new Promise(resolve=>setTimeout(resolve,0))
  assert.deepEqual(h.edits[0].args,['events/source','PATCH',{tie_to_event_id:'chosen'}])
})

test('Check score API sends current revision and returns a check result without decoding/replacing score',async()=>{
  const requests=[]
  const result={revision:1,diagnostics:[],warning_count:0,technical_error_count:0,truncated:false}
  const api=load('../src/services/api.ts',{}, {fetch:async(url,options)=>{requests.push({url,options});return {ok:true,json:async()=>result}}})
  assert.equal(await api.checkReviewMusic({...review,id:'r/id'}),result)
  assert.equal(requests[0].url,'/api/v1/reviews/r%2Fid/music-check')
  assert.deepEqual(plain(requests[0].options),{method:'POST',headers:{'If-Match':'"1"'}})
})

test('browser regression: real note can start Tie without precomputed candidates or despite raw-markup errors',()=>{
  const props={review,event:{...note,tie_target_ids:[],tie_correction_error:'This endpoint has distinct tie markings'},measure,position:null,adding:false,tying:false,disabled:false,readOnly:false,change:async()=>{},select(){},add(){},tie(){},advanced(){}}
  assert.equal(button(harness('../src/components/ScoreCorrectionToolbar.tsx',{...props,group:'tie'}).render(),'Add tie').props.disabled,false)
})
test('browser regression: next selected real note is authoritative even when absent from candidate list',async()=>{
  const source={...note,tie_target_ids:[]}
  const r={...review,score:{...review.score,parts:[{id:'p',measures:[{...measure,voices:[{id:'1',events:[source,target,other]}]}]}]}}
  const h=view(r)
  child(h.render(),'./MusicSheetViewer').props.onSelect('source')
  child(h.render(),'./ScoreCorrectionToolbar').props.tie()
  child(h.render(),'./MusicSheetViewer').props.onSelect('chosen')
  await new Promise(resolve=>setTimeout(resolve,0))
  assert.deepEqual(h.edits[0]?.args,['events/source','PATCH',{tie_to_event_id:'chosen'}])
})

test('genuine backend technical source limitation disables Tie with its exact reason',()=>{
  const props={review,event:{...note,tie_source_editable:false,tie_correction_error:'A tie endpoint needs exactly one pitched MusicXML note.'},measure,position:null,adding:false,tying:false,disabled:false,readOnly:false,change:async()=>{},select(){},add(){},tie(){},advanced(){}}
  const tree=harness('../src/components/ScoreCorrectionToolbar.tsx',{...props,group:'tie'}).render()
  assert.equal(button(tree,'Add tie').props.disabled,true)
  assert.ok(find(tree,e=>e.type==='p'&&e.props.children===props.event.tie_correction_error))
})
test('canonical repeated correction success leaves verification and transposed lifecycle untouched',async()=>{
  const changes=[]
  const h=harness('../src/components/RecognitionReview.tsx',{review:{...review,state:'VERIFIED'},onChange:r=>changes.push(r),onBusy(){},download(){}},{'../services/api':{changeReview:async r=>({...r})}})
  child(h.render(),'./MusicSheetViewer').props.onSelect('source')
  child(h.render(),'./ScoreCorrectionToolbar').props.tie()
  child(h.render(),'./MusicSheetViewer').props.onSelect('chosen')
  await new Promise(resolve=>setTimeout(resolve,0))
  assert.equal(changes.length,0)
})
