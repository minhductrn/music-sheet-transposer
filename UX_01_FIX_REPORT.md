# UX-01-FIX — UI correction report

Status: **IN PROGRESS — implementation and automated verification complete; browser verification and Technical Lead review pending.** No Product Owner acceptance is claimed.

## Authorization and evidence

Authorization: IMPLEMENT_UI_CORRECTIONS_ONLY. Read AGENTS.md, PRODUCT_CONSTITUTION.md and ACCEPTANCE_CRITERIA.md before implementation. All five distinct Firefox screenshots and the three approved references were visually accessible in the conversation. The fifth Firefox image was repeated twice; repeats were treated as duplicate evidence.

References A/B/C establish the compact Concert workspace, compact Stage 1 comparison and two-row contextual editor respectively. Firefox evidence, in supplied order:

1. Landing: workflow banner, large Backend connection and Concert Workspace cards, collapsed Import.
2. Opened MusicXML: redundant status text and empty Original with “No source retained”.
3. Review detail: empty Original beside a rendered editable score.
4. Concert before Apply: large Original engraving and empty result awaiting required confirmation.
5. Concert after Apply: Original at 70% and My Score at 50%, different system grouping and toolbar/notation offsets.

The current working tree already contained the earlier compact-header implementation; the supplied landing screenshots do not match that source. Preserved it, added structural regression coverage and moved the optional comparison-source input behind More on the empty landing. No claim is made that the supplied screenshots depict the current build.

## Changes in this task

| File | Change |
| --- | --- |
| frontend/src/pages/Home.tsx | Preserve direct Import PDF / Image and Open MusicXML actions; put optional comparison input and connection detail behind More on empty landing; expose connection failure as an alert. |
| frontend/src/components/RecognitionReview.tsx | When no PDF/image source exists, use the saved MusicXML Blob as read-only Original. Edits remain separate from that snapshot. |
| frontend/src/components/MusicSheetViewer.tsx | Read saved XML system breaks for standalone previews; use the same bounded, measured source engraving algorithm as editable Review. Apply the existing rhythmic small-note display treatment consistently to Original. Freeze engraving width independently of viewport/zoom and remove pane-triggered re-engraving. |
| frontend/src/utils/sourceEngraving.ts | Extract compatible, explicit system/page boundaries from MusicXML across parts; reject incompatible grouping. Does not modify XML. |
| frontend/src/components/ReviewScoreViewport.tsx | Keep each instance's independent zoom and existing measured Fit calculation; preserve relative scroll offsets when scale changes. |
| frontend/src/index.css | Keep equal grid columns and equal scroll-window heights; align Original's notation start with the compact editing row through a matching spacer. |
| frontend/tests/local-score-file.test.mjs | Test saved MusicXML Original presence, read-only behavior and snapshot preservation after edits. |
| frontend/tests/source-engraving.test.mjs | Test saved XML grouping, incompatible-part fallback and nonmutation. |
| frontend/tests/review-workspace.test.mjs | Test compact landing structure, equal-column CSS, measured Fit, displayed percentage, independent zoom and unchanged engraving width/children. Adapt effect cleanup harness. |
| frontend/tests/visual-review.test.mjs | Retain stale-load and selection checks; verify resize does not re-engrave. Update renderer boundary mocks. |
| UX_01_FIX_REPORT.md | This report. |

## Control and rendering behavior

Original Concert continues to read sourceFile.blob; My Score continues to read the independent result editing session. Review now also displays a saved MusicXML Original when no original image/PDF was supplied. Neither Original exposes editing callbacks. Canonical files, API operations and transposition data were not changed.

Saved XML with compatible explicit systems now uses the same renderer options, source-width seed and bounded graphical grouping verification as editable source-layout scores. Without trusted systems, engraving uses declared page width or the initial measured panel width (XML measure-width seed when mounted hidden), then remains fixed. Zoom transforms the existing engraving; changing zoom does not feed a width into OSMD or call updateGraphic/render. Fit remains computed from actual viewport.clientWidth divided by measured unscaled content width, capped at natural size, rather than an assigned percentage. Displayed percentage is the rounded actual transform scale. Each viewport retains its own state and observer measurements. Relative scroll offsets are adjusted on scale changes, subject to browser scroll clamping.

