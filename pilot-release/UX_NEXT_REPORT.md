# Current status — October 31, 2026

UX Next 1.0.0-rc1 is ACCEPTED. See UX_NEXT_RC1_ACCEPTANCE.json and UX_NEXT_RC1_REPORT.md. The dated sections below describe earlier candidate stages and do not override RC1 acceptance.

# UX Next — Independent Layout Implementation

Date: 2026-10-29 (America/New_York).
Status: TECHNICALLY VERIFIED — PENDING PRODUCT OWNER ACCEPTANCE. Product Owner acceptance of the implementation is separate from approval of its design.

## Authority and scope

The Product Owner approved the compact Symphony Pro-inspired presentation, required every accepted capability to remain, requested an independently runnable version, and explicitly authorized UX Next implementation. Cloud deployment is deferred. Changes concern layout, grouping, popup placement and an accessible entry to existing key-signature correction. No musical processing, backend, OMR engine or dependencies were changed.

Relevant governance: PC-02 user correction, PC-03 canonical Concert, PC-04 independent instruments, PC-05 persistence, PC-06 user control, PC-07 regression protection and PC-08 acceptance authority. Explicit subsequent Product Owner decisions about readable saxophone registers and unchanged imported MusicXML remain authoritative; this task does not redefine them.

## Version separation

- Accepted Classic: `/home/dtran/music-sheet-transposer-releases/music-sheet-transposer-classic-task06`; exact Task 06 accepted archive hash 6ca19a222c1d899f5ec9a27bcdb5b059041fbded86a9d1173669fc33b965ce8a.
- Independent source: `/home/dtran/music-sheet-transposer-ux-next`.
- Candidate: `/home/dtran/music-sheet-transposer-releases/music-sheet-transposer-ux-next-preview8`; manifest version `ux-next-preview.8`. Header text `UX Next · preview.1` identifies the initial layout series; the package manifest identifies the precise candidate build.
- Classic uses port 5181 when launched by the supplied command. UX Next uses port 5230. Existing Classic/accepted development sessions were not stopped or replaced. Only internal unaccepted preview processes created in this task were replaced.
- Baseline sources were exported from 47286f983c953bfa06ede32cafd602fa1bb06e89 and overlaid with exactly five PDF source files from accepted Task 06. Every initial application hash matched Classic before UX edits. `UX_NEXT_BASELINE.json` records that provenance.
- No Git branch, commit, push, reset, clean or stash was performed. This independent directory is a source snapshot, not a newly created Git checkout.

## Implementation

Application changes are limited to `frontend-v2/src/main.tsx`, `frontend-v2/src/real/RealWorkspace.tsx`, and new `frontend-v2/src/ux-next.css`.

The toolbar runs horizontally above the aligned score panes and stays reachable during page scrolling. DOM keyboard order matches visual order. Source Fit/zoom are aligned with Working Score Fit/zoom. Tools wrap on narrow screens without extending the document width. Expanded tools remain overlaid instead of adding forms above the score. Note popup positioning is bounded by the viewport and no longer assumes a left vertical rail. Groups stays over the source side so destination note clicks remain possible. Register explanation is expandable; its content is retained.

Concert Key uses a compact two-column layout with every original control. Correct Key Signature is a presentation-only entry to the existing measureContext key correction; it uses a visual 0–7 sharp/flat selector and leaves note pitches/durations unchanged. Existing More tools and raw explicit correction remain available. Header actions remain directly accessible rather than hiding accepted commands behind incomplete menus.

## Preserved capability map

