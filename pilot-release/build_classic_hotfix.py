from pathlib import Path
import argparse,hashlib,json,shutil,subprocess,tarfile
ROOT=Path(__file__).resolve().parents[1]
BASE=Path('/home/dtran/music-sheet-transposer-releases/music-sheet-transposer-classic-task06')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);a=parser.parse_args();out=a.output.resolve()
 archive=Path(str(out)+'.tar.gz')
 if out.exists() or archive.exists():raise SystemExit('Output exists; nothing overwritten.')
 original=json.loads((BASE/'manifest.json').read_text())
 for n,h in original['sha256'].items():
  if sha(BASE/n)!=h:raise SystemExit('Classic integrity failure: '+n)
 allowed={'frontend-v2/src/App.tsx','frontend-v2/src/styles.css','frontend-v2/src/real/RealWorkspace.tsx'}
 for n,h in original['application_source_sha256'].items():
  if n not in allowed and sha(ROOT/n)!=h:raise SystemExit('Outside hotfix scope: '+n)
 subprocess.run(['npm','run','build'],cwd=ROOT/'frontend-v2',check=True)
 shutil.copytree(BASE,out,ignore=shutil.ignore_patterns('web','manifest.json'))
 shutil.copytree(ROOT/'frontend-v2/dist',out/'web')
 shutil.copy2(ROOT/'pilot-release/CLASSIC_HOTFIX_GUIDE_EN.md',out/'USER_GUIDE_EN.md')
 m=original.copy();m.update(version='classic-task06.1-home-chord',acceptance='PENDING hotfix Product Owner acceptance',baseline_manifest_sha256=sha(BASE/'manifest.json'),application_source_sha256={n:sha(ROOT/n) for n in original['application_source_sha256']},sha256={})
 for f in out.rglob('*'):
  if f.is_file():m['sha256'][str(f.relative_to(out))]=sha(f)
 (out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
 subprocess.run(['/usr/bin/python3','-I','-B',str(out/'start.py'),'--check'],check=True)
 with tarfile.open(archive,'w:gz') as tar:tar.add(out,arcname=out.name)
 Path(str(archive)+'.sha256').write_text(sha(archive)+'  '+archive.name+'\n')
 print(out);print('Archive SHA256: '+sha(archive))
if __name__=='__main__':main()
