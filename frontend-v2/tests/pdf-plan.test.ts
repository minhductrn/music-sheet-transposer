import {describe,it,expect} from 'vitest';
import {planA4} from '../src/real/a4Layout';
describe('PDF placement without score mutations',()=>{
 it('keeps negative outer ink and scales uniformly inside A4',()=>{const b={x:-30,y:-12,width:1200,height:2400};const copy={...b};const p=planA4(b,{layout:'one-page',margins:'auto'},[]);expect(p.pages).toHaveLength(1);const {source,target}=p.pages[0];expect(source).toEqual(b);expect(b).toEqual(copy);expect(target.width/source.width).toBeCloseTo(target.height/source.height);expect(target.x).toBeGreaterThanOrEqual(10);expect(target.y+target.height).toBeLessThanOrEqual(285);});
 it('uses balanced spacing for compact content and standard on request',()=>{const b={x:0,y:0,width:900,height:600};expect(planA4(b,{layout:'one-page',margins:'auto'},[]).profile).toBe('Balanced');expect(planA4(b,{layout:'one-page',margins:'standard'},[]).pages[0].target.y).toBe(12);});
 it('splits only between systems without cutting text',()=>{const p=planA4({x:0,y:0,width:1100,height:4000},{layout:'multiple-pages',margins:'auto'},[1000,1500,2000,3000],[{top:1490,bottom:1510}]);expect(p.pages.length).toBeGreaterThan(1);expect(p.pages.some(v=>v.source.y+v.source.height===1500)).toBe(false);expect(p.pages.reduce((s,v)=>s+v.source.height,0)).toBe(4000);});
 it('rejects empty content and oversized unsplittable systems',()=>{expect(()=>planA4({x:0,y:0,width:0,height:1},{layout:'one-page',margins:'auto'},[])).toThrow();expect(()=>planA4({x:0,y:0,width:1100,height:4000},{layout:'multiple-pages',margins:'auto'},[])).toThrow();});
});
