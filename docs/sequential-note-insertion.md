# Sequential note insertion — development change

Select a duration-bearing note or rest in Working Score. In the note tools, choose **Add note before** or **Add note after**. Set pitch, accidental, octave, duration, optional dot and voice, then choose **Insert note**. The selected staff is retained. Cancel leaves the score unchanged.

In the selected voice, this uses the existing sequential-anchor API and moves following XML content in the measure. Review all voices, especially imported polyphonic scores, after insertion. A different voice uses an explicit onset and keeps existing positions; conflicting occupancy is rejected by the existing API. This feature does not automatically reconstruct incorrect OMR voice assignments or shift notes into another measure. Grace-note anchors are disabled.

A predicted measure overflow displays a warning, without disabling insertion. Use Validate to inspect the resulting score. This allows deliberate OMR correction; adding a note does not itself repair other incorrect notes or durations.

Changes use the canonical review edit/history path and the shared Working Score editor in both stages. Production 1.0.6 remains unchanged. No release, commit or push is included.

## Verification

- Frontend lint and build: passed (existing bundle-size warning).
- Backend insertion/chord/scanner regression tests: 72 passed.
- Firefox before/after insertion: passed for C5 dotted half plus C5 quarter, Undo/Redo, MusicXML export/reimport and lyric preservation.
- Initial browser scripts failed due SVG pointer hit-testing and Undo/Redo selectors; scripts corrected before the passing run.
- Relevant constitution: PC-01/02/06 explicit user correction, PC-03/05 canonical persistence, PC-07 regression protection.
- Product Owner acceptance pending. No claim of automatic repair of the supplied OMR document.

## Drag placement on Working Score

Open **Notes** and drag a duration button onto a staff. During dragging, a blue notehead marks the snapped destination; the tooltip shows pitch, measure, beat and voice. Release to add; Escape or release outside the staff cancels. Position snapping uses the supported clef and a binary grid through 64th-note positions, plus existing recognized onsets. Unsupported clefs and positions outside rendered staff bands do not produce insertions.

Existing notes retain their positions. A distinct pitch with the same onset and duration joins the current voice's chord. A unison, occupied rest, overlapping sustained note, different simultaneous duration or insufficient finite gap uses a new unused voice, visibly identified before release. This does not automatically correct earlier OMR voice assignments. The preferred voice is the selected event's voice, otherwise voice 1. Original Source remains read-only.

The backend refines divisions for bounded binary drop onsets only, preserving all original musical times. Existing arbitrary non-representable tuplet guards remain intact. An initial unrestricted refinement failed one legacy guard test; refinement was narrowed and the regression suite then passed.

Verified: 5 drop planning tests; 3 Firefox mouse tests (same position, intermediate position, Escape cancellation and Undo); 73 backend tests including binary-grid MusicXML roundtrip. Frontend lint/build passed. Initial browser script failures were due duration-button labeling and taking a bounding box during a score rerender; corrected before passing. iPad/touch and all instrument editor combinations have not been manually verified. Product Owner acceptance pending.

Discoverability update: a labeled **Drag notes onto staff** strip is always available under the Working Score heading and at the top of Selected note tools. Starting a drag closes the edit popover. Three Firefox tests pass using these visible strips, including dragging while Selected note tools is open. On a short window, scroll Working Score into view so both source button and target staff are visible.

Additional investigation: same-position drag tests pass at 70% and 50% zoom. Adding a quarter after the last voice-1 note in measure 3 of the supplied unedited Giêsu Vua Muôn Vua XML did not reproduce the reported outside-staff rendering at 70%; note bounds remained inside that measure. This does not verify the currently edited user document. The edited MusicXML is needed before a rendering or positioning correction can be selected. No speculative layout fix was applied.

## Existing-note movement and voice layout

Select a note, then drag predominantly horizontally to reposition it within the same measure, staff and voice. The preview shows its new beat, fixed pitch and voice. The edit popover closes when dragging starts. A predominantly vertical drag retains the existing pitch-edit behavior. Escape, pointer cancellation or release outside the original measure/staff cancels. Shared heads use the explicitly selected event, or retain the existing ambiguity chooser. A successful move is one canonical edit with Undo/Redo; other notes keep their onsets. Same-voice collisions fail atomically without silently joining a chord or switching voices.

Same-owner repositioning preserves ties, articulation and lyrics. Cross-owner safeguards remain unchanged. Notes with beam, tuplet or instrument-specific context still require that context to be resolved before changing their temporal position; arbitrary tuplet/beam movement is not claimed.

