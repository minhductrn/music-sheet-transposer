# Task 06 — PDF Export Layout and UX, v0.1

Date: 2026-10-29. Status: **DESIGN READY FOR PRODUCT OWNER REVIEW**. This document is a proposal, not implementation authorization or acceptance. No application code has been changed for Task 06.

## Baseline and evidence actually read

- Repository checkpoint: `47286f983c953bfa06ede32cafd602fa1bb06e89`, closing accepted Task 05. Application code baseline: `945821c55cb7760a7200329ebbea7ed79055ffd2`.
- `AGENTS.md`, `PRODUCT_CONSTITUTION.md`, `ACCEPTANCE_CRITERIA.md`, `pilot-release/TASK_05_RELEASE.md`.
- `frontend-v2/src/real/a4Layout.ts`, `scorePDF.tsx`, `PDFSource.tsx`, and `frontend-v2/tests/a4-layout.test.ts`.
- The accepted exporter uses portrait A4, fixed 12 mm margins, a 1100-pixel disposable print rendering, embedded Unicode fonts, one-page uniform fit and system-aware multi-page slicing. It does not change MusicXML.
- The existing PDF source renderer caps original PDFs at ten pages and renders all pages. Reusing it unchanged for an arbitrary-length export preview would impose an unrelated input limit; reuse the installed PDF.js library/worker but render only the selected preview page.

## Objective and exact scope

Make exported pages use A4 space more effectively while retaining all existing content, and make the PDF export dialog clear and easy to close. This task is exclusively about PDF output, not music theory or score editing. Apply the same behavior to Concert and instrument Working Scores, in Compare and Edit Only. Source data remains read-only.

Included:
1. Automatic content-aware outer margins, plus a Standard 12 mm compatibility option.
2. Keep Fit in 1 A4 page as the default layout; keep Multiple A4 pages as an explicit choice.
3. A small English PDF dialog with a preview of the actual generated PDF, page navigation, Export and Cancel/close controls.
4. Consistent close/Cancel/Escape and keyboard behavior inside the PDF export dialog only. Leave all editor tools and their behavior unchanged.

Excluded: automatic internal re-engraving beyond the existing compact print rules; changing pitches, rhythm, keys, lyrics, ties or slurs; new notation features; changes to OMR or backend; a full visual redesign; cloud/services/dependencies; nested/cross-measure tuplets; multi-part expansion; passage copy/paste/transposition. These remain later roadmap work.

## PDF layout contract

### Content and margins

- A4 portrait remains 210 x 297 mm.
- Auto margins measures actual visible print content: notation, accidentals, ledger lines, dots, tuplets, curves, lyrics, title/composer and supported text/marks. Remove editor hit targets from the print clone before measuring. Include small stroke/text padding so cropping does not touch visible ink.
- Trim empty outer SVG space only. Do not delete intentional internal spacing or treat an OCR error as whitespace to remove.
- Load and measure the actual export font before calculating text bounds. Preview and final PDF must use the same font metrics and generated Blob.
- Proposed minimum-margin profiles, in millimeters: Balanced (16 on all sides), Standard (12 on all sides), Compact (10 left/right/top and 12 bottom). These are design values for approval, not a claim of universal printer support.
- Use the current 186 mm / 1100 print-pixel reference scale to select the least compact profile that contains the content without additional shrinking. If no profile fits in one-page mode, use Compact and uniformly reduce the complete content. Never distort horizontal and vertical scales independently.
- Center the content horizontally and anchor its title/header region at the selected top inset. A short score may retain bottom whitespace; do not stretch music vertically to fill a page.
- Reserve the existing page-number footer independently from the score content. Ensure it cannot overlap a lyric or final system. Title/composer are page content, not fixed screen overlays.
- Profiles describe minimum insets. Actual whitespace can be larger when the aspect ratio requires it; automatic margins do not guarantee edge-to-edge filling.
- Standard 12 mm preserves the accepted layout path and remains available as a comparison/fallback.

### One page and multiple pages

- Fit in 1 A4 page must retain the complete score on one page. A very long score can become small; present a concise, non-blocking note with the Multiple A4 pages option, rather than silently switching modes.
- Multi-page layout uses one consistent margin profile/scale for the document. Split only between complete systems and outside text rows/curves as supported by the accepted boundary logic. Do not duplicate or omit lyrics, titles or notes, or add an empty final page.
- If content cannot be represented safely (for example, a single indivisible system exceeds a page in multi-page mode), report the concrete problem and retain the document unchanged. Do not clip it silently.

## User interaction

