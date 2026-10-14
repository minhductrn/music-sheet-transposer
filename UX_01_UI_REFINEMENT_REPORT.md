# UX-01 — Approved UI refinement

Date: 2026-10-12. Authorization: IMPLEMENT_APPROVED_UX, Checkpoint 2 approved by Technical Lead after Checkpoint 1.

Status: IN PROGRESS — implementation and automated verification prepared; STOPPED for Technical Lead review. Visual verification is incomplete. Product Owner acceptance is not claimed.

## References and scope

Read AGENTS.md, PRODUCT_CONSTITUTION.md, ACCEPTANCE_CRITERIA.md and S2A_02_UNIFIED_WORKSPACE.md. All three user-provided reference images were accessible and used as the visual authority. Work is limited to approved frontend components, styles, relevant frontend tests and this report. No dependencies were added.

## Implemented layout

- One compact header: Music Sheet Transposer, Import PDF / Image, Open MusicXML. Stage 1 Save is in this header. Connection status is a small accessible indicator. The workflow banner, upload card and connection card are removed.
- Before opening/importing, the interface provides compact selection/settings without empty score panels. The optional original-source comparison input remains available.
- Stage 1 retains equal-width Original / My Score panels. Key/Instrument controls belong only to Concert mode. Recognition settings, warning details, baseline/Audiveris downloads and the accepted semitone workflow are available through contextual More controls.
- Concert places Key and Instrument above the panels, followed by compact Source Key confirmation and direction controls and Apply. Original uses a read-only viewer; My Score uses the existing editor. Save below the panels requests independent Concert MusicXML through the existing result save path. Instrument defaults to Concert; all unimplemented choices are disabled. There is no Share or Export PDF action.
- My Score's persistent chrome has two rows: its header with Undo, Redo, Fit, minus, numeric zoom/reset and plus; then Select, Note, Lyrics, Tie, More. Existing contextual controls appear under the selected tool. Duplicate history buttons and separate persistent editing toolbars are removed.
- Original MusicXML and source images use the same independent viewport Fit/Zoom controls as My Score. PDF uses its native embedded viewer with separate Fit/Zoom and page controls, plus Open source fallback. Each pane owns its own zoom state.
- Responsive CSS stacks the equal-width desktop panels below 900px. Controls wrap at narrow widths. Styling follows the references' light background, thin neutral borders, rounded panels, compact typography, pill-shaped file/key controls and dark primary actions.

Both Review and Concert sessions remain mounted when changing workspace mode. Their source/result separation and unsaved-change protections remain intact. No result is automatically promoted to the saved source.

## Complete control mapping

| Approved location | Existing operations retained |
| --- | --- |
| Select | Score click/keyboard selection; selection context; cancellation of active insertion/tie interactions |
| Note | Add note, delete selected notation, pitch letter/octave, pitch drag, duration, explicit accidentals including double alterations/clear, Normal/Small and retained Cue display, duration-bearing/grace timing |
| Note contextual insertion | Visual caret placement, selected note's exact onset, pitch/accidental/duration/size/timing drafts, primary/secondary voice choice, Add/Cancel |
| Note contextual position and properties | Add at musical position, correction measure and insertion staff; explicit onset/voice/new voice/rest insertion; empty-measure first event; before/after/simultaneous additions; staff-step pitch correction; detailed numeric properties and Apply correction; explicit destination measure/onset/voice/staff ownership |
| Lyrics | Existing LyricEditor, verse/segment selection, additional verses, text apply/delete, normal-note lyric owner selection, selected-event lyrics; Direct Lyric Editor remains attached to visible lyrics with its existing Enter/Escape, composition, stale-binding and owner-fallback protections |
| Tie | Add/cancel tie, score-based source/destination selection, destination dropdown, removal, explicit Tie Up and Tie Down; contextual exact endpoints and inserted-note tie controls; existing technical eligibility/error handling |
| More | Visual/Advanced access, reload, technical diagnostics/Inspect event, advisory Check score and source confirmation, title/printed-credit editing, harmony root/alter/kind/display text/add-before-event; corrected/transposed semitone preview selection; recognition details/settings/downloads and interval transposition |
| Header row | One accessible Undo/Redo pair and Fit/minus/current percentage/plus; percentage also resets to 100% |
| Save/file actions | Stage 1 header Save submits the existing editor save handler; contextual Save As and saved MusicXML export; download acknowledgement, close/discard confirmation and recovery download; Concert bottom Save retains the existing independent Save As behavior and acknowledgement |
| Original pane | Independent Fit/Zoom; PDF page selection; Open source for both images and PDFs; source-evidence highlighting/details; native viewer fallback |

