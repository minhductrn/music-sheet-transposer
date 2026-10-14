# S2A-02 implementation and verification report

Date: 2026-10-12. Authorization: IMPLEMENT_APPROVED_UX.
Status: IN PROGRESS — implementation and automated verification are ready for Technical Lead review. Neither TECHNICALLY VERIFIED nor ACCEPTED is claimed.

## Implementation

One labeled Open MusicXML file input in the Concert Workspace opens a saved file directly through `createReview`, without OMR. Review and Transpose select the same source without a second file selection. PDF/image recognition remains a separate import disclosure. Optional original-source comparison remains available when opening a review.

Review reuses RecognitionReview with its default Original Source / Working Score comparison, visual and advanced correction tools, Direct Lyric Editor, score checks, Undo/Redo, and existing Save/Save As/export paths. The accepted semitone workflow remains available in Review's Interval transposition disclosure; its action is labeled Transpose by semitones to distinguish it from workspace navigation.

Transpose automatically inspects the opened saved snapshot with the existing S2A-01A API. Its compact controls retain explicit Source Key choice/confirmation, compatible candidates, Target Key, and direction. One-flat input without mode offers F major and D minor without selecting either. Incompatible choices cannot be confirmed. Source-key changes clear confirmation; key/direction/confirmation changes invalidate results after any required discard confirmation.

The desktop workspace places Original Concert on the left and Transposed Concert on the right; CSS stacks panels below 900px. Original uses MusicSheetViewer with interaction explicitly disabled and no correction controls. Result creates an independent Stage 1 review session and reuses RecognitionReview in a result-only composition. This option omits its internal source pane and canonical-source persistence actions; all correction tools retain their existing semantics. Result persistence lives above the two panels.

Save As Concert MusicXML verifies the current result session and exports its current canonical MusicXML through the existing Stage 1 endpoints. It requests an independent browser download, rejects the source filename, and requires an explicit acknowledgement before reporting that the result was saved. Later edits invalidate acknowledgement for the current revision. The initial transposition blob never substitutes for the edited export. The retained download is reopened through Open MusicXML.

## State and discard protection

- Saved source: the immutable File selected through Open MusicXML. Review saves and result edits never replace it.
- Review working state: its own ReviewSession and revision-matched saved-file state.
- Initial result: an independent transposition blob and result metadata.
- Edited result: a separate ReviewSession; corrections, checks and history use the accepted editor/API.
- Download requested: a revision-specific snapshot awaiting user acknowledgement.
- User-acknowledged save: a separate revision-specific SavedScoreFile.

Both modes remain mounted while hidden, preserving their editor/history/save state on mode switches. File replacement checks unsaved work in either session. Retransposition and key/direction changes check unsaved result work. Review close confirms discarding unsaved work. PDF selection, recognition reruns, recognition-profile changes and quality changes also guard replacement. A beforeunload handler protects pending applied score changes on page exit. Backend failures while preparing a replacement result leave the previous result available.

A result is never automatically promoted to the source. Opening a retained saved file is the explicit promotion operation. No database, cloud persistence, instrument transposition, PDF export, OMR algorithm, key-detection algorithm or transposition-engine changes were made.

## Changed files for this task

- `frontend/src/pages/Home.tsx`: shared open/navigation, source snapshot, session isolation and replacement guards.
- `frontend/src/components/ConcertTranspose.tsx`: existing key controls integrated with independent editable result and current-revision Save As.
- `frontend/src/components/RecognitionReview.tsx`: optional result-only composition and close safeguard; default comparison remains.
- `frontend/src/index.css`: responsive panels and compact concert controls.
- `frontend/tests/concert-transpose.test.mjs`: 13 workflow/API regressions covering ambiguity, explicit confirmation, compatibility, state isolation, editor composition, current edited export, acknowledgement and discard protection.
- `frontend/tests/review-lifecycle.test.mjs`: existing lifecycle regressions adapted to the unified input and distinct semitone-action label. Existing corrected-master/stale-revision assertions remain.
- `frontend/tests/review-workspace.test.mjs`: existing layout-order assertion adapted to the conditional class expression.
- `backend/tests/test_concert_workspace.py`: synthetic integration test for concert transpose, right-panel API edits, independent export and reimport.
- This report.

Before editing, all 25 preexisting modified/untracked files were backed up and hashed under `/tmp/s2a02-baseline`. Only Home, ConcertTranspose and its workflow tests changed among those files, as required by the authorized integration. The other 22 match their preflight SHA-256 hashes, including README, backend API/engine/tests, frontend API, technical documents and private MusicXML. No preexisting file was removed. Governance documents were not edited. No Git add, commit, push, reset, restore, clean or stash was performed.

## Automated verification

Final commands and results:

