# P0.3 — Music semantics and voice mapping audit

Architecture and code audit only. 2026-10-06, America/New_York. No recommendations implemented.

## 1. Executive summary

**Answer: PARTIALLY.** The XML-backed review model has the necessary independent fields for simple hymn scores: part, staff, voice, per-note pitch and exact duration/onset, chord membership, display size, grace/cue semantics, and multiple lyric verses. A second melody can share staff 1 without SATB parts or a second staff. Small display neither requires grace timing nor voice 2. Recognized notes are not reduced to one event per onset.

However, representation capability is stronger than editing and rendering fidelity. Same-onset insertion infers chord membership from compatible overlap; voice/grace edits apply to the whole chord; the manual tie sidecar permits one outgoing relationship per source event; slurs and detailed stems remain XML-only; and OSMD needs a view adapter for ordinary duration-bearing small heads. A newly reproduced chord-duration validation inconsistency can admit XML the importer then flags as structurally erroneous. These warrant narrow corrections, not a model replacement or database redesign.

The conclusions in [the regression RCA](P0_3_SMALL_NOTE_REGRESSION_RCA.md) and [the real benchmark audit](P0_3_REAL_BENCHMARK_EVIDENCE_AUDIT.md) remain unchanged: the missing upper Mừng/Trời notes are already absent in Audiveris; ta/cùng upper heads survive as normal-sized; all 51 exported notes reach recovery, review, and OSMD parsing. Neither the historical regression nor browser engraving was verified. This audit reused those artifacts without changing or regenerating them.

## 2. Terminology: Vietnamese / English / MusicXML

Vietnamese labels below distinguish concepts; they are not automatic classification rules.

| Vietnamese | English | Representation / distinction |
|---|---|---|
| Bè/phần nhạc của một nhạc cụ hoặc giọng hát | Musical part | `<score-part id>` metadata and matching `<part id>`; not necessarily one staff or one voice |
| Khuông nhạc | Staff | `<attributes><staves>` and per-note `<staff>`; several voices can share a staff |
| Bè/dòng giai điệu độc lập | Musical voice | Per-note `<voice>` label within a part; identity is not note size or lyric verse |
| Lời 1, lời 2 / phiên khúc | Lyric verse/stanza | `<lyric number="1">`, `<lyric number="2">` on notes |
| Nhóm nốt đồng thời trong hợp âm | Chord tones | Additional `<note><chord/>…</note>` events; distinct pitches and ties retained |
| Các nốt đồng thời thuộc các bè độc lập | Independent simultaneous notes | Same onset, separate explicit voices, using timed XML streams |
| Nốt cỡ thường / nốt cỡ nhỏ | Normal / small display note | `<type size="normal|cue">`, notehead visual attributes; independent of rhythmic duration |
| Nốt báo / nốt gợi ý không phát âm | Semantic cue note | `<cue/>`; distinguish from a sounding note merely drawn cue-sized |
| Nốt láy / nốt hoa mỹ | Grace note | `<grace/>`; no ordinary `<duration>` |
| Dấu nối trường độ | Tie | `<tie>` for sound and `<notations><tied>` for appearance |
| Dấu luyến | Slur | `<notations><slur>`; not a tie and not a duration merger |
| Thời điểm bắt đầu / trường độ | Onset / duration | Exact rational quarter beats in projection; divisions-based XML timing |

MusicXML defines voice as a time-linear event sequence within a part. The project uses labels, not an assumed SATB numbering scheme. [MusicXML voice reference](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/voice/).

## 3. Current Music Data Model and authority

There are **two Python model families**, with materially different fidelity:

1. **Active preserved-XML review path:** [review/models.py](app/music/review/models.py), [document.py](app/music/review/document.py), [importer.py](app/music/review/importer.py). `Document` owns the XML tree, original bytes, node references, and correction sidecars. `EditableScore` is its UI/diagnostic projection, not an export replacement. This is the model used by the reviews API and verified review transposition.
2. **Older reduced score path:** [models/note.py](app/music/models/note.py), [models/score.py](app/music/models/score.py), [musicxml/parser.py](app/music/musicxml/parser.py), [exporter.py](app/music/musicxml/exporter.py). `Note` has integer duration, staff, chord flag, and optional voice but no lyric, grace, cue, display-size, tie/slur, or original-XML storage. Rebuilding arbitrary source XML through this family would lose notation. Repository call-site search found no application call to these parse/export functions outside their definitions; review transposition uses the preserved-tree transposer. Keep the reduced path out of production fidelity workflows.

Active hierarchy: `EditableScore.parts[] → Part.measures[] → Measure.voices[] → Voice.events[]`. Each `Event` independently stores `pitch`, rational-string `onset`/`duration`, original `duration_units`/`divisions`, `voice`, `staff`, `chord_id`, `chord_member`, `grace`, `cue`, `display_size`, tie-direction summary and `lyric_ids`. Lyrics are separate records with note reference and verse `number`. Staff descriptions, context changes, source pages/systems and layout are projected separately.

Voice labels are measure-local records, not global objects identifying singers. Their meaningful scope is part plus voice label; staff is an independent property. Existing raw voice/staff nodes remain authoritative even when projection defaults missing fields to voice/staff 1. No field says that a small head belongs to another voice.

`Document.parse()` accepts score-partwise only, checks XML/entity/depth/size safety, retains comments and processing instructions, and assigns internal ordinal node IDs. `clone()` preserves references and sidecars for history. `xml()` returns original bytes when unchanged; edited XML is ElementTree serialization. Unsupported nodes/attributes remain in the tree, but edited output is not promised byte-identical: declaration/DTD, prefixes, whitespace and attribute formatting can change. This is preservation of notation content, not a universal lexical round-trip guarantee. Ordinal event IDs remain stable within a review/Undo/Redo, but can rebind on independent reimport after insertion. Do not use them as cross-recognition physical identities.

## 4. Actual voice and lyric rules

### Audiveris interpretation

Inspected upstream Java at the installed engine commit `9e1e55cd2746037d059345881c53e6a6754bffbd`, not only product documentation. `MeasureRhythm` builds time slots, maps new chords against active voice chords, and creates voices for new streams. `Voice` stores chord sequences and slot occupancy. Its constructor derives a voice kind and obtains an unused ID. `Measure.inferVoiceKind()` uses starting staff for ordinary parts and stem direction for merged parts; `generateVoiceId()` allocates from the kind's family offset. These are native interpretations and labels, not proof of singer identity or lyric stanza. [Audiveris MeasureRhythm source](https://raw.githubusercontent.com/Audiveris/audiveris/9e1e55cd2746037d059345881c53e6a6754bffbd/app/src/main/java/org/audiveris/omr/sheet/rhythm/MeasureRhythm.java), [Measure source](https://raw.githubusercontent.com/Audiveris/audiveris/9e1e55cd2746037d059345881c53e6a6754bffbd/app/src/main/java/org/audiveris/omr/sheet/rhythm/Measure.java), [Voice source](https://raw.githubusercontent.com/Audiveris/audiveris/9e1e55cd2746037d059345881c53e6a6754bffbd/app/src/main/java/org/audiveris/omr/sheet/rhythm/Voice.java).

### Project mapping

- `recovery/omr.py::_sheet()` reads native `<voice id>` slot BEGIN entries, associates chord IDs with voice/time-offset, and converts whole-note offsets to quarter beats. A head with ambiguous chord/rhythm correspondence gets unknown voice/onset, not an invented second voice. Size comes from shape/geometry separately.
- `review/importer.py::import_score()` reads `<note><voice>` and groups events under that label. It reads `<lyric number>` separately into lyric records linked to that note. It never uses lyric `number` to choose a voice.
- `review/service.py::lyric_add()` uses `LyricAdd.number`, whose default is "1"; frontend types preserve this separate verse field. `EventInspector` edits voice independently from display size/grace. No inspected project rule converts verse 2 or small size into voice 2.
- One note/voice can own several lyric verse records. Several voices can use staff 1. Neither requires a separate musical part.