Common Note, Lyrics and Tie actions are directly under their corresponding tool. Detailed forms remain contextual/disclosed rather than permanently expanded above the notation. Existing Apply buttons, validation and disabled states are preserved. The legacy advanced inspector is available under Note and Tie; it is not required to access common pitch/size/lyric/direction actions.

## Changed files

Frontend implementation:

- `frontend/src/components/Layout.tsx`: remove duplicate application title header.
- `frontend/src/pages/Home.tsx`: compact shared header, Stage 1 Save/form association and contextual secondary controls.
- `frontend/src/components/RecognitionReview.tsx`: compose the accepted editor into two toolbar rows and contextual tool groups; retain existing handlers and save logic.
- `frontend/src/components/ScoreCorrectionToolbar.tsx`: five labeled groups; existing note operations and explicit tie directions within their contexts.
- `frontend/src/components/MusicSheetViewer.tsx`: accept header/tool content and use a zoom viewport for both editable and read-only MusicXML.
- `frontend/src/components/ReviewScoreViewport.tsx`: consolidate panel title/history/zoom in its header; retain engraving and zoom calculations.
- `frontend/src/components/SourceViewer.tsx`: shared image Fit/Zoom, independent native PDF controls and retained Open source/evidence paths.
- `frontend/src/components/ConcertTranspose.tsx`: Key/Instrument/Apply placement, compact confirmation and bottom Save; original/result isolation retained.
- `frontend/src/index.css`: reference-based light styling, compact controls and responsive panels.

Frontend tests updated: `concert-transpose.test.mjs`, `local-score-file.test.mjs`, `review-insertion.test.mjs`, `review-lifecycle.test.mjs`, `review-selection.test.mjs`, `review-workspace.test.mjs`, `score-correction.test.mjs`, `source-engraving.test.mjs`, `user-ties-check.test.mjs`, and `visual-review.test.mjs` under `frontend/tests/`.

Existing test tree traversal now follows actual React composition slots (`headerActions`, `toolbar`, `context`, `moreControls`). Selectors follow Apply/Save and accessible history labels; toolbar mutation tests explicitly select the corresponding tool. Existing correction payload, persistence, revision, identity and source-isolation assertions remain. Six new UX tests cover contextual visibility, retained tool state, header/history composition, independent zoom, Stage 1 form association/mode-specific Save, validated form saving/acknowledgement, and source image/PDF UI controls (some cases combine multiple requirements).

## Verification

Final results:

| Check | Command | Result |
| --- | --- | --- |
| Full frontend suite | `mapfile -t frontend_tests < <(rg --files tests -g '*.test.mjs' | sort)` followed by `node --test --test-isolation=none --test-reporter=tap "${frontend_tests[@]}"` from frontend | PASS — 256 tests, zero failures/skips, 4.94 seconds |
| Frontend lint | `npm run lint --prefix frontend` | PASS |
| Frontend production build | `npm run build --prefix frontend` | PASS — existing large-chunk warning remains |
| Whitespace | `git diff --check` | PASS |
| Worktree inventory | `git status --short` | Completed; all work remains uncommitted |
| Baseline preservation | SHA-256 comparison against `/tmp/ux01-baseline/hashes.json` | 19 existing frontend source/test files changed; the other 201 existing files unchanged |
| Handler preservation | Text comparison against the preflight backup | RecognitionReview's complete `saveScore` implementation unchanged; Home's handler section from `mayReplace` through download unchanged |

Final frontend suite log: `/tmp/ux01-frontend.log`. Preflight frontend backups and hashes: `/tmp/ux01-baseline`.

