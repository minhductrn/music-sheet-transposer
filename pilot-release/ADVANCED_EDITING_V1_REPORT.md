# Advanced Editing v1 — Technical Verification Report

Date: October 31, 2026. Branch: `ux-next/advanced-editing-v1`. Parent: accepted RC1 commit `91d74a3`.

Current status: **ACCEPTED** by the Product Owner on October 31, 2026, including the preview.5 layout correction. See `ADVANCED_EDITING_V1_ACCEPTANCE.json`. The verification and handoff entries below are historical records of each candidate before acceptance. Commit/push was subsequently explicitly authorized; Classic production remains unchanged.

## Implemented scope

Complete contiguous measures from one part/one staff can be selected directly on Working Score or with From/Through controls. All voices in the selected measures are included. Preview copies and transposes the selected passage without changing the active document. Apply appends the copy at the end, with a double barline and explicit destination key; notes and chord roots/basses transpose together. Existing measures remain unchanged. The operation is atomic and supports Undo/Redo and MusicXML save/reimport.

Source key is populated from the passage and remains editable. Minus/plus changes the interval by 0.5 tones (one semitone). Destination selection and Up/Down remain available, including same-key register changes. Concert Key shares this compact control and has Preview/Apply. Section editing is available in Stage 1 and Stage 2, in Compare and Edit Only. PDF drafts must first be corrected and saved as MusicXML. Instrument editing uses written pitches and retains instrument transposition metadata without rewriting Concert input.

## Verification evidence

- Full browser regression: **124 passed**, 7.6 minutes, against the initial preview.3 package on port 5242. Evidence: `frontend-v2/evidence/advanced-v1/browser-regression-124.json`. This covers 119 existing checks and five new checks, including PDF replay, saved-key handling, instrument independence, editable notes/lyrics/accidentals/ties/tuplets, PDF output, Home, zoom and save/reimport.
- Source review then identified a delayed Preview response after changing the selected range. The final guard requires the Preview fingerprint to match the current request and review revision before Apply is enabled. No other application change followed the regression run.
- Final-package focused browser verification: **8 passed**, 23.3 seconds, on port 5243. Includes the delayed-response guard; Stage 1/2 mouse selection, Preview, Apply, Undo/Redo and MusicXML roundtrip; Concert stepper/source editing; boundary cancellation; temporary Preview cleanup; and Stage 1/2 Edit Only append followed by PDF export. Evidence: `frontend-v2/evidence/advanced-v1/browser-focused-preview3.json`.
- Backend section/transposition suite: **32 passed** (`test_advanced_sections`, `test_concert_key_api`, `test_concert_workspace`, `test_musicxml_transpose_api`, `test_transposition_schema`, `test_transpose_api`).
- Backend relationship regression: **91 passed** (`test_advanced_sections`, `test_measure_accidental_scope`, `test_p021_user_ties`, `test_tie_direction`, `test_review_existing_ties`, `test_review_tied_insertion`). The eight new section tests are included in both backend runs, not additional unique tests.
- Frontend unit checks: **63 passed**. Lint, TypeScript/Vite build, and `git diff --check`: PASS. Existing non-failing Python deprecation and Vite bundle-size notices remain.
- Final package integrity/ABI and current application source hashes: PASS. Classic Task06.1 (866 files) and accepted RC1 (868 files) match their recorded manifests. Evidence: `frontend-v2/evidence/advanced-v1/package-integrity.json`.
- Visual source review: the floating compact panel leaves the score layout stationary; complete measures are shaded and the preview shows the appended destination signature. Both Concert and instrument screenshots are retained in the same evidence directory.

Initial implementation verification exposed a Stage 2 failure when the existing Concert transposer received instrument metadata. This was fixed by transposing the excerpt's written pitches while temporarily separating and then restoring its original metadata. Backend and browser tests above confirm the corrected path. No failed check remains unresolved.

## Technical source review

PC-02/PC-06: musical intent comes from explicit source/destination/interval choices; Preview does not invent content or modify the live score. PC-03/PC-05: saved MusicXML includes appended content, new signature and chord changes; complete tie identities are remapped so copied ties remain independently editable. PC-04: shared editor operates on the active output and preserves saved Concert input. PC-07: original measure nodes, rhythmic ownership and accepted editing workflows are protected by tests. PC-08: automated verification does not grant Product Owner acceptance.

Preview uses the existing revision check and quota checks without storing a new document. Apply uses the existing atomic edit/history path, rechecks revision, and reports errors without partial writes. Copied XML identities are remapped; complete ties are given independent visual ownership and available tie numbers. Incomplete boundary relationships are reported rather than clipped. API callers that omit the new exact interval retain the previous Concert endpoint behavior. No dependency, OMR engine, cloud, Classic application or original repository working changes were introduced.

