# Baseline Manifest

Prepared 2026-10-14 under GOV-03; updated through GOV-08 authorized repository
preparation. See
[PROJECT_STATE_AND_DECISIONS.md](PROJECT_STATE_AND_DECISIONS.md) and the governing
[constitution](PRODUCT_CONSTITUTION.md), [acceptance gates](ACCEPTANCE_CRITERIA.md)
and [repository instructions](AGENTS.md). This is a proposed manifest, not
staging authorization or a declaration that baseline verification passed.

## Inventory and disposition

The numbered table enumerates all 48 GOV-02 files, with repository-relative paths.
`M` means unstaged tracked modification (` M` in short status); `??` means
untracked. GOV-02 had no staged changes. The table preserves that historical
inventory; GOV-07/08 additions and current index/ignore status are recorded below.

Include = proposed baseline content, conditional on required verification and
Technical Lead approval. Review = resolve stated scope/provenance/status before
inclusion. Hold = preserve locally outside the proposed checkpoint. No disposition
proposes deletion or relocation. Tracked snapshot conflicts are identified below.

Groups and verification codes:

- C: Concert-Key foundation. Review engine/API contracts and confirmation guards;
  run backend Concert-Key/API and export/reimport integration regressions (BC).
- U: shared workspace/UX checkpoint, including mixed functional integration and
  rendering. Review full diff/hunk boundaries (MX); run frontend suite, lint,
  build and diff-check (FE). Inspect Firefox UI where applicable (UI).
- F: local artifact and dependent test, excluded by PO policy. Preserve both
  locally and run the existing regression (FT) without weakening coverage.
- D: documentation/history. Reconcile current claims with code and explicit
  acceptance, validate references and distinguish historical evidence (DR).

Dependencies are file names or group identifiers. FE/BC identify required checks;
GOV-04 results are recorded below and GOV-06 reruns them. Every group
requires Technical Lead review; user-visible acceptance follows the mandatory
gates. UI acceptance of UX-03C does not approve unrelated functional changes.

