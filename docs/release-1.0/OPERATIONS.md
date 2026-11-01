# Music Sheet Transposer 1.0 — Operations

## Deployment and prerequisites

This is the existing personal Ubuntu WSL deployment. One Uvicorn process on loopback serves UI/backend. Cloudflare/public free access and hosting policy remain future work.

The bundle contains static frontend, backend and Python libraries. It needs the recorded Linux architecture/system Python ABI plus existing Audiveris, Java and English/Vietnamese OCR models. Node/npm and source checkout are unnecessary at runtime. The launcher installs nothing.

## Install and run

Archive: `music-sheet-transposer-1.0.0.tar.gz`, with adjacent `.sha256`. Extract into a new directory, never over an older release. Top-level folder: `music-sheet-transposer-1.0.0`.

Package contains `start.py`, `Start-Pilot.ps1`, `web/`, `backend/app/`, `runtime/`, `requirements.lock`, `manifest.json`, current English docs and acceptance/verification receipts. The manifest records version, ABI, source baseline and file hashes.

```bash
python3 -B /home/dtran/music-sheet-transposer-releases/music-sheet-transposer-1.0.0/start.py --check
python3 -B /home/dtran/music-sheet-transposer-releases/music-sheet-transposer-1.0.0/start.py --port 5250
```

Open http://localhost:5250. Default port is 5250. Startup verifies files and ABI. An occupied port causes exit; another server is never stopped. Use another `--port` if necessary. Ctrl+C stops this process; save first.

For relocation replace the folder path with the extracted location. ABI compatibility still applies. The PowerShell wrapper forwards arguments through WSL. Package version/manifest, not port, identifies the release.

Set `AUDIVERIS_EXECUTABLE` and `AUDIVERIS_TESSDATA_PATH` for non-default prerequisites. Normal executable: `/opt/audiveris/bin/Audiveris`; models: `~/.config/AudiverisLtd/audiveris/tessdata`, including `vie.traineddata` and `eng.traineddata`. Existing Java/Audiveris must remain available. They are not bundled.

## Data, backup and rollback

No durable score database exists. Sessions, sources and Undo history occupy bounded process memory and expire. Recognition can use temporary local artifacts. Retained MusicXML is durable recovery: save Concert and desired instrument variants separately. PDF is not a substitute.

After restart/expiry import the last saved MusicXML and retain the original PDF separately for comparison. Unsaved changes cannot be guaranteed recoverable. Back up score files with your device backup process; release archives contain no personal scores.

Version 1.0.0 is production. Classic Task06.1, RC1 and previews are untouched fallback packages. Save first, start a chosen version on another free port, and import your file. Review IDs and caches do not transfer between processes. Do not edit package files in place; integrity checks reject changes. Rollback changes the application, not saved musical edits. No running user server is automatically terminated.

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

Tag `v1.0.0` identifies source. The builder records accepted feature checkpoint e8a6b24 and source hashes. Building requires existing development dependencies and the accepted preview.5 runtime baseline; no network installation is performed. The artifact is host-ABI specific. Archive SHA-256 identifies distribution bytes; the manifest verifies extracted files.

## Maintainer build and seal sequence

Build to a new output path with `pilot-release/build_release_1_0.py --output <new-package-directory>`. Test that exact package, including browser workflows and `pilot-release/verify_release_1_0.py --package <new-package-directory>`. Record actual results in `docs/release-1.0/VERIFICATION.json`; the seal step refuses a non-PASS verification record. Then run `pilot-release/build_release_1_0.py --output <new-package-directory> --seal`. This verifies unchanged application bytes, finalizes documentation/receipts and creates the archive/checksum. Do not modify the sealed package afterward. A changed application requires a new release build and verification, not replacement inside an existing archive.
