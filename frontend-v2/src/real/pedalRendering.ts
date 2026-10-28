import type {OpenSheetMusicDisplay} from 'opensheetmusicdisplay';
type Context={openGroup?:(name:string,id:string)=>unknown;closeGroup?:()=>unknown};
type Native={getAttribute:(name:string)=>string;getContext?:()=>Context;context?:Context;draw:(...args:unknown[])=>unknown};
type Graphic={editablePedalSVGId?:string;getPedalMarking?:()=>Native};
type Drawer={drawPedals?:(line:{Pedals?:Graphic[]})=>unknown};
// The SVG drawer is initialized lazily inside render(). Install an instance-only
// adapter immediately after backend preparation, and restore all hooks in finally.
export function renderPedalIdentities(osmd:OpenSheetMusicDisplay){
 const restored:{drawer:Drawer;draw:NonNullable<Drawer['drawPedals']>}[]=[];
 const install=()=>{
  const drawer=osmd.Drawer as unknown as Drawer;
  if(!drawer?.drawPedals||restored.some(e=>e.drawer===drawer))return;
  const draw=drawer.drawPedals;restored.push({drawer,draw});
  drawer.drawPedals=function(line){
   const getters:{graphic:Graphic;get:()=>Native;own:boolean}[]=[];
   try{
    for(const graphic of line.Pedals??[]){const get=graphic.getPedalMarking;if(!get)continue;getters.push({graphic,get,own:Object.prototype.hasOwnProperty.call(graphic,'getPedalMarking')});graphic.getPedalMarking=function(){const native=get.call(this);this.editablePedalSVGId=native.getAttribute('id');const original=native.draw;native.draw=function(...args){const context=this.getContext?.()??this.context;if(!context?.openGroup||!context.closeGroup)return original.apply(this,args);context.openGroup('editable-pedal',this.getAttribute('id'));try{return original.apply(this,args);}finally{context.closeGroup();}};return native;};}
    return draw.call(this,line);
   }finally{for(const {graphic,get,own} of getters){if(own)graphic.getPedalMarking=get;else delete graphic.getPedalMarking;}}
  };
 };
 const display=osmd as unknown as {createOrRefreshRenderBackend?:()=>void};const prepare=display.createOrRefreshRenderBackend;
 if(prepare)display.createOrRefreshRenderBackend=function(){prepare.call(this);install();};
 try{install();osmd.render();}finally{if(prepare)display.createOrRefreshRenderBackend=prepare;for(const {drawer,draw} of restored)drawer.drawPedals=draw;}
}
