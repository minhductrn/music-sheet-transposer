# UX-02A — Initial Landing Page Refinement

Status: IN PROGRESS — awaiting Technical Lead review and Product Owner visual acceptance.

## Scope and preflight

Read AGENTS.md, PRODUCT_CONSTITUTION.md and ACCEPTANCE_CRITERIA.md. PROJECT_STATE_AND_DECISIONS.md was not available locally. Inspected Home's file actions, import settings, workspace branches and CSS. Ran `git status --short` before editing.

Preexisting uncommitted work included README/backend transpose/API changes; frontend Layout, Home, renderer, correction, viewport, source-viewer, API, engraving and regression-test changes; untracked ConcertTranspose and its tests; earlier reports, backend diagnostics/tests/Concert implementation and review-cungdemtimung.musicxml. Preserved all of it. No Git staging, commit, push, reset, restore, clean or stash was performed.

A pre-edit SHA-256 inventory is /tmp/ux02a-baseline.json; the original Home source is /tmp/ux02a-home-before.tsx. Inventory comparison confirms this task modified only the three frontend files below, plus this new report. No score-rendering or workspace component was modified.

## Files and before/after structure

- frontend/src/pages/Home.tsx: reuse the existing file-action JSX in one location at a time. Initial header retains identity and small connection indicator. A centered welcome area displays “Your music, your way.”, the specified introductory sentence and exactly two prominent file actions. After selecting a file, actions occupy their existing compact header position. Removed the duplicate empty-state instruction. More retains optional source/diagnostic controls; errors remain visible.
- frontend/src/index.css: added landing-only centered typography, balanced white action surfaces, subtle borders, restrained blue hover/focus accents and responsive stacking below 560px. Loaded-workspace styling is unchanged.
- frontend/tests/concert-transpose.test.mjs: three focused tests for central action count/header absence, PDF selection into existing recognition setup, and MusicXML transition with preserved Review/Transpose header controls.
- UX_02A_LANDING_REPORT.md: this report.

Before: Import/Open in the header, followed by an empty-state instruction and secondary settings.
After: title in the header; centered welcome/message/Import/Open; secondary More below. Selecting PDF/image shows existing recognition setup. Opening MusicXML shows the existing Review workspace and retained Concert session.

The extracted file-action markup, input IDs, accepted types, disabled behavior and onChange handlers are textually identical to the pre-edit block. No new file handling or application state was added. Existing replacement confirmation, recognition flow, createReview, saved-source snapshot and mode switching are reused.

## Verification

Commands executed from repository root:

| Command | Result |
| --- | --- |
| `node --test --test-isolation=none --test-reporter=tap frontend/tests/concert-transpose.test.mjs` | PASS — 17 tests, zero failures/skips |
| `node --test --test-isolation=none --test-reporter=tap frontend/tests/*.test.mjs` | PASS — 266 tests, zero failures/skips |
| `npm run lint --prefix frontend` | PASS |
| `npm run build --prefix frontend` | PASS; existing large-chunk warning remains |
| `git diff --check` | PASS |

Logs: /tmp/ux02a-focused.log, /tmp/ux02a-full.log, /tmp/ux02a-lint.log, /tmp/ux02a-build.log.

Regression safeguards: full existing frontend suite covers correction, tie direction, history, persistence, unsaved replacement protection, Concert operations and rendering lifecycle. Existing editor/renderer/OSMD components, backend/APIs, Fit/Zoom, serialization, transposition and save operations were not edited. No dependencies or persistent state were introduced. Backend verification is inapplicable to this frontend-only landing change.

Focused tests exercise Home's real handlers through the repository's controlled React/API harness. They do not certify native file dialogs, browser layout or visual acceptance. No browser executable is available; Firefox visual verification is incomplete. No fresh screenshots were generated.

## Manual Firefox checklist

1. Fresh load: title, welcome text and exactly two balanced central actions; no duplicate header Import/Open or duplicate instruction.
2. Keyboard navigation: both file inputs reachable, visible focus; More remains secondary.
3. Select PDF/image: existing recognition setup appears with filename/profile/quality/recognize; compact header actions return. Cancel picker: landing remains.
4. Open saved MusicXML: existing Review comparison and header Import/Open/Save appear. Switch to Transpose: compact approved controls remain.
5. Make unsaved edits in both sessions; switch modes and attempt replacement. Confirm retained edits and existing replacement protection.
6. Narrow browser below 560px: actions stack without horizontal overflow; text remains readable. Inspect loading/error states and compare visual hierarchy with supplied reference.

## Governance and acceptance

PC-01 through PC-06 are preserved through unchanged score workflows/data boundaries. PC-07 is supported by full regression checks. PC-08 and acceptance gates reserve review and acceptance to the Technical Lead and Product Owner. Implementation and automated verification are complete; Technical Lead review and Product Owner visual acceptance are pending. No TECHNICALLY VERIFIED or ACCEPTED status is claimed. Stopped for review.