| Capability | UX Next access | Preservation |
| --- | --- | --- |
| Home, open/import, discard/cancel/save | Header and existing prompts | Original handlers |
| Notes and rests | Horizontal Notes/Rest palettes | All seven supported written values |
| Accidentals | Toolbar group and selected-note tools | Double flat, flat, natural, sharp, double sharp; same explicit command |
| Dots | Expandable Dots group and note tools | Missing-dot correction, dot, double dot |
| Tie/slur | Horizontal tools and direct curve interaction | Original ownership/direction/delete behavior |
| Groups | Groups palette | All eight ratios, split/apply/remove, appearance, equal/mixed forms, beams |
| Pitch/duration/voice/staff | Direct selection and note popup | Original commands and per-note Small/Normal |
| Lyrics/verses/text/chords | Direct score editing, same tools | Add/edit/move/delete and original associations |
| Measure/context | Add measure, More, Correct Key Signature | Existing engine and boundaries |
| Concert transposition | Concert Key | Source/mode/confirmation/new key/Up/Down/Keep Original/Apply |
| Missing original key on Save | Existing Save prompt | User choice and tentative opening-chord suggestion |
| Instrument transposition | Instrument cards and Direction | Independent Alto/Soprano/Tenor variants |
| Compare/Edit Only | Same view switch in both stages | Same tools; source hidden only in Edit Only |
| Undo/Redo, Validate, Save/Save As | Existing header/actions | Original state and explicit local file handling |
| MusicXML/PDF export | Existing actions and accepted PDF dialog | Task 06 implementation unchanged |

Static AST comparison found 166 original JSX event handlers, all retained. Added presentation entries do not replace old handlers. This check supports source review but is not a substitute for behavioral tests.

## Verification and repairs

Lint/typecheck/production build passed. The 60 unit tests passed. The focused key-signature test passed: all note IDs, pitches and durations remained identical after explicit signature correction. Packaged regression is complete through the broad run and the scoped final rerun described below.

Prototype checks exposed popup positioning inherited from the old rail, Groups covering a destination, a validation overlay crossing the toolbar and narrow pane overflow. These presentation issues were corrected before final verification. Existing tests were updated only where the approved layout changed their assumptions: first button location, vertical-rail alignment, source/working zoom scoping, version label and explicit opening of collapsed Dots. Musical/persistence assertions were retained. A first invocation used the wrong working directory for test fixtures and was discarded as a harness setup error. Local private replay fixtures are evidence only and are not included in distributable packages.

Some large private-fixture assertions initially timed out while two browser runs shared the machine. Final verification runs serial workers and allows 15 seconds for UI assertions; those assertion contents are unchanged. Any remaining failures must be reported, not treated as accepted functionality.

No actual OMR recognition was rerun for this presentation change. Existing recognized-MusicXML replay and mocked recognition flows exercise correction and save behavior. No broad accuracy certification is claimed.

## Launch and rollback

```sh
# Classic
python3 -B /home/dtran/music-sheet-transposer-releases/music-sheet-transposer-classic-task06/start.py --port 5181
# UX Next
python3 -B /home/dtran/music-sheet-transposer-releases/music-sheet-transposer-ux-next-preview8/start.py --port 5230
```

Keep the relevant terminal open. Save work as separately named MusicXML files before stopping. Both services use independent process-memory review stores; local files are only shared if the user explicitly chooses the same save destination. No automated migration occurs. Returning to Classic means opening its existing URL/package, not replacing its files.

## Limits and release gate

Preview only, pending Product Owner acceptance. All existing OMR, multipart and unsupported-notation limits remain. Technical PASS does not grant acceptance. No cloud deployment, external publication or GitHub checkpoint was performed. Documentation is English. A later approved checkpoint can commit the scoped source/report after review without including private scores or unrelated legacy changes.

## Final verification record

- ESLint PASS; TypeScript/production build PASS; 60 unit tests PASS.
- Broad preview.7 run: 102 passed, 3 failed, 1 skipped, 7 not run after early-stop. The three failures were the same Source-control CSS leakage into Demo, not musical-command failures.
- Final preview.8 scoped run: 30 passed, 0 failed, 0 skipped. It covers all Demo workflows, the full PDF recognition replay, real horizontal layout and explicit key-signature correction. The source CSS is now limited to real workspaces and preserves Demo controls.
- Merged coverage: 113 unique browser scenarios; latest result for each: {'passed': 113}. These are combined run results, not a claim that one full suite ran against preview.8. Every prior final-run failure and skip was explicitly exercised successfully in the scoped rerun.
- All 166 original JSX handlers are retained. The backend is byte-identical to Classic. All 866 Classic files and its accepted archive remain intact; all 619 protected pre-existing files remain unchanged. Candidate integrity passes.
- Final archive: `/home/dtran/music-sheet-transposer-releases/music-sheet-transposer-ux-next-preview8.tar.gz`.
- SHA-256: `26c72132cc6cf50a8479ecb501644d0418e71c8cbbda9f959f158c6c148b7687`.
- Application changes remain exactly three UI files. The final change after the broad run only scopes Source/label styling to real workspaces; no command handler or backend change occurred.

