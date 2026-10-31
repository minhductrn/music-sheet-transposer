from pathlib import Path
import argparse,hashlib,json,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1]
BASE=Path('/home/dtran/music-sheet-transposer-releases/music-sheet-transposer-ux-next-1.0.0-rc1-accepted')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args();out=args.output.resolve()
 if out.exists():raise SystemExit('Output exists; nothing overwritten.')
 baseline=json.loads((BASE/'manifest.json').read_text())
 for n,h in baseline['sha256'].items():
  if sha(BASE/n)!=h:raise SystemExit('Accepted RC1 changed: '+n)
 allowed={'backend/app/api/v1/reviews.py','backend/app/api/v1/transpose.py','backend/app/music/review/models.py','backend/app/music/review/service.py','backend/app/music/review/sections.py'}
 for f in (ROOT/'backend/app').rglob('*.py'):
  n=str(f.relative_to(ROOT))
  if n not in allowed and sha(f)!=baseline['application_source_sha256'].get(n):raise SystemExit('Outside backend scope: '+n)
 subprocess.run(['npm','run','build'],cwd=ROOT/'frontend-v2',check=True)
 shutil.copytree(BASE,out,ignore=shutil.ignore_patterns('web','backend','manifest.json','ACCEPTANCE.json','VERIFICATION.json'))
 shutil.copytree(ROOT/'frontend-v2/dist',out/'web')
 shutil.copytree(ROOT/'backend/app',out/'backend/app',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
 (out/'README.md').write_text('# Advanced Editing v1 preview.5\n\nIndependent preview; Product Owner acceptance pending. Run python3 -B start.py --port 5245. Accepted RC1 and Classic are unchanged. See USER_GUIDE_EN.md.\n')
 shutil.copy2(ROOT/'pilot-release/ADVANCED_EDITING_GUIDE_EN.md',out/'USER_GUIDE_EN.md')
 (out/'ACCEPTANCE.json').write_text(json.dumps({'version':'advanced-v1-preview.5','status':'PENDING','parent_checkpoint':'91d74a3','note':'Parent RC1 acceptance does not apply to Advanced Editing.'},indent=2)+'\n')
 m=baseline.copy();m.update(version='advanced-v1-preview.5',acceptance='PENDING',source_acceptance='PENDING Advanced Editing v1',parent_manifest_sha256=sha(BASE/'manifest.json'),sha256={})
 m['application_source_sha256']={str(f.relative_to(ROOT)):sha(f) for folder in ['backend/app','frontend-v2/src'] for f in (ROOT/folder).rglob('*') if f.is_file() and '__pycache__' not in f.parts}
 for f in out.rglob('*'):
  if f.is_file() and f.name!='manifest.json':m['sha256'][str(f.relative_to(out))]=sha(f)
 (out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
 subprocess.run(['/usr/bin/python3','-I','-B',str(out/'start.py'),'--check'],check=True)
 print(out)
if __name__=='__main__':main()
