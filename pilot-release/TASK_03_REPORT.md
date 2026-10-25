# Task 03 — Independent pilot handoff

Date: 2026-10-25. Status: **ACCEPTED**. The Product Owner reported successful practical testing (“toi da thu nghiẻm thanh cong”) and then explicitly accepted Task 03 (“nghiệm thu”). This acceptance applies to the bounded Task 03 independent local pilot described below. User authorized completion of the four bounded packaging items. No new editing features, OMR, agents, architecture migration, or source-code changes were introduced.

## Deliverable

- Application baseline: `bcac2d889da59406cefb0824a589ce20564b699a`, unchanged locally and on the established GitHub checkpoint.
- Final package: `frontend-v2/evidence/task03/music-sheet-transposer-pilot-task03-v0.1-r1.tar.gz` (12,328,495 bytes), with adjacent SHA256 file and extracted runnable folder.
- Archive SHA256: `b0160e2346fc808da2a04776fa1cfc362f6cd4f1dced2e0434a7bcec7def4789`.
- Built React assets, unchanged backend app, 21 bundled Python runtime distributions, requirements.lock, per-file manifest, Python and PowerShell launchers, and Vietnamese user guide. Runtime supports the current Ubuntu WSL Linux x86_64 / CPython 3.14 ABI. No Python interpreter or native Windows installer is bundled.
- Default local URL: http://localhost:5180. Existing development URL http://localhost:5174 remains separate. Run the PowerShell command documented in USER_GUIDE_VI.md or `python3 -B /path/to/package/start.py`; Ctrl+C stops the pilot. No Node, npm, Codex session, original repository, or Internet is required while running.

## Four authorized acceptance items

| Item | Technical result | Evidence |
| --- | --- | --- |
| Package frontend/backend and document startup | PASS: built from accepted Git archive; extracted elsewhere; started with system Python `-I`, clean application environment and working directory outside the repository. PowerShell launcher `--check` also passed. | `evidence/task03/final-build-r1.log`, `package-checks.json`, `restart-r1/server.log` |
| Save, close and reopen Concert/instrument | PASS: edited pitch/explicit accidental, Vietnamese lyrics and tie direction; saved Concert; generated Alto, edited lyric and added a measure/note; saved instrument. Closed browser and backend, restarted both, reopened both real files, compared exact bytes and complete score/slur projections, then saved again identically. Old live review ID returned 404 after restart. Canonical Concert stayed unchanged by instrument edits. | `restart-r1/results.json`, saved synthetic MusicXML files, before/after screenshots |
| MusicXML/PDF on packaged runtime | PASS: exact MusicXML roundtrip and four PDF exports in restart test. PDFs parse as A4, preserve Unicode, and rendered page images before/after restart match exactly. Existing browser suite also exported approved private Concert/instrument PDFs and a two-page synthetic PDF; all pages parsed and were visually reviewed. | `restart-r1/pdf-checks.json`, `pdf-render-comparison.json`, `regression-pdf/checks.json`, `regression.json` |
| Short guide and limits | COMPLETE: USER_GUIDE_VI.md is present both here and inside the verified archive. | user guide and manifest |

## Automated verification

- Production frontend build passed; existing large-bundle warning remains.
- Existing full Firefox suite against the packaged production assets and bundled backend: **49 passed, 0 failed** in 3.4 minutes, including the approved private MusicXML sample. This used separate test ports and did not replace the user's development server.
- Dedicated restart integration: PASS for Concert and instrument, including export/reimport, tuplets, voices, lyrics, ties and directions through full projection equality.
- Package integrity and ABI validation, deliberate file-corruption rejection, and occupied-port refusal: PASS.
- No backend/editor source changed, so the checkpoint's earlier 493 backend / 44 unit results remain historical evidence and are not represented as newly rerun Task 03 checks.

## Technical Lead source review (Gate 3)

Reviewed build.py, start.py, Start-Pilot.ps1, verification harness/config, guide, manifest/dependency closure and generated evidence. The builder selects the fixed accepted commit and excludes dirty working files. Runtime imports use only packaged backend/runtime; static assets and APIs share one local origin. The launcher uses one loopback-bound process, disables the recognition route in this pilot, preserves existing application lifecycle, rejects occupied ports, verifies package files and never launches agents or OMR. All actual musical edits use the unchanged accepted application paths. Existing renderer behavior, including dense lyric spacing, is retained; this task does not certify every possible score engraving.

Reviewed PC-03 (saved canonical data), PC-04 (independent two-stage outputs), PC-05 (persistence/export integrity), PC-06 (explicit save decisions), PC-07 (49-case regression), and PC-08 (separate PO acceptance). Gate 1 implementation and Gate 2 automated verification are complete; Gate 3 technical review is complete. Gate 4 is complete: the Product Owner explicitly accepted Task 03 on 2026-10-25 after reporting successful practical testing.

## Protection and limitations

619 pre-existing uncommitted/untracked files were hash-checked and unchanged; accepted tracked backend/frontend sources and Git index/HEAD were unchanged. The original private MusicXML retained its recorded checksum. Private scores, evidence and user files are absent from the package. No Git mutation or push was performed during Task 03 implementation and acceptance; publication is authorized separately below.

Persistence is file-based: Save/Save As (or retained download) must complete before closing. Backend reviews, unsaved edits, Undo/Redo and six instrument variant caches are transient. Reopened written instrument MusicXML is a standalone document, not an auto-restored Stage 2 session; regenerate instruments only from saved Concert input to avoid a second transposition. Firefox download-retention confirmation was tested; the native save picker on other browsers was not newly certified. This is one-user local Ubuntu WSL pilot software, not production hosting or a cross-platform installer.

## Resolved verification failures

The first packaging run exposed an archive-name suffix issue (version .1 was omitted from its filename); builder naming was corrected. The first full restart test exposed a socket TIME_WAIT startup refusal; the launcher now uses SO_REUSEADDR and the complete restart test passed on the final r1 package. The initial direct PowerShell invocation was refused by the machine's script-signing policy; the documented process-scoped `-ExecutionPolicy Bypass` command passed without changing system policy. These failures are retained in local preliminary logs, and superseded by the final evidence above.

No additional feature implementation or manual investigation is required to review this Task 03 handoff.

## Product Owner acceptance record

On 2026-10-25 (America/New_York), the Product Owner confirmed successful practical testing and explicitly stated “nghiệm thu”. Task 03 is ACCEPTED for the verified Ubuntu WSL local pilot scope: packaged startup, file-based Concert/instrument save and reopen, MusicXML/PDF outputs, and the supplied guide and limitations. This does not authorize OMR, additional features, production deployment, or Git commit/push. The delivered archive and application source are unchanged by this documentation update.

## GitHub publication authorization

On 2026-10-25, after Task 03 acceptance, the Product Owner agreed (“ok”) to the stated commit/push scope: only the packaging sources, launchers, verification harness/config, user guide and acceptance report in pilot-release/. Runtime bundles, private music, generated evidence, and unrelated legacy changes remain local. Publication does not change the accepted application baseline or the tested archive.
