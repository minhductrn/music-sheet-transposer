# UX-02A-FIX — Import File Selection Continuity

Status: IN PROGRESS — implementation and automated verification complete; Technical Lead review and Product Owner acceptance pending.

## Preflight and confirmed root cause

Read AGENTS.md, PRODUCT_CONSTITUTION.md and ACCEPTANCE_CRITERIA.md, inspected Home import/open/recognition paths and ran `git status --short`. Preserved the existing uncommitted backend, frontend, test, documentation and MusicXML work. No prohibited Git operation was performed.

The observed transition is UI ambiguity, not demonstrated recognition-state loss:

- Home.tsx line 24 owns the main File in existing `file` state.
- The `sheet-upload` handler assigns the selected File to that state. Switching the file-action markup from landing to header does not reset Home state.
- The existing recognition handler, line 86, passes that same `file` directly to `recognizeSheetMusic(file, profile, inputQuality || undefined)`; createReview also receives it as recognition source.
- A separate `reviewSource` state, line 38, belongs to the optional comparison input. That input was a visible native chooser in Import Workspace. Its empty FileList does not mean the main recognition File is missing. It is used when opening MusicXML through createReview(selected, reviewSource), not as recognition request input.
- The filename already appeared in workspace metadata, but the optional chooser and absence of an explicit Change File label obscured which file was active.
- Separately, the previous main-input handler assigned null on an empty selection event. This was a confirmed cancellation-path defect, not evidence that the observed successful selection lost state.

The precise browser widget displaying the reported native text was not inspected live. Code establishes the visible optional chooser and the recognition-state ownership; Firefox confirmation remains pending.

## Exact files changed

1. frontend/src/pages/Home.tsx — explicit Recognition input filename/status in import setup; contextual Change File label on the existing primary input; ignore empty selection events; place optional comparison selection inside a labeled disclosure with explanation and an input ID. Existing `file` and `reviewSource` state are reused. No changes to recognition request logic, MusicXML Open handler, landing design/styles or workspace components.
2. frontend/tests/concert-transpose.test.mjs — optional recognition stub in existing Home harness and three focused cases (PDF, image, replacement/cancellation), asserting actual File identity and profile/quality arguments.
3. UX_02A_FIX_IMPORT_REPORT.md — this report.

The pre-edit Home source is /tmp/ux02a-fix-home-before.tsx. All source edits are limited to Home. No second source of truth, dependencies, backend contracts, OMR processing, rendering, editing, persistence or Fit/Zoom changes were introduced.

## Verification

Exact commands, from repository root:

| Command | Result |
| --- | --- |
| `node --test --test-isolation=none --test-reporter=tap frontend/tests/concert-transpose.test.mjs` | PASS — 20 tests, zero failures/skips |
| `node --test --test-isolation=none --test-reporter=tap frontend/tests/*.test.mjs` | PASS — 269 tests, zero failures/skips |
| `npm run lint --prefix frontend` | PASS |
| `npm run build --prefix frontend` | PASS; existing large-chunk warning remains |
| `git diff --check` | PASS |

New tests confirm PDF and image filenames persist; recognition receives the originally selected File despite independent optional comparison selection; profile/quality arguments remain functional; replacement uses the new File; an empty selection preserves the previous File. Existing Open MusicXML, workspace transition and unsaved-change regression checks pass unchanged.

Logs: /tmp/ux02a-fix-focused.log, /tmp/ux02a-fix-full.log, /tmp/ux02a-fix-lint.log, /tmp/ux02a-fix-build.log.

Tests use the existing controlled React/API harness. Native picker behavior and Firefox visual verification are incomplete because browser access is unavailable. Backend tests are inapplicable to this UI-only correction.

## Firefox checklist

1. From landing, select cungdemTinMung.pdf. Confirm Recognition input displays its name and no reselection is requested.
2. Repeat with an image. Change Recognition Profile and Source Quality; confirm the filename persists.
3. Expand Optional comparison source for MusicXML. Confirm the chooser is clearly secondary; selecting a reference does not replace the recognition filename.
4. Select Recognize Sheet Music. Inspect the recognition request's uploaded file/name and selected profile/quality.
5. Use Change File to select another PDF/image; verify filename and subsequent recognition upload change.
6. Cancel Change File; verify the previous filename and recognition input remain active.
7. Open MusicXML and exercise existing Review/Transpose and replacement-confirmation flows; confirm unchanged behavior.

## Governance

PC-01 OMR and PC-02 corrections remain untouched; PC-03/PC-04 authoritative saved-source workflows and PC-05 persistence are unchanged; PC-06 explicit user selection is preserved; PC-07 regression protection is supported by passing checks; PC-08 reserves acceptance to the Product Owner. Implementation and automated verification gates are complete within scope. Technical Lead review and Product Owner acceptance remain pending; neither TECHNICALLY VERIFIED nor ACCEPTED is claimed. Stopped for review.
