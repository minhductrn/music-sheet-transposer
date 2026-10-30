"""Build UX Next independently; never overwrite Classic or an existing candidate."""
from pathlib import Path
import hashlib,json,shutil,subprocess,argparse,re
ROOT=Path(__file__).resolve().parents[1]
CLASSIC=Path('/home/dtran/music-sheet-transposer-releases/music-sheet-transposer-classic-task06')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--version',required=True);args=parser.parse_args();out=args.output.resolve()
 if out.exists():raise SystemExit('Output exists; nothing overwritten.')
 baseline=json.loads((CLASSIC/'manifest.json').read_text())
 for n,v in baseline['sha256'].items():
  if digest(CLASSIC/n)!=v:raise SystemExit('Classic integrity failure: '+n)
 for f in (ROOT/'backend/app').rglob('*.py'):
  other=CLASSIC/'backend/app'/f.relative_to(ROOT/'backend/app')
  if (not other.is_file() or digest(f)!=digest(other)) and str(f.relative_to(ROOT)) not in {'backend/app/music/review/models.py','backend/app/music/review/patcher.py'}:raise SystemExit('Backend differs from approved scope.')
 subprocess.run(['npm','run','build'],cwd=ROOT/'frontend-v2',check=True)
 shutil.copytree(CLASSIC,out,ignore=shutil.ignore_patterns('web','manifest.json'))
 shutil.copytree(ROOT/'frontend-v2/dist',out/'web')
 for name in ['models.py','patcher.py']:shutil.copy2(ROOT/'backend/app/music/review'/name,out/'backend/app/music/review'/name)
 guide=(ROOT/'pilot-release/UX_NEXT_USER_GUIDE_EN.md').read_text()
 guide=re.sub(r'UX Next preview\.\d+',args.version,guide)
 guide=re.sub(r'music-sheet-transposer-ux-next-preview\d+',out.name,guide)
 (out/'USER_GUIDE_EN.md').write_text(guide)
 manifest=baseline.copy();manifest.update(version=args.version,release='Independent UX layout candidate',acceptance='PENDING',source_acceptance='PENDING UX Next; accepted Classic baseline',classic_manifest_sha256=digest(CLASSIC/'manifest.json'),sha256={})
 manifest['application_source_sha256']={str(f.relative_to(ROOT)):digest(f) for d in ['backend/app','frontend-v2/src'] for f in (ROOT/d).rglob('*') if f.is_file()}
 for f in sorted(out.rglob('*')):
  if f.is_file():manifest['sha256'][str(f.relative_to(out))]=digest(f)
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2))
 subprocess.run(['/usr/bin/python3','-I','-B',str(out/'start.py'),'--check'],check=True)
 print(out)
if __name__=='__main__':main()