Technical Lead source review: the accepted commands remain attached to the same handlers; the explicit key-correction entry reuses the accepted helper; geometry changes are presentation-only. The separate process uses MemoryReviewStore, avoiding shared review state with Classic. Private replay data and screenshots stay in local evidence and are not distributed in the candidate package. Visual review inspected Concert Compare, compact Concert Key, instrument Compare and narrow Edit Only; tool and popup defects found during prototypes were corrected and regression-tested. Gates 1–3 are complete for this bounded UX candidate. Gate 4 requires explicit Product Owner acceptance. No Git commit/push or cloud deployment occurred.

## Home-only refinement — 2026-10-30

Product Owner requested removal of the Stage 1 status bar, vertical editing rail and inactive header actions from the initial Home page. Implemented in independent candidate `ux-next-preview.10`, superseding preview.8 for local review. Classic and previous candidates are unchanged.

Added a loaded-state presentation wrapper in App.tsx and scoped Home styles in ux-next.css. The existing import, Demo, edit and save handlers are unchanged. Home now shows the product title and import area, with relevant error feedback retained. The simulated-workspace subtitle and default redundant notice are hidden before loading only. Editor controls return when a score is opened. This refinement adds App.tsx to the presentation allowlist; the musical model/backend remain untouched.

Verification: ESLint, TypeScript/build and 60 unit tests PASS. First Home/Demo regression run: 34 passed, no failures/skips. Final import-feedback refinement: 10 Home tests passed, no failures/skips, including 1338/650 px Home, real import, Demo tools restoration, save/discard navigation and unsupported-file feedback. The previous 113-scenario regression record above remains evidence for unchanged editor commands; it was not rerun in full for this Home-only refinement. Visual/AX inspection of the actual 5230 page confirms only title/import controls on Home. Product Owner acceptance remains pending.

Active command: `python3 -B /home/dtran/music-sheet-transposer-releases/music-sheet-transposer-ux-next-preview10/start.py --port 5230`. The short launcher run-ux-next.sh points to this package. No Git operations or cloud deployment occurred.

## Remove accidental — 2026-10-30
UX Next preview.11 adds Remove accidental to the toolbar and selected-note tools. It uses the existing backend patch with written_accidental=null and the selected note's key-signature alteration. This is an explicit pitch correction, not a hide-symbol operation. No backend or Classic files changed. The shared RealWorkspace supplies the control to concert/instrument editors and Compare/Edit Only.
Verification: ESLint, TypeScript, production build, package integrity and Python ABI passed. Browser check passed for sharp removal on the selected note and Undo restoring the sharp. Initial test harness failures were a ledger-line pointer interception, incorrect test traversal, and an Undo accessible-name mismatch; keyboard selection and corrected assertions passed. Mouse selection on that ledger-line fixture remains a known limitation outside this change. Full regression, Stage 2 and export/reimport were not rerun for this addition. Product Owner acceptance pending.
Preview is served separately on port 5231; port 5230 and open work were preserved.

