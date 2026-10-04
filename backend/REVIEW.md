# Phase 4E: Review → Correct → Verify → Transpose → Export

PDF/image → Audiveris → **draft** MusicXML → source comparison and corrections →
structural validation → explicit human verification → corrected MusicXML →
the existing preservation transposer.

The recognition provider, compressed-MXL boundary, preservation transposer, old
internal models/parser/exporter and both transposition endpoints remain unchanged.
No recognition pass runs when an event or text object is corrected.

Phase 4D.2 adds [Audiveris semantic recovery](SEMANTIC_RECOVERY.md) before review.
Optional `omr`/`analysis_omr` uploads populate candidate evidence in this same session.
Automatic recovery preserves the original MusicXML and can be undone; ambiguous
candidates select related events for explicit correction. Candidate evidence records
the import, while current rhythm is checked again during validation/verification.

## Model and preservation boundary

`app/music/review/` is a separate correction layer:

- `models.py`: `EditableScore`, parts, measures, voices and events; typed correction
  requests. Duration/onset are exact rational **quarter beats**, serialized as strings
  such as `1`, `1/2`, `2/3`. Original duration units and effective divisions are also
  exposed. Events include pitch, rest/unpitched identity, voice, staff, chord group,
  grace timing, visual size, ties and lyric IDs. Lyrics retain separate text segments;
  harmonies retain their root, kind, displayed text, measure and onset.
- `document.py`: safely parse original partwise XML and retain the complete tree.
  Reject entity declarations, excessive depth (>64), excessive nodes and malformed
  documents. External DTDs are never fetched. Initial object IDs are deterministic
  document-order identifiers, kept in a sidecar mapping to actual XML nodes.
- `importer.py`: project the preserved tree and evaluate ordered note/chord,
  backup/forward timing using inherited attributes and exact fractions. Derive
  diagnostics without altering XML or assuming a small note has grace timing.
- `patcher.py`: change selected XML nodes. All unrelated layout, directions,
  dynamics, tempo, lyrics, ties, slurs, articulations, beams, metadata and unsupported
  elements remain in the tree. Sequential insertion/deletion deliberately changes
  the ordered rhythmic stream; it does not guess compensating backup/forward events.
- `storage.py`: replaceable `ReviewStore` protocol and bounded process-local memory
  implementation. The XML/identities travel together in history snapshots.
- `source.py` / `service.py`: safe original source retention, atomic corrections,
  revision checks, bounded history, lifecycle and verification.
- `api/v1/reviews.py`: HTTP boundary; parsing, edits, validation, base64 and large
  JSON encoding run off the event loop.

No review IDs are inserted into the exported MusicXML. Existing IDs survive edits,
deletion of neighboring events and undo/redo. Newly created objects receive session
sequence IDs that are never reused after branching history. Creating a new session
from an export establishes new deterministic initial IDs.

An unedited document exports **identical original bytes**. After a correction,
ElementTree serializes the preserved tree as UTF-8. Namespace prefixes, quotes,
empty-element formatting and the original DOCTYPE may change; comments and
processing instructions inside the root survive. Original uploaded XML bytes remain
available separately for the lifetime of the session. This is tree preservation,
not a byte-level text editor or full MusicXML schema validator.

## Corrections and timing

The event inspector edits pitch/alter/octave, duration, voice, staff, display size
and explicit grace status. Pitch edits retain the note's other notation. Existing
printed accidentals are updated when appropriate. Rests and unpitched events remain
their own kinds; replace one by an explicit delete/add operation when necessary.

Duration edits retain the current divisions and existing simple tuplet ratio, and select
a matching note type and up to three dots. Tuplets with an explicit `normal-type`
require a notation editor for duration changes. Durations not representable in these
divisions or this notation are rejected, rather than silently changing divisions
throughout a score. Duration, voice and grace changes apply to an entire shared
chord; staff changes may affect one member for cross-staff notation. Converting a
grace chord to ordinary timing requires an explicit duration.

