# Non-blocking correction and lyric/grace follow-up

Date: 2026-11-23. Preview only; no production release, commit or push.

## Requirements and scope

Addresses PC-02, PC-05, PC-06, PC-07 and PC-09 and the note editing, relationship, Undo/Redo, save and reimport acceptance checks. All Concert and written-instrument editors use the shared RealWorkspace commands. User-directed changes must not be vetoed by musical consistency diagnostics. Validate remains optional; Save retains current XML exactly, including unresolved musical errors.

The inherited typed Voice inspector and before/after display-size inheritance are preserved.

## Changes

- Beam commands no longer reject selected rests, chord members, differing voices/staves/measures or non-eighth written values. Only selected beam tags change; pitch, duration, ownership and unrelated notes stay intact. Imported unisons map in source order and measures map by their actual part/index. A renderer-scoped adapter restores explicit native beams in time order after note dragging reverses XML append order.
- Draft tuplet apply, divide, mixed rhythm and remove accept partial chords, interleaved voices, existing groups and cross-measure selections. Exact cursor compensation preserves unselected onsets; no automatic packing or voice substitution. Splitting preserves selected original note identities and associations at the first position; new positions inherit pitch/voice/staff/display characteristics without duplicating lyrics or ties.
- Timing-preserving deletion can remove malformed notes or unequal chord leaders. Surviving member durations and known onsets are preserved rather than normalized. The superseded tests requiring rejection now assert removal, survivor preservation and Undo.
- Draft slurs accept explicit different-voice endpoints and unconventional time order. Matching endpoint markings can also be removed in draft mode. Imported musical diagnostics do not override the selected endpoints.
- Draft pitch, size, duration and staff editing remove old musical eligibility gates; representable subdivisions refine exact divisions. Existing technical identity, XML parsing, stale-revision, request-shape and file-write errors remain actual failures, not music-validation gates. An operation that cannot identify its object or read a required time value cannot fabricate one.
- Lyrics with the same verse number share one visual row across voices. Rendering strips stale imported coordinates and renders lyrics below the staff. Editing a word no longer allocates a synthetic lower verse. Actual imported verse numbers, words and note attachments remain unchanged.
- Grace before and Slashed grace explicitly add a grace-to-principal slur. Grace has no duration element and adds no beats; all principal notes retain their timing. Same-onset grace/principal slurs are recognized, rendered, editable and persisted. The command uses the selected principal note as the explicit target.

Musically inconsistent beam/tuplet data is intentionally allowed to be saved. Native engraving may not display a conventional beam for intrinsically incompatible values (e.g. a whole note and an eighth in different voices); the application must retain the user's markings rather than alter note values to force engraving.

## Verification record

- Full backend suite before the final grace follow-up: 1,142 passed, 3 skipped. Two old rejection expectations were deliberately replaced by PC-09 preservation/Undo assertions. Initial failure of a draft tuplet regression exposed automatic packing; removed packing and reran successfully.
- Final grace/slur and chord-replacement backend regression: 75 passed, 3 skipped. Includes slash/no-slash, zero added beats, unchanged principal onsets/durations, explicit slur endpoints, reimport and Undo.
- Frontend unit suite: 71 passed; typecheck, lint and build passed. Build reports the existing large bundle advisory.
- Shared editor, before/after inheritance, beam and lyric layout E2E: 26 passed on the refreshed isolated preview.
- Tuplet tools, Small/Normal on single/chord members, active-instrument Save/Validate and Undo regression: 11 passed. Updated test navigation to open the accepted collapsed Notation & expressions group.
- Cross-voice/incompatible beam followed by exact-byte Save: 4 passed, Concert/Alto/Soprano/Tenor (included in the 26 above).
- Grace/slashed-grace visible slur and Undo on all four stages: 8 E2E passed. Final typecheck/lint passed.
- Live score was read and imported into an owned temporary review only. The user's original 5327 review remained untouched. No private score committed.

Preview: http://localhost:5328/. The active 5327 process was preserved. Production 1.0.7 and GitHub were not changed.

Automated evidence is not Product Owner acceptance. Technical Lead review and explicit user acceptance of this preview remain pending under ACCEPTANCE_CRITERIA.md.

## Live-session beam follow-up

The active 5327 tab was still running the earlier frontend bundle. A read-only snapshot of revision 113 showed that the requested D5/C5 Voice-2 beam markings were already present in canonical XML; the old renderer failed to display their reversed append order. The isolated refreshed editor rendered a native beam spanning these two small noteheads, including their existing 3/16-beat gap. No pitches, durations or onsets were changed.

Added explicit same-session resume for a refreshed editor tab: GET the existing review rather than import/recognize again, retain review ID, revision, source PDF and Undo/Redo. A resumed view does not own or delete the borrowed review on unmount. The original owner tab must remain open while its borrowed session is used; closing the original owner still invokes the existing session-deletion behavior.

Selection highlighting is reapplied after asynchronous engraving and includes all selected group members. Resume/history/selection regression and both XML-order beam regressions: 3 passed. The live user's musical document was not changed to obtain this result.

