# Accepted application checkpoint before Task 04

Date: 2026-10-25 (America/New_York).

The Product Owner authorized checking current status, completing the standalone package checkpoint and synchronizing GitHub before Task 04. This checkpoint introduces no application functionality and does not claim Task 04 acceptance.

## Protected baseline

Accepted application commit: `ba45579917b02e2af9682b30e567de74122077e4`. GitHub master was independently read and matched this commit before this documentation commit. Home navigation and upper-left placement, real MusicXML editing, Concert/instrument workflows, and the approved Tenor Down +2 / standard Up +14 behavior are included. Earlier acceptance evidence is in HOME_NAVIGATION_REPORT.md, TENOR_REGISTER_REPORT.md and TASK_03_REPORT.md.

## Complete standalone delivery

Reuse the immutable, previously tested package; rebuilding identical application sources is unnecessary:

- Archive: `frontend-v2/evidence/tenor/music-sheet-transposer-pilot-tenor-v0.3.tar.gz`.
- Extracted folder: `frontend-v2/evidence/tenor/music-sheet-transposer-pilot-tenor-v0.3/`.
- SHA256: `a382a30deeeae8f8f20507ce0d04406e53fe5a0b19abeae5e716c75ebc06d53b`.
- Includes built frontend, backend, 21 runtime distributions, manifest, launchers and Vietnamese guide. Ubuntu WSL Linux x86_64 CPython 3.14 is required; this is not a native Windows installer.
- Start in Ubuntu: `python3 -B /home/dtran/music-sheet-transposer/frontend-v2/evidence/tenor/music-sheet-transposer-pilot-tenor-v0.3/start.py --port 5183`; browse to http://localhost:5183. An occupied port is rejected; existing sessions are not stopped.

The original manifest records the older build base plus explicit source overlays. All 31 source/test hashes recorded for that tested delivery now match the current accepted source checkpoint. Do not mistake the manifest base field alone for the delivered application contents.

## Current verification and historical evidence

Newly verified for this checkpoint: archive hash matches; all 861 manifest file hashes match; all 31 tested source/test hashes match; packaged launcher integrity and Python ABI check PASS. Git index was empty. All 619 pre-existing dirty/untracked files were hashed for protection.

Historical accepted verification, not newly rerun here: 496 backend tests, 44 frontend unit tests, 54 Firefox package tests, typecheck/lint/build PASS. No source changed since those verified hashes, so no redundant functional test run is claimed. Save/reopen, MusicXML/PDF and instrument integrity evidence remains in the accepted reports.

## Boundaries and publication

Only this checkpoint document is added to GitHub. Private PDFs/MusicXML, generated evidence, runtime archives, and all unrelated local work remain excluded. No reset, restore, clean or stash is used. Local dirty files are not a clean checkout and must continue to be protected during Task 04.

PDF/image recognition is not implemented in the accepted frontend-v2 delivery; its pilot blocks recognition routes. Task 04 remains pending design/implementation and must preserve this checkpoint. Saved user MusicXML files remain the durable musical records; unsaved review/history and instrument variant caches are transient.

PC-03/04/05/07/08 apply: preserve canonical Concert and independent instrument outputs, retain accepted behavior, and keep Product Owner acceptance distinct from technical verification. No new user-visible feature is submitted for acceptance by this checkpoint.