1. Export PDF opens one centered dialog. Keep the accepted accessible names PDF layout, PDF page layout and Export where practical.
2. Top controls: Layout (Fit in 1 A4 page / Multiple A4 pages) and Margins (Auto / Standard 12 mm). Defaults: one page + Auto.
3. Generate a preview for those settings and display page count plus previous/next controls. Render only the selected page, so long exports do not inherit the original-source ten-page/pixel-budget behavior.
4. Changing settings invalidates the previous preview. Show generation progress; only the latest completed settings may be exported. Avoid overlapping exports and stale previews.
5. Export downloads the exact Blob shown in preview; do not regenerate a different layout after approval. Preserve the existing filename convention.
6. Cancel, the close button and Escape close without downloading or falsely reporting success. Return focus to the invoking control and preserve Working Score scroll, selection, zoom, unsaved state and history.
7. Use a constrained-height dialog with a scrollable preview body and always-visible actions on short/narrow screens. Do not insert forms above the score and push it out of view.
8. Do not add or change any score-editing action or music-theory control. The exported PDF is derived from the current score exactly as supplied.

Settings are local export choices for the current interaction; do not write them into MusicXML or add persistence/backend preferences in this task. No new custom-margin form is required in v0.1.

## Reused components and bounded implementation task

Proposed implementation task: **TASK-06-001 — Automatic A4 margins and PDF export UX**.

Reuse RenderedScore printCompact, the existing Unicode font assets, jsPDF/svg2pdf, installed PDF.js/worker, accepted review models, and existing A4 system boundaries. No new dependency or rendering engine.

Allowed files, after implementation authorization:
- `frontend-v2/src/real/a4Layout.ts`, `scorePDF.tsx`, `real.css`.
- New `frontend-v2/src/real/PDFExportDialog.tsx` and `PDFPreview.tsx` if needed to keep the export UI small and isolated.
- `frontend-v2/src/real/RealWorkspace.tsx` only if required to invoke/close the PDF dialog; no editor-tool, notation or musical-command changes.
- `frontend-v2/tests/a4-layout.test.ts`, `tests/e2e/pdf-a4.spec.ts`, and new `tests/e2e/pdf-export-ux.spec.ts` and `tests/pdf-plan.test.ts`.
- A new `pilot-release/build_task06.py` only for an isolated verification package recording the baseline plus exact approved source overlay, with `pilot-release/playwright.task06.config.cjs` for isolated verification; do not change Task 05's fixed-baseline builder or immutable packages.
- This design/report, `README.md` and `pilot-release/USER_GUIDE_EN.md` for English documentation after implementation.

Safeguards: retain the accepted Task 05 archive and its hash, all protected/legacy changes and private samples. Use an isolated new candidate/server port. Do not stop the user's application or restart WSL without separate authorization. Do not stage/commit/push or create a release checkpoint as part of implementation unless explicitly authorized.

Stop before an affected out-of-scope change if backend/OMR work, a new dependency, unplanned renderer changes, protected-file changes or ambiguous musical ownership are required. Record a specific evidence gap; do not launch broad security/architecture investigations or invent missing approvals.

## Acceptance criteria

1. Auto selects content-aware insets and crops only unused outer rendering space; Standard 12 mm remains selectable. All visible ink and footer are retained within the chosen A4 frame.
2. One-page fit exports exactly one A4 page. Multi-page output retains complete systems and all content once, without an empty final page.
3. Preview and downloaded PDF match the same settings and Blob, including page count, Unicode, composer/title, verses, ties/slurs and small noteheads.
4. Cancel/close/Escape and a rendering failure produce no download or false success; the score's selection, scroll and zoom remain stable.
5. The PDF dialog fits desktop/short/narrow viewports; close/actions remain reachable. Its labels use English, while the score content retains its own language.
6. Behavior is available in both stages and views; Original Source and the saved Concert remain unchanged when exporting instrument scores.
7. PDF operations make no review edit requests and leave canonical MusicXML bytes, voice/staff ownership, history and saved status unchanged.
8. The accepted Task 05 regression baseline remains intact. Technical PASS does not imply Product Owner acceptance.

## One integrated verification plan

- Geometry tests: asymmetric/tall/wide content, title/composer and three lyric verses, negative/overflowing ink bounds, footer exclusion, profile selection, one-page fit and safe multi-page boundaries.
- Browser flow: Concert and instrument exports in Compare/Edit Only; both layout and margin modes; preview page navigation; rapidly changed settings; keyboard close/cancel; desktop 1338 x 590 and a narrow viewport. Verify no document edits or scroll resets.
- PDF checks: page size/count, every synthetic lyric token once, no clipping/overlap at page boundaries and preview/download byte identity. Render representative PDFs and visually inspect them at readable resolution.
- Reuse the supplied Dieu Ran G/Gb MusicXML and saved Alto example locally, plus synthetic short/long/three-verse scores. Do not rerun OMR for a layout change and do not commit private inputs.
- Run layout unit tests, lint/typecheck/build and export-related packaged tests once focused checks pass. Confirm the score data is unchanged; do not add new music-theory tests or rerun OMR. Retain failures/skips and broaden checks only for an affected shared caller or an evidenced regression.
- Technical Lead reviews the scoped diff, PDF visual evidence and invariants, then presents a new candidate for Product Owner acceptance. No repeated manual test rounds are requested without a concrete gap.