| Check | Command | Result |
| --- | --- | --- |
| Full backend | `cd backend; PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q tests -o faulthandler_timeout=30` | PASS: 788 passed, two existing Starlette/AnyIO deprecation warnings, 23.32s |
| Full frontend | From frontend: collect every `tests/*.test.mjs` recursively with `rg --files tests -g '*.test.mjs'`, sort, then `node --test --test-isolation=none --test-reporter=tap "${frontend_tests[@]}"` | PASS: 250 passed, no exclusions or skips, 7.08s |
| Lint | `cd frontend; npm run lint` | PASS |
| Production build | `cd frontend; npm run build` | PASS; existing large-chunk warning remains |
| Whitespace | `git diff --check` | PASS |
| Worktree inventory | `git status --short` | Completed; preexisting work retained, task edits and new test/report remain uncommitted |

Final suite logs: `/tmp/s2a02-backend-full.log` and `/tmp/s2a02-frontend-full.log`.

Earlier checks and corrections: sandboxed backend runs stalled before test execution inside the Starlette/AnyIO thread portal and were interrupted. A faulthandler trace identified that wait. Running the same suite outside the sandbox completed. The first frontend pass exposed obsolete entry-point selectors and a new test's whitespace-sensitive assertion; these were corrected while retaining regression intent. The first backend run outside the sandbox passed 787 existing tests and failed the new test because lyrics are represented in MusicXML rather than an event `lyrics` field. That assertion was corrected to compare XML lyric nodes. The final full suites above pass.

## Requirement evidence and limits

| Required area | Evidence | Limit / remaining check |
| --- | --- | --- |
| A: Stage 1 | Full existing frontend/backend suites; default editor tools and comparison composition retained; lifecycle regressions retain corrected-master and revision gating assertions | Actual browser acceptance of all correction tools remains pending |
| B: Unified entry | Home callback tests open one File, switch modes, retain Review revision and assert the exact saved File remains the concert input; no OMR call | Native file dialog interaction not browser-tested |
| C: Source confirmation | Frontend major/minor ambiguity, explicit suggestion, incompatible key and invalidated-confirmation tests; existing API key tests pass | Browser interaction remains pending |
| D: Two panels | Tests assert separate labeled panes, viewer-only original and accepted editor result; responsive CSS added | Desktop/narrow-screen visual layout not browser-tested |
| E: Musical benchmark | New synthetic API test verifies one flat → three flats, Gm → Fm, C7 → B-flat7, F → E-flat; unrelated notation invariant matches before/after transpose | `concert-cungdemtinmung.musicxml` is unavailable. The differently named preexisting `review-cungdemtimung.musicxml` was preserved and was not treated as the approved benchmark |
| F: Edited result persistence | Frontend exports the latest edited revision, rejects source filename and tracks acknowledgement separately. Backend edits tie direction and Small Note state, exports/reopens actual scratch files, checks identities/directions, notes, lyrics, chords and source bytes | Actual downloaded-file reopen in Firefox remains untested |
| G: Unsaved safeguards | Cancel/approve tests for key, target, confirmation, direction and retransposition; pending Review/result file-replacement tests; modes preserve sessions | Native confirmations, page-exit prompt and unapplied text drafts not tested in a browser |
| H: Automation | All final commands above pass, including the full frontend suite with the historical private-fixture test included | Test harnesses stub React hooks/API for frontend interactions; they do not establish rendered browser behavior |

## Constitution and acceptance checklist

PC-01: MusicXML bypasses OMR; PDF/image path remains independent. PC-02: accepted correction engine reused. PC-03: saved source snapshot remains authoritative; right-panel edits are exported from their own current canonical session. PC-04: Stage 2A does not overwrite the source or rerun recognition; no instrument stage added. PC-05: XML-preserving export/reimport and relationship assertions pass. PC-06: explicit source-key confirmation and advisory score checks remain. PC-07: full regression suites pass. PC-08: Technical Lead and Product Owner decisions remain external gates.

Relevant acceptance checklist evidence includes note/pitch/size editing, addition/deletion, lyrics/associations, ties/identities/directions, Undo/Redo, canonical save, and export/reimport through existing regression suites, with a new edited-result persistence integration test. The instrument-specific Stage 2 checklist item has no new implementation in this frontend-only task; existing backend regressions still run. Actual user-visible functional validation is pending and is not inferred from test success.

Gate 1: authorized implementation prepared, pending Technical Lead review of scope and behavior.
Gate 2: automated checks PASS with the browser/benchmark limitations recorded above.
Gate 3: NOT COMPLETE — no Technical Lead review recorded.
Gate 4: NOT COMPLETE — no Product Owner acceptance recorded.

Status remains IN PROGRESS pending those reviews. Firefox acceptance, native download completion, real benchmark validation and responsive visual usability are not claimed.
