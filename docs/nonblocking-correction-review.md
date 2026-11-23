# Non-blocking correction and lyric layout review — 2026-11-22

Status: IN PROGRESS pending Technical Lead review and Product Owner acceptance. Production 1.0.6 and GitHub were not published or changed by this work.

## Approved requirements

PC-02, PC-05, PC-06, PC-07 and PC-09 apply. OMR and musical diagnostics must not decide whether a user may correct a draft or save it. Preserve the chosen voice, unrelated notes, imported markings and exact saved bytes. Validate remains optional.

The Product Owner also requires lyric rows top-aligned, with the first row one staff space below the lowest note-bearing staff/ledger line on that system. Subsequent verses stack downward. “Upper” means top alignment, not uppercase text. Verse numbers align across voices; only simultaneous conflicting lyrics need extra rows.

## Confirmed live failure

Read-only inspection of the active review found `negative_onset` in measure m-3: a backup moves the imported XML cursor before the measure start. `position_context` rejected every explicit insertion into a measure containing any ERROR, before the draft insertion policy could run. A second negative-cursor check also rejected this known arithmetic. Both now honor draft editing. Signed existing cursor arithmetic is retained; the original backup and notes are not corrected automatically.

The exact active MusicXML was copied to temporary storage for verification, not committed. Inserting a quarter C5 into m-3 returned HTTP 200. All 186 original events retained onset, duration, voice and pitch; one event was added. The user's live review was not mutated.

## Correction paths reviewed and changed

- Explicit insertion and movement preflight now consistently propagate draft intent through the service and patcher.
- Draft moves permit occupied positions and preserve imported tie, beam, tuplet and instrument markup. Detaching a beam is an explicit command, not an automatic side effect.
- Duration changes and accidental edits are not rejected solely because existing chord/tuplet/tie notation is musically inconsistent. Known valid relationships continue to use established behavior; malformed relationships are retained rather than blocking the requested field correction.
- Draft triplet insertion accepts existing content and preserved-gap conflicts. Expanding groups writes a positive backup rather than an invalid negative forward.
- Draft tuplet ratio edits accept noncontiguous/interleaved XML and imported group errors. Per-position cursor compensation keeps unrelated onsets unchanged.
- The negative-cursor diagnostic no longer blocks timing-preserving note deletion.
- Frontend draft intent includes direct note patches and triplet insertion. A duration palette entry is no longer unavailable merely because the existing imported rhythmic representation is inconsistent.
- Save/Save As continue to serialize the current review without requiring Validate, VERIFIED status, key declaration or comparison attestation.

Nonmusical checks were not indiscriminately deleted: missing object IDs, stale revisions, actual unreadable XML, upload/resource limits, unsupported command shapes and timing that cannot be calculated still report errors. This is not a claim that every specialized conversion supports every malformed document. The audit must not be described as removal of all error handling.

## Lyric root causes and correction

Imported lyrics contained default-y values -99 and -133. The previous view removed those coordinates only in multi-voice lyric allocation, leaving single-owner scores too far below the staff. Global allocation by voice also put verse 1 of a later voice below the earlier voice's verse 2.

The disposable rendering view now omits stale lyric offsets for all voices and aligns by verse number. Additional lanes are allocated only for simultaneous different-voice words in the same verse. A per-renderer lyric calculator places top-aligned rows before system spacing, one staff space below the lowest note-bearing staff/ledger line. Canonical words, verse numbers, voice ownership, note associations and stored offsets remain unchanged. No global library patch is applied.

## Evidence

- Full backend suite: 1135 passed, 3 skipped; existing dependency deprecation warnings only. Additional draft tuplets/interleaved-voice regression subsequently passed in the focused 10-test suite.
- Focused backend correction/notation suite: 147 passed before the additional regression.
- Frontend unit suite: 71 passed.
- Frontend lint and production build passed; existing large-bundle warning remains.
- Browser regression suite: 20 passed; the new cross-voice lyric test initially compared glyph ink bounds, which differ for Vietnamese accents. Inspecting SVG confirmed identical text baselines. The assertion now compares transformed text baselines, which verifies row alignment correctly; all four lyric tests passed on the separate rerun. A final 22-test workflow/provenance suite and lint also passed.
- Visual inspection of the exact active score confirmed verse alignment after layout changes. Live-score insertion verification preserved every original event.

No claim of Product Owner acceptance is made. The original preview remains running with its unsaved session. A new isolated preview serves the corrected implementation.


## Product Owner feedback — lower verse 1

The Product Owner confirmed note addition works well and requested lowering verse 1, using the displayed word “tầng” as the visual reference. The first-row clearance was increased by two staff spaces (from one to three); following rows move with it and remain top-aligned. This supersedes the earlier one-space display requirement for this preview. Canonical lyrics and note associations remain unchanged.

Verification: all five lyric browser regressions passed, including a low-ledger-note case measuring the three-space first-row clearance, later-verse stacking, cross-voice verse alignment and unchanged MusicXML bytes. Lint and build passed. Visual inspection of the retained real-score copy confirmed the lower placement. Addition to its formerly blocked measure still returned HTTP 200 and preserved all 186 original events. No production release or Git operation was performed. Acceptance of this revised lyric position remains pending.


## Clarified lyric-position requirement

The Product Owner clarified that verse 1 should occupy the former third-row position represented by “tầng”, leaving sufficient clearance below noteheads, stems and beams. Imported extra verses 3/4/5 must remain independently selectable for the user to delete; they must not be automatically renumbered or merged.

The renderer now adds two lyric-row steps to the existing first-row clearance. Subsequent rows stack below it. No automatic compaction of imported verse numbers was included. Canonical lyric content, numbering and note ownership remain unchanged.

Verification: all six lyric browser checks passed, including the lower first-row geometry, cross-voice alignment, unchanged XML, and selecting an extra verse with its original verse identity. The test browser needed explicit scrolling and a visible text click because its automatic SVG-group scrolling could place the target outside the viewport. Visual inspection of the real-score copy confirmed clearance below stems/beam in the reported passage. Lint/build passed; production and GitHub were not published. Acceptance remains pending.


## Production acceptance

On 2026-11-22 the Product Owner explicitly confirmed the requirements were met and requested commit, production packaging, updated launcher and GitHub push. The accepted correction/lyric work is promoted as 1.0.7. See docs/release-1.0.7 for current acceptance and package verification; earlier pending-status entries are historical implementation evidence.