## Decisions requested

A. Approve Task 06 design v0.1, including Auto as the default margins choice and the proposed bounded profiles.

B. Authorize Codex to implement TASK-06-001 within the allowlist and safeguards above.

These are separate governance decisions and may be approved together. No blocking evidence gap prevents this design. The subsequent approval below authorizes implementation; final functional acceptance is still pending.


## Product Owner clarification — 2026-10-29

The Product Owner clarified that this work is PDF export only and needs no musical-theory functionality. This v0.1 proposal has been narrowed accordingly: no Groups/palette/editor redesign, no new notation controls and no musical processing. Checking that the export retains all original content is an output-integrity check, not a new music feature. The Product Owner subsequently replied "ok", authorizing this narrowed design and its implementation. Final functional acceptance remains separate.

## Implementation and Technical Lead verification — 2026-10-29

Status: IMPLEMENTED, TECHNICALLY VERIFIED, PENDING PRODUCT OWNER ACCEPTANCE. No commit or push has been made for Task 06.

Implemented only the PDF export path: automatic outer-ink bounds and Balanced/Standard/Compact margin profiles, selectable Standard 12 mm, uniform one-page fit and safe multi-page placement, a native modal dialog, selected-page PDF.js preview, and download of the exact preview Blob. Cancel, close and Escape produce no download. Existing fonts and libraries are reused; no dependencies were installed. Canonical score editing and backend/OMR code were not changed. The existing Task 05 package remains the accepted release.

Verification results:
- ESLint: PASS. TypeScript and production build: PASS. Existing bundle-size advisory remains non-blocking.
- Unit tests: 60 PASS, including four additional PDF geometry cases.
- Packaged PDF regression: 7 PASS, 0 FAIL, 0 SKIP; complete lyric tokens and title once, A4 dimensions, one-page local Tien Buoc and Dieu Ran Concert/Alto, and long-score system-aware pagination.
- Packaged PDF UX: 5 PASS, 0 FAIL, 0 SKIP; byte-for-byte preview/download identity, Auto/Standard changes, Cancel/close/Escape, 650 x 590 dialog, Alto/Soprano/Tenor Edit Only previews and multi-page navigation. Export checks observed zero document-edit requests.
- Visually inspected rendered Dieu Ran Alto one-page A4, long synthetic multi-page output and narrow preview screenshot. Existing OCR text errors in private input are preserved rather than silently corrected.
- All 619 protected files match their recorded hashes. All 866 candidate package files match the manifest. Task 05 archive SHA-256 remains 65e5797a6df645dbd0a3efe1a0f347dda2c4777ad1a20922994f0f1ccfbb1058.

Candidate: `frontend-v2/evidence/task06/music-sheet-transposer-task06-v0.1-preview1.tar.gz`.
SHA-256: `6ca19a222c1d899f5ec9a27bcdb5b059041fbded86a9d1173669fc33b965ce8a`.
Baseline: 47286f983c953bfa06ede32cafd602fa1bb06e89, plus exactly five PDF frontend source files recorded in the candidate manifest. Backend is from the accepted baseline. Pre-existing unrelated checkout changes were excluded. The candidate is a review package, not a new accepted release; its embedded Task 05 guide describes the accepted baseline. The instructions below describe the PDF candidate.

### Candidate use

Open the isolated candidate at http://localhost:5217. Import a MusicXML score, then Export PDF. Choose Fit in 1 A4 page or Multiple A4 pages, and Auto or Standard 12 mm margins. Review pages with Previous/Next. Export downloads those exact PDF bytes. Cancel, x or Escape returns to the score. Save editable work as MusicXML; PDF is print output.

For another launch, use `python3 -B /actual/candidate/path/start.py --port 5217` with the extracted candidate path. Keep the terminal open. The existing Task 05 server on port 5180 is not stopped or replaced.

### Limits and acceptance

Auto margins select bounded profiles from visible content; they do not recompose notation, repair OCR or offer arbitrary custom margins. Fit in one page can make a very long score small. Multi-page mode stops with an error if an indivisible system cannot fit safely. PDF appearance depends on the supplied score, which remains unchanged. This change does not certify broader OMR accuracy. Final Product Owner acceptance and any GitHub commit/push remain pending.