Add a note/rest before or after a selected **whole chord group**, or append to an
empty measure. Add a simultaneous pitched note after the existing chord members:
it inherits the anchor's duration, type/dots, tuplet ratio and stem, while its size
and pitch are chosen explicitly. It does not copy lyrics, ties or articulations.
Deleting a chord leader promotes the next surviving member and preserves the
advancing duration. Deleting a lone event advances later notes earlier. Inspect the
resulting diagnostics and compare positions with the original; no hidden timing
repair is performed.

The title editor updates movement/work titles. Printed credit text has independent
controls so a reviewer can correct the visible title without changing a composer
credit by inference. Lyrics support editing individual elided text segments and
adding an omitted verse on a selected event. Harmony edits affect root, alteration,
kind and displayed symbol while preserving degrees, bass, frames and other fields;
new harmonies anchor before an event's whole chord group. Roman-numeral/function
root conversions are rejected rather than changing harmonic semantics implicitly.

## Mixed-size simultaneous notes

An ordinary A4 plus a small C5 is represented as two duration-bearing chord events
with the same onset, duration and voice, `grace=false` on both, and independent
`display_size` values. Size is never converted to grace timing.

For a newly corrected small note, the XML uses **visual** MusicXML attributes:

```xml
<note>
  <chord/>
  <pitch><step>C</step><octave>5</octave></pitch>
  <duration>4</duration>
  <voice>1</voice>
  <type size="cue">quarter</type>
  <stem>up</stem>
  <notehead font-size="small">normal</notehead>
  <staff>1</staff>
</note>
```