The compact My Score rows remain Undo/Redo/Fit/Zoom and Select/Note/Lyrics/Tie/More. Existing contextual correction controls, explicit Tie Up/Down, MusicXML Save/Save As, download acknowledgement and unsaved-change safeguards remain in place. No Instrument Transposition, Share or PDF Export was implemented or tested.

## Before/after comparison and verification limits

| Comparison | Before evidence | Implemented after behavior | Browser status |
| --- | --- | --- | --- |
| Landing versus A/B | Firefox 1–2: large cards/banner/collapsed Import | Existing compact header preserved; optional input moved to More; errors visible | Fresh screenshot unavailable |
| Original presence | Firefox 2–3: empty Original | Saved MusicXML fallback with read-only props; automated snapshot check | Fresh screenshot unavailable |
| Concert Fit versus A | Firefox 4–5: different engraving paths | Shared explicit-system engraving algorithm and measured per-pane Fit | Actual notation size/staff spacing visually unverified |
| Equivalent visible scale | Firefox 5: different percentages and grouping | Fixed engraving geometry, independent actual-scale percentage controls | Same-scale visual comparison unverified |
| Zoom behavior versus C | Firefox 5: inconsistent layout | Transform-only zoom, no pane-driven re-engraving; scroll adjustment | Browser zoom/scroll behavior unverified |

No Firefox/Chromium/Chrome executable was found, and no browser automation tool is exposed in this session. The supplied images were inspected, but they are before evidence. No after screenshots were generated. **Required fresh browser verification is incomplete**, including real OSMD spacing, equal usable dimensions under browser font metrics, same-scale comparison, contextual toolbar heights and scroll behavior. Static CSS assertions and controlled renderer tests are not substitutes for this verification.

Native PDF rendering remains browser-controlled. Existing PDF controls request page-width/numeric zoom through URL fragments; application code cannot measure or guarantee the native viewer's resulting scale or scroll retention. No new rendering dependency was introduced. Image/MusicXML viewport geometry checks do not certify native PDF scaling.

The existing bounded source-group algorithm may fail to preserve unusually demanding systems within its rendering limit; its existing warning remains. No source bytes or music semantics are changed to force a fit.

## Automated checks

- Full frontend suite, from frontend: `node --test --test-isolation=none --test-reporter=tap tests/*.test.mjs` — **PASS, 260 tests, zero failures/skips**. Includes existing note, lyrics, ties/directions, Undo/Redo, persistence, download acknowledgement, unsaved protection and Concert regression suites, plus four new checks.
- `npm run lint --prefix frontend` — PASS.
- `npm run build --prefix frontend` — PASS. Existing large-bundle warning remains.
- `git diff --check` — PASS.
- Initial verification found an outdated resize-reengraving expectation; updated to the authorized stable-layout behavior. Effect-test cleanup was adapted for an effect with no cleanup. Final suite passes.
- Backend tests were not run: this task does not change backend/API/music-engine behavior. Instrument Transposition was not tested.
- Logs: /tmp/ux01-fix-tests.log, /tmp/ux01-fix-lint.log, /tmp/ux01-fix-build.log.

## Preservation and acceptance gates

A pre-edit SHA-256 inventory was saved at /tmp/ux01-fix-baseline.json. Comparison identifies only the ten frontend files listed above as modified by this task, plus this new report. Preexisting backend/API, source MusicXML, dependency manifests, governance documents and earlier reports remain unchanged. Existing uncommitted frontend work was edited in place and retained. No prohibited Git operations were performed.

Relevant principles: PC-02/PC-06 preserve user correction operations and explicit choices; PC-03/PC-04 retain the saved authoritative source and independent result; PC-05 preserve canonical bytes/persistence; PC-07 protect regressions; PC-08 defer acceptance to the Product Owner. PC-01 OMR is untouched.

Gate 1 implementation is complete within UI scope. Gate 2 automated checks pass, with browser verification explicitly incomplete. Existing automated checks cover the applicable correction/persistence/relationship acceptance checklist; no new manual persistence acceptance is claimed. Gate 3 Technical Lead review is pending. Gate 4 Product Owner acceptance is pending. Status remains IN PROGRESS, not TECHNICALLY VERIFIED or ACCEPTED. Stopped for Technical Lead review.
