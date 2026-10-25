"""Local packaged pilot. No development server or repository imports."""
from pathlib import Path
import argparse
import hashlib
import json
import platform
import socket
import sys
import sysconfig

ROOT = Path(__file__).resolve().parent

def verify():
    manifest = json.loads((ROOT / "manifest.json").read_text())
    if sysconfig.get_config_var("SOABI") != manifest["python_abi"] or platform.machine() != manifest["machine"] or sys.platform != "linux":
        raise SystemExit("This bundle requires its recorded Ubuntu Linux / Python ABI. Rebuild on the target host.")
    for name, expected in manifest["sha256"].items():
        file = ROOT / name
        if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest() != expected:
            raise SystemExit("Package verification failed: " + name)
    return manifest

def main():
    parser = argparse.ArgumentParser(description="Music Sheet Transposer local pilot")
    parser.add_argument("--port", type=int, default=5180)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    verify()
    if args.check:
        print("Package integrity and Python ABI: PASS")
        return
    if not 1024 <= args.port <= 65535:
        parser.error("port must be between 1024 and 65535")
    # Fail rather than replace an existing app.
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind(("127.0.0.1", args.port))
        except OSError:
            raise SystemExit("Port is already in use. Stop this pilot or choose --port.")
    sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "runtime")]
    from app.main import app
    from fastapi.responses import JSONResponse
    from fastapi.staticfiles import StaticFiles
    import uvicorn

    @app.middleware("http")
    async def pilot_boundary(request, call_next):
        if request.url.path.startswith("/api/") and not request.url.path.startswith(("/api/v1/reviews", "/api/v1/transpose", "/api/v1/concert-key", "/api/v1/health")):
            return JSONResponse({"detail": "This pilot supports MusicXML only; OMR is outside Task 03."}, status_code=404)
        return await call_next(request)

    app.mount("/", StaticFiles(directory=ROOT / "web", html=True), name="pilot")
    print(f"Open http://localhost:{args.port} — Ctrl+C to stop. Save MusicXML before closing.", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=args.port, workers=1, access_log=False, loop="asyncio", http="h11")

if __name__ == "__main__":
    main()
