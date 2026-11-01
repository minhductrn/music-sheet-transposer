# Music Sheet Transposer 1.0.2 — Operations

## Deployment and prerequisites

This is the existing personal Ubuntu WSL deployment. One Uvicorn process on loopback serves UI/backend. Cloudflare/public free access and hosting policy remain future work.

The bundle contains static frontend, backend and Python libraries. It needs the recorded Linux architecture/system Python ABI plus existing Audiveris, Java and English/Vietnamese OCR models. Node/npm and source checkout are unnecessary at runtime. The launcher installs nothing.

## Install and run

Archive: `music-sheet-transposer-1.0.2.tar.gz`, with adjacent `.sha256`. Extract into a new directory, never over an older release. Top-level folder: `music-sheet-transposer-1.0.2`.

Package contains `start.py`, `Start-Pilot.ps1`, `web/`, `backend/app/`, `runtime/`, `requirements.lock`, `manifest.json`, current English docs and acceptance/verification receipts. The manifest records version, ABI, source baseline and file hashes.

```bash
python3 -B /home/dtran/music-sheet-transposer-releases/music-sheet-transposer-1.0.2/start.py --check
python3 -B /home/dtran/music-sheet-transposer-releases/music-sheet-transposer-1.0.2/start.py --port 5250
```

Open http://localhost:5250. Default port is 5250. Startup verifies files and ABI. An occupied port causes exit; another server is never stopped. Use another `--port` if necessary. Ctrl+C stops this process; save first.

For relocation replace the folder path with the extracted location. ABI compatibility still applies. The PowerShell wrapper forwards arguments through WSL. Package version/manifest, not port, identifies the release.

Set `AUDIVERIS_EXECUTABLE` and `AUDIVERIS_TESSDATA_PATH` for non-default prerequisites. Normal executable: `/opt/audiveris/bin/Audiveris`; models: `~/.config/AudiverisLtd/audiveris/tessdata`, including `vie.traineddata` and `eng.traineddata`. Existing Java/Audiveris must remain available. They are not bundled.

## Data, backup and rollback

No durable score database exists. Sessions, sources and Undo history occupy bounded process memory and expire. Recognition can use temporary local artifacts. Retained MusicXML is durable recovery: save Concert and desired instrument variants separately. PDF is not a substitute.

After restart/expiry import the last saved MusicXML and retain the original PDF separately for comparison. Unsaved changes cannot be guaranteed recoverable. Back up score files with your device backup process; release archives contain no personal scores.

Version 1.0.2 is the accepted maintenance production release. Versions 1.0.0 and 1.0.1 are unchanged rollback packages. Classic Task06.1, RC1 and previews are untouched fallback packages. Save first, start a chosen version on another free port, and import your file. Review IDs and caches do not transfer between processes. Do not edit package files in place; integrity checks reject changes. Rollback changes the application, not saved musical edits. No running user server is automatically terminated.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| Occupied port | Use a free port; save before stopping an older server |
| Integrity failure | Verify archive checksum; extract a fresh copy into a new folder |
| ABI mismatch | Use recorded Ubuntu/Python; rebuild for a different ABI |
| Missing Audiveris/models | Restore local prerequisites or set documented paths |
| Review expired/not found | Reimport last retained MusicXML |
| Canceled Save | Save again and retain the actual file |
| Tiny PDF notation | Choose multiple pages instead of forcing one A4 page |
| Section boundary error | Extend selection or correct the ambiguous relationship |
| Wrong OMR key/lyrics/voice | Correct Working Score against the source before transposition |

## Release provenance

Tag `v1.0.2` identifies the source checkpoint for the accepted maintenance update. Published `v1.0.0` is retained. The application archive and manifest identify the exact tested package; the separately published documentation ZIP contains the current English documentation. Documentation refreshed after package sealing does not rewrite the sealed application's bytes.

Check the adjacent SHA-256 file before extraction and run `start.py --check` afterward. Extract to a new directory; never edit a sealed package in place. Cloud/public hosting and direct camera/Web Share remain outside scope.

## Maintainer build and seal sequence

The existing host builder `pilot-release/build_release_1_0_2.py` requires the retained sealed 1.0.1 package and existing Node dependencies. It refuses existing package/archive paths and installs nothing. Run it before verification, test the exact package, record actual results in `VERIFICATION.json`, then run the same builder with `--seal`. Retain the resulting archive, checksum and manifest. This script reconstructs the existing host-specific release; it is not a general installer for another ABI.

## Troubleshooting WSL and restart

Save MusicXML before stopping any server. Normally Ctrl+C in the application terminal is sufficient; WSL shutdown is not needed. Docker Desktop or another WSL-connected app may restart a distribution after shutdown. Quit those connections before a deliberate WSL-wide shutdown. Music Sheet Transposer itself does not require Docker. Never stop an unrelated process solely to free a port; choose a free port instead.

## Repeat the bounded PDF maintenance check

Start a separate copy of the package on a free port (the verifier defaults to 5299), preserving the user's running session. In the existing development checkout, set `MST_MUSICXML_G`, `MST_MUSICXML_GB` and `MST_MUSICXML_ALTO` to private local MusicXML samples. Optionally set `MST_BASE_URL`, `MST_FIREFOX` and `MST_OUTPUT`. Run `node pilot-release/verify_pdf_maintenance.cjs` with existing Playwright dependencies. The verifier fails if a sample is absent; it does not fabricate a PASS. Outputs are local only. It checks three one-page exports, lyric center alignment, browser errors and absence of musical-mutation requests. It does not certify general engraving quality, OMR accuracy or instrument generation.