## Measure accidental command — 2026-10-30
Supersedes the selected-note-only behavior for explicit accidental commands in UX Next preview.12. Authorized scope: models.py, patcher.py, shared RealWorkspace commands and bounded tests/package builder. Classic remains immutable.
A toolbar or note-popover accidental command opts into accidental_scope_measure. The command carries the selected spelling to later events with the same step, octave and staff in the same measure, ending at an explicit replacement accidental or changed key context. Other octaves, staves, bars and explicit replacements remain unchanged. Removing an accidental restores the prior explicit accidental context or key signature. No repeat accidental nodes are invented. Existing imported XML is not globally normalized. The shared editor supplies the behavior in Stage 1, Stage 2, Compare and Edit Only.
Tied affected notes are explicitly blocked rather than breaking cross-boundary relationships; full tied-note propagation is not implemented.
Verification: 24 targeted backend tests passed, including sharp/flat, boundaries, exact undo/redo and serialized XML reimport. Browser check passed for sharp propagation, removal and Undo restoring both affected notes. Lint, TypeScript, production build, package integrity and Python ABI passed. Two initial added-test failures omitted the existing required matching pitch in the test requests; corrected requests passed. Stage 2-specific end-to-end and PDF export were not rerun; no full regression claim is made.
Review: PC-02/03/05/06/07 addressed by explicit user command, serialized corrections, unchanged unrelated content and history checks. Status: targeted verification complete; tied-note limitation and untested paths remain disclosed; Product Owner acceptance pending.
Preview: http://localhost:5232/ . Previous running sessions 5230/5231 retained.

## Tied-note accidental correction — 2026-10-30
UX Next preview.13 supersedes the blanket tied-note block in preview.12. A measure accidental command resolves existing tie relationships against the pre-edit score and updates the connected chain, including either endpoint and cross-bar continuations. Tie nodes, identities, directions and durations remain intact. Cross-bar continuation does not propagate the accidental into unrelated later notes in that next bar. Ambiguous/incomplete ties and originally mismatched pitch endpoints remain blocked, with no guessing or authored connections.
Shared editor command applies to Stage 1/2 and Compare/Edit Only. Classic and running earlier preview sessions remain unchanged.
Evidence: 47 targeted backend tests passed (measure accidental, musical controls, existing ties); tests cover both chain endpoints, three-measure continuation, unrelated next-bar note, preserved tie markup, serialized/reimported XML and exact Undo/Redo. Browser smoke passed for tied-note sharp, removal and Undo. Initial browser assertion used a same-measure index for a cross-bar fixture; corrected assertion passed. Production build/TypeScript and package integrity/ABI passed. Stage 2-specific end-to-end and PDF were not rerun for this follow-up.
Technical source review: edits use existing tie resolver and atomic revision/history path; no tie invention, no unrelated source edits. PC-02/03/05/06/07 apply. Product Owner acceptance pending. Preview http://localhost:5233/.

## Scoped Product Owner acceptance — 2026-10-30
Status: ACCEPTED for UX Next accidental editing and resolved tie-chain corrections, version preview.13. The Product Owner requested acceptance before advanced editing after confirming tests of tied notes and notes sharing a position/chord. Earlier user confirmation covered Stage 1, Stage 2 and PDF on the preceding accidental-scope revision; no new preview.13 automated Stage 2/PDF claim is made.
The exact package manifest digest, evidence and limitations are recorded in UX_NEXT_ACCIDENTAL_TIE_ACCEPTANCE.json. Package hashes were rechecked successfully. PC-02/03/05/06/07 and acceptance gates 1–4 are addressed within this bounded scope. Ambiguous/incomplete or originally mismatched ties remain explicit rejection cases. Classic and immutable preview packages were not modified. No GitHub commit/push/tag was made. Advanced editing has not started.

## GitHub checkpoint verification — 2026-10-30
The independent commit checkout matches all preview.13 application-source hashes. README and the English guide now distinguish scoped accepted corrections from the candidate UX redesign and accepted Classic baseline. Reverification on the commit checkout: 60 frontend unit tests, 47 targeted backend tests, ESLint, TypeScript and production build passed. Existing Vite bundle-size and Python deprecation warnings remain; no new dependency installation was performed. Private scores, OMR evidence, generated packages and unrelated preexisting edits are excluded. The checkpoint is published on ux-next/checkpoint-2026-10-30 without replacing master. No advanced editing implementation is included.