This introduces neither `<grace/>` nor `<cue/>`. `small` uses the notehead font size
plus type size; `cue` display size uses type size alone. Existing explicit `<cue/>`
semantics are retained, so a display-only edit cannot remove actual cue semantics;
normal-size overrides on an explicit cue use `type size="normal"` while retaining
the original cue element and duration.
Reimport recognizes the small notehead attribute before type-size cues. Arbitrary
numeric font sizes are preserved but not guessed into relative size categories.
See the [MusicXML type-size definition](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/type/)
and [font-size definition](https://www.w3.org/2021/06/musicxml40/musicxml-reference/data-types/font-size/).

`tests/music/fixtures/review_mixed_size.musicxml` is an independent rich MusicXML
fixture proving both pitches, same onset/duration, chord/stem semantics, per-note
sizes and non-grace timing survive correction, reimport and 0/+2/-2 transposition.
There are no song-specific correction rules.

## API

All paths below start with `/api/v1/reviews`.

| Method | Path | Operation |
|---|---|---|
| POST | (root) | Multipart `musicxml` and optional original `source`; create DRAFT |
| GET | `/{id}` | Editable score, state, revision, diagnostics and current XML |
| DELETE | `/{id}` | Release XML, source and history immediately |
| PATCH | `/{id}/events/{event_id}` | Correct an event |
| POST | `/{id}/events` | Add note/rest, sequential or simultaneous |
| DELETE | `/{id}/events/{event_id}` | Delete event |
| PATCH | `/{id}/lyrics/{lyric_id}` | Correct text; optional `segment_index` (default 0) |
| POST | `/{id}/events/{event_id}/lyrics` | Add lyric `text` and verse `number` |
| PATCH / POST | `/{id}/harmonies/{harmony_id}` / `/{id}/harmonies` | Correct/add harmony |
| PATCH | `/{id}/metadata/title` | Correct score title |
| PATCH | `/{id}/credits/{credit_id}` | Correct printed credit |
| POST | `/{id}/validate` | Evaluate corrections; never verify automatically |
| POST | `/{id}/verify` | Explicit confirmation; block on ERROR |
| POST | `/{id}/undo` / `/{id}/redo` | Restore bounded correction and handling snapshots |
| POST | `/{id}/issues/resolve` | Confirm related manual correction or accept notation after source comparison |
| POST | `/{id}/transpose` | Revision-checked VERIFIED corrected XML → existing transposer → downloadable XML |
| GET | `/{id}/musicxml` | Corrected XML, or `?original=true` for exact draft bytes |
| GET | `/{id}/musicxml?verified_only=true` | Only VERIFIED corrected XML (409 otherwise) |
| GET | `/{id}/source` | Original PDF/image bytes with validated MIME |

JSON review responses carry `score`, `validation`, `musicxml_base64`, `state`,
`revision`, `expires_at`, `source`, `can_undo` and `can_redo`. Mutation requests
(including validate, verify, undo/redo) require `If-Match: "<revision>"` from the
last response/ETag: missing headers return 428, stale revisions 409. Invalid object
or expired session IDs return 404. No path input or provider invocation exists in
these endpoints. Responses use `Cache-Control: no-store`.

For example, to add the missing upper chord member in any score:

```json
{
  "measure_id": "m-1",
  "chord_with_id": "e-1",
  "kind": "note",
  "pitch": {"step": "C", "alter": "0", "octave": 5},
  "display_size": "small"
}
```

The chord anchor supplies the actual duration. Sequential additions instead use
`before_event_id` or `after_event_id` plus `duration` in quarter beats. Choose only
one anchor. Request schemas reject unknown fields and XML-incompatible text.

## Lifecycle, validation and verification

New recognition reviews start **DRAFT**, or **REVIEW_REQUIRED** when imported
semantic evidence includes recovery or review candidates. Corrections or first validation move them
to **REVIEW_REQUIRED**. Only an explicit verify request with
`{"confirmed_source_comparison": true}` moves a score to **VERIFIED**.

- **ERROR**: invalid pitch/octave, missing event representation/duration/divisions,
  invalid staff/voice, broken chords, overlapping intervals in one voice, negative timing, invalid required meter fields
  or an empty score. Verification is blocked until corrected.
- **WARNING**: measure duration mismatch, suspicious empty measures and timing that
  needs manual review (e.g. differing staff meters). Warnings remain visible and
  may be accepted only after source comparison.
- **INFO**: reminder that these checks cannot establish recognition accuracy.

Every correction, issue-handling action and undo/redo invalidates verification.
Unresolved semantic candidates also block verification; see the handling policy below. A structurally clean score
stays a draft until the user confirms comparison. Up to 500 diagnostics are returned;
all errors, including omitted diagnostics, still block verification. Duration
mismatch is a warning because pickups, unmeasured notation and export conventions
need musical judgment. Explicit `implicit="yes"` pickup measures may be shorter.

The frontend disables recognized-score transposition until VERIFIED. It sends the
review ID, integer semitone amount and current `If-Match` revision to the review
transpose endpoint. Under the existing storage lock, the backend checks that
revision and VERIFIED state, obtains current corrected XML, and calls the unchanged
preservation transposer. There is no download/re-upload step or original-XML
fallback. Direct MusicXML upload retains its existing transposition API; that API
remains independent of review sessions, so review gating is not a general access
control policy for uploaded XML.

## Source retention, limits and undo/redo

The original PDF/image is retained without re-recognition, validated by pypdf/Pillow
and served only as PDF/PNG/JPEG/WEBP. Size/page/pixel limits reuse recognition limits.
The viewer supports image zoom and native embedded PDF page/zoom controls, with an
Open source fallback where a browser ignores embedded PDF fragments.

The store is process-local, with opaque random capability IDs and a fixed lifetime.
Closing a review releases all data. Expiry is checked on every store access; a
FastAPI lifespan task also sweeps expired sessions at most every 60 seconds. Edits
do not extend lifetime. Restarting the backend discards sessions. Run a **single
backend worker** for this local implementation; a persistent/shared store must
replace `ReviewStore` before supporting multiple workers or production accounts.
Local browser state does not survive page reload; download corrected XML first.

| Environment variable | Default |
|---|---|
| REVIEW_LIFETIME_SECONDS | 3600 |
| REVIEW_MAX_SESSIONS | 8 |
| REVIEW_MAX_TOTAL_BYTES | 134217728 (conservative source/tree/history accounting) |
| REVIEW_HISTORY_LIMIT | 20 snapshots per undo/redo stack |
| REVIEW_HISTORY_MAX_BYTES | 8388608 per stack |
| REVIEW_MAX_XML_NODES | 100000 (also a fixed maximum depth of 64) |

Exceeding storage capacity returns 503 without changing existing sessions. Older
history is dropped when count/byte budgets are exceeded; large scores can have less
history or no history. Each edit applies to a candidate tree and commits only after
the edit and quota checks succeed. Concurrent updates to one revision have one
winner. A new correction after undo clears redo but never reuses an object ID.

## OSMD interaction and remaining limits

The workspace uses measure/voice/event navigation rather than fragile SVG click
matching. IDs are linked to XML nodes and canonical event positions. Selection
uses OSMD's public cursor iterator with measure index and exact onset (converted
from quarter beats to OSMD whole-note units). The inspector identifies pitch,
voice and staff; the cursor identifies the shared rhythmic position. It does not
claim to distinguish individual overlapping chord tones or separate grace heads.
Entries OSMD cannot expose retain an inspector label without a misleading cursor.
Preview resizing uses a component-owned ResizeObserver that is disconnected on
updates/unmount, avoiding accumulated window resize listeners during corrections.
See [OSMD 2.1.2 cursor](https://github.com/opensheetmusicdisplay/opensheetmusicdisplay/blob/2.1.2/src/OpenSheetMusicDisplay/Cursor.ts)
and [iterator](https://github.com/opensheetmusicdisplay/opensheetmusicdisplay/blob/2.1.2/src/MusicalScore/MusicParts/MusicPartManagerIterator.ts).

OSMD's VexFlow conversion selects cue scaling from the first graphical note in a
chord. It therefore cannot be relied upon to show independent mixed-size heads
faithfully. XML timing, pitches and per-note size remain correct; the workspace
warns about the preview limitation and exports the data for a capable notation
editor. No CSS/global note resizing or renderer internals are patched.
[OSMD VexFlow converter](https://github.com/opensheetmusicdisplay/opensheetmusicdisplay/blob/2.1.2/src/MusicalScore/Graphical/VexFlow/VexFlowConverter.ts).

This focused editor does not edit measure/staff creation, arbitrary onset placement,
backup/forward amounts, tuplet ratios, beams, arbitrary ties/slurs or full harmony degrees.
An inserted or existing note can explicitly connect a tie to an adjacent matching note;
see the missing-note correction workflow below.
It preserves them and reports relevant structural errors; complex rhythmic repairs
can require an external notation editor. Existing imported ties are not reconciled after a pitch
edit; manually connected insertion ties are checked and block verification if broken.
It does not infer new beam groupings. Small/cue rendering and native PDF controls need
real-browser validation. The existing transposer's limitations still apply:
nonzero microtonal/nontraditional-key transposition is unsupported, and harmony
symbols are retained rather than transposed. Verification does not add transposer
capabilities or promise faithful engraving.

## Exact real-world validation: Cùng Đem Tin Mừng

1. Start the existing Audiveris-configured backend with one worker and the frontend:
   `env -u PYTHONPATH .venv/bin/python -m uvicorn app.main:app --reload` from `backend`,
   and `npm run dev` from `frontend`. Keep the working OCR environment from OMR.md.
2. Import the PDF, choose Vocal song / clean digital score, and Recognize Sheet
   Music. Confirm the automatic review opens as DRAFT or REVIEW_REQUIRED with the original source.
3. Navigate/zoom the source and compare each measure with the OSMD preview. Record
   omitted notes, wrong pitches, timing, text and ties; do not accept the OMR export
   as ground truth. No further recognition runs when reviewing.
4. Open Title, lyrics and chord symbols. Correct score title and printed title
   credit independently. Select each lyric-bearing event, edit its text segments,
   or Add lyric when OCR omitted it. Correct/add harmonies against the original.
5. Select wrong notes by part/measure/voice/event. Correct pitch, alter, octave,
   duration and staff. Add before/after an event to restore omitted rhythmic notes;
   inspect onset/duration in the event label and the XML rather than just spacing.
6. At “ta”, ensure the duration-bearing A4 is **Normal**, then select/correct its
   simultaneous C5 to **Small**. If absent, set C5 / Small in the inspector and
   choose Add simultaneous note. Leave Grace timing unchecked on both.
7. At “cùng”, use normal F4 plus small A4 with the same onset/duration/voice. At
   “đem”, restore normal G4 at its original onset first, then add small B4 or Bb4
   using the **explicit alter required by the original** (`-1` for Bb). Do not set
   grace merely because the upper head is small. Confirm stem/chord membership.
8. Exercise Undo/Redo for a note, addition/deletion, lyric and harmony. Validate
   corrections, inspect every ERROR/WARNING and compare all measure timing with the
   PDF. Complex tie/beam or timing-event repairs may require a notation editor.
9. Handle every candidate issue by confirming a related correction or explicitly
   accepting it after source comparison, with a note. After resolving errors and
   reviewing warnings, check the source-comparison
   confirmation and Mark VERIFIED. Confirm transposition enables. Make one edit
   and ensure verification/transposition are invalidated; undo, review and verify
   again. Export corrected-verified.musicxml before closing/restarting.
10. Transpose 0, +2 and -2 separately. Download each XML. At 0 confirm the corrected
    bytes are unchanged; at ±2 confirm expected pitch changes and unchanged chord
    markers, duration/onset relationships, voices/staves, sizes and non-grace
    timing. Compare layout/ties/lyrics with the corrected document. Record the
    OSMD mixed-size limitation separately from XML correctness.

Automated checks: run the complete backend suite with its `.venv`, then frontend
`npm run lint`, `npm run build`, and `git diff --check`. There is no established
frontend test framework; this milestone adds no separate browser-test stack.


## Phase 4E issue handling and provenance

The existing `DRAFT`, `REVIEW_REQUIRED`, and `VERIFIED` states are retained.
The frontend displays correction/validation progress rather than persisting a
second state machine. Every accepted mutation projects and validates the patched
XML before committing and returns updated XML for immediate OSMD reload. Stable
selection survives ordinary edits; unsupported preview engraving does not undo a
valid XML patch.

`review_issues` projects import-time semantic candidates with current handling:

- `REVIEW_REQUIRED`: unresolved; verification is blocked.
- `AUTO_RECOVERED`: the corroborated import patch is present in its history snapshot.
- `MANUALLY_CORRECTED`: a related event/measure has a recorded manual edit and the
  reviewer explicitly confirms the issue is handled, with a nonempty note.
- `ACCEPTED`: the reviewer explicitly accepts the current notation after source
  comparison, with a nonempty note. This permits accepting a false-positive issue
  without fabricating a correction.

Use `POST /api/v1/reviews/{id}/issues/resolve` with `If-Match` and JSON such as:

```json
{
  "issue_id": "the-id-returned-in-review_issues",
  "disposition": "MANUALLY_CORRECTED",
  "note": "Compared the upper chord member with the source and corrected its display size."
}
```

`ACCEPTED` is the alternative disposition. Unknown issues return 404, stale
revisions/already-handled issues return 409, and invalid input returns 422.
Applying a patch does not silently claim it resolves musical uncertainty. A
correction in an issue's related measure conservatively reopens handling; its
previous note remains visible, and earlier snapshots retain the prior disposition.
Handle issues after finishing corrections in that measure. Global evidence
warnings without candidate IDs remain visible for whole-score source comparison.

Issue handling, manual-field provenance, stable evidence-to-event bindings and XML
share the existing bounded undo/redo stack and storage accounting. Undoing import
recovery reopens its issue; undoing a handling action restores its unresolved state.
Undo never restores VERIFIED status. New edits after undo still clear redo.
Event provenance distinguishes baseline/imported XML, semantic additions and manual
additions, and lists manually changed fields and related evidence IDs. Pitch edits
retain evidence identity. The original semantic report and original XML remain
unchanged. Sidecars are session data and are not embedded in exported MusicXML;
there is no durable audit log across session expiry/reimport.

## Validation, transpose and export behavior

The existing ordered MusicXML importer validates durations, chords, divisions,
staff/voice and backup/forward context; the existing exact-fraction rhythm checker
now detects voice overlap even without uploaded `.omr` evidence. Voice underfill
is a warning. The existing policies are preserved: ordinary review measure-extent
mismatch is a source-comparison warning, while semantic-evidence reviews also
retain recovery's blocking overfill check. Invalid/unrepresentable patches roll
back with an explanation. Structurally representable edits producing musical
errors remain visible, undoable and unverified; they are not silently discarded.
A display-size-only patch introduces no timing change or special rhythm rule.

`POST /api/v1/reviews/{id}/transpose`, with `If-Match` and
`{"semitones": 2}`, returns transposed MusicXML as an attachment without mutating
the verified review. Missing revision returns 428; stale/unverified reviews return
409; unsupported transposer values return 422. The stable transposer has no new
pitch/key/harmony semantics. The response carries the input revision as its ETag.

The workspace offers a draft download for saving work, a server-gated **Export
verified corrected MusicXML** action, and a separate transposed MusicXML download.
Changing the review, undoing/redoing, closing/reloading it, changing the import, or
changing semitones clears derived transposed preview/output. Export alone does not
invalidate that output. Another client's changes are detected by revision checks
on the next request; the local screen has no live cross-client synchronization.

Candidate selection coordinates inspector, OSMD rhythmic cursor and source
location. Valid bounds with page dimensions support a normalized image overlay
only when source aspect ratio is compatible; these are OMR evidence locations,
not a pixel-accurate source registration guarantee. Missing/incompatible geometry
shows an explicit fallback. Native embedded PDFs navigate to the evidence page
and display coordinates but do not support a box overlay. No new viewer or OSMD
internal rendering patch is introduced.

## Phase 4E validation checkpoint

The complete backend suite passes **611 tests** (the existing 544 plus 24 focused
workflow regressions, 18 human tied-insertion regressions and 22 existing-note
tie correction regressions plus 3 overfill-diagnostic regressions), with the same two dependency deprecation warnings. Frontend
lint and production build pass; Vite still warns about the large OSMD bundle.
The regressions cover mixed-size patches, unrelated XML preservation, invalid
inputs, undo/redo, issue acceptance/correction, provenance after pitch edits,
verification gates, stale revisions, corrected exports, and corrected-byte input
capture through 0/+2/-2 transposition.

Saved Cùng Đem Tin Mừng artifacts were unavailable in this checkout. Equivalent
synthetic A4+C5 and F4+A4 pairs were corrected regular→small, verified, and sent
through zero-semitone transposition with unchanged pitch/onset/duration/voice/staff,
chord structure and non-grace timing. No Audiveris recognition or SMT benchmark
was rerun. Native PDF navigation and mixed-size engraving still need real-browser
acceptance testing. Seventeen focused frontend component regressions use Node's built-in
test tools with the installed TypeScript compiler; no browser runner is installed.

## Human missing-note correction with a tie

Insertion already supported pitch step/alter/octave, exact rational duration in
quarter beats, voice/staff, grace and sequential/chord placement. Phase 4E adds
optional `tie_to_event_id` to `POST /api/v1/reviews/{id}/events`. No recognition
or recovery rule is involved. Durations are quarter beats: convert source beats
using its meter before entering the value.

Select an existing event as the insertion anchor. Set the missing note's pitch,
duration, voice, staff and display size in the inspector; leave Grace timing off.
Choose Note and optionally choose **Tie inserted note to**, then **Add before
selected**, **Add after selected**, or **Add simultaneous note** for a chord.
Targets are offered in this and the following measure of the same part. The
server checks matching written pitch, voice/staff, known duration-bearing timing,
and temporal adjacency (including a barline). Rest/grace/cue targets, skipped
measures, timing gaps, intervening events and rhythm errors are rejected atomically.
A continuation's existing tie start and unrelated notations remain intact.

Both semantic `<tie type="start/stop"/>` and notation
`<notations><tied type="start/stop"/></notations>` are patched. This is a musical
tie, not visual-only markup. An existing target stop is retained without duplication.
Undo/redo snapshot the inserted event, both endpoints, provenance and tie ownership.
Deleting an endpoint cleans the counterpart markup introduced by this operation,
while preserving preexisting target stops. Subsequent edits that invalidate a manual
link produce an `invalid_manual_tie` error and prevent verification.

Invalid tied insertions are rejected without changing revision. Ordinary insertions
can remain as undoable drafts; overlap/overfill errors block verification and
underfill remains a warning under the existing partial-voice/pickup policy.
Every insertion invalidates verification and clears transposed output through the
existing revision update. The preview loads corrected bytes without re-upload.
Inspect preview/diagnostics, Undo if incorrect, Redo if appropriate, compare with
the source, then verify, transpose and export using the existing workflow.

### Known source versus preview layout limitation

Real browser acceptance observed substantially different source-PDF and OSMD
system layouts. Preserved MusicXML layout information does not reconstruct source
line breaks, spacing or page/system geometry, and OSMD may reflow the score.
Compare musical events with the source independently of system placement.
Layout reconstruction is outside this correction task and remains unsolved.

The synthetic regressions cover a missing two-quarter-beat A note tied to its
following note, namespaces, barline connections, chord onset/alter, existing
continuations, rejection without mutation, deletion cleanup, undo/redo, verification
invalidation, unrelated XML preservation, corrected exports and corrected-byte
0/+2/-2 transposition with ties preserved. Run frontend checks with:

```bash
cd frontend
node tests/review-insertion.test.mjs
node tests/review-selection.test.mjs
npm run lint
npm run build
```

Repeat real-browser acceptance for the new insertion controls and tie engraving;
component tests do not validate OSMD rendering or native browser downloads.

## Existing-note tie correction

The first note may already be present. Select it, choose **Tie to** in the inspector,
and use **Apply correction**. The dropdown shows compatible notes by measure,
voice, pitch, onset, duration and staff; no internal event ID must be entered.
Its current outgoing target is selected automatically. Choose another compatible
target to change the relationship or **No tie** to remove it. Target changes are
limited to valid adjacent notes (for example equivalent chord peers), not notes
separated by a gap or an intervening event. The insertion selector remains separate.

The existing `PATCH /api/v1/reviews/{id}/events/{event_id}` accepts
`{"tie_to_event_id":"target-event-id"}` to add/change an outgoing tie, or
`{"tie_to_event_id":null}` to remove it. Omission retains the current relationship.
The shared tie helpers used by insertion patch both sound `<tie>` and notation
`<tied>` endpoints; only the source start and target stop are changed. Incoming
source stops, outgoing target starts, slurs, ornaments, articulations, lyrics,
harmony, timing and unrelated XML remain intact. Unambiguously paired imported
ties are supported; unresolved or duplicated endpoints require an external editor
rather than unsafe guessing. Missing IDs return a JSON 404 error; invalid
relationships return a JSON 422 error; stale revisions return a JSON 409 error.
Failures leave the document and revision unchanged.

Normal validation is rerun after the edit. Unlike insertion, tie-only correction
does not change rhythm and may repair a tie while unrelated errors remain. Those
errors/warnings are retained and verification stays blocked by any error. The
regressions include a draft with one error and seven warnings, whose diagnostics
remain identical after the tie correction. Musical compatibility still requires
valid, non-grace pitched endpoints of identical step/alter/octave, voice and staff
in the same part, at contiguous onsets in this or the immediately following measure.
Existing incoming relationships cannot be stolen from another source.

Add/change/remove travel through normal revision, provenance and undo/redo
snapshots. Each edit requires source comparison and verification again and clears
the stale transposed preview/download. Inspector drafts remount by revision so
correction and undo/redo display the current tie target. Automated frontend checks
exercise the actual component callbacks, with API/provider calls stubbed. Also run:

```bash
cd frontend
node tests/review-lifecycle.test.mjs
```

Synthetic A4 duration 2 at onset 0 tied to A4 duration 1/2 at onset 2 remains two
distinct notes. Corrected bytes feed the unchanged preservation transposer at
0/+2/-2 semitones with both sound and notation endpoints preserved. No recognition,
recovery heuristics, SMT, transposition algorithm or layout reconstruction changes
are part of this correction. Repeat browser acceptance: select the existing
source, add the tie, inspect both notes and diagnostics, undo/redo, remove/undo
removal, correct any remaining blocking errors, verify, transpose and export.
Do not insert the already-present note again. The OSMD/source system-layout
limitation documented above still applies.

## Final overfill diagnostic investigation

See [the diagnostic investigation](PHASE4E_DIAGNOSTIC_REVIEW.md) for the evidence
boundary, exact synthetic one-error/seven-warning reproduction, cursor arithmetic,
sequential insertion/backup limits and checkpoint decision. The real session's
event ledger and source barlines still require inspection; no production timing
or validation rule was changed to clear an invalid score.
