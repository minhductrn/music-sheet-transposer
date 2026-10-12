# Phase 4F — Visual Score Correction UX

Implemented for browser acceptance; not checkpointed. Principle:
**See the mistake → click it → correct it.**

## One correction document, two editing levels

**Visual Review** is the default. Click a rendered notehead/rest, or focus it and
press Enter/Space, to select the corresponding semantic event. Selected heads
highlight blue. The toolbar provides Pitch, Duration, Lyric, Add note, Tie,
Remove tie, Delete note and Advanced. Undo/Redo remain prominent above the score.
**Advanced Review** retains the existing technical Event Inspector, navigation,
metadata/harmony controls and validator diagnostics. Both modes use the same
selection, backend document, revision, history and Phase 4E API.

OSMD remains a renderer. The mapping compares its untransposed source note's
part, measure, staff, voice, relative timestamp, duration, pitch and grace identity
with the backend projection. Only unique matches whose source measure agrees with the graphical measure are
accepted; renderer-generated continuations across barlines are not insertion anchors. VexFlow's key index
maps each chord member to its own SVG head; shared/ambiguous unison heads are not
assigned arbitrarily. IDs stay in view bindings, never in exported MusicXML.
Bindings are discarded and rebuilt after XML refresh or resize. Deleted selection
clears; surviving selection stays, and added/restored events become selected.

Pitch buttons move one diatonic staff step, including octave boundaries, independent
of clef or pixels. Destination spelling follows the effective traditional key at
the selected event, including mid-measure changes. Flat/Natural/Sharp provide an
explicit override. Earlier measure accidentals are not inferred as editorial intent.
Unsupported key spelling requires Advanced review. **No dragging or snapping is
implemented.** There is no fake drag preview.

Duration choices show musical symbols and names (sixteenth/eighth/quarter/dotted
quarter/half/dotted half/whole), never raw fractions. Backend picker options are
checked using the existing duration patcher against divisions and all affected
chord members, including tuplet restrictions. Grace timing remains Advanced.
Sequential insertion uses standard values representable in the anchor divisions.

## Missing notes, barlines and ties

Select an existing pitched anchor → Add note → Before/After/At the same time.
The draft starts at its pitch, with step buttons, accidental and named duration
controls; relative staff-step feedback identifies the draft's position. Apply
patches the document, validates and refreshes the actual score. The draft is not
engraved on an arbitrary guessed staff position. The inserted note is selected,
so repeat Add note to insert multiple adjacent missing events. A simultaneous
addition shares the anchor's existing rhythm. Sequential additions inherit its
voice/staff through the existing API. Rests/empty measures without a safe pitch
anchor use Advanced; **empty-space insertion and arbitrary onset placement are
not implemented**.

Placement stays in the selected anchor's measure. To add across a barline, select
an anchor there. No overflow movement, barline rewriting, backup/forward repair
or automatic voice rebalancing occurs. Insertion overfill stays ERROR. A newly
exposed duration-edit gap was fixed by marking timing edits for the same existing
blocking overfill check; the ordinary imported-score mismatch policy is otherwise
unchanged. Representable invalid drafts remain visible and undoable; verification
is blocked. Friendly messages explain excessive measure length and offer technical
details. This cannot establish source measure ownership automatically.

Select source → Tie → valid target heads highlight green → click/Enter target.
Only the backend's current compatible targets may be used. New adjacent manually
inserted notes are eligible. Two tied notes remain separate duration-bearing
notes. Existing ties can change target or be removed. Phase 4E sound `<tie>` and
notation `<tied>` semantics, adjacency checks and preservation rules are reused.
If a target cannot be mapped visually, use the Advanced tie dropdown.

## Lyrics and lifecycle

Select an existing or newly added note → Lyric. Add a verse, edit a specific verse
and text segment, or Remove lyric for that verse on that note. Vietnamese Unicode
is sent unchanged. Text-only edits retain syllabic, elision, extend and verse
structure. Other verses and musical fields remain intact. Removal intentionally
removes the selected whole lyric element; complex melisma/attachment reconstruction
is not inferred. Lyrics can be edited without inserting/recreating notes.

The only new mutation endpoint is revision-checked
`DELETE /api/v1/reviews/{id}/lyrics/{lyric_id}`. Add/edit/remove record lyric
provenance on the owning event and use existing snapshots, validation and
verification invalidation. Home clears derived transposed output on every updated
review. Verified corrected bytes enter the unchanged preservation transposer;
lyrics survive 0/+2/−2 without alteration.

MusicXML uploads now offer **Open Visual Review**, with optional PDF/image source.
PDF/image recognition still opens the same review. An open MusicXML review must be
verified before transposition, and transposition uses its corrected document.
Direct MusicXML transposition without an open review remains available.

Sessions still use bounded process memory and expire or disappear on restart.
A session-not-found response retains the browser's XML, disables corrections and
explains that reimport is required. **Download corrected XML** remains local and
available. Save it before closing/reloading, then upload that download and open
Visual Review again. Persistence was not redesigned.

## Source comparison and limitations

Source and score stay side by side when space permits. Existing issue evidence
coordinates drive source highlights only when trustworthy geometry exists; note
selection also selects related evidence. Native PDFs retain the existing page
navigation limitation. No coordinates are fabricated for manually added notes.
OSMD may reflow systems/pages substantially compared with the PDF; mixed-size
chords and tie engraving still require browser inspection. Layout reconstruction
is outside Phase 4F.

