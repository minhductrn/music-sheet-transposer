import {it,expect} from 'vitest';
import {concertKeyRange} from '../src/real/concertKeyRange';
it('offers an explicit enharmonic target covering every section',()=>{expect(concertKeyRange([0,3],0,5)).toEqual({supported:false,alternative:-7});expect(concertKeyRange([0,3],0,-7)).toEqual({supported:true,alternative:null});});
it('does not suggest a range that breaks another section',()=>{expect(concertKeyRange([-7,7],0,5)).toEqual({supported:false,alternative:null});expect(concertKeyRange([],0,3)).toEqual({supported:true,alternative:null});});