Confirmed layout cause in the user's updated XML: VexFlow Formatter.createTickContexts takes the horizontal span from the first voice's getTicksUsed(), even if another voice extends farther. The adapter in editingLayout.ts supplies the longest voice span to these disposable layout getters, on this renderer instance only, before width calculation. It changes no canonical XML, meter, voice membership, tickables or note timestamps. The initial Duration and totalTicks attempts did not fix the issue and were replaced; no debug probe remains in source. Keep this adapter under regression tests when upgrading OSMD/VexFlow.

The updated user file's voice 2 in measure 3 has four beats of notes starting at 21/8 beats; this offset is preserved. Fixing layout does not automatically realign that musical timeline. Before the adapter, the last two notes rendered past the stave; after it, the measured note bounds are inside. This is independent of the rule that each voice has its own meter capacity.

Verification: 75 targeted backend tests passed, including same-voice movement, collision atomicity, tie/lyric preservation, binary-grid refinement, Undo/Redo and XML roundtrip. Ten Firefox tests passed, including unequal voice spans at 100/70/50 percent with unchanged canonical XML, actual horizontal dragging preserving voice 2, and prior insertion/drag workflows. Frontend lint/build passed, with the existing bundle-size warning. Preview 5321 includes Audiveris configuration; existing previews and production were not restarted. Product Owner acceptance remains pending; complex beamed/tuplet movement is an explicit limitation.

## Layout correction — 2026-11-22

Per Product Owner feedback, the standalone drag strip in Working Score and its duplicate in Selected note tools were removed. Drag insertion now belongs only to the shared **Notes** toolbar palette, consistent with Rest/Groups and the established page layout. The palette briefly explains drag-to-add versus click-to-edit. It closes only after a real drag begins, preserving duration-click behavior. No score or backend semantics changed. This supersedes the earlier discoverability strip arrangement; Product Owner acceptance of the revised placement is pending (PC-06/07/08).

## Explicit beam detachment — 2026-11-22

Dragging a beamed note to a free position now offers **Detach beam and move** or **Cancel move** after the unchanged default request rejects it. Confirmation un-beams only its complete connected beam group within the same measure, voice and staff, then moves only the selected note. Pitch, duration, voice, tie/lyric data and other note onsets are retained. One Undo restores both beam connections and position. Cancel and failed confirmation do not change the canonical score; stale pending moves are cleared when review revision changes. Incomplete/cross-measure groups are rejected instead of guessed. Tuplet/instrument-specific timing is still guarded and cannot be bypassed by this beam option.

Verification: 76 targeted backend tests and 11 Firefox tests passed; lint/build passed. Browser coverage includes cancel without a revision change, explicit confirmation, unchanged companion notes and Undo restoring beam tags. Preview 5322 uses the updated backend; older preview sessions and production remain untouched. Product Owner acceptance pending. This supersedes the prior blanket beam-movement limitation for complete local groups, while maintaining PC-02/03/05/06/07.

## Individual voice correction for OMR chords — 2026-11-22

The supplied XML incorrectly represents G4 and C5 as one voice-1 chord. The existing PATCH voice behavior updates every chord member, so using it from a selected-note field could not split these into independent voices. The Selected event voice field now uses the existing explicit ownership endpoint when the chosen pitched note shares chord membership; other note types retain their previous path. Only the selected note changes voice, while pitch, duration, staff and onset remain fixed. Related context safeguards remain active.

Verified with synthetic G4/C5 at beat 4: G4 becomes voice 2, C5 remains voice 1, their onsets stay at 3 quarter-beats and their rendered head centers align within 3 pixels. Backend roundtrip and Undo preserve/restore chord membership correctly. Four targeted backend tests and four Firefox voice/layout/movement tests passed; lint/build passed. Current preview 5322 serves this update without restarting its backend. Original user XML was read, not modified. Product Owner acceptance pending (PC-02/03/05/06/07).

## Lyric layout across voices — 2026-11-22

The former post-render voice offset moved lyric SVG rows after system spacing was already decided; it could place a voice's lyrics in the gap above the next system. Multi-voice lyrics now receive distinct renderer-only lane numbers per part/staff before OSMD engraving. Imported absolute/relative lyric offsets are omitted only from that disposable multi-voice view, so native layout reserves the needed rows and system spacing. Canonical verse numbers, words and note associations remain unchanged. The renderer maps each displayed lane back to the original verse when binding the lyric editor. Single-voice layout retains its existing numbers and hints.

Two Firefox regression cases at 100/80 percent verify lyric rows below their own stave and above the actual next system, correct voice row order, unchanged canonical XML and opening the original verse-1 editor for a voice-2 lyric displayed in a later layout lane. Initial test failure compared the next measure on the same staffline with the next system; corrected to measure actual staffline boundaries. Build and lint passed. This fixes view layout, not incorrect user/OMR word-to-note assignments; no automatic reassignment is performed. Product Owner acceptance pending (PC-02/03/05/07).

