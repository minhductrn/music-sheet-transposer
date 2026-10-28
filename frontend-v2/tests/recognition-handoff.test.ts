import {afterEach,expect,it,vi} from 'vitest';
import {recognizeSource} from '../src/real/api';
afterEach(()=>vi.unstubAllGlobals());
it('hands baseline, immutable original and both evidence artifacts to one review without repeating recognition',async()=>{
 const original=new File(['pdf'],'original.pdf',{type:'application/pdf'});
 const baseline=btoa('<baseline/>'), recovered=btoa('<recovered/>');
 const fetcher=vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({musicxml_base64:recovered,baseline_musicxml_base64:baseline,provider:'audiveris',profile:'SATB',warnings:[],omr_artifact:{data_base64:btoa('evidence')},semantic_evidence_artifact:{data_base64:btoa('analysis')}}))).mockResolvedValueOnce(new Response(JSON.stringify({id:'r1',revision:0,musicxml_base64:recovered})));
 vi.stubGlobal('fetch',fetcher);
 const result=await recognizeSource(original,'SATB');
 expect(fetcher).toHaveBeenCalledTimes(2);
 expect(fetcher.mock.calls[0][0]).toBe('/api/v1/recognize');
 const request=fetcher.mock.calls[0][1].body as FormData;
 expect(request.get('profile')).toBe('SATB');expect(request.get('response_format')).toBe('json');
 const form=fetcher.mock.calls[1][1].body as FormData;
 expect(await (form.get('musicxml') as Blob).text()).toBe('<baseline/>');
 expect(await (form.get('source') as Blob).text()).toBe('pdf');
 expect(await (form.get('omr') as Blob).text()).toBe('evidence');
 expect(await (form.get('analysis_omr') as Blob).text()).toBe('analysis');
 expect(result.review.xml).toBe('<recovered/>');
});
it('reports OMR failure without creating a fake score or retrying',async()=>{
 const fetcher=vi.fn().mockResolvedValue(new Response(JSON.stringify({detail:'Recognition timed out'}),{status:504}));vi.stubGlobal('fetch',fetcher);
 await expect(recognizeSource(new File(['x'],'score.pdf'))).rejects.toThrow('Recognition timed out');expect(fetcher).toHaveBeenCalledTimes(1);
});
