import {it,expect} from 'vitest';
import {suggestOriginalKey} from '../src/real/originalKeySuggestion';
const chord={measure_id:'m-1',onset:'0',root_step:'A',root_alter:'0',kind:'minor'};
it('offers an explicit tentative Am suggestion from the opening chord',()=>{expect(suggestOriginalKey([chord],'m-1')).toMatchObject({fifths:0,mode:'minor',tonic:'A',chord:'Am'});expect(suggestOriginalKey([{...chord,root_step:'F',root_alter:'1'}],'m-1')).toMatchObject({fifths:3,mode:'minor'});});
it('does not infer a key from late or unsupported chords',()=>{expect(suggestOriginalKey([],'m-1')).toBeNull();expect(suggestOriginalKey([{...chord,kind:'dominant'}],'m-1')).toBeNull();expect(suggestOriginalKey([{...chord,onset:'1'}],'m-1')).toBeNull();expect(suggestOriginalKey([chord],'m-2')).toBeNull();});
