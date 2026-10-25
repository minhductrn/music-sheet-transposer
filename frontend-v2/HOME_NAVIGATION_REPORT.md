# Home navigation and save guard

Date: 2026-10-25. Status: **ACCEPTED**. Product Owner requested a Home action for importing another file, with a reminder to save unsaved work. After testing, the Product Owner explicitly confirmed “xác nhận chức năng Home”; acceptance is recorded below.

## Behavior and use

Home replaces the misleading Demo workspace exit in the real MusicXML header and is available in Concert and Instrument Scores. If the Concert and every generated instrument variant have confirmed saved snapshots matching their current XML, Home releases the real workspace and returns to Import Score. The import view and hidden demo state reset; another file, including the same filename, can be opened without refreshing the page.

If any score is not saved, the Save before returning Home dialog lists it. Open Concert to save or Open [instrument/direction] to save navigates to the existing editor; use its normal Save/Save As, retain the download and confirm when asked, then choose Home again. Continue editing or Escape cancels Home without discarding work. There is no discard action in the Home guard.

A pending/unconfirmed download, canceled picker, failed verification or failed file write does not establish a saved snapshot. Busy operations and unfinished inline edits block Home. Instrument save receipts remain associated with the correct variant while switching instruments/directions; later edits invalidate the comparison. The original Concert source remains independent. Export instrument MusicXML alone is not treated as a confirmed Save for this new guard.

## Bounded source scope

- src/App.tsx: reset to the actual import screen on workspace exit; import copy distinguishes real MusicXML from simulated PDF/image/demo.
- src/real/RealWorkspace.tsx: Home, save reminder, per-variant confirmed save snapshots, state restoration across switches and dialog keyboard/busy protections. Reuses existing Save and download-retention confirmation; no new backend API.
- src/real/real.css: bounded scrolling for the Home reminder.
- tests/e2e/home.spec.ts: three integrated safety/navigation cases.
- tests/e2e/task02-stage2.spec.ts: existing busy-lock expectation now targets Home instead of the removed Demo workspace button.

No backend, legacy frontend, musical edit contract, frozen baseline, root entry point or accepted Task 03 archive was changed. Direct Open MusicXML retains its existing separate confirmation flow; this change concerns Home.

## Local standalone delivery

The previous Task 03 package is immutable and does not gain Home automatically. A separate local package is supplied at evidence/home/music-sheet-transposer-pilot-home-v0.2-r1.tar.gz, with an extracted runnable folder beside it and SHA256 file. It reuses the verified Task 03 backend/runtime and launcher, replaces only built frontend assets, and records the three frontend source overlay hashes in manifest.json. Its application source base is 474af9bad99fc2684ad782546756be74da495b0a; the overlay has not been committed or pushed.

Archive SHA256: 0fd3df2ec83c58f090ce67cf5992cf5ca7c9588861b279678bcbf47e01bd5edf.

Keep the old pilot running if needed and launch this package with `python3 -B /path/to/music-sheet-transposer-pilot-home-v0.2-r1/start.py --port 5181`; open http://localhost:5181. Alternatively stop the old pilot with Ctrl+C and start the new package on default port 5180. Save old-session work before transferring files; sessions are not shared between package processes.

## Verification and review

Final source typecheck, lint, 44 unit tests and build passed. Preliminary development-server regression passed 52 browser cases (49 prior cases plus 3 Home cases). A final keyboard guard was then added to prevent a selected background note from being deleted while the reminder has focus; final source was rebuilt and the exact packaged Home v0.2-r1 regression passed **52/52 Firefox cases, zero failures/skips**, in 3.1 minutes. Source/test SHA256 values remained unchanged throughout this final packaged run. A first test-authoring case selected the instrument note's existing pitch, causing no change; its fixture action was corrected to select a different pitch.

The dedicated Home tests cover warning/cancel, download retention cancellation, save failure, pending operation, canceled native picker, successful return/import of another file without reload, inactive unsaved instrument detection, remembered saves across switches, later edits, unchanged Concert bytes and keyboard dismissal. Native picker cancellation is mocked; OS picker behavior beyond existing accepted coverage is not newly certified.