| # | File | Git | Group | Disposition | Dependencies | Required verification |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `README.md` | M | D | Review | C/U reports and state record | DR: GOV-06 reconciled status; Technical Lead review pending |
| 2 | `backend/app/api/v1/transpose.py` | M | C | Review | concert_key.py, API tests, frontend API client | BC: backend/API scope |
| 3 | `frontend/src/components/Layout.tsx` | M | U | Include | Home.tsx, index.css | MX, FE, UI |
| 4 | `frontend/src/components/MusicSheetViewer.tsx` | M | U | Review | viewport, sourceEngraving.ts, visual tests | MX: rendering plus UX, FE, UI |
| 5 | `frontend/src/components/RecognitionReview.tsx` | M | U | Review | toolbar, viewer, ConcertTranspose.tsx, editor tests | MX: shared functional/UX composition, FE, UI |
| 6 | `frontend/src/components/ReviewScoreViewport.tsx` | M | U | Review | viewer, source viewer, workspace tests | MX: viewport behavior plus UX, FE, UI |
| 7 | `frontend/src/components/ScoreCorrectionToolbar.tsx` | M | U | Include | shared editor, correction tests | MX, FE: operation accessibility, UI |
| 8 | `frontend/src/components/SourceViewer.tsx` | M | U | Include | viewport, source API, workspace tests | MX, FE, UI: native PDF limitations |
| 9 | `frontend/src/index.css` | M | U | Include | all workspace components | MX, FE, UI: responsive layout |
| 10 | `frontend/src/pages/Home.tsx` | M | U | Review | ConcertTranspose.tsx, C client, shared editor | MX: integration plus UX/import continuity, FE, UI |
| 11 | `frontend/src/services/api.ts` | M | C | Review | backend routes, Concert client tests | BC, FE: contract parity |
| 12 | `frontend/src/utils/sourceEngraving.ts` | M | U | Review | viewer, source-engraving tests | MX: rendering behavior, FE, UI |
| 13 | `frontend/tests/local-score-file.test.mjs` | M | U | Include | shared editor/save helpers | FE: saved snapshot/export behavior |
| 14 | `frontend/tests/review-insertion.test.mjs` | M | U | Include | shared editor/insertion components | FE: insertion workflows |
| 15 | `frontend/tests/review-lifecycle.test.mjs` | M | U | Include | Home.tsx, shared editor | FE: revision invalidation |
| 16 | `frontend/tests/review-selection.test.mjs` | M | U | Include | shared editor, More controls | FE: selection/history/accessibility |
| 17 | `frontend/tests/review-workspace.test.mjs` | M | U | Include | Home.tsx, viewport, styles | FE, UI: structural tests are not screenshots |
| 18 | `frontend/tests/score-correction.test.mjs` | M | U | Include | toolbar and existing correction components | FE: notes/lyrics/ties/Up/Down |
| 19 | `frontend/tests/source-engraving.test.mjs` | M | U | Include | sourceEngraving.ts | FE: grouping/nonmutation |
| 20 | `frontend/tests/user-ties-check.test.mjs` | M | U | Include | shared editor/tie controls | FE: explicit choices/advisory checks |
| 21 | `frontend/tests/visual-review.test.mjs` | M | U | Include | viewer/shared editor | FE, UI: mocked renderer limits |
| 22 | `CONCERT_KEY_TRANSPOSITION.md` | ?? | C | Review | C implementation/tests | DR: historical counts/layout and acceptance |
| 23 | `S2A_02_UNIFIED_WORKSPACE.md` | ?? | U | Review | C/U, test_concert_workspace.py | DR: historical checkpoint, pending claims |
| 24 | `UX_01_FIX_REPORT.md` | ?? | U | Review | U rendering/layout changes | DR: historical verification/acceptance |
| 25 | `UX_01_UI_REFINEMENT_REPORT.md` | ?? | U | Review | U components/styles/tests | DR: historical verification/acceptance |
| 26 | `UX_02A_FIX_IMPORT_REPORT.md` | ?? | U | Review | Home.tsx, concert-transpose tests | DR: import continuity evidence |
| 27 | `UX_02A_LANDING_REPORT.md` | ?? | U | Review | Home.tsx, styles/tests | DR: landing evidence |
| 28 | `backend/P0_2_1_USER_DRIVEN_TIE_AND_OPTIONAL_CHECK.md` | ?? | D | Review | existing tie implementation/history | DR: superseding sections/limits |
| 29 | `backend/P0_2_2_SIMULTANEOUS_NOTES_MULTI_TIE_FIDELITY.md` | ?? | D | Review | existing multi-tie implementation/history | DR: historical functional evidence |
| 30 | `backend/P0_2_DIRECT_PITCH_DRAG_IMPLEMENTATION.md` | ?? | D | Review | existing pitch interaction/history | DR: historical functional evidence |
| 31 | `backend/P0_3_MUSIC_SEMANTICS_VOICE_MAPPING_AUDIT.md` | ?? | D | Review | cited source/test snapshots | DR: findings are not approved fixes |
| 32 | `backend/P0_3_REAL_BENCHMARK_EVIDENCE_AUDIT.md` | ?? | D | Review | cited benchmark/probe artifacts | DR: artifact availability/provenance |
| 33 | `backend/P0_3_SMALL_NOTE_REGRESSION_RCA.md` | ?? | D | Review | cited history and local probes | DR: bounded hypotheses/confirmed evidence |
| 34 | `backend/P0_5_SMALL_NOTE_CLASSIFICATION_RENDERING.md` | ?? | D | Review | existing rendering work/history | DR: implementation and acceptance scope |
| 35 | `backend/P0_BROWSER_ACCEPTANCE_UX_FIX.md` | ?? | D | Review | earlier editor/UI work | DR: historical browser claims |
| 36 | `backend/P0_SCANNER_CORRECTION_EDITOR_IMPLEMENTATION.md` | ?? | D | Review | earlier editor implementation | DR: historical capability claims |
| 37 | `backend/PHASE4F1_SOURCE_FIDELITY_HALF_NOTE_DIAGNOSTIC.md` | ?? | D | Review | captured source/OMR/XML evidence | DR: diagnostic provenance and limits |
| 38 | `backend/PHASE4F1_SOURCE_LAYOUT_DIAGNOSTIC.md` | ?? | D | Review | captured layout/source evidence | DR: historical renderer findings |
| 39 | `backend/SCANNER_CORRECTION_EDITOR_CAPABILITY_AUDIT.md` | ?? | D | Review | earlier source/capability snapshot | DR: current versus historical capability |
| 40 | `backend/SCANNER_FIDELITY_RECOVERY_ARCHITECTURE.md` | ?? | D | Review | historical evidence; no architecture decision reopened | DR: preserve proposal, not approved implementation |
| 41 | `backend/app/music/musicxml/concert_key.py` | ?? | C | Review | existing transposer/document helpers, C tests | BC: algorithm/integrity/limitations |
| 42 | `backend/tests/music/test_concert_key.py` | ?? | C | Include | concert_key.py | BC: synthetic invariants |
| 43 | `backend/tests/test_concert_key_api.py` | ?? | C | Include | routes, concert_key.py, test helpers | BC: confirmation/API/export-reimport |
| 44 | `backend/tests/test_concert_workspace.py` | ?? | C | Include | C routes, music/test_concert_key.py, existing workflow helpers | BC: edited-result Save/reimport/source isolation |
| 45 | `frontend/src/components/ConcertTranspose.tsx` | ?? | U | Review | C API client, shared editor/save helpers | MX: functional integration plus UX, FE, BC, UI |
| 46 | `frontend/tests/concert-transpose.test.mjs` | ?? | U | Include | Home.tsx, ConcertTranspose.tsx, C client | FE: workflow/confirmation/source isolation |
| 47 | `frontend/tests/standalone-ties.test.mjs` | ?? | F | Hold | review-cungdemtimung.musicxml (direct file read) | FT; exclude from checkpoint, preserve unchanged |
| 48 | `review-cungdemtimung.musicxml` | Ignored, local | F | Hold | standalone-ties.test.mjs | PO local-artifact policy; preserve unchanged |

