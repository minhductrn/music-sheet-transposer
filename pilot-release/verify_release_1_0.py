"""Verify packaged runtime restart and retained MusicXML, using a synthetic fixture."""
from pathlib import Path
import argparse,base64,hashlib,json,os,subprocess,time
import httpx
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--package',type=Path,required=True);p.add_argument('--port',type=int,default=5252);a=p.parse_args()
 evidence=ROOT/'frontend-v2/evidence/release-1.0';evidence.mkdir(parents=True,exist_ok=True)
 client=httpx.Client(base_url=f'http://127.0.0.1:{a.port}',timeout=30);server=None
 log=(evidence/'restart.log').open('w')
 def start():
  nonlocal server
  server=subprocess.Popen(['/usr/bin/python3','-I','-B',str(a.package/'start.py'),'--port',str(a.port)],cwd='/tmp',env={'PATH':'/usr/bin:/bin','HOME':str(Path.home()),'LANG':'C.UTF-8'},stdout=log,stderr=log)
  for _ in range(250):
   if server.poll() is not None:raise RuntimeError('Packaged server exited; see restart.log')
   try:
    if client.get('/api/v1/health').status_code==200:return
   except httpx.HTTPError:pass
   time.sleep(.1)
  raise RuntimeError('Packaged startup timeout')
 def stop():
  nonlocal server
  if server is not None and server.poll() is None:server.terminate();server.wait(timeout=20)
  server=None
 def checked(response):response.raise_for_status();return response
 def open_xml(raw):return checked(client.post('/api/v1/reviews',files={'musicxml':('score.musicxml',raw,'application/xml')})).json()
 def xml(review):return base64.b64decode(review['musicxml_base64'])
 try:
  start();raw=(ROOT/'frontend-v2/tests/fixtures/task02.musicxml').read_bytes();review=open_xml(raw)
  modified=checked(client.patch('/api/v1/reviews/'+review['id']+'/events/e-1',json={'display_size':'small'},headers={'If-Match':str(review['revision'])})).json()
  concert=checked(client.post('/api/v1/transpose/concert-key',files={'file':('concert.musicxml',xml(modified),'application/xml')},data={'source_fifths':'-1','source_mode':'major','source_confirmed':'true','target_fifths':'0','direction':'up','semitones':'7'})).content
  scores={'concert':concert}
  for instrument,direction in [('alto','down'),('soprano','up'),('tenor','down')]:
   scores[instrument]=checked(client.post('/api/v1/transpose/instrument',files={'file':('concert.musicxml',concert,'application/xml')},data={'instrument':instrument,'direction':direction})).content
  for name,data in scores.items():(evidence/(name+'.musicxml')).write_bytes(data)
  stop();start()
  results={}
  for name,data in scores.items():
   reopened=open_xml(data);assert xml(reopened)==data
   events=[e for p in reopened['score']['parts'] for m in p['measures'] for v in m['voices'] for e in v['events']]
   assert any(e['display_size']=='small' for e in events)
   results[name]={'sha256':hashlib.sha256(data).hexdigest(),'notes':len(events),'retained_edit':True,'exact_reimport':True}
   checked(client.delete('/api/v1/reviews/'+reopened['id']))
  result={'status':'PASS','isolated_python_runtime':True,'cwd':'/tmp','server_restarted':True,'saved_musicxml_roundtrip':results,'source_file_unchanged':(ROOT/'frontend-v2/tests/fixtures/task02.musicxml').read_bytes()==raw}
  (evidence/'restart-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
 finally:stop();client.close();log.close()
if __name__=='__main__':main()
