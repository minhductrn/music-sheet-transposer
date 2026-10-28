"""Build Task 04 without touching the accepted Task 03/Tenor archives."""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess,sys,tarfile
REPO=Path(__file__).resolve().parents[1]
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--output',required=True,type=Path);parser.add_argument('--accepted',action='store_true',help='Package the Product Owner accepted Task 04 scope');args=parser.parse_args();target=args.output.resolve()
 archive=Path(str(target)+'.tar.gz')
 if target.exists() or archive.exists():raise SystemExit('Output exists; nothing overwritten.')
 source=REPO/'frontend-v2/evidence/tenor/music-sheet-transposer-pilot-tenor-v0.3'
 manifest=json.loads((source/'manifest.json').read_text())
 for name,digest in manifest['sha256'].items():
  if hashlib.sha256((source/name).read_bytes()).hexdigest()!=digest:raise SystemExit('Accepted package integrity failure: '+name)
 subprocess.run(['npm','run','build'],cwd=REPO/'frontend-v2',check=True)
 target.mkdir(parents=True)
 shutil.copytree(source/'runtime',target/'runtime')
 shutil.copytree(REPO/'frontend-v2/dist',target/'web')
 shutil.copytree(REPO/'backend/app',target/'backend/app',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
 for name in ['start.py','Start-Pilot.ps1','USER_GUIDE_VI.md','TASK_04_GUIDE_VI.md']:
  shutil.copy2(REPO/'pilot-release'/name,target/name)
 for name in ['PRODUCT_CONSTITUTION.md','ACCEPTANCE_CRITERIA.md']:
  shutil.copy2(REPO/name,target/name)
 shutil.copy2(source/'requirements.lock',target/'requirements.lock')
 sources={}
 for folder in ['backend/app','frontend-v2/src','pilot-release']:
  for p in (REPO/folder).rglob('*'):
   if p.is_file() and '__pycache__' not in p.parts and p.suffix in ['.py','.tsx','.ts','.css','.md','.ps1']:
    sources[str(p.relative_to(REPO))]=hashlib.sha256(p.read_bytes()).hexdigest()
 for name in ['frontend-v2/package.json','frontend-v2/package-lock.json']:
  sources[name]=hashlib.sha256((REPO/name).read_bytes()).hexdigest()
 output={k:v for k,v in manifest.items() if k in ['machine','python_abi','python_version','runtime_distributions','platform']}
 output.update(accepted_checkpoint='5b1e8e44f981cf54c4d7ccf0461f10e6435f278a',release='Task 04 accepted checkpoint' if args.accepted else 'Task 04 development candidate',acceptance='ACCEPTED' if args.accepted else 'PENDING',omr_enabled=True,source_sha256=sources,sha256={})
 for p in sorted(target.rglob('*')):
  if p.is_file():output['sha256'][str(p.relative_to(target))]=hashlib.sha256(p.read_bytes()).hexdigest()
 (target/'manifest.json').write_text(json.dumps(output,indent=2))
 subprocess.run([sys.executable,'-B',str(target/'start.py'),'--check'],check=True)
 with tarfile.open(archive,'w:gz') as tar:tar.add(target,arcname=target.name)
 archive.with_suffix('.gz.sha256').write_text(hashlib.sha256(archive.read_bytes()).hexdigest()+'  '+archive.name+'\n')
 print(archive)
if __name__=='__main__':main()