## New governance records outside GOV-02

| File | Git | Group | Disposition | Dependencies | Required verification |
| --- | --- | --- | --- | --- | --- |
| `PROJECT_STATE_AND_DECISIONS.md` | ?? | D | Review | constitution, acceptance criteria, reports and explicit PO statements | DR, Technical Lead review |
| `BASELINE_MANIFEST.md` | ?? | D | Review | GOV-02 inventory and current short status | exact path/status completeness, DR, diff-check |

## Proposed commit boundaries and outstanding decisions

1. Combined C/U: `feat: checkpoint shared Review and Transpose workflows`.
2. D: `docs: record baseline evidence and local artifact policy`.

These groups are logical, not an executable staging plan. C and U are coupled:
backend imports require the new module; Home and ConcertTranspose require the
client; shared editor/viewer changes mix earlier functionality and accepted UX.
Prefer a combined implementation checkpoint to unverified intermediate commits.
Keep dependent tests with their code. Exclude both F files from the checkpoint
while preserving/running them locally. No artifact-free candidate is verified.

GOV-06 reconciles README status and records explicit PO confirmations: P0.6B
Tie Up/Down, Undo/Redo and MusicXML Save/Download/Reimport accepted; corrected
MusicXML export accepted within verified Stage 1 scope; UX-03C accepted.
Concert-Key Transposition has automated and UI verification evidence; transposed
MusicXML export is implemented. Transposed PDF Export and Stage 2 saxophone
transposition are not implemented. Recognition duration issues remain deferred.
Historical reports remain unchanged, with their original evidence and limitations.

## P05 dependency resolution and GOV-08 index preparation

GOV-07 changed only the test fixture dependency and added independent synthetic
data. All nine assertion statements were unchanged; original/updated targeted
runs passed five cases each, and the full backend suite passed 788 tests.

| File | Git | Disposition | Dependency and implication |
| --- | --- | --- | --- |
| `backend/tests/music/fixtures/p05_benchmark_raw.musicxml` | D in index; ignored local copy | Exclude from future snapshot | GOV-08 index-only removal; local contents unchanged |
| `backend/tests/test_p05_small_note_preservation.py` | M, unstaged | Include with synthetic fixture | Reads p05_synthetic_preservation.musicxml; assertions unchanged |
| `backend/tests/music/fixtures/p05_synthetic_preservation.musicxml` | ?? | Include with P05 test | Independently authored GOV-07 fixture, not a user artifact |
| `.gitignore` | M, unstaged | Include repository policy | Exact artifact paths and /local-user-artifacts/; existing rules retained |

PO policy excludes user-imported PDFs/images and resulting MusicXML/PDF files
from GitHub. Copyright compliance when users share files is their responsibility;
copyright enforcement is outside application scope. Save/Export is unchanged.
GOV-08 explicitly authorized `git rm --cached --` for the original P05 path only.
Preflight confirmed both fixtures exist, the P05 test uses the synthetic fixture,
and no other active backend/frontend test references the original filename.
The sandbox initially denied index.lock creation; the authorized exact command
then succeeded outside the sandbox. The sole cached name-status entry is
`D backend/tests/music/fixtures/p05_benchmark_raw.musicxml`; no artifact is staged
for addition. Original SHA-256 before and after:
`ce6213fdc50f3c9646a4e5eded76caaf4e041c30097b2f2bcafcce241aa9af1e`.
The local file remains intact. Ignore rules protect both original local artifacts
and every file type under /local-user-artifacts/ without global extension rules.
Synthetic fixtures remain eligible. No application storage/Save/Export changes.
The original remains in earlier Git history; this task neither removes history
nor certifies earlier publication status.