Other limitations: duplicate semantic events/shared unison heads, nonnumeric voice
labels or renderer-normalized unsupported events can require Advanced selection;
rendered lyrics are edited through their selected note, not direct lyric clicks.
Pitch dragging, empty-position placement, structural repair and melisma editing
are not implemented. Keyboard/buttons provide every implemented action.

## Validation and manual browser acceptance

The complete backend suite passes **627 tests**, with two existing dependency
warnings. The complete frontend suite passes **50 regressions**; lint and
production build pass, with the existing OSMD bundle-size warning.

Automated tests exercise actual component callbacks and the OSMD binding adapter
with semantic/SVG doubles. They do not establish real-browser engraving, focus,
resize behavior or downloads. Browser acceptance is required before checkpointing.
No Audiveris or SMT invocation is needed for this synthetic fixture.

From the repository root, start one backend worker and the frontend:

```bash
cd backend
env -u PYTHONPATH .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In another terminal:

```bash
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

Open `http://127.0.0.1:5173`. Docker/database services are not required for review
storage. Leave an existing server/session running if already available.

1. Upload `backend/tests/music/fixtures/visual_review.musicxml`, clearly labeled
   synthetic. Optionally attach a comparison image/PDF; click Open Visual Review.
2. Click the first measure's notehead. Confirm its blue highlight and keyboard
   focus/Enter selection. Open Advanced to confirm synchronization; return Visual.
3. Use Pitch → one staff step up/down; use Duration → Eighth, then Undo to restore
   Quarter. Confirm each update refreshes the score and uses the next revision.
4. On that first note, Add note → After → Draft pitch up once → Half → Apply.
   This creates the first missing note. On the inserted note, Add note → After →
   Eighth → Apply without moving draft pitch. Both must remain separate notes.
5. Select the first inserted note → Tie → click the green second inserted note.
   Inspect both endpoints in Advanced. Undo/Redo, Remove tie/Undo; ensure timing
   remains unchanged. Changing targets requires another backend-compatible target,
   such as an equal-pitch adjacent chord member in a separate test document.
6. On the original note, Lyric → Verse 1 → change `khế“ịp` to `khắp` → Apply.
   Confirm Verse 2 remains `khác`. On a new note add `đây`; Remove lyric, Undo/Redo,
   then Undo removal. Inspect exported Unicode and syllabic metadata.
7. Delete the original note; Undo, Redo, then Undo to restore intended content.
   Check selection clears after deletion and follows restored notes.
8. On the inserted half note, choose Whole to deliberately overfill the measure.
   Confirm the friendly barline message, ERROR in technical details and blocked
   verification. Undo. Select the second measure's note and insert an Eighth
   after it; it must stay in measure 2, report overfill and never move a barline.
   Undo. Optionally test simultaneous insertion and Undo.
9. Resize the browser; verify selection/highlight, chord heads, keyboard targeting
   and source comparison still work. Select an issue in an evidence-backed review
   to check coordinated source/score highlighting and missing-geometry fallback.
10. Validate; resolve any candidate issues and confirm source comparison only after
    checking the intended musical content. Mark VERIFIED, transpose +2, download
    verified corrected and transposed XML; compare pitches, ties and exact lyrics.
11. Make a lyric/pitch edit after verification. Confirm VERIFIED is removed and
    transposed preview/download disappears; Undo/Redo must still require verification.
12. To check session resilience in a disposable review, close its server session
    through the API or wait for expiry while retaining the browser tab. Attempt a
    correction; confirm the reimport message and retained local corrected download.
    Save, reupload the corrected XML, open Visual Review and continue editing.

Do not apply synthetic fixture arithmetic as a diagnosis of the unavailable real
Phase 4E browser session. Its cause remains unknown.

## Phase 4F.1 foundation update

The architecture review and its SOURCE FIDELITY CONTRACT supersede the earlier
unchanged-architecture acceptance recommendation. Existing Visual Review editing
primitives remain. XML-bound structure, independent source evidence and guarded
source grouping now supplement them. Overfilled imports are blocking conflicts,
not silently repaired. Source layout uses a stable-width OSMD review mode and
renderer-only hints; export XML remains preserved. Dragging, empty-position
insertion and structural reassignment are still absent. Browser acceptance has
not been performed; see the architecture document for the next scoped gate.

## Review workspace containment fix

Browser acceptance reported that the fixed 1000px source-review engraving page
was displayed at full scale inside a narrower comparison pane. Visual Review now
uses independent bounded source/score scroll panes and proportional **Fit / − /
100% / +** score controls. Fit is the default; zoom changes only a CSS presentation
transform and the scroll canvas dimensions. The source-review engraving width
stays 1000px, so zoom does not change grouping, XML, evidence or musical timing.
Normal preview outside review retains its previous rendering behavior.

One expandable Validation panel now precedes the comparison workspace and stays
nearby while scrolling; it uses the same backend result, with bounded details.
Existing PDF page/zoom/open-source controls, VisualNoteEditor and Advanced Review
are retained. Narrow screens stack the panes. Zoomed notation scrolls locally.

Source grouping is a separate concern: explicit XML breaks still pass through the
rendering document with OSMD break options enabled; guarded `.omr` groups still
produce renderer-only print hints. The viewer's load path is regression-tested.
This establishes the integration path, not the correctness of any unavailable
real-score source mapping or OSMD's exact final line breaks. Repeat real-browser
acceptance at normal desktop sizes, exercising Fit/100%/zoom, pane scrolling,
selection/ties, PDF controls and validation visibility. No musical reconstruction
or Phase 4F.2 functionality was added.