Acceptance Gates 1–3 are complete for this bounded implementation. Gate 4 remains pending explicit Product Owner acceptance.

## Limits and untested claims

V1 supports a contiguous complete-measure range, one part/one staff, append-to-end only. It does not implement arbitrary middle insertion, clipboard exchange, repeat/ending copying, multipart expansion or new nested/cross-bar tuplet authoring. Complete existing ties/slurs/tuplets must be contained; cross-voice slur boundary ambiguity can require correction. Unsupported key spellings or out-of-range octaves are reported. Fresh general OMR accuracy was not benchmarked; regression uses retained recognition replay. PDF export was checked for the appended output, not a guarantee that every arbitrarily long score fits one readable A4 page.

## Handoff

Final independent package: `/home/dtran/music-sheet-transposer-releases/music-sheet-transposer-advanced-v1-preview3-reviewed`.

```bash
python3 -B /home/dtran/music-sheet-transposer-releases/music-sheet-transposer-advanced-v1-preview3-reviewed/start.py --port 5243
```

Open http://localhost:5243. The package is already running for review. Manifest SHA-256: `55f6cdc1feec400e60d8a6f52f94d5d72b866e49ddbcdee314bfc7ab1755a320`.

Accepted RC1 and Classic launch commands and packages remain available. Advanced Editing is not a production replacement until accepted. Commit/push requires a separate explicit instruction.

## Preview.4 layout correction — October 31, 2026

The Product Owner reported the section action description was obscured on a 1338×590 viewport. The description now occupies its own wrapping row, separate from Preview/Apply/Cancel. Unrelated workspace notifications are hidden while this panel is open, and panel height is bounded by the viewport. No backend or musical operation changed.

Lint, TypeScript/Vite build and package integrity: PASS. Twelve focused browser tests passed on the packaged preview.4 at port 5244, including 1338×590 and 650×590 for Concert and instrument workspaces, unobscured action hit targets, all eight previous Advanced integration checks, and PDF export. Screenshots were visually checked. Evidence: `frontend-v2/evidence/advanced-v1/browser-preview4-layout-12.json` and `layout-1338-false.png`.

Current handoff: `/home/dtran/music-sheet-transposer-releases/music-sheet-transposer-advanced-v1-preview4/start.py --port 5244`. Open http://localhost:5244. Earlier packages and the user's 5243 session remain intact. Product Owner acceptance and commit/push remain pending.

## Preview.5 Concert Preview layout correction

The Product Owner accepted preview.4, then reported the Concert Preview was constrained to a narrow button-grid cell. This follow-up changes presentation only: a panel up to 920px wide, compact wrapping key controls, non-stretched action buttons, and a full-width read-only Preview row at a larger score scale. Preview height follows the viewport and remains scrollable. All source/destination, Mode, half-tone steps, Up/Down, confirmation, Keep Original, Preview, Apply and Close actions remain available. No backend or transposition semantics changed.

Lint, TypeScript/Vite build and package integrity passed. Fourteen focused browser checks passed on preview.5, including full-width Preview at 1338×590 and 650×590, successful Concert Apply, four section layout cases, and the eight Advanced integration checks. Screenshots were visually reviewed. Evidence: `frontend-v2/evidence/advanced-v1/browser-results.json` and `concert-wide-preview-1338.png`. Relevant principles: PC-06 explicit control, PC-07 preservation and PC-08 separate Product Owner acceptance. Gates 1–3 complete for this layout fix; acceptance of preview.5 remains pending.

Current review package: `/home/dtran/music-sheet-transposer-releases/music-sheet-transposer-advanced-v1-preview5`. Start with `python3 -B /home/dtran/music-sheet-transposer-releases/music-sheet-transposer-advanced-v1-preview5/start.py --port 5245`; open http://localhost:5245. Preview.4 and earlier accepted packages remain intact; no commit/push.

## Final Product Owner acceptance and GitHub checkpoint

The Product Owner explicitly accepted Advanced Editing v1 with preview.4 and subsequently accepted the preview.5 full-width Concert Preview correction. The final feature status is ACCEPTED, including Gate 4. The Product Owner then explicitly authorized commit/push and an English README update. The structured acceptance record contains the final package manifest hash and verification summary.

Final package integrity and all application source hashes were rechecked before preparing the commit: PASS. No application source has changed since preview.5 verification. The accepted package is preserved byte-for-byte, including its historical pre-acceptance receipt; this repository acceptance record supersedes that receipt's pending status. No private scores, generated packages, dependencies or local evidence artifacts are included in the commit.
