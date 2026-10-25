import {it,expect} from 'vitest';
import {decode,dottedWritten} from '../src/real/api';
it('dot palette uses exact written fractions including tuplet bases',()=>{expect(dottedWritten('1',true)).toBe('3/2');expect(dottedWritten('1/2',true)).toBe('3/4');expect(dottedWritten('1/4',true)).toBe('3/8');expect(dottedWritten('1',false)).toBe('1');const palette={'1':'2/3','3/2':'1'};expect(palette[dottedWritten('1',true) as keyof typeof palette]).toBe('1');});
it('decodes UTF16 XML without losing Vietnamese while normalizing browser transport declaration',()=>{const xml='<?xml version="1.0" encoding="UTF-16"?><score-partwise><work-title>Niềm tin</work-title></score-partwise>';const bytes=Buffer.from('\ufeff'+xml,'utf16le');const decoded=decode(bytes.toString('base64'));expect(decoded).toContain('Niềm tin');expect(decoded).toContain('encoding="utf-8"');expect(decoded).not.toContain('\u0000');});

it('UTF16 declarations allow XML whitespace around the encoding attribute',()=>{const xml='<?xml version="1.0" encoding = "UTF-16"?><score-partwise/>';expect(decode(Buffer.from('\ufeff'+xml,'utf16le').toString('base64'))).toContain('encoding = "utf-8"');});
