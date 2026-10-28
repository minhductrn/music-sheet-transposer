import {describe,it,expect} from 'vitest';
import {parseChordInput} from '../src/real/chordInput';
describe('literal chord entry',()=>{
 it('keeps the user harmony choice',()=>{expect(parseChordInput('Bm')).toEqual({root_step:'B',root_alter:'0',kind:'minor',text:'m'});expect(parseChordInput('E7').kind).toBe('dominant');expect(parseChordInput('G').kind).toBe('major');expect(parseChordInput('F#m7').root_alter).toBe('1');expect(parseChordInput('Bb13').text).toBe('13');});
 it('does not silently reinterpret unsupported slash bass',()=>{expect(()=>parseChordInput('C/E')).toThrow();expect(()=>parseChordInput('hello')).toThrow();});
});
