import {it,expect} from 'vitest';
import {a4Slices,A4} from '../src/real/a4Layout';
it('keeps a short score on one portrait A4 page',()=>{expect(A4).toEqual({width:210,height:297,margin:12});expect(a4Slices(794,600,[300])).toEqual([{start:0,end:600}]);});
it('breaks long scores only between complete systems and text rows',()=>{const pages=a4Slices(794,2500,[600,1000,1100,1600,2100],[{top:1090,bottom:1120}]);expect(pages).toEqual([{start:0,end:1000},{start:1000,end:2100},{start:2100,end:2500}]);});
it('refuses a system larger than a page instead of clipping notation',()=>{expect(()=>a4Slices(794,2000,[])).toThrow('exceeds an A4 page');});
