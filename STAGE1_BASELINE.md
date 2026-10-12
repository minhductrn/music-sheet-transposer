# Accepted Stage 1 baseline — P0.9

The Product Owner accepted P0.8B, confirmed the reopened Concert MusicXML score,
and authorized this integrated Stage 1 checkpoint. Acceptance comes from that
explicit decision, not from automated test results.

The baseline preserves direct correction of OMR-derived scores: Normal/Small
notes, pitch and duration, lyrics, tie creation/removal and explicit Up/Down,
Undo/Redo, and MusicXML round trips. Review Issues and its mandatory handling
gate are removed. Technical integrity checks remain.

The user-saved local MusicXML file is the durable Canonical Concert Score.
Editing sessions remain temporary. Save/Save As use a user-selected writable
file where the browser supports it; otherwise they request a download and wait
for explicit acknowledgement that the file was retained. The application cannot
observe Firefox download completion. Open MusicXML does not rerun OMR. Unsaved
edits do not replace the saved snapshot and cannot unlock reviewed transposition.
See [the local-file workflow](backend/REVIEW.md#p08b--local-file-save-save-as-and-open).

[PRODUCT_CONSTITUTION.md](PRODUCT_CONSTITUTION.md),
[ACCEPTANCE_CRITERIA.md](ACCEPTANCE_CRITERIA.md), and [AGENTS.md](AGENTS.md)
govern future work. Earlier specification provisions for SQLite/server score
storage and earlier review-acceptance reports do not supersede the later
Product Owner-approved local-file architecture and accepted Stage 1 behavior.

## Validation and exclusions

Checkpoint validation covers the available backend regressions, frontend Node
tests, frontend lint, and production build. A separate candidate-tree check
verifies that committed source and tests work without private local score files.

The historical untracked `frontend/tests/standalone-ties.test.mjs` requires the
private root-level `review-cungdemtimung.musicxml`; both are excluded from this
checkpoint. Controlled tie, renderer, correction, history, and local-file
round-trip regressions remain included. Neither local user files nor generated
build outputs, dependencies, caches, or credentials belong in the checkpoint.

Stage 2 instrument-score generation is not implemented by this checkpoint.