Applied Beam 2 via the updated browser editor to existing new-54/new-57 on the live 5327 review. Native beam geometry spans both noteheads; 203 events, pitch/duration/onset/voice/staff/grace/display-size/lyric ownership unchanged, Undo retained. Updated tab is kept open; original owner tab is retained to preserve its in-memory session lifetime.

## Preview process outage recovery

Both tool-attached preview servers stopped between turns, causing Failed to fetch in the still-open editor. Before reloading anything, Save and Export saved MusicXML preserved the current browser document at a local MusicXML recovery file. Recovery copies are under /tmp and were not committed.

Restarted 5327 as a detached process in its own session, with optional DiskReviewStore JSON checkpoints under ~/.local/state/music-sheet-transposer/preview-5327. Restored the same review ID/revision 114, stable event/lyric IDs and original PDF. The restored MusicXML is byte-identical to the newly exported browser file and contains 203 events. Older in-memory Undo history was lost with the process; only the closest available pre-beam checkpoint was recoverable. No claim of complete older history recovery is made. The pending empty verse-4 input on e-33 was left untouched; the page was not reloaded.

The recovered review is explicitly protected from stale owner-tab pagehide DELETE requests, so the old tab no longer controls its lifetime. Other review deletions retain their normal semantics. Checkpoint serialization retains XML bytes, IDs, source and history across subsequent restarts, uses atomic replacement and rolls memory back if checkpoint writing fails. Three persistence tests passed; restart equality and a real isolated Vietnamese lyric PATCH succeeded on the live server.

## Restored identity allocator follow-up

The subsequent lyric-add 500 was a separate recovery bug: the seeded sequence was 100/105 while retained lyric refs already included new-106, new-107 and new-108. The next lyric addition overwrote an existing ref; payload projection raised KeyError before commit. The last valid review remained intact. The edit allocator now reserves the highest new-N prefix across the current document, Undo and Redo before allocating a fresh ID. It does not renumber existing refs. Added direct regression tests for stale counters, lyrics, suffix IDs and history. Together with checkpoint/workflow regressions: 27 passed.

Reproduced the exact e-31/verse-2/su command on a full isolated copy of live revision 119: succeeded using new-109 and retained existing lyrics. Restarted the same durable 5327 server from its latest checkpoint; replayed the user's pending su command through the current inline editor without reloading. Live revision 120 contains su at e-31 verse 2; all 203 events remain. Successful lyric requests now also set Lyric saved instead of leaving an earlier failure notice visible (frontend source follow-up).

## Chord symbol at a shared note position

2026-11-23: Added C7 directly on the active 5327 review at m-11 onset 0 (selected C5 e-61, shared with Voice-2 C5 e-60). Persisted harmony new-199 is root C, alteration 0, dominant, text 7. Live revision 210 retains all 207 event identities and all pitches/onsets/durations/voices/staves/lyric associations from revision 209.

The shared frontend now opens Add Chord immediately at an already selected note. When a pointer hits several voices at the same measure/staff/onset, chord entry uses that position directly instead of requiring a note-voice decision. Note editing retains its voice chooser. Successful chord save clears the instructional notice. The same live tab was refreshed against its existing durable review after checking there were no pending inputs; original PDF (2 pages), 207 heads, saved C7 and 50% working zoom were verified.

Regression coverage includes physical mouse hits on overlapping noteheads and selected-note activation on Concert/Alto/Soprano/Tenor. Typecheck/build and lint passed. Test navigation scrolls notes into view after toolbar activation and scopes the chord popup outside the stage fieldset. The live review was not used as a synthetic test fixture.


### 2026-11-25 — engraving timelines, lyric collisions and syllable control

Addressed PC-02, PC-05, PC-06, PC-07 and PC-09. Rebuilt disposable per-voice engraving streams in temporal order, including invisible spacing rests and engraving-only overlap spans. Original canonical XML, event onsets/durations/voices, playback and saved content remain untouched. Retained original durations for interactive event mapping. Added a shared Lyrics syllable connection control: independent/start/middle/end.

Verification: production frontend build passed; equal-onset coordinate regression passed for C4/Bb4 and A4/D5; rendered beam regression passed; adjacent Giê/su bounds regression passed after waiting for both labels; shared inspector six cases and Stem Auto/Up/Down four stage cases passed; syllable connection persistence test passed with unchanged text and note model. Initial asynchronous-bounds checks failed and were corrected to await rendered labels. In the existing borrowed session, both pairs of head centers aligned within 0.001 CSS px at 60% and canonical XML/revision were identical before/after refresh. Musical user content was not changed. Technical review and Product Owner acceptance remain pending.


### 2026-11-25 — PDF transparent spacer regression

Removed invisible rest SVG groups, including modifiers, before display/PDF conversion. PDF serialization now explicitly drops fully transparent paint and hidden ancestor content because eight-digit hex alpha was converted to black by svg2pdf. The corrected Export PDF UI was built, verified with Auto and Standard 12 mm margins using the exact recovered Alto, and loaded into the existing user tab. Source Concert and Alto XML were exported through the existing UI for recovery; the Alto was restored unchanged, including its saved status. A scoped resumeOutput/Instrument/Direction recovery path reopens the persisted instrument review rather than re-transposing it. Both PDF generation and manual preview checks passed; before/after Alto bytes and revision were unchanged. Acceptance and technical review remain pending.
