"""Build a host-specific pilot from the accepted commit, never from dirty files."""
from pathlib import Path
import argparse
import hashlib
import importlib.metadata as metadata
import io
import json
import os
import platform
import shutil
import subprocess
import sys
import sysconfig
import tarfile
import tempfile
from packaging.requirements import Requirement

REPO = Path(__file__).resolve().parents[1]
BASELINE = "bcac2d889da59406cefb0824a589ce20564b699a"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    target = args.output.resolve()
    if target.exists() or Path(str(target) + ".tar.gz").exists():
        raise SystemExit("Output exists; choose a new directory. Nothing overwritten.")
    target.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix="mst-task03-build-") as temp:
        checkout = Path(temp)
        archive = subprocess.check_output(["git", "archive", BASELINE], cwd=REPO)
        with tarfile.open(fileobj=io.BytesIO(archive)) as source:
            source.extractall(checkout, filter="data")
        frontend = checkout / "frontend-v2"
        (frontend / "node_modules").symlink_to(REPO / "frontend-v2/node_modules", target_is_directory=True)
        subprocess.run(["npm", "run", "build"], cwd=frontend, check=True)
        shutil.copytree(frontend / "dist", target / "web")
        shutil.copytree(checkout / "backend/app", target / "backend/app")
        for name in ["PRODUCT_CONSTITUTION.md", "ACCEPTANCE_CRITERIA.md"]:
            shutil.copy2(checkout / name, target / name)
    runtime = target / "runtime"
    runtime.mkdir()
    # Preserve each wheel's code, native libraries, metadata and license files.
    selected = {}
    pending = ["fastapi", "uvicorn", "pydantic-settings", "python-multipart", "pypdf", "Pillow", "httpx"]
    while pending:
        dist = metadata.distribution(pending.pop())
        name = dist.metadata["Name"]
        key = name.lower().replace("_", "-")
        if key in selected:
            continue
        selected[key] = dist.version
        root = Path(dist.locate_file("")).resolve()
        for record in dist.files or []:
            source = Path(dist.locate_file(record)).resolve()
            if not source.is_relative_to(root) or not source.is_file() or "__pycache__" in source.parts or source.suffix == ".pyc":
                continue
            destination = runtime / source.relative_to(root)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        for entry in dist.requires or []:
            requirement = Requirement(entry)
            if requirement.marker is None or requirement.marker.evaluate({"extra": ""}):
                pending.append(requirement.name)
    (target / "requirements.lock").write_text("".join(f"{name}=={version}\n" for name, version in sorted(selected.items())))
    for name in ["start.py", "Start-Pilot.ps1", "USER_GUIDE_VI.md"]:
        shutil.copy2(Path(__file__).parent / name, target / name)
    manifest = {"baseline_commit": BASELINE, "platform": platform.platform(), "machine": platform.machine(), "python_abi": sysconfig.get_config_var("SOABI"), "python_version": platform.python_version(), "runtime_distributions": selected, "sha256": {}}
    for file in sorted(target.rglob("*")):
        if file.is_file():
            manifest["sha256"][str(file.relative_to(target))] = hashlib.sha256(file.read_bytes()).hexdigest()
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2))
    subprocess.run([sys.executable, "-B", str(target / "start.py"), "--check"], check=True)
    archive = Path(str(target) + ".tar.gz")
    with tarfile.open(archive, "w:gz") as bundle:
        bundle.add(target, arcname=target.name)
    archive.with_suffix(archive.suffix + ".sha256").write_text(hashlib.sha256(archive.read_bytes()).hexdigest() + "  " + archive.name + "\n")
    print("BUNDLE:", archive)

if __name__ == "__main__":
    main()
