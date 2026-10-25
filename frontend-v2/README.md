# Music Sheet Transposer — UX v2

Accepted Task 01 synthetic workspace and Task 02 real MusicXML pilot.

## Run

Start the existing backend with its configured Python environment on 127.0.0.1:8000 (`python -m uvicorn app.main:app --host 127.0.0.1 --port 8000` from backend). In this directory, use Node 24, run `npm ci`, then `npm run dev`. Open http://localhost:5174. Set AI_SDF_BACKEND_URL when the backend uses a different address.

Open MusicXML to edit a local score. Original Source remains read-only. Save/Save As use a supported local picker, or download with explicit retention confirmation. Instrument Scores uses the saved concert version; each instrument and direction has independent working edits. Export MusicXML and PDF are available. Fit fills pane width with vertical scrolling.

Try Demo Score remains explicitly synthetic and keeps simulated data in memory. Real OMR and AI agents are outside this release.

## Checks

Run `npm run typecheck`, `npm run lint`, `npm test`, and `npm run build`. `npm run test:e2e` starts its own frontend on 5174 and backend on 8812; those ports must be free. The checked-in browser configuration uses the existing WSL Firefox installation; adjust its executable path locally on another host. Private sample tests are opt-in with AI_SDF_TASK02_SAMPLE; no private score is bundled.

See RELEASE_CHECKPOINT.md for acceptance and verification. Full local reports, screenshots, and private evidence are intentionally excluded from publication.
