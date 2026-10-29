"""Isolated package restart/round-trip verification; never uses user sessions."""
from pathlib import Path
import argparse, base64, hashlib, json, os, subprocess, tempfile, time
from xml.etree import ElementTree as ET
import httpx


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--bundle',required=True,type=Path)
    parser.add_argument('--evidence',required=True,type=Path)
    parser.add_argument('--fixture',required=True,type=Path)
    parser.add_argument('--pdf',type=Path)
    args=parser.parse_args();evidence=args.evidence.resolve();evidence.mkdir(parents=True,exist_ok=True)
    bundle=args.bundle.resolve();checks=[];server=None;logs=open(evidence/'restart-server.log','w')
    client=httpx.Client(base_url='http://127.0.0.1:5223',timeout=180)
    original=args.fixture.read_bytes();sha=lambda b:hashlib.sha256(b).hexdigest()
    result={'status':'IN PROGRESS','bundle':str(bundle),'checks':checks}
    def checked(response):
        assert response.is_success,(response.status_code,response.text[:1500])
        return response
    def start():
        nonlocal server
        server=subprocess.Popen(['/usr/bin/python3','-I','-B',str(bundle/'start.py'),'--port','5223'],cwd=tempfile.gettempdir(),env={'PATH':'/usr/bin:/bin','HOME':str(Path.home()),'LANG':'C.UTF-8'},stdout=logs,stderr=logs)
        for _ in range(150):
            assert server.poll() is None,'Packaged server exited; inspect log.'
            try:
                if client.get('/api/v1/health').is_success:return
            except httpx.ConnectError:pass
            time.sleep(.1)
        raise AssertionError('Package did not start')
    def stop():
        nonlocal server
        if server and server.poll() is None:
            server.send_signal(2);server.wait(timeout=30)
        server=None
    def create(xml,extras=None):
        files={'musicxml':('saved.musicxml',xml,'application/xml')};files.update(extras or {})
        return checked(client.post('/api/v1/reviews',files=files)).json()
    def edit(review,path,body,method='POST'):
        return checked(client.request(method,'/api/v1/reviews/'+review['id']+'/'+path,json=body,headers={'If-Match':str(review['revision'])})).json()
    def export(review):return checked(client.get('/api/v1/reviews/'+review['id']+'/musicxml')).content
    def close(review):checked(client.delete('/api/v1/reviews/'+review['id']))
    def transpose(xml,instrument=None):
        data={'instrument':instrument,'direction':'down' if instrument in ('alto','tenor') else 'up'} if instrument else {'source_fifths':'-1','source_mode':'major','source_confirmed':'true','target_fifths':'1','direction':'up'}
        path='/api/v1/transpose/instrument' if instrument else '/api/v1/transpose/concert-key'
        return checked(client.post(path,files={'file':('score.musicxml',xml,'application/xml')},data=data)).content
    def musical(xml):
        root=ET.fromstring(xml)
        return [[(c.tag,c.text,sorted(c.attrib.items())) for c in n.iter()] for n in root.findall('.//note')]
    try:
        subprocess.run(['/usr/bin/python3','-I','-B',str(bundle/'start.py'),'--check'],check=True)
        start();html=checked(client.get('/')).text
        assert '/assets/' in html and '@vite/client' not in html
        checks.append('Relocated package runs with system Python -I, clean PATH and /tmp cwd, without source-checkout application imports or a development server.')
        source=create(original);source_id=source['id']
        changed=edit(source,'events/e-2',{'pitch':{'step':'E','alter':'1','octave':5}},'PATCH')
        changed=edit(changed,'events/e-2/lyrics',{'text':'Release round-trip verse 2','number':'2'})
        edited_bytes=export(changed)
        assert checked(client.get('/api/v1/reviews/'+source_id+'/musicxml',params={'original':'true'})).content==original
        concert=transpose(edited_bytes);assert musical(concert)!=musical(edited_bytes)
        saved={'concert':concert};(evidence/'concert.musicxml').write_bytes(concert)
        for instrument in ('alto','soprano','tenor'):
            written=transpose(concert,instrument);review=create(written)
            patched=edit(review,'events/e-2',{'display_size':'small'},'PATCH')
            output=export(patched);assert b'Release round-trip verse 2' in output
            assert ET.fromstring(output).find('.//transpose') is not None
            saved[instrument]=output;(evidence/(instrument+'.musicxml')).write_bytes(output)
            assert export(changed)==edited_bytes
            close(patched)
        checks.append('Concert key change and Alto/Soprano/Tenor generation preserve a corrected lyric and independent per-note edits; original Concert input is unchanged.')
        stop();start();assert client.get('/api/v1/reviews/'+source_id).status_code==404
        for label,contents in saved.items():
            reopened=create((evidence/(label+'.musicxml')).read_bytes())
            assert export(reopened)==contents
            assert musical(export(reopened))==musical(contents)
            close(reopened)
        checks.append('After owned server shutdown and restart, all four saved documents reopen byte-identically; temporary sessions are intentionally absent.')
        if args.pdf:
            pdf=args.pdf.read_bytes();begin=time.monotonic()
            response=client.post('/api/v1/recognize',files={'file':(args.pdf.name,pdf,'application/pdf')},data={'profile':'VOCAL_SONG','response_format':'json'})
            result['omr']={'status_code':response.status_code,'source_name':args.pdf.name,'source_sha256':sha(pdf),'duration_seconds':round(time.monotonic()-begin,2),'attempts':1}
            recognition=checked(response).json();(evidence/'real-omr-private.json').write_text(json.dumps(recognition))
            extras={'source':(args.pdf.name,pdf,'application/pdf')}
            if recognition.get('omr_artifact'):extras['omr']=('recognized.omr',base64.b64decode(recognition['omr_artifact']['data_base64']),'application/octet-stream')
            if recognition.get('semantic_evidence_artifact'):extras['analysis_omr']=('analysis.omr',base64.b64decode(recognition['semantic_evidence_artifact']['data_base64']),'application/octet-stream')
            draft=create(base64.b64decode(recognition.get('baseline_musicxml_base64') or recognition['musicxml_base64']),extras)
            events=[e for p in draft['score']['parts'] for m in p['measures'] for v in m['voices'] for e in v['events']]
            chosen=next(e for e in events if e['pitch'] and not e['grace'])
            corrected=edit(draft,'events/'+chosen['id'],{'pitch':{**chosen['pitch'],'octave':chosen['pitch']['octave']+1}},'PATCH')
            contents=export(corrected);(evidence/'omr-corrected-draft.musicxml').write_bytes(contents)
            assert checked(client.get('/api/v1/reviews/'+draft['id']+'/source')).content==pdf
            close(corrected);reopened=create(contents);assert export(reopened)==contents;close(reopened)
            assert args.pdf.read_bytes()==pdf
            result['omr'].update(provider=recognition['provider'],warning_count=len(recognition.get('warnings',[])),mapped_events=len(events))
            checks.append('One real local PDF recognition attempt produced an editable draft; an explicit correction exported/reopened without changing the original PDF. This is not an accuracy certification or Product Owner score comparison.')
        assert args.fixture.read_bytes()==original
        result.update(status='PASS',files={k:sha(v) for k,v in saved.items()})
    except Exception as error:
        result.update(status='FAIL',error=repr(error));raise
    finally:
        stop();client.close();logs.close();(evidence/'restart-results.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))

if __name__=='__main__':main()