Technical Lead source review checked PC-03/04/05 canonical/file integrity, PC-06 explicit user save/cancel, PC-07 regression protection and PC-08 separate acceptance. XML equality, rather than click counts or filenames, governs saved status. The same successful Save path records a receipt only after the file write or explicit download-retention confirmation. Workspace unmount uses existing review-session cleanup. No OMR or agent execution was added.

All evidence, screenshots, runtime bundles and private sample use remain local under ignored evidence/home/. No Git add/commit/push was performed during implementation; consolidated publication is now authorized below. Product Owner acceptance is recorded below.

## Final evidence and protection

- `evidence/home/final-checks.json`: typecheck/lint/44 unit/build PASS.
- `evidence/home/production-regression.json` and `production-browser.log`: 52/52 packaged browser cases PASS, including the approved private MusicXML sample.
- `evidence/home/save-before-home.png` and `new-import.png`: reviewed Home warning and fresh import UI.
- `evidence/home/final-source-hashes.json`: tested source unchanged during final packaged verification.
- 619 prior dirty/untracked files, the original private sample, and the accepted Task 03 archive remained byte-identical. Git index is empty and HEAD remains 474af9b. No backend or legacy frontend edit, no data migration, no dependency installation, and no Git publication occurred.

Gates 1–3 are complete for this bounded change. Gate 4 is complete following the Product Owner confirmation on 2026-10-25; the prior Task 03 acceptance remains unchanged.

## Product Owner acceptance

On 2026-10-25 (America/New_York), the Product Owner explicitly confirmed “xác nhận chức năng Home”. The bounded Home navigation and save-guard feature is ACCEPTED: return to Import after confirmed saves; preserve work and identify unsaved Concert/instrument variants otherwise; cancellation or save failure does not exit. This documentation update does not change application source or the verified Home v0.2-r1 bundle. Git commit/push has not been performed for this feature.

## Home position adjustment — v0.2-r2

After accepting the Home behavior, the Product Owner requested a more convenient, conventional website placement. Home now appears at the upper left, before the application brand, inside a separate Main navigation region with a house icon and visible Home text. It is no longer mixed into score actions such as Save/Export. Save guards, variant tracking and callbacks are unchanged.

Position update status: **ACCEPTED** with the consolidated delivered-result acceptance and commit/push authorization on 2026-10-25. The prior Home behavior acceptance remains valid. Root typecheck/lint/44 unit/build passed. Four focused packaged browser tests passed: the three Home save-safety flows plus placement at 1440, 650 and 390 pixel widths. Desktop and narrow header screenshots were inspected. The previous 52-case packaged run remains evidence for the behavior; it was not repeated for this header-only adjustment. Existing narrow score overflow is outside this placement change.

Updated local bundle: evidence/home/music-sheet-transposer-pilot-home-v0.2-r2.tar.gz, SHA256 34cd99785e9de8f7fc3a4e3d5a31388a18e463699e3ffea522024063f257e358. The extracted folder beside it can run with --port 5182 to compare with the r1 app on 5181, or stop the previous process and reuse the same port. Task 03 and Home r1 archives remain unchanged. No Git commit/push occurred for this adjustment. Evidence: position-checks.json, position-regression.json, position-browser.log, home-position-1440.png, home-position-650.png and home-position-390.png.

## Consolidated publication authorization

On 2026-10-25, after receiving the current delivery including upper-left Home and the Tenor correction, the Product Owner stated “xác nhận nghiệm thu và đề nghi commit, push kết quả”. The current Home placement joins its already accepted save-guard behavior in the consolidated source checkpoint. This authorizes publication of the bounded Home/Tenor source, tests and reports; it does not include private evidence, runtime archives or legacy edits. Earlier no-publication/HEAD statements above are historical implementation-time records. The accepted pilot archives are retained unchanged locally.
