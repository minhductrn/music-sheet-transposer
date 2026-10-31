# UX Next 1.0.0-rc1 — stabilization report

Date: October 30, 2026.
Status: ACCEPTED by the Product Owner on October 31, 2026.

## Scope and provenance

Stabilization of the independent UX Next candidate only. Header and manifest now share version 1.0.0-rc1. Relative to preview.13, application-source differences are restricted to RealWorkspace version presentation and the new version constant. No new editing command, engine, dependency, cloud deployment or advanced composition feature is introduced. Classic Task 06 and Classic Task 06.1 package hashes remain unchanged.

Relevant principles: PC-02 user corrections, PC-03 canonical Concert score, PC-04 independent instruments, PC-05 persistence, PC-06 user control, PC-07 regression protection and PC-08 Product Owner authority. Technical gates 1–3 are complete within this stabilization scope. Gate 4 was completed by explicit Product Owner acceptance on October 31, 2026.

## Verification

- ESLint, TypeScript and production build: PASS.
- Frontend unit tests: 60 PASS.
- Targeted accidental/tie backend tests: 47 PASS.
- Full packaged browser run: 117 PASS, zero failures, zero skips.
- Additional tied-note integration checks: 2 PASS on the same package, covering Stage 1/Stage 2, unaffected next-bar notes, global Undo and Edit Only access.
- Package integrity, ABI and exact current application-source hashes: PASS.
- Visual review of the Concert Compare screenshot confirmed the RC1 header, horizontal toolbar and independent panes.

Browser coverage includes PDF draft correction and original-source preservation, MusicXML import, notes/lyrics/chords/marks/tuplets, per-chord-head Small, Undo/Redo, source-key confirmation, Concert transposition, all three saxophone variants/directions, independent output edits, Save/Save As and XML reimport, PDF A4/layout preview/download, Compare/Edit Only, desktop/narrow layouts, Home save/discard and the synthetic Demo.

The first broad run was stopped after stale Classic UI assumptions failed. Tests were updated to open collapsed Dots, recognize the sixth accidental control, scope working-pane zoom and use horizontal-toolbar geometry. Existing verified UX test gestures/private replay paths were reused without removing musical assertions. The corrected complete run passed on the unchanged RC1 application package. Initial failed runs are not represented as PASS.

## Evidence and limits

Exact package/archive digests and local result paths are in UX_NEXT_RC1_VERIFICATION.json. Browser evidence is local; private scores and recognition replay are not embedded in the application package. PDF workflow verification used synthetic responses and existing OMR replay; no fresh generalized OMR accuracy claim is made. Bundle-size and Python deprecation warnings remain. Multipart, nested/cross-measure tuplets and ambiguous or mismatched tie limitations remain.

## Handoff

Run the package on port 5234 using UX_NEXT_RC1_GUIDE_EN.md. The archive is approximately 13 MB and is independently runnable with the recorded existing WSL prerequisites. Save MusicXML explicitly and reopen that file to recover work; unsaved sessions are temporary.

Classic Task 06.1 remains production. The RC1 changes and English documentation are prepared locally; no new commit, push, merge or release tag was performed in this stabilization step. Following Product Owner acceptance, create the release checkpoint before beginning separately scoped advanced editing.

## Product Owner acceptance — October 31, 2026

The delivered RC1 was explicitly accepted. UX_NEXT_RC1_ACCEPTANCE.json binds this approval to the verified immutable manifest and archive digests. The original package manifest retains its build-time pending status; the separate acceptance record is authoritative for subsequent approval. No package was rewritten, production server replaced, Git mutation performed or advanced editing started by this acceptance step.

## Authorized GitHub checkpoint — October 31, 2026

The Product Owner authorized commit/push and an English README update after acceptance. This checkpoint includes the version constant, independent package builder/launcher, integration test adaptations and synthetic tie fixture, verification and acceptance records. The accepted archive and its manifest remain byte-for-byte unchanged. Private score inputs, OMR replay, generated browser output, dependencies and archives are excluded. Existing documented package/runtime prerequisites and limitations remain. Classic production and master are not changed.
