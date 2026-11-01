"""Build and seal the accepted local 1.0 release; never overwrite an old package."""
from pathlib import Path
import argparse, hashlib, json, shutil, subprocess, tarfile
ROOT=Path(__file__).resolve().parents[1]
BASE=Path('/home/dtran/music-sheet-transposer-releases/music-sheet-transposer-advanced-v1-preview5')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def file_hashes(out):return {str(f.relative_to(out)):sha(f) for f in sorted(out.rglob('*')) if f.is_file() and f.name!='manifest.json' and '__pycache__' not in f.parts}
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--seal',action='store_true');a=p.parse_args();out=a.output.resolve()
 if a.seal:
  if not out.is_dir():raise SystemExit('Build the package before sealing.')
  m=json.loads((out/'manifest.json').read_text())
  if m.get('version')!='1.0.0' or m.get('sealed'):raise SystemExit('Only an unsealed 1.0.0 package can be sealed.')
  source={str(f.relative_to(ROOT)):sha(f) for folder in ['backend/app','frontend-v2/src'] for f in (ROOT/folder).rglob('*') if f.is_file() and '__pycache__' not in f.parts}
  if source!=m['application_source_sha256']:raise SystemExit('Application source changed after build.')
  verification=json.loads((ROOT/'docs/release-1.0/VERIFICATION.json').read_text())
  if verification.get('package_verification')!='PASS':raise SystemExit('Final package verification is not PASS.')
  # Only documentation/receipts are finalized here; application files remain unchanged.
  for name,h in m['sha256'].items():
   if name.startswith(('web/','backend/','runtime/')) or name in {'start.py','Start-Pilot.ps1','requirements.lock'}:
    if sha(out/name)!=h:raise SystemExit('Packaged application changed: '+name)
  shutil.copy2(ROOT/'README.md',out/'README.md')
  shutil.copytree(ROOT/'docs/release-1.0',out/'docs/release-1.0',dirs_exist_ok=True)
  shutil.copy2(ROOT/'docs/release-1.0/VERIFICATION.json',out/'VERIFICATION.json')
  m['sealed']=True;m['sha256']=file_hashes(out)
  archive=out.parent/(out.name+'.tar.gz')
  if archive.exists():raise SystemExit('Archive exists; nothing overwritten.')
  (out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
  subprocess.run(['/usr/bin/python3','-I','-B',str(out/'start.py'),'--check'],check=True)
  with tarfile.open(archive,'w:gz') as tar:tar.add(out,arcname=out.name,filter=lambda info:None if '__pycache__' in Path(info.name).parts else info)
  digest=sha(archive);(archive.parent/(archive.name+'.sha256')).write_text(digest+'  '+archive.name+'\n')
  print(json.dumps({'archive':str(archive),'sha256':digest,'manifest_sha256':sha(out/'manifest.json')},indent=2));return
 if out.exists():raise SystemExit('Output exists; nothing overwritten.')
 baseline=json.loads((BASE/'manifest.json').read_text())
 for n,h in baseline['sha256'].items():
  if sha(BASE/n)!=h:raise SystemExit('Accepted package changed: '+n)
 source={str(f.relative_to(ROOT)):sha(f) for folder in ['backend/app','frontend-v2/src'] for f in (ROOT/folder).rglob('*') if f.is_file() and '__pycache__' not in f.parts}
 expected=baseline['application_source_sha256']
 if set(source)!=set(expected):raise SystemExit('Application file set differs from accepted baseline.')
 for n,h in source.items():
  if n!='frontend-v2/src/version.ts' and h!=expected[n]:raise SystemExit('Outside release promotion: '+n)
 if (ROOT/'frontend-v2/src/version.ts').read_text().strip()!="export const UX_NEXT_VERSION = '1.0.0';":raise SystemExit('Incorrect release version.')
 subprocess.run(['npm','run','build'],cwd=ROOT/'frontend-v2',check=True)
 shutil.copytree(BASE,out,ignore=shutil.ignore_patterns('web','backend','manifest.json','ACCEPTANCE.json','VERIFICATION.json','README.md','USER_GUIDE_EN.md'))
 shutil.copytree(ROOT/'frontend-v2/dist',out/'web');shutil.copytree(ROOT/'backend/app',out/'backend/app',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
 shutil.copy2(ROOT/'pilot-release/release_start.py',out/'start.py')
 shutil.copy2(ROOT/'README.md',out/'README.md');shutil.copytree(ROOT/'docs/release-1.0',out/'docs/release-1.0')
 for name in ['PRODUCT_CONSTITUTION.md','ACCEPTANCE_CRITERIA.md']:shutil.copy2(ROOT/name,out/name)
 for name in ['ACCEPTANCE.json','VERIFICATION.json']:shutil.copy2(ROOT/'docs/release-1.0'/name,out/name)
 m=baseline.copy();m.update(version='1.0.0',acceptance='ACCEPTED',source_acceptance='Product Owner production designation',sealed=False,feature_checkpoint='e8a6b24627bc84f643ede2ef4b4fba67c375e3d8',parent_manifest_sha256=sha(BASE/'manifest.json'),application_source_sha256=source,sha256=file_hashes(out))
 (out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
 subprocess.run(['/usr/bin/python3','-I','-B',str(out/'start.py'),'--check'],check=True);print(out)
if __name__=='__main__':main()