Intermediate checks were not all passing: moving JSX initially introduced a Home syntax error, corrected before the final build. The first suite run exposed selectors and tree walkers tied to the previous layout. Subsequent runs exposed an updated fixture dropping insertion props, and two new test setup/cleanup mistakes; these were corrected. The final full run passes. No unresolved automated failure is hidden or treated as a PASS.

The full frontend suite retains regression coverage for pitch/duration/size and insertion, direct lyrics/ownership, tie creation/removal/direction, Undo/Redo, saved-snapshot exports and acknowledgement, source-key confirmation, edited Concert result persistence and unsaved replacement protection. Frontend interaction tests use the repository's TypeScript/React callback harnesses, not a real browser.

Backend tests were not rerun for this frontend-only task. Backend sources/tests, API service code, MusicXML utilities/semantics, package manifests/lockfiles and governance documents are unchanged relative to preflight. No Instrument Transposition was implemented or functionally tested.

## Screenshot comparison and visual limitations

Browser access was unavailable: no browser tools were exposed; Firefox/Chromium/Chrome executables and common installation/cache paths were absent; Playwright/Puppeteer packages were not installed. No dependencies or browser installation were introduced. No implemented browser screenshots were produced, and no mock image is offered as screenshot evidence.

| Required screenshot | Reference and implemented structure | Visual result |
| --- | --- | --- |
| Stage 1 Import / Review | B: compact title/import/open/save header, equal Original/My Score panels | INCOMPLETE — browser screenshot and default readability not verified |
| Concert workspace | A: Key/Instrument/Apply above Original/My Score, Save below | INCOMPLETE — browser screenshot and pixel comparison not verified |
| My Score — Note | C: two toolbar rows, contextual note actions and property controls | INCOMPLETE — browser screenshot and contextual height not verified |
| My Score — Lyrics | C: same chrome, contextual lyric/verse/owner controls | INCOMPLETE — browser screenshot and direct-editor placement not verified |
| My Score — Tie | C: same chrome, explicit source/destination, Remove and Up/Down | INCOMPLETE — browser screenshot and visible direction controls not verified |

Known deliberate differences required by approved functionality: compact Source Key confirmation and interval direction supplement Reference A; Review/Transpose mode selection remains available; native PDF page/Open source controls remain; PDF export shown in A is omitted because it is unavailable. The reference's decorative expand controls are not replaced by an invented fullscreen workflow. Open source provides the existing external-source action. These differences are recorded for Technical Lead review.

Pixel accuracy, desktop/narrow-screen usability, actual score readability at Fit, native file dialogs, Firefox downloads and browser unsaved prompts remain unverified. Native PDF Fit requests `zoom=page-width`; honoring this fragment, native viewer chrome and zoom behavior vary by browser. Open source remains the fallback. No new PDF renderer was added.

## Governance and acceptance

PC-01: OMR import and direct MusicXML opening remain separate. PC-02: accepted correction handlers and all supported editing operations are reused. PC-03/05: canonical MusicXML save, exported snapshots, acknowledgement and reimport paths remain unchanged. PC-04: saved source and independent Concert result remain isolated; no instrument stage added. PC-06: explicit key confirmation, tie directions and advisory checks remain under user control. PC-07: all applicable frontend regressions pass. PC-08: implementation stops for Technical Lead review; Product Owner controls functional acceptance.

Acceptance checklist evidence: frontend regressions cover note properties/addition/deletion, lyrics/associations, ties/directions, Undo/Redo and persistence/export state. The existing backend score-semantic checks are unchanged but were not rerun. Instrument-specific acceptance is outside this task. UI visual behavior requires browser verification; automated success does not certify it.

Gate 1: implementation prepared within approved frontend scope; Technical Lead review pending.
Gate 2: applicable automated frontend checks PASS; browser visual evidence incomplete as explicitly allowed when access is unavailable.
Gate 3: NOT COMPLETE — awaiting Technical Lead review of this implementation.
Gate 4: NOT COMPLETE — no Product Owner acceptance recorded.

STOPPED after implementation and verification for Technical Lead review. Status remains IN PROGRESS, not TECHNICALLY VERIFIED or ACCEPTED.
