import {describe,it,expect} from 'vitest';
import {destinationFor,intervalFor} from '../src/real/KeyShiftControl';
describe('compact key interval control',()=>{
 it('uses one semitone for each half-tone step',()=>{expect(destinationFor(0,1)).toBe(-5);expect(destinationFor(0,-1)).toBe(5);expect(intervalFor(0,-5,'up')).toBe(1);});
 it('preserves an explicitly chosen enharmonic key and octave registers',()=>{expect(destinationFor(0,-1,-7)).toBe(-7);expect(destinationFor(3,12)).toBe(3);expect(intervalFor(3,3,'down')).toBe(-12);expect(intervalFor(3,3,'up')).toBe(0);});
 it('keeps destination congruent across the supported range',()=>{for(let source=-7;source<=7;source++)for(let n=-24;n<=24;n++){const target=destinationFor(source,n);expect(((7*(target-source)-n)%12+12)%12).toBe(0);}});
});
