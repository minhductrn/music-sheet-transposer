# Phase 4D: Recognition review and correction

PDF/image → Audiveris → **draft** MusicXML → source comparison and corrections →
structural validation → explicit human verification → corrected MusicXML →
the existing preservation transposer.

The recognition provider, compressed-MXL boundary, preservation transposer, old
internal models/parser/exporter and both transposition endpoints remain unchanged.
No recognition pass runs when an event or text object is corrected.

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
| POST | `/{id}/undo` / `/{id}/redo` | Restore bounded correction snapshots |
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

New recognition reviews start **DRAFT**. Corrections or first validation move them
to **REVIEW_REQUIRED**. Only an explicit verify request with
`{"confirmed_source_comparison": true}` moves a score to **VERIFIED**.

- **ERROR**: invalid pitch/octave, missing event representation/duration/divisions,
  invalid staff/voice, broken chords, negative timing, invalid required meter fields
  or an empty score. Verification is blocked until corrected.
- **WARNING**: measure duration mismatch, suspicious empty measures and timing that
  needs manual review (e.g. differing staff meters). Warnings remain visible and
  may be accepted only after source comparison.
- **INFO**: reminder that these checks cannot establish recognition accuracy.

Every correction and undo/redo invalidates verification. A structurally clean score
stays a draft until the user confirms comparison. Up to 500 diagnostics are returned;
all errors, including omitted diagnostics, still block verification. Duration
mismatch is a warning because pickups, unmeasured notation and export conventions
need musical judgment. Explicit `implicit="yes"` pickup measures may be shorter.

The frontend disables recognized-score transposition until VERIFIED, then retrieves
the server's verified corrected bytes immediately before calling the existing
MusicXML transposition API. Direct MusicXML upload retains its previous workflow.
The stable transposition API remains unaware of review sessions and models; review
gating is a product workflow, not an access-control change to that existing API.

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
backup/forward amounts, tuplet ratios, beams, ties/slurs or full harmony degrees.
It preserves them and reports relevant structural errors; complex rhythmic repairs
can require an external notation editor. It does not reconcile ties after a pitch
edit or infer new beam groupings. Small/cue rendering and native PDF controls need
real-browser validation. The existing transposer's limitations still apply:
nonzero microtonal/nontraditional-key transposition is unsupported, and harmony
symbols are retained rather than transposed. Verification does not add transposer
capabilities or promise faithful engraving.

## Exact real-world validation: Cùng Đem Tin Mừng

1. Start the existing Audiveris-configured backend with one worker and the frontend:
   `env -u PYTHONPATH .venv/bin/python -m uvicorn app.main:app --reload` from `backend`,
   and `npm run dev` from `frontend`. Keep the working OCR environment from OMR.md.
2. Import the PDF, choose Vocal song / clean digital score, and Recognize Sheet
   Music. Confirm the automatic review opens as DRAFT with the original source.
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
9. After resolving errors and reviewing warnings, check the source-comparison
   confirmation and Mark VERIFIED. Confirm transposition enables. Make one edit
   and ensure verification/transposition are invalidated; undo, review and verify
   again. Download verified.musicxml before closing/restarting.
10. Transpose 0, +2 and -2 separately. Download each XML. At 0 confirm the corrected
    bytes are unchanged; at ±2 confirm expected pitch changes and unchanged chord
    markers, duration/onset relationships, voices/staves, sizes and non-grace
    timing. Compare layout/ties/lyrics with the corrected document. Record the
    OSMD mixed-size limitation separately from XML correctness.

Automated checks: run the complete backend suite with its `.venv`, then frontend
`npm run lint`, `npm run build`, and `git diff --check`. There is no established
frontend test framework; this milestone adds no separate browser-test stack.