## Candidate scope and verification

Proposed checkpoint scope: the prior 48 eligible changed files (26 C/U production
and independent-test files, 22 documents), plus .gitignore, the P05 test dependency
change and its new synthetic fixture, plus the authorized index-only P05 removal:
52 candidate paths. The standalone frontend test and its ignored local artifact
remain outside the checkpoint. Other existing independent tests/synthetic fixtures
remain inherited. Only the original P05 removal is staged; no other staging is
authorized by GOV-08. Keep its removal and the synthetic test migration together
in the eventual checkpoint so a clean checkout retains the P05 dependency.

GOV-04 recorded 788 backend tests, 270 frontend tests, lint, build and diff-check
PASS; backend required an outside-sandbox retry after a test-client portal timeout.
GOV-06 ran full suites including local artifact-dependent tests, with no tests
disabled or weakened. Passing tests do not grant PO acceptance or certify a
future artifact-free candidate tree.

### GOV-06 actual verification (2026-10-14)

Backend command from `backend/`, run outside the sandbox because GOV-04 already
established the sandbox test-client portal stall:

```bash
timeout 90s env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests -p no:cacheprovider -o faulthandler_timeout=60
```

PASS: 788 tests in 27.90 seconds, two existing Starlette/AnyIO deprecation warnings.
No tests excluded. Frontend commands from `frontend/`:

```bash
node --test --test-isolation=none --test-reporter=dot tests/*.test.mjs
npm run lint
./node_modules/.bin/tsc -p tsconfig.app.json --incremental --tsBuildInfoFile /tmp/gov06-app.tsbuildinfo
./node_modules/.bin/tsc -p tsconfig.node.json --incremental --tsBuildInfoFile /tmp/gov06-node.tsbuildinfo
./node_modules/.bin/vite build --configLoader runner --outDir /tmp/gov06-build
```

Frontend suite PASS: 270 tests, including the standalone local-fixture cases.
Lint was invoked equivalently from root as `npm run lint --prefix frontend`:
PASS. Type checks and production build PASS; existing large-bundle warning and
informational outside-project output-directory warning remain. Build outputs
and incremental metadata went to `/tmp`, not repository build artifacts.
Root `git diff --check` PASS; separate new-document whitespace checks reported
no whitespace errors. No browser/Save-Reimport run was performed by GOV-06;
the explicit P0.6B PO acceptance remains recorded independently of these tests.

### GOV-08 verification

P05 targeted suite: 5 passed. Complete backend suite: 788 passed in 30.32 seconds,
two existing Starlette/AnyIO deprecation warnings. Full frontend suite: 270 tests
passed with no exclusions. Frontend lint, both TypeScript project checks and Vite
production build passed. Build retains the large-bundle warning and informational
outside-project output-directory warning; outputs went to /tmp/gov08-build and
TypeScript incremental metadata to /tmp/gov08-*.tsbuildinfo.

Backend pytest used the existing virtual environment, disabled plugin autoload
and pytest caching, and retained all tests. Full backend execution used the
established outside-sandbox test-client workaround. Frontend ran
`node --test --test-isolation=none --test-reporter=dot tests/*.test.mjs`;
lint used `npm run lint --prefix frontend`. TypeScript checked tsconfig.app.json
and tsconfig.node.json, followed by `vite build --configLoader runner`.

Both `git diff --check` and `git diff --cached --check` passed. Inspected short
status and cached name-status: only the exact P05 artifact is staged, as deletion;
no user artifact is staged for addition. `git check-ignore -v` confirms the exact
P05 and root MusicXML paths and the dedicated directory for PDFs/images/scores.
The synthetic fixture is not ignored. SHA-256 of the original remains the value
recorded above. Comparison of 227 preexisting repository files found only
.gitignore and this manifest changed; no files were missing. Application code,
tests, regression assertions, both fixtures and other documentation are untouched.

Current preparation: IN PROGRESS pending Technical Lead review. GOV-08 checks
support GO for the next controlled baseline-preparation checkpoint, not a commit
of the current index alone. The P05 dependency and future-snapshot exclusion blockers are resolved
within the authorized scope. No new functional acceptance is declared. A complete
artifact-free candidate checkout is not verified by tests on the current local
tree, which still includes the excluded standalone test/artifact. Further staging,
commit and push require explicit authorization. No history rewrite, local deletion,
reset, restore, clean or stash is authorized.