## Mandatory non-blocking save and OMR correction — 2026-11-22

The Product Owner requires editing to treat the original score as the user's reference and musical checking as optional. Workspace insertion, tuplet edits and ownership moves now explicitly request draft editing. Rhythmic occupancy and finite-gap guards are bypassed for these draft commands, while legacy API callers retain the previous strict default. No automatic voice switching is performed by the drag planner; the Notes palette exposes the insertion voice. Existing-note movement retains its own voice. A complete beam group may be detached as part of the draft move without a repeated confirmation, with Undo restoring the operation. Structural relationship limitations, including complex tuplet/instrument-specific movement, remain; this change does not claim arbitrary malformed XML support.

Save/Save As no longer check can_verify, require OMR comparison confirmation, force key declaration or call verify. They write the current review bytes directly and retain the existing honest download/file-receipt behavior. Validation information is available only as an optional user tool and does not gate persistence or normalize musical data. Production packages and GitHub have not been updated.

Verified: browser test loads a review with can_verify=false, invokes Validate, chooses Save and compares the actual downloaded file byte-for-byte with the review; no verify request is made and the review revision/content stay unchanged. A second browser test permits temporary same-voice overlap without shifting another note. Eight drag-planning tests passed; 78 targeted backend tests passed, including strict-default compatibility and explicit draft-conflict editing. Lint/build passed. Preview 5323 includes the updated draft API; previous user sessions were not restarted. PC-09 is recorded in the constitution and acceptance checklist; Product Owner functional acceptance is pending.

Magnetic alignment now favors an existing note onset within eight screen pixels, independent of zoom; a green vertical guide and Aligned status indicate exact note-column alignment. Different voices remain independent. Alt retains fine-grid placement. The regression case moves a voice-2 G4 to the voice-1 D5 onset while preserving the preceding voice-2 note and displays the aligned voice and beat before release.

## User-selected beaming after appended edits — 2026-11-22

Beam selection previously required adjacent same-voice XML nodes, which rejected visually adjacent notes added later through isolated backup/forward streams. That storage-order gate is removed. Selected notes are ordered by canonical onset, and only their beam elements are changed. Tuplet markings, pitches, voices, lyrics, timing and nonselected notes are retained. Beamable values include eighth, sixteenth, thirty-second and sixty-fourth notes; secondary levels use forward/backward hooks for mixed values. Groups now includes Beam selection and Beam 7 alongside the prior fixed counts. Selection must still resolve existing pitched beamable notes in one measure, staff and voice; no automatic duration conversion is performed.

Firefox regression recreates two eighth notes at beats 1 and 1.5 whose XML nodes are separated by a later quarter note. Beam 2 succeeds, renders one beam, retains all three notes' pitches/onsets/durations and supports Undo. Lint/build passed. Current preview 5323 was updated without restarting its backend or clearing user sessions. This is a presentation edit under PC-02/05/06/07/09; Product Owner acceptance pending.

## Equal-onset alignment with transient same-voice overlap — 2026-11-22

Read-only inspection of the live user session confirmed that C5 voice 1 and G4 voice 2 already shared onset 59/16, while their rendered head centers differed by approximately 15 pixels. The preceding A4 voice-2 interval overlapped G4; VexFlow advanced that voice's sequential tickables and displaced the later head despite the canonical timestamp. This was a renderer defect, not a failed move command.

rhythmicView.ts now assigns overlapping intervals to independent disposable engraving tracks, grouped by canonical part/staff/voice and onset. The renderer maps each track back to the user's voice when identifying noteheads, binding lyrics and editing. Lyric lane allocation also uses canonical voices, so temporary rendering tracks do not become extra user verses. No canonical XML, voice, pitch, duration, onset or playback data is rewritten. Missing view-only stem hints follow the original voice convention. The adapter uses chronological interval assignment, independent of the XML append order.

On a read-only snapshot of the exact live session, C5/G4 center separation fell below 0.01 pixel. A synthetic regression reproduces its fractional onsets and overlap at 100/70/50 percent, retains all six note identities and original voices, verifies canonical bytes unchanged, and opens the correct voice-2 verse-1 lyric editor. Nineteen Firefox regressions passed, including unrestricted Save, draft editing, alignment guide, lyrics and Beam 2; lint/build passed. Existing user sessions were not refreshed or edited. Product Owner acceptance remains pending (PC-02/03/05/06/07/09).
