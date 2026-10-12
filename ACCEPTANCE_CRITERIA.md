# Music Sheet Transposer — Acceptance Criteria

Acceptance follows the [Product Constitution](PRODUCT_CONSTITUTION.md). These gates are mandatory; this document does not certify any existing feature as passing or accepted.

## Mandatory gates

### Gate 1 — Implementation

Changes satisfy the approved task scope, authorization mode, and relevant Product Constitution principles. Preserve accepted features and identify the principles and acceptance requirements addressed in the implementation report.

### Gate 2 — Automated Verification

Relevant tests, build, lint, and regression checks pass. For score corrections, include appropriate persistence and export/reimport checks. Record commands, results, and limitations. Do not mark untested functionality as passing; document any inapplicable check and its reason.

### Gate 3 — Technical Review

The Technical Lead reviews the implementation, evidence, data integrity, and regression risks. Passing automated checks alone does not complete this gate.

### Gate 4 — Product Owner Acceptance

The Product Owner validates user-visible behavior when applicable. A Codex test PASS does not imply Product Owner acceptance. Only explicit Product Owner approval permits final ACCEPTED status for user-visible functionality.

## Status vocabulary

| Status | Meaning |
| --- | --- |
| NOT STARTED | Authorized work has not begun. |
| IN PROGRESS | Implementation, verification, or review is underway. |
| BLOCKED | Required evidence, authorization, or a prerequisite is unavailable; report the blocker. |
| TECHNICALLY VERIFIED | Gates 1–3 are complete with recorded evidence; Product Owner acceptance is still pending. |
| ACCEPTED | Applicable gates are complete, including explicit Product Owner approval for user-visible functionality. |

A failed check must be reported as failed and prevents the relevant gate from passing. A blocked or untested check is not a PASS.

## Acceptance checklist

For each relevant item, record evidence and the result, or explain why it is not applicable. Unchecked items do not imply verification.

- [ ] Note editing preserves intended pitch, duration, voice, staff, chord membership, and unrelated musical properties.
- [ ] Note addition and deletion support approved workflows and preserve measure integrity and subsequent notes.
- [ ] Lyrics and their note associations remain correct through edits and subsequent operations.
- [ ] Tie creation and removal preserve the intended source/destination identities and unrelated relationships.
- [ ] Explicit tie Up/Down changes preserve the relationship and unrelated ties; direction persists in canonical data.
- [ ] Undo/Redo restores and reapplies edits, including relationships and direction.
- [ ] Save retains all supported corrections in the canonical concert-pitch score.
- [ ] Export/reimport retains supported notes, lyrics, ties, directions, and score structure.
- [ ] Stage 2 reads only the saved Stage 1 canonical score, uses the approved instrument offsets, and keeps outputs independent without overwriting Stage 1 or rerunning OMR.
- [ ] Relevant regression tests, lint, and build pass with recorded evidence.
- [ ] Technical Lead review is recorded.
- [ ] Product Owner acceptance of applicable user-visible behavior is explicitly recorded.
