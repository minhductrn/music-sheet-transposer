"""Package the accepted application tree, never the dirty checkout."""
from pathlib import Path
import argparse, hashlib, io, json, shutil, subprocess, sys, tarfile, tempfile

REPO = Path(__file__).resolve().parents[1]
BASELINE = '945821c55cb7760a7200329ebbea7ed79055ffd2'
VERSION = '1.0.0-rc2'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    target = args.output.resolve()
    archive = Path(str(target) + '.tar.gz')
    checksum = Path(str(archive) + '.sha256')
    if any(p.exists() for p in (target, archive, checksum)):
        raise SystemExit('Output exists; nothing overwritten.')
    runtime = REPO / 'frontend-v2/evidence/tenor/music-sheet-transposer-pilot-tenor-v0.3'
    old = json.loads((runtime / 'manifest.json').read_text())
    for name, value in old['sha256'].items():
        if digest(runtime / name) != value:
            raise SystemExit('Runtime baseline integrity failure: ' + name)
    resolved = subprocess.check_output(['git', 'rev-parse', BASELINE + '^{commit}'], cwd=REPO, text=True).strip()
    if resolved != BASELINE:
        raise SystemExit('Unexpected application baseline.')
    tree = subprocess.check_output(['git', 'archive', '--format=tar', BASELINE], cwd=REPO)
    with tempfile.TemporaryDirectory(prefix='mst-task05-source-') as temp:
        frozen = Path(temp)
        with tarfile.open(fileobj=io.BytesIO(tree)) as package:
            package.extractall(frozen, filter='data')
        app_hashes = {}
        for folder in ('backend/app', 'frontend-v2/src'):
            for source in sorted((frozen / folder).rglob('*')):
                if source.is_file():
                    app_hashes[str(source.relative_to(frozen))] = digest(source)
        for name in ('frontend-v2/package.json', 'frontend-v2/package-lock.json'):
            app_hashes[name] = digest(frozen / name)
        # Build accepted sources with existing dependencies; no installation/network.
        (frozen / 'frontend-v2/node_modules').symlink_to(REPO / 'frontend-v2/node_modules', target_is_directory=True)
        subprocess.run(['npm', 'run', 'build'], cwd=frozen / 'frontend-v2', check=True)
        target.mkdir(parents=True)
        shutil.copytree(runtime / 'runtime', target / 'runtime')
        shutil.copytree(frozen / 'backend/app', target / 'backend/app')
        shutil.copytree(frozen / 'frontend-v2/dist', target / 'web')
        for name in ('start.py', 'Start-Pilot.ps1'):
            shutil.copy2(frozen / 'pilot-release' / name, target / name)
        for name in ('PRODUCT_CONSTITUTION.md', 'ACCEPTANCE_CRITERIA.md'):
            shutil.copy2(frozen / name, target / name)
    shutil.copy2(runtime / 'requirements.lock', target / 'requirements.lock')
    guide = REPO / 'pilot-release/USER_GUIDE_EN.md'
    shutil.copy2(guide, target / 'USER_GUIDE_EN.md')
    (target / 'README.md').write_text(
        '# Music Sheet Transposer ' + VERSION + '\n\n'
        'Release candidate; package acceptance is pending. Application source was accepted separately.\n\n'
        'Read USER_GUIDE_EN.md. From Ubuntu WSL: `python3 -B /actual/package/path/start.py --check`, '
        'then `python3 -B /actual/package/path/start.py --port 5180`. Open http://localhost:5180.\n\n'
        'Save MusicXML before stopping. The OMR-enabled launcher validates local Audiveris and language models. '
        'Python must match the manifest ABI. No automatic software installation occurs.\n')
    manifest = {k: old[k] for k in ('machine', 'python_abi', 'python_version', 'runtime_distributions', 'platform')}
    manifest.update(version=VERSION, release='Task 05 standalone release candidate',
                    source_checkpoint=BASELINE, accepted_checkpoint=BASELINE,
                    source_acceptance='ACCEPTED', acceptance='PENDING', omr_enabled=True,
                    application_source_sha256=app_hashes,
                    packaging_overlay_sha256={'pilot-release/build_task05.py': digest(Path(__file__)),
                                              'pilot-release/USER_GUIDE_EN.md': digest(guide)},
                    sha256={})
    for file in sorted(target.rglob('*')):
        if file.is_file():
            manifest['sha256'][str(file.relative_to(target))] = digest(file)
    (target / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    subprocess.run([sys.executable, '-I', '-B', str(target / 'start.py'), '--check'], check=True)
    with tarfile.open(archive, 'w:gz') as output:
        output.add(target, arcname=target.name)
    checksum.write_text(digest(archive) + '  ' + archive.name + '\n')
    print(archive)

if __name__ == '__main__':
    main()
