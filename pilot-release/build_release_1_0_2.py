"""Package only the accepted PDF lyric maintenance scope; preserve published 1.0.0."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,tarfile
ROOT=Path(__file__).resolve().parents[1]
BASE=Path('/home/dtran/music-sheet-transposer-releases/music-sheet-transposer-1.0.1')
OUT=BASE.parent/'music-sheet-transposer-1.0.2'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def hashes(p):return {str(f.relative_to(p)):sha(f) for f in sorted(p.rglob('*')) if f.is_file() and f.name!='manifest.json' and '__pycache__' not in f.parts}
def seal():
 archive=Path(str(OUT)+'.tar.gz')
 if archive.exists():raise SystemExit('Archive exists; nothing overwritten.')
 m=json.loads((OUT/'manifest.json').read_text())
 if m.get('sealed'):raise SystemExit('Package is already sealed.')
 for n,h in m['sha256'].items():
  if sha(OUT/n)!=h:raise SystemExit('Package changed before verification: '+n)
 for n,h in m['application_source_sha256'].items():
  if sha(ROOT/n)!=h:raise SystemExit('Source changed after build: '+n)
 v=json.loads((ROOT/'docs/release-1.0.2/VERIFICATION.json').read_text())
 if v.get('package_verification')!='PASS':raise SystemExit('Package verification is not PASS.')
 shutil.copytree(ROOT/'docs/release-1.0.2',OUT/'docs/release-1.0.2',dirs_exist_ok=True)
 shutil.copy2(ROOT/'docs/release-1.0.2/VERIFICATION.json',OUT/'VERIFICATION.json')
 m.update(sealed=True,package_verification='PASS',sha256=hashes(OUT))
 (OUT/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
 subprocess.run(['/usr/bin/python3','-I','-B',str(OUT/'start.py'),'--check'],check=True)
 with tarfile.open(archive,'w:gz') as tar:tar.add(OUT,arcname=OUT.name,filter=lambda i:None if '__pycache__' in Path(i.name).parts else i)
 Path(str(archive)+'.sha256').write_text(sha(archive)+'  '+archive.name+'\n')
 print(json.dumps({'version':'1.0.2','archive':str(archive),'sha256':sha(archive),'manifest_sha256':sha(OUT/'manifest.json'),'github_published':False},indent=2))
def main():
 if sys.argv[1:]==['--seal']:return seal()
 if sys.argv[1:]:raise SystemExit('Usage: build_release_1_0_2.py [--seal]')
 if OUT.exists() or Path(str(OUT)+'.tar.gz').exists():raise SystemExit('Output exists; nothing overwritten.')
 base=json.loads((BASE/'manifest.json').read_text())
 for n,h in base['sha256'].items():
  if sha(BASE/n)!=h:raise SystemExit('Baseline integrity failure: '+n)
 source={str(f.relative_to(ROOT)):sha(f) for folder in ['backend/app','frontend-v2/src'] for f in (ROOT/folder).rglob('*') if f.is_file() and '__pycache__' not in f.parts}
 expected=base['application_source_sha256']
 allowed={'frontend-v2/src/version.ts','frontend-v2/src/real/RenderedScore.tsx'}
 if set(source)!=set(expected):raise SystemExit('Application file set differs from baseline.')
 for n,h in source.items():
  if n not in allowed and h!=expected[n]:raise SystemExit('Outside maintenance scope: '+n)
 subprocess.run(['npm','run','build'],cwd=ROOT/'frontend-v2',check=True)
 shutil.copytree(BASE,OUT,ignore=shutil.ignore_patterns('__pycache__','*.pyc','web','manifest.json'))
 shutil.copytree(ROOT/'frontend-v2/dist',OUT/'web')
 shutil.copy2(ROOT/'README.md',OUT/'README.md');shutil.copy2(ROOT/'PROJECT_SPEC.md',OUT/'PROJECT_SPEC.md')
 shutil.copytree(ROOT/'docs/release-1.0.2',OUT/'docs/release-1.0.2')
 shutil.copy2(ROOT/'docs/release-1.0.2/ACCEPTANCE.json',OUT/'ACCEPTANCE.json')
 m=base.copy();m.update(version='1.0.2',sealed=False,acceptance='ACCEPTED',package_verification='PENDING',source_checkpoint='ad7cdb8eaba5d993b51abbeca8043a545f14e01c plus accepted local PDF lyric maintenance delta',parent_manifest_sha256=sha(BASE/'manifest.json'),application_source_sha256=source,maintenance_scope=sorted(allowed),sha256=hashes(OUT))
 (OUT/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
 subprocess.run(['/usr/bin/python3','-I','-B',str(OUT/'start.py'),'--check'],check=True)
 print(OUT)
if __name__=='__main__':main()