Multiple verse numbers on the same melody are standard MusicXML usage. [MusicXML lyrics tutorial](https://www.w3.org/2021/06/musicxml40/tutorial/midi-compatible-part/).

## 5. Normal, small, cue and grace

| Rule | Actual implementation | Classification / limitation |
|---|---|---|
| Size projection | `importer.display_size()` prefers small head/note font hints; then normal type override; otherwise cue element/type size | Project precedence over standard visual/semantic attributes; coarse category, original detail retained in XML |
| Semantic cue | `event.cue = presence of <cue/>` | Standard cue semantics stored separately |
| Grace timing | `event.grace = presence of <grace/>`; ordinary duration absent; cursor does not advance | Standard timing, independent of display size |
| Explicit small edit | `patcher.size_patch()` sets type size=cue plus notehead font-size=small | Standard visual constructs combined by project convention; does not add cue/grace or change duration/voice |
| Explicit cue-sized edit | Same function sets type size=cue, removes small head font hint | A display choice; does not create semantic `<cue/>` |
| Explicit normal edit | Removes size hints, or sets normal type on existing semantic cue | Existing cue silence remains; no automatic sounding conversion |
| Recognized small shape | `recovery.omr._sheet()` maps SMALL shapes; narrow black-head width may yield possibly_small | Audiveris shape plus project geometry heuristic |
| Automatic recovery | `recovery.service` requires corroborated shared chord/stem, pitch/timing and explicit small shape for strong automatic decision | Conservative project policy; geometry alone is advisory |

MusicXML explicitly separates silent `<cue/>` from sounding notes drawn cue-sized with `<type>`. Grace is another timing construct. [MusicXML cue reference](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/cue/).

A small note with duration 1/2 and a normal note with duration 1 can share onset 0, voice 1 and staff 1. The diagnostic probe reproduced this without grace. Choosing voice 2 with normal size produced an independent voice at the same onset. No small=grace or small=voice2 assumption was found in the active backend. `display_size="cue"` does not by itself indicate playback silence; callers must inspect `cue`.

Limits: display-size projection is not a complete model of numeric scaling, large/grace-cue sizes, stem/beam scaling or detailed cue/grace playback parameters; those remain XML-backed. There is no general semantic cue toggle in EventPatch. Imported true cues can be preserved even when not fully editable.

## 6. Chords versus independent voices and timing

`import_score()` walks the actual ordered XML cursor. Ordinary note duration advances it; backup/forward subtract/add exact divisions-based durations; a chord member adopts the preceding event's onset without advancing. Every note is appended as an event, including identical pitches/onsets. Part/staff/voice are not deduplication keys. Chord grouping uses preceding note/voice/grace compatibility and does not require the same staff, allowing cross-staff groups to be preserved. Stem text and beam/slur details are retained in XML rather than used to invent event ownership.

MusicXML permits a chord member shorter than its preceding note, but not longer. Chord is a notational relation, not merely coincidence of onset. [MusicXML chord reference](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/chord/).

| Situation | Current behavior | Assessment |
|---|---|---|
| Explicit chord | Per-note events with shared chord ID, per-note pitch/size/ties and possible shorter duration | Structurally supported |
| Different voices, same staff/onset | Separate events/voice labels, timed backup/forward streams | Structurally supported; not SATB-specific |
| Same-onset anchor insertion | `add_event()` resolves selected onset exactly and preserves requested voice/staff | Supported; no tiny sequential duration |
| Compatible same-voice overlap | `add_at_position()` joins the unique chord when duration ≤ preceding member | Project insertion inference; no explicit “keep independent” switch |
| Longer same-voice overlapping note | Appends isolated backup/note/forward stream, retaining same voice | Exact data retained, but independent line identity remains unresolved; conventional voice linearity and browser behavior need review |
| Overlap across another onset / multiple groups | Rejects ambiguous insertion with explicit-secondary-voice guidance | Bounded editing limitation; existing imported notes not deleted |
| Voice edit on selected chord member | `patch_event()` changes all chord members | Reproduced group scope, not per-note ownership correction |
| Grace edit on chord member | Applies to group; explicit normal conversion requires duration | Intentional bounded group edit; no size-driven conversion |
| Duration edit | Defaults chord scope; supports note scope and optional onset compensation | Requires clear UI scope; distinct durations must not be normalized silently |
| Pitch/size/accidental edit | Selected note only; staff edit also selected note | Independent per-note fields |

Shared stems do not prove independent voices, nor do smaller heads. For source groups with equal rhythm/shared stems, a mixed-size chord is a valid representation without assigning voice 2. For independently advancing melodies, explicit separate voice labels and rhythmic streams are needed. The current model can hold both, but “same onset” currently chooses compatible chord encoding rather than exposing all notational-intent choices.

### Newly confirmed duration safety defect

Diagnostic XML: three voice-1 chord notes at onset 0 with durations 1, 1/2, 1/4 quarter beats. Patch third note to 3/4 with `duration_scope="note"`. `patch_event()` compares 3/4 only against the leader's duration 1 and accepts. `import_score()` compares it against preceding member 1/2 and returns ERROR `chord_duration`. An isolated `ReviewService.event_patch()` also accepts revision 2 with this error in its payload. No event is lost, but the operation admits a structurally inconsistent chord according to the project's own importer and the MusicXML rule above.

Recommendation: validate every affected adjacency, or use a deliberate source-preserving serialization strategy. Reject invalid new XML atomically, without blocking unusual yet structurally valid music. Do not shorten another note or automatically reassign a voice. This reproducer is unrelated to the benchmark's missing raw heads.

## 7. Ties, slurs and preservation

`Event.ties` is a deduplicated list of endpoint directions collected from sound `<tie>` and visual `<tied>`. It is a UI summary, not a full relationship graph. Original endpoint multiplicity, orientation, repeat scope, number, Bézier attributes and slurs remain in `Document`. Standard sound ties and notated curves are distinct constructs. [MusicXML tied reference](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/tied/).

`ties.connect/set_target` authors explicit pairs using sound endpoints and numbered visual endpoints. A manual sidecar links source event to target and records which nodes it owns. Two pairs involving different normal/small source notes remain independent. Pair replay is idempotent; removal targets owned nodes; Undo/Redo snapshots restore XML and sidecars. Pitch/voice/timing unusualness is advisory, whereas missing/self/cross-part endpoints and unsafe ambiguous XML are technical gates.

Limitations: `manual_ties[source_id]` is one outgoing link; the UI `tie_relationship` is singular. Several distinguishable outgoing curves from the same source are preserved but not generally editable. Identical endpoint deduplication occurs only at explicitly edited endpoints. Different formatting/number/repeat signatures cause refusal rather than global removal. `connect()` allocates currently unused numbers 2–16 across the entire part, so sequential unrelated corrections can exhaust 15 numbers even when their spans do not overlap. Standard tied IDs carry paired export identity, but the `review-tie-…` naming/ownership convention is project-specific, not a general MusicXML pairing rule.

Slurs are not promoted into ties by the review importer or tie editor. They are preserved, not exposed as editable canonical relationships. This prevents unsupported slurs from being discarded, but limits source correction capability.

## 8. OSMD rendering boundary

Inspected frontend `scoreRenderer.reviewDocument`, `scoreInteraction.bindScore`, `MusicSheetViewer`, and the installed OSMD reader evidence from the prior audits.

- Actual OSMD 2.1.2 source parsing retains all 51 benchmark notes including two musical voices sharing pickup staff 1. This confirms reader preservation, not a general browser engraving result.
- Previous controlled small-spelled XML yields OSMD `IsCueNote=true` from type size=cue, with unchanged length/onset and `IsGraceNote=false`. Thus OSMD's cue flag conflates a visual cue-size hint with its graphical cue path. It must not become a canonical grace rule.
- Editable Working Score uses a view-only clone to remove the cue-size attribute only for ordinary duration-bearing notes also marked with small notehead font, excluding actual cue/grace. The uploaded/exported bytes stay untouched. `bindScore` then scales uniquely mapped small head SVG around its engraved center by 0.65. This changes visual appearance, not onset or XML. It does not prove full source stem/beam sizing or parallel tie fidelity.
- The mitigation is enabled by `Boolean(onSelect)`, so noneditable viewers can take a different cue-rendering path. This is a confirmed code-path difference, not a reproduced disappearance.
- Visual-to-canonical mapping requires a unique match in part/measure/staff/voice/onset/duration/pitch/grace. Ambiguous shared unison heads are not bound arbitrarily. Approximate numeric frontend matching is a hit-selection aid; backend timing remains rational.
- Parallel semantic pairs are supported in XML. Actual OSMD tie curve spacing, duplicate raw endpoint handling, mixed head sizes, Fit/zoom and source systems remain browser-unverified. OSMD output must never be used to rebuild the authoritative document.

## 9. Benchmark findings and representation capability

Verified benchmark PDF remains at the requested path; its SHA-256 and unchanged native artifacts are documented in the prior evidence audit. No Audiveris rerun/settings changes were needed here.

| Location | Established evidence | Model capability / boundary |
|---|---|---|
| ta, m1 | A4 normal and C5 source-small; exported v1/s1, onset 1/2, duration 1/2 each; upper e-3 normal | Existing distinct chord events can store independent size; no need to change voice or timing |
| cùng, m1 | F4 normal and A4 source-small; exported v1/s1, onset 1, duration 1/2 each; upper e-5 normal | Same; incorrect size originates before review model |
| Mừng, m2→3 | Lower C4 e-10→e-11 survives; both upper G4 heads absent in raw graph; both curves attached to lower pair upstream | Model can hold explicitly corrected upper events and independent ties, but missing event fields must come from trusted source/user choice |
| Trời, m6→7 | Lower C4 e-24→e-25 survives; upper heads absent; doubled lower endpoints already in native export | Same; no automatic second tie or voice from simultaneous appearance |
| Pickup | e-1/v1 and e-6/v2 share C5/onset 0/duration 1/2/staff 1 and a visible head with opposite stems | Multiple voices on one staff represented; do not discard a unison solely by pitch/onset |
| Later sections | Exported v1 melody has lyric numbers 1 and 2; m9 first F4/A4 pair retains two distinct events | Printed verse labels are not demonstrated voice 2; model correctly permits several verses on one voice |

The model can represent the main melody, smaller simultaneous secondary heads, chosen independent voices/rhythms, and independent per-note ties. It cannot infer missing trusted data or guarantee source engraving. No new missing pitch, duration, or numeric voice assignment was applied.

## 10. Source-code and test inventory

All implementation claims above came from inspected code. Classification: S = standard MusicXML semantics; A = Audiveris interpretation; P = project rule/heuristic; O = OSMD behavior.

| Code / function | Rule category and transformation | Existing relevant coverage / loss boundary |
|---|---|---|
| `review/models.py::Event, Voice, LyricAdd`; `frontend/types/review.ts::ScoreEvent` | P projection, independent voice/staff/size/grace/cue/verse fields | `music/test_review_document.py`; projection deliberately incomplete, raw XML retained |
| `review/importer.py::import_score, display_size` | S cursor/chord/lyric semantics; P defaults and size precedence | Exact timeline/mixed-size tests; tie direction summary loses detail only in projection |
| `review/document.py::parse, clone, xml` | P authority, safety, identity and history | Byte-identical untouched roundtrip and clone tests; edited lexical XML not identical |
| `review/structure.py::project_structure, source_layout` | P staff/context/layout projection from S XML/A ordered evidence | Phase4F structure/source engraving tests; geometric layout not voice ownership |
| `recovery/omr.py::_sheet`; `recovery/models.py` | A graph slots/shapes; P extraction/geometry | `test_semantic_recovery.py`; missing graph heads unavailable to extraction |
| `recovery/musicxml.py::correlate`; `recovery/service.py::recover` | P confidence/pitch/rhythm corroboration | Conservative recovery/idempotency tests; no synthetic voice from size |
| `review/patcher.py::size_patch, add_at_position, patch_event, move_event` | S XML edits; P scope, overlap and ownership restrictions | P0.2.2 tests; new three-member guard defect not covered |
| `review/ties.py::connect, set_target, remove_owned, restore_explicit_relationships` | S endpoints; P ownership and singular link | Existing ties/P0.2.1/P0.2.2 scoped removal tests; complex original relations remain XML-only |
| `review/service.py::edit, undo, redo, music_check, transpose` | P atomic snapshots/revisions/read-only Check | Workflow/API and optional Check tests; new structural chord error can be accepted by edit |
| `musicxml/transposer.py::transpose_musicxml_document` | S preserved tree; P pitch spelling/support limits | XML preservation/transposition tests; refuses microtonal/nontraditional unsupported values |
| `scoreRenderer.ts::reviewDocument`; `scoreInteraction.ts::bindScore` | O cue behavior; P view clone/head scaling | Renderer/visual tests use probes/mocks, not browser fidelity acceptance |
| `visualReview.ts::mappedEvent`; `EventInspector.tsx` | P unique graphical matching and explicit separate fields | Visual-review tests; ambiguous head is unbound rather than dropped |
| Legacy `musicxml/parser.py`, `exporter.py`, `models/note.py` | P reduced model/rebuilt XML | Legacy roundtrip tests; insufficient for full fidelity and not active review export |

Verified review transposition invokes `transpose_musicxml_document` on authoritative XML, not the reduced Score exporter. It changes pitches/keys/written accidentals through destination-key spelling while preserving voice, staff, cursor elements, size, grace, chord members, ties, slurs and lyrics. Zero semitones returns original bytes. Microtonal pitches and nontraditional keys are explicitly unsupported rather than normalized. Harmony symbols and other pitch-bearing unsupported notations are not generally transposed by this walker; preservation is not proof that every such marking remains musically correct after a nonzero transposition. Keep this support boundary explicit.

## 11. Confirmed defects versus hypotheses

Confirmed defect: the three-member chord edit described above passes a leader-only guard, then produces `chord_duration` ERROR and is stored by the isolated service. Fix technical XML consistency without making music-theory warnings correction gates.

Confirmed bounded capabilities, not benchmark-loss diagnoses: group-scoped voice/grace edits; inferred chord insertion; same-voice overlapping independent stream; singular outgoing manual ties; part-wide number exhaustion; XML-only slurs/stems; noneditable cue-rendering path difference; reduced legacy model limitations. No generic onset deduplication or verse/voice conflation was found. Small display and grace are independent in canonical data.

Confirmed upstream benchmark failures remain missing HeadInter objects and normal classification of surviving source-small heads. OSMD disappearing SVG, historical recognition regression, and incorrect independent-line voice assignment are unresolved hypotheses, not established by this model audit.

## 12. Minimal recommendations and prioritized plan

1. **P0 — consistent structural edits:** correct affected chord duration checks and add a narrow mutation postcondition for newly introduced structural XML errors. Preserve already imported unsupported/erroneous material without blanket rejection; do not gate valid unusual music on optional Check. Require atomic rollback for the reproduced failure.
2. **P0 — explicit edit intent:** keep existing fields and XML authority. Expose clear per-note versus chord scope. Use existing move/ownership machinery for separating one member; add a small explicit insertion choice for chord versus independent voice when source/user evidence warrants it. Do not derive voice from size/stanza or auto-revoice same-onset data.
3. **P1 — renderer boundary:** apply the duration-bearing small-note adaptation consistently to relevant viewing modes; retain true cue/grace and source bytes. Add real SVG verification for normal/small same-onset heads and independent curves before claiming acceptance.
4. **P1 — complex relationship limits:** retain singular manual ties for the supported MVP case of one outgoing tie per note. Only extend to a per-source relationship collection if an actual correction requires multiple distinct relationships from one source; reuse standard tied numbers/IDs and scoped ownership. Allocate numbers by safe overlapping span when necessary rather than exhausting them across unrelated spans. Keep unsupported slurs preserved.
5. **P1 — recognition recall evidence:** maintain labelled source-note correspondences and run a representative set with locked input/settings. Separate native missed heads, size/pitch/timing errors, downstream loss and browser fidelity. Preserve upstream omission findings while investigating historical artifacts when available.

No new abstraction, schema/database migration, global Audiveris switch change or broad refactor is recommended. Keep display size, cue semantics, grace status, voice and verse as separate existing values; make their labels/contract explicit rather than duplicating data. Keep lossless XML mutation/transposition path and user corrections authoritative.

## 13. Regression tests and acceptance criteria

Existing tests cover exact anchored size/duration insertion, independent pairs, scoped removal, idempotency, Undo/Redo, lyrics, untouched XML, multivoice timing, and preserved-tree transposition. Extend them with independent oracles:

- Three-member decreasing-duration chord: disallowed increase beyond preceding member fails atomically; a valid increase retains other members and timing. Test serialized XML against the relevant standard rule, not only canonical output.
- Staff 1 voice 1 and 2, including unison heads, multiple verses on one note, cross-staff chord preservation, missing voice defaults, and ambiguous ownership. No verse/size-driven revoice.
- Ordinary normal/small/cue-sized notes and true cue/grace: independent duration/onset/silence fields, small open heads, no implicit grace conversion. Explicit chord versus independent-stream intent retains all distinct identities.
- Parallel normal/small ties, continuations, complex numbers/formatting and slurs: selected removal only, no global endpoint normalization; export/reimport and history preserve relationships.
- Nonzero transposition structural comparison that masks only intended pitch/key/accidental changes and checks all events, lyrics, timing, size, stems and unsupported nodes. State unsupported pitch-bearing notation limits.
- Actual browser SVG across editable/readonly modes: two correctly mapped noteheads at the same rhythmic position, optical collision displacement allowed, independent curves, source grouping 5/5/7, Fit/zoom, drag and corrections preserved. Compare authoritative XML before/after view-only operations.
- Read-only optional Check must leave XML, revision, history, pitches/durations/voices and user corrections unchanged.

Recognition target: **at least 90% note recall on a representative, source-labelled benchmark set**. Define source semantic-note instances (including separate voices sharing a head) and match within part/staff/measure/pitch/onset; report physical-head recall separately where useful. Do not use 51 surviving exports as the source denominator or claim recall from XML roundtrip counts. This audit does not establish the 90% target. Independently require 100% preservation of recognized and user-corrected supported event/notation data through review, history, export and transposition, except the explicitly requested pitch transformation.

## 14. Validation and safety

Read both prerequisite reports, current backend/frontend source, retained benchmark traces, MusicXML primary references, and version-pinned Audiveris source. Diagnostic probes and isolated service sessions were created only in `/tmp/p03-music-semantics-czyjq2ld/`; no live user session was changed and no benchmark artifact was edited.

Focused existing backend tests: **83 passed** (60 document/preservation/transposition; 23 simultaneous/lyrics workflow). Focused frontend tests: **3 test files passed** (renderer, visual review, ties). Initial test collection encountered an unrelated globally loaded ROS plugin and then missing Python path; the successful invocation used `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=.`. Sandbox TestClient execution stalled and was interrupted; the same workflow tests passed outside the sandbox. No test or production source was changed. This is not full-suite or browser acceptance.

Working-tree file hashes were captured before documentation and compared after it. All pre-existing tracked/nonignored files remain unchanged; only this new report was added by this task. Report whitespace and `git diff --check` passed. Audiveris configuration and all prior uncommitted work were preserved. No reset, restore, clean, stash, stage, commit or push was performed.
