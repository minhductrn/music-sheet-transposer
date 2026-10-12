# Music Sheet Transposer — Product Constitution

These Product Owner-approved principles govern development and acceptance. They define requirements, not claims that the current implementation has met them. Changes to these principles require explicit Product Owner authorization.

## PC-01 — OMR is an initial recognition layer

OMR reconstructs the initial musical score from PDF or images. OMR output may contain errors and is not the final source of truth. Do not automatically invent or compose missing musical content.

## PC-02 — User corrections take precedence

Users must be able to correct supported score elements independently of whether OMR originally recognized them correctly. Supported corrections include:

- Add, delete, and edit notes.
- Change note pitch.
- Edit lyrics and their note associations.
- Add and remove ties.
- Set tie direction Up or Down explicitly.
- Use other correction tools already implemented or approved.

Do not reject valid user correction workflows merely because imported MusicXML contains inconsistent or ambiguous OMR markings. Preserve existing musical relationships unless the user explicitly changes them.

## PC-03 — Canonical Concert Score

The user-corrected and saved concert-pitch score is the authoritative source for subsequent operations. All supported corrections must persist in the canonical score. Preview-only or temporary overlay changes do not satisfy persistence requirements.

## PC-04 — Two-stage architecture

**Stage 1:** Import → Recognition → User Correction → Optional Concert-Key Transposition → Save Canonical Concert Score.

**Stage 2:** Generate instrument-specific written scores only from the saved Stage 1 canonical score.

Approved instrument transpositions from concert pitch:

| Instrument | Transposition |
| --- | --- |
| Alto Saxophone E♭ | +9 semitones |
| Soprano Saxophone B♭ | +2 semitones |
| Tenor Saxophone B♭ | +14 semitones |

Stage 2 must not rerun OMR, overwrite Stage 1, or silently discard user corrections. Instrument outputs must remain independent of one another.

## PC-05 — Data integrity

Save, export, and reimport must preserve supported user corrections, including notes, lyrics, ties, tie directions, and musical relationships. Do not silently normalize, remove, or overwrite user-confirmed musical content.

## PC-06 — User control

The user decides musical corrections. Optional score checking may flag potential issues but must not automatically override user decisions. Tie Up/Down is an explicit user choice, not an automatic recommendation.

## PC-07 — Regression protection

Previously accepted features must remain functional. A new feature cannot be considered complete if it breaks existing accepted behavior.

## PC-08 — Product Owner authority

The Product Owner approves product requirements and final functional acceptance. The Technical Lead owns architecture, scope, implementation specifications, and technical review. Codex implements authorized changes and reports evidence. Codex must not independently redefine approved product requirements.
