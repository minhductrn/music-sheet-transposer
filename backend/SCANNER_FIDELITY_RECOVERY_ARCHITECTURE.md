# Scanner Fidelity Recovery architecture and audit

Status: **architecture proposal only; no production change**. Decision: **GO for
an evidence-only candidate milestone; NO-GO for generalized automatic recovery
or full scanner-fidelity acceptance today**. No A4-specific patch is implemented.
The accepted Phase 4F.1 renderer fix remains unchanged; the user reports real
source-system browser acceptance passed at **1–5 / 6–10 / 11–17**.
Phase 4F.2 is not started.

This contract governs a future scanner-fidelity extension. It proposes a scoped
change to the earlier architecture document's unconditional overfill/Verify
policy; it does not claim that change exists now. Recognition-loss diagnosis is
separate from musical validity and from engraving acceptance.

## 1. Product and source-fidelity contract

The product is **source image/PDF → scanner/OMR → faithful MusicXML reconstruction
→ visual correction → user verification → transposition → export**. The source
is authoritative. Music theory may describe discrepancies; it cannot establish
that source notation is absent or authorize changing it.

For every source-supported event or mark preserve its identity/count, pitch,
onset/relative placement, duration, written accidental, display size,
simultaneous/chord relationship, supported voice/part/staff assignment, ties,
slurs, rests, barlines, clef, key, meter, Unicode lyrics, harmony symbols and
source-system ownership in review. Unsupported source notation remains visible
as unresolved evidence, not silently omitted from a fidelity claim. Every
accepted reconstruction must have source evidence or an explicit human decision.

Pitch, duration, onset, voice/part relationship, display size and grace semantics
are independent. **Small does not mean grace.** A visually small secondary vocal
note may be a full duration-bearing event. Never create `<grace>` or `<cue>`
merely because the head is small. Nor does a shared staff prove a single voice,
or matching pitch prove a tie.

Prohibited evidence and actions: meter completion, harmonic/melodic plausibility,
rest padding, duration normalization, overflow redistribution, guessed barlines,
merging tied events, deleting unusual notes, or converting size to timing. No
confidence score may contain “fills the measure”, “fits the chord” or “sounds
likely”. A capacity mismatch can prioritize source comparison, never supply a
candidate's pitch, existence or duration.

Preserved MusicXML remains the only mutable score authority. Source observations
are immutable provenance; proposed interpretations and user decisions are
separate, revision-bound records. OSMD is a derived view. Recovery uses local,
atomic preservation patches, never wholesale regeneration of unrelated XML.

## 2. Audit evidence and scope

Read alongside [the exact half-note trace](PHASE4F1_SOURCE_FIDELITY_HALF_NOTE_DIAGNOSTIC.md)
and [the notation-editor architecture](PHASE4F_NOTATION_EDITOR_ARCHITECTURE.md).
The latter contains historical assessments; current code and its Phase 4F.1
addendum take precedence for descriptions of implemented behavior.

Real artifacts reside at `/tmp/music-sheet-transposer-phase4f1-cungdemtinmung/`:
source.pdf, recognized.omr, source-audiveris-gray.png, export-copy/recognized/review
MusicXML, source-evidence.json, review-response.json, structural-score.json and
captured rendering-clone.musicxml. Review ID is
`-Z7DrCMLUEL4Y6YgbpMvZV3wJ9LsTEhi`, revision 1. The export-copy is the labeled
recognized baseline, not an independent Audiveris export request. Captured clone
records predate the accepted renderer fix. No fresh recognition or browser run
occurs in this audit; `/tmp` artifacts require durable fixture packaging later.

The trace establishes source A4 half (2 quarter units), smaller adjacent C5 half,
and visible arcs to following A4/C5 eighth heads. Source measure 4, system 1,
staff 1 occupies x=1692–1863. The persisted recognized measure has no heads,
chords, voice or slots; stack duration is 0. The following A4 survives as head
590/chord 2057 and XML/review e-16, duration 1/2 in measure 5. Raw glyph fragments
survive, but no recognized missing-note or tie object does. Classification is
**A, recognition loss**, not an evidenced exporter/recovery deletion.

Inspected current implementation: `recovery/{omr,models,musicxml,service}.py`,
`review/{document,importer,patcher,ties,service,storage,structure}.py`, API Verify
contract, frontend review confirmation and accepted renderer/selection utilities.
OSMD audit uses installed **2.1.2** declarations and bundled implementation,
including `getCueNoteAndNoteTypeXml`, `VoiceGenerator.addNoteInfo` and
`VexFlowConverter.StaveNote`. No renderer migration is proposed.

## 3. Evidence available below recognized notation

| Layer | Usable evidence | What it does not prove |
| --- | --- | --- |
| Original PDF/image | Original visual notation, crop for human comparison | Reliable event IDs, voices or exact timing by itself |
| OMR GRAY/BINARY raster | Registered sheet pixels; gray preserves faint/open contours; binary aids segmentation | That binarization retained all ink or that a black component is a note |
| Glyph index run tables | Pixel runs, dimensions, left/top coordinates, glyph IDs and unclassified/composite fragments | Classification, duration, onset or musical ownership |
| Free-glyph references | System association for some fragments | Semantic validity or a unique note per glyph |
| Staff polylines/interline | Local line positions, scale and staff association | Clef/key correctness or PDF crop/rotation registration |
| Stacks/barline observations | Candidate measure bounds and physical ordering | That every recognized barline is correct |
| Recognized inters/relations | Clef/key context, heads, stems, beams, slur curves, containment, endpoint links where retained | Source truth without corroboration; graph can omit or misbind objects |
| Slots/voice entries | Exact reported time offsets and chord membership for assigned recognized chords | Timing for an unassigned fragment; expected stack duration is not missing-note evidence |

In the real omitted-note region, unclassified glyphs include 2246
`[1757,636,18,97]`, 2248 `[1772,657,15,19]`, composite 2383
`[1757,636,30,97]`, and arc-region glyphs 2100 `[1790,659,130,28]`,
2107 `[1775,605,161,31]`. None has a recognized inter interpretation there.
Overlapping composites and fragments are alternate pixel groupings, not separate
notes. They must be deduplicated by provenance and pixel coverage before counting
heads. The raw raster is the fallback when fragments are incomplete.

Current `parse_omr` retains recognized head candidates and generic structural
inters/relations, staff lines and stack slots. It does **not** project the glyph
index run tables or source raster bytes into recovery candidates. Generic inter
retention therefore cannot expose a fragment that never became an inter.

A bounded raw-evidence extractor is feasible: reuse ZIP/XML validation, read only
registered image regions and selected run tables, and preserve orientation/runs
without musical labels. It requires limits on decoded image dimensions, total
pixels, run counts, allocation, region count and candidate count in addition to
existing archive/XML limits. Validate run totals and coordinate extents before
decoding. Do not extract arbitrary paths or leak book source paths. Preserve
original pixels; staff removal/denoising must be a versioned analysis view so a
hollow head or arc is never permanently erased from the evidence.

## 4. Independent evidence requirements for omitted notes

“Deterministic” below means reproducible from validated observations and stated
context. It is not a claim that arbitrary image recognition is error-free.

| Property | Required positive evidence | Deterministic result / review boundary |
| --- | --- | --- |
| Existence/count | Visible head contour/fill, source crop, segmentation separating heads from text/staff/arc; unique pixel support | Recognized shape within a calibrated supported class; otherwise a region candidate, not a new event |
| Center/geometry | Registered pixel mask/contour, local staff geometry and uncertainty bounds | Mask bounds/centroid once segmentation is fixed; composite glyph bbox alone is not a head center |
| Pitch | Local line/space position, reliable clef sign/line/octave, ledger lines and applicable octave markings | Diatonic pitch from known context; ambiguous staff/clef requires confirmation |
| Accidental | Visible attached accidental or known source key and same-measure accidental scope | Written sign and effective alteration separately; unsupported scope stays unknown, never choose by harmony |
| Display size | Head dimensions normalized to local interline and comparable same-shape heads; image quality/shape compensation | Normal/small observation plus optional ratio; distorted/merged/faint head requires confirmation |
| Stem | Continuous or corroborated pixel connection and head attachment; crossings resolved | Supported shared/individual stem relation; nearby vertical ink alone is insufficient |
| Beam/flag | Connected beam/flag pixels and count with attachment/disambiguation | Supported count/relationship; staff line or slur must not substitute for a beam |
| Duration | Head class + stem presence + beam/flag count + dots and explicit tuplet context | Standard written value and rational duration if every required mark is known; no beam detection is not proof of no beam |
| Relative placement | Source x ordering, stem/head displacement and measure bounds | Ordered/simultaneous hints; engraved x spacing is not proportional time |
| Exact onset | Trusted slot association, confirmed onset of a shared rhythmic anchor, or complete source-supported sequence with known voice and preceding durations | Exact rational only when independently determined; no interpolation against meter capacity |
| Simultaneity/chord | Shared stem or explicit synchronized voice evidence, compatible durations and supported engraving convention | Same-voice chord only when supported; aligned x alone cannot distinguish voices |
| Voice/part/staff | Source staff membership plus established part context; voice stems/continuity, explicit labels or human assignment | Staff often resolvable; voice IDs/secondary-part meaning can remain unknown despite clear pitch/duration |
| Measure ownership | Source barline/stack correspondence and geometry, checked for conflicting boundaries | Unique registered region may bind; no moving overflow to a neighboring measure |
| Grace/cue semantics | Explicit source convention confirmed by context/human, corroborated notation marks | Visual smallness alone never supplies either semantic property |

For the real pair, the image supports open heads with a shared downward stem and
A4/C5 staff positions. It supports written half-note durations, not an automatic
voice/onset assignment from empty-measure capacity. The following recognized
heads supply potential endpoint identities. A source reviewer can confirm a
same-voice chord representation or secondary voice assignment; detection must
not encode a separate part solely from the small upper head.

## 5. Proposed evidence and candidate boundary

Add an observation path beside the existing recognized-head path:

```text
registered source raster / raw glyph runs / recognized graph
  → bounded immutable region and shape observations
  → proposed notes and arcs with per-property evidence and unknowns
  → unique correspondence to existing XML or proposed local insertion
  → source review / future calibrated automatic decision
  → preservation transaction → reproject → report fidelity + validity separately
  → final user verification → existing transposer/export
```

Proposed observation records need artifact/member/raster hashes, sheet/page/staff
IDs, coordinate space, raw glyph IDs, pixel support, analysis version and method,
registration uncertainty, shape alternatives and positive/negative observations.
A proposed event needs existence identity, independently evidenced pitch,
written/sounding duration, size, grace/cue semantics, placement/order, ownership,
voice/part/chord proposal and references for each fact. Unknowns are nullable,
not filled with a meter-derived default. A proposed arc has its own geometry,
kind alternatives and endpoint candidates. XML event IDs are correspondence
results, not glyph IDs. User acceptance/rejection is separate from detector grade.

Reuse candidate correlation for already recognized heads; introduce an explicit
raw-observation type instead of constructing a fake `CandidateNoteEvidence`
with fabricated chord/stem/slot IDs. Candidate detection must search more than
empty/underfilled measures: a missing note may be masked by another voice or by
another recognition error. Meter discrepancies are not candidate-generating facts.

A source-supported insertion may increase measure extent. Existing “actual
extent unchanged” gating is appropriate to the current simultaneous-note
operation, **not** a universal scanner-fidelity invariant. Future insertion
invariants are: unrelated events unchanged, supported ownership and timing
preserved, all changes accounted for by source evidence, structural XML
representable, diagnostics retained. A local patch planner must explicitly handle
supported backup/forward/voice sequencing. Refuse unsupported plans atomically;
retain the candidate for review rather than delete its source observation.

## 6. Confidence model and automatic boundary

Use per-property evidence states: **OBSERVED**, **DERIVED_FROM_SUPPORTED_CONTEXT**,
**USER_CONFIRMED**, **AMBIGUOUS**, **UNKNOWN**, **CONTRADICTED**. Store derivation
inputs and uncertainty; do not average a certain pitch and unknown duration into
one “high” note score. `EXACT` correlation means identity agreement, not certainty
that the source was recognized correctly. Audiveris grade .8 is not a calibrated
probability for raw-fragment reconstruction.

| Outcome | Requirements | Behavior |
| --- | --- | --- |
| Future automatic reconstruction | Calibrated detector for a supported class; source pixels confirm existence; all required event fields resolved; unique ownership/correspondence; no duplicate pixel/event claim; validated patch plan; no contradictory evidence | Atomic evidence-linked patch, audit ledger, reversible history, still an unverified recognition draft |
| Review-required candidate | Positive source-region evidence, but any required semantic field, identity, endpoint or representation is ambiguous; or detector lacks calibration | Show source crop and alternatives/unknowns; user supplies or confirms fields before a patch |
| Insufficient evidence | No reliable head/arc support, wrong registration, truncated/incomplete image, conflict with text/staff ink, or unsupported source format | Retain region/reason and allow source inspection; create no semantic event or tie |

At this checkpoint **raw-glyph recovery is review-only**. Automatic mutation is
NO-GO until varied held-out source fixtures establish precision, coverage and
calibration and preservation tests cover supported plans. Multiple fragments
from one image are not independent recognizer votes. Human confirmation resolves
an ambiguity through provenance, not by retroactively changing detector confidence.

Auto note recovery and auto arc recovery are separate gates. A fully resolved
note may be proposed while its tie remains unresolved; do not invent endpoints
to complete the candidate. Overall fidelity cannot pass while required source
marks remain unhandled. No rejected/unresolved region disappears from metrics.

## 7. Tie and slur recovery

Raw arcs can survive as pixels, fragments and unclassified curve-sized glyphs;
recognized `slur` inters may additionally retain Bezier geometry, `tie=true` and
slur-head relations. The real A/C arcs survive only below recognized inters.
Our parser cannot acquire safe endpoint relationships simply by naming glyph
2100 a tie.

A supported arc detector needs continuous/fragment-connected curvature evidence,
local thickness and orientation, separation from beams/staff/text/lyric extenders,
registered endpoint geometry, and robust handling of overlapping upper/lower arcs.
Endpoint resolution must enumerate nearby **individual heads**, including small
heads and proposed missing heads, then reject non-unique assignments. Across
systems/pages require continuation evidence and source-system identity; do not
join arc ends merely because pitches recur. Distances use local source units and
uncertainty, never browser pixels.

Tie versus slur classification needs source notation/context or human confirmation.
Same pitch is a compatibility check, not positive evidence of a tie; equal-pitch
slurs are possible. Different pitches must not be “corrected” to make a tie.
Unsupported apparent ties remain faithfully recorded visual observations pending
an explicit semantic decision rather than being converted to a slur automatically.

Proposed semantic edges retain kind, endpoint event IDs, source geometry/provenance,
number/continuations and visual attributes. Keep sound and visual tie bindings
separate: a ordinary duration-bearing tie uses `<tie type="start|stop">` for
sound and `<notations><tied type="start|stop">` for notation. Slurs use numbered
`<notations><slur type="start|stop|continue" number="…">` without sound ties.
Preserve existing numbering, placement/orientation, line types, Bezier fields and
unsupported extensions. Source pixel coordinates require a validated conversion
before use as MusicXML tenths; preserve endpoint fidelity even if curve spacing
is re-engraved. [MusicXML tie](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/tie/),
[tied](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/tied/),
and [slur](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/slur/)
define these distinct representations.

Verification compares source arc count/type/endpoints against semantic edges,
XML start/stop/continue bindings and actual OSMD graphical endpoints. Test each
head of a chord, cross-measure/system arcs, overlapping/nested slurs, same-pitch
slurs, duplicate bindings and continuation cases. A SVG curve alone cannot prove
correct sound-tie serialization; XML alone cannot prove the visible endpoint.
Never merge the two tied duration-bearing note events into one longer note.

## 8. Display-size fidelity and MusicXML representation

Retain source head mask and locally normalized size observation; semantic state
stores `display_size` independently of pitch, onset, duration, chord/voice and
`grace`. Preserve a measured ratio as evidence when available; normal/small
categories do not promise pixel-identical engraving. An explicit `<cue>` semantic
flag also needs a separate field in a future richer projection: current
`display_size='cue'` conflates explicit cue markup and type-size shorthand.

For an ordinary, small duration-bearing chord member, use an ordinary `<note>`
with `<duration>`, `<type size="cue">` as **visual size**, optional notehead font
size and an evidence-supported chord/voice assignment. Do not introduce `<cue>`
or `<grace>`. With effective divisions=2, this illustrative secondary C5 half
chord member has two quarter units; it is an encoding example, not a real patch:

```xml
<note>
  <chord/>
  <pitch><step>C</step><octave>5</octave></pitch>
  <duration>4</duration>
  <voice>1</voice>
  <type size="cue">half</type>
  <stem>down</stem>
  <notehead font-size="small">normal</notehead>
  <staff>1</staff>
</note>
```

The preceding normal half-note leader has the same duration and voice, with
`<type>half</type>` or `size="full"`. Use `<chord>` only with supported same-voice
simultaneity. A genuinely separate voice/part requires ordinary duration-bearing
notes in that voice/part and correctly planned backup/forward timing, not a fake
same-voice chord. Written type/dots/time-modification and exact sounding duration
must survive independently. Existing explicit cue/grace semantics remain opaque
or explicitly represented until a user-supported semantic edit is requested.

MusicXML defines `type@size` as a visual distinction and allows `notehead@font-size`;
ordinary notes have duration, while grace notes do not. Explicit cue notes have
different semantics and do not support sound `<tie>` in the note content model.
This is an additional reason not to use `<cue>` for a tied secondary vocal note.
[Type size](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/type/),
[notehead attributes](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/notehead/),
and [note content](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/note/)
support this representation.

Current `size_patch` already writes `type size="cue"` plus
`notehead font-size="small"` for display_size small, without adding cue/grace
semantics. The importer recognizes small notehead markup before cue-size type.
Preservation retains these attributes through XML transactions. Future fixtures
must validate representation, reimport, correction/undo/redo and transposition;
never infer grace from the renderer's internal class name.

Additional audit finding, not fixed here: the existing normal-display branch
for an explicit `<cue>` emits `type size="normal"`; the specification's ordinary
symbol-size value is **full**. Schema-valid normalization in that narrow branch
needs a separately scoped fix/test while preserving explicit cue semantics.
The small-duration-bearing example above does not use that branch.

## 9. OSMD rendering feasibility

Installed OSMD 2.1.2 `getCueNoteAndNoteTypeXml` sets `IsCueNote` for either an
explicit `<cue>` or `type@size="cue"`. Its source note separately retains length
and `IsGraceNote`. VexFlow conversion chooses cue/GraceNote glyph construction
from **the first source note of a graphical voice entry**, using
`notes[0].sourceNote.IsCueNote`. Thus whole cue-sized entries have a rendering
path, but mixed normal/small heads sharing an entry are not faithfully handled
by this code path. A normal leader can leave the smaller secondary head normal;
a small leader can scale the whole entry. Notehead parsing examined here handles
shape/fill; it does not provide an evidenced per-head font-size scaling path.

**Feasible in MusicXML/semantic state; not currently proven faithfully rendered
for mixed-size chords.** Do not reorder chord members to manipulate the first
note or split them into invented voices to induce glyph scaling. CSS scaling the
entire score affects both heads and cannot restore their relative size.

Keep OSMD and the accepted system-width/Fit adapter. A future isolated renderer
capability fixture should compare separate small entries and mixed-size chords,
hollow/filled heads, both stem directions, beams, ties, click/keyboard selection
and Fit/zoom. If it confirms the limitation, assess a supported per-head hook or
a narrowly maintained view-only VexFlow/OSMD adapter change; no supported solution
has been established in this audit. A post-render head-only transform is not
accepted without stem/beam/tie attachment and hit-target checks. Renderer limits
must be visible as fidelity limits; valid XML does not establish visual acceptance.
A migration is NO-GO without that focused experiment.

## 10. Validator and Verify policy proposal

Current `rhythm` marks measure overfill ERROR and voice underfill WARNING.
`ReviewService._projection` adds overfill to all imported reviews;
`validation.can_verify` requires zero ERRORs and zero unresolved recovery issues.
`verify` rejects any ERROR. The source-comparison checkbox and recovery issue
`ACCEPTED` handling do not waive rhythmic validator errors. Underfill warnings
can already coexist with Verify after comparison, but there is no per-conflict
source-matching confirmation record.

A second meter assumption exists in `ties.check_link`: across a measure boundary
it requires source end to equal **expected meter duration** and target onset=0.
`connect` for tied insertion also checks affected rhythm; tie-only editing skips
that rhythm check but still uses the expected-duration adjacency condition.
This can reject a visibly supported cross-barline tie in unusual source notation.
A future source-confirmed edge path must use actual supported event order/voice
boundary and explicit source endpoint evidence, not meter completion or a global
maximum extent from another voice. Preserve the existing conservative command
as a supported normal case until an alternative plan is tested.

Proposed separation:

| Diagnostic class | Verification treatment |
| --- | --- |
| Technical/representation failure: malformed XML, invalid/missing required event fields, negative/unknown timing needed for export, dangling IDs, unsupported patch plan | Still blocking; a source-comparison assertion cannot make an unusable serialization trustworthy |
| Source fidelity unresolved: missing/ambiguous source event, size or arc; conflicting ownership/endpoint evidence | Requires correction or an explicit source decision resolving the actual discrepancy; blanket acceptance cannot certify an absent source note |
| Representable theory discrepancy: measure underfill/overfill relative to printed meter | Visible diagnostic; may be confirmed as source-matching without changing XML, after scoped source comparison |
| Potential encoding conflict such as same-voice overlap | Classify first; wrong voice/chord encoding remains unresolved, genuine supported source structure may need a representable explicit plan; no blanket rhythm waiver |

Add an explicit **“This unusual notation matches the source”** disposition for
eligible diagnostics. It stores diagnostic code, affected event/measure/context
fingerprint, score revision/XML hash, source artifact/page/region references,
comparison note, confirmer identity if available and decision timestamp. Keep
the original actual/expected values and diagnostic; separate severity from
`blocks_verify` and acceptance disposition. No `implicit=yes`, duration, rest,
voice, meter or barline patch accompanies the confirmation.

Backend computes eligibility and effective blockers over the **full** diagnostic
set, including diagnostics omitted by the UI limit. Eligibility must be narrow,
not an arbitrary “ignore error” endpoint. Effective source decisions participate
in revision checks, Undo/Redo and bounded session storage. A relevant change
invalidates the decision by fingerprint; all corrections invalidate VERIFIED.
Undo may restore a decision whose exact source/document dependencies are restored,
but must never automatically restore VERIFIED. Require fresh final comparison
for the current revision. Expiry loses session decisions today; any future durable
review export needs to package provenance/confirmations separately from score XML.

VERIFIED means **human-confirmed source fidelity for supported/representable
notation**, not “the source obeys music theory”. Transposition must consume the
exact verified corrected XML and preserve unusual timing, size, ties/slurs and
notation; test this before allowing confirmed overfilled sources through that
workflow. Unknown capacity alone is not a license to guess timing. This proposal
supersedes only the theory-as-unconditional-blocker rule when implemented; all
current protections remain unchanged in this task.

## 11. Reusable implementation versus extensions

| Component | Reuse | Required extension / boundary |
| --- | --- | --- |
| `recovery/omr.py`, recognition archive readers | Bounded ZIP/XML parsing, source identity, graph/staff/stack extraction and registration checks | Raw runs/raster regions, decode budgets, observation schema; no glyph→note shortcut |
| `recovery/models.py` | Immutable evidence/provenance and correspondence concepts | Per-property evidence/unknowns, pixel identity, proposed missing notes/arcs, distinct cue semantics |
| `recovery/musicxml.py` | Exact fractions, XML context, recognized-head correlation, rhythm reports | Supported source context/accidental resolution, unique raw-to-XML correspondence, theory-independent confidence |
| `recovery/service.py` | Separate decisions, cloned proposals, bounded patches, duplicate prevention, baseline conflict reporting | Operation-specific invariants; sequential note and arc proposals; calibrated raw detector; unchanged extent is not a universal gate |
| `review/document.py`, patcher/importer | Preserved tree/opaque XML, references, local edits, size independence, reproject after mutation | Explicit supported onset/voice plans, source-backed candidates, independent semantic fields and schema checks |
| `review/ties.py` | Atomic sound/visual endpoint edits, ambiguity rejection and cleanup | Source-confirmed unusual-boundary path; numbered slur model/patches; preserve unsupported arcs rather than recast them |
| `review/service.py`, storage/history/API | Revisions, Undo/Redo, issue decisions, verification invalidation, verified-byte routing | Scoped source-match theory decisions, blocker categories, dependency fingerprints, metadata memory accounting |
| Existing lyrics/harmony handling | Unicode/verse/segment edits and preservation of unknown XML | Source OCR/attachment evidence and fidelity metrics; no automatic language-based text invention |
| Accepted renderer and `scoreInteraction.ts` | Verified system grouping, presentation-only zoom, semantic SVG-head identity | Focused mixed-size/arc capability fixture; no changes to the accepted layout fix |

The proposed extension grows the existing XML-backed editor, not a second mutable
score or a song-specific recovery branch. Preservation-only slurs and unsupported
context remain valid opaque input; automatic editing needs explicit supported
contracts. Pixel detectors and confidence calibration are new capabilities,
not supplied by `correlate` or OSMD's graphical geometry.

## 12. Scanner-fidelity metrics

Build a source-annotated ledger before scoring reconstruction. Each head/rest/arc/
text/context mark has source region, identity, supported facts and unresolved
facts. Count heads as note events, including small heads and separate tied notes;
never count overlapping glyph fragments as notes. Annotators record uncertainty
and disagreements. Do not manufacture a full reference ledger from this local
trace or treat the recognized 51-note total as the correct source note count.

Report missing, extra, correct, wrong and unresolved counts with per-property
coverage. Precision = supported correctly reconstructed objects / reconstructed
objects; recall = source-supported correctly reconstructed objects / annotated
source objects. A coincidentally equal total note count is insufficient. Unknown
facts cannot count as correct or disappear from the denominator without reporting
an explicit unavailable-reference category.

| Metric | Required measurement |
| --- | --- |
| Note-count fidelity | One-to-one source head↔semantic note mapping; omissions, extras and duplicates separately; small/tied events included |
| Pitch fidelity | Exact written step/octave/alteration plus accidental display and supported context scope |
| Duration fidelity | Exact rational duration and written type/dots/tuplet spelling; grace independently scored |
| Placement/relationships | Source order, exact onset where annotated, simultaneous/chord identity, supported voice/staff/part and measure ownership |
| Small-note fidelity | Normal/small class and optional normalized ratio in evidence, semantic state, XML and actual rendered heads; no small→grace/cue conversion |
| Tie fidelity | Exact source/target event pairs, count and sound/visual XML agreement; separate visible attachment check |
| Slur fidelity | Arc kind, numbered endpoints/continuations and source correspondence; not replaced by tie logic |
| Lyric fidelity | Unicode text/character errors, verse/segment order, syllabic/extender metadata and note attachment |
| Harmony fidelity | Visible text plus supported root/bass/alteration/kind/degrees and location; retained opaque unsupported symbols |
| Source-system fidelity | Exact ordered measure partition and explicit page/system breaks; accepted real 1–5 / 6–10 / 11–17 remains a regression requirement |
| Rest/structure fidelity | Rest count/type/duration; barline kind/bounds/ownership; clef/key/time/context transitions; no theory-driven changes |

Scoped acceptance requires **100% supported-property agreement, zero invented
objects and zero unresolved required facts** in the declared reference regions;
unimplemented properties are disclosed and cannot receive full-fidelity PASS.
Dataset detector thresholds must be measured on held-out varied sources, with
confidence intervals and failure classes, before automatic enablement. No
precision/recall or calibrated detector performance is measured by this audit.

## 13. Smallest next milestone and acceptance plan

**Propose, do not begin:** a read-only, bounded raw-evidence candidate slice for
standard hollow/filled heads, stems and nearby arcs in registered staff regions.
Retain raw run tables/raster crop provenance, deduplicate pixel support, expose
per-property observations/unknowns and show them for source comparison. Include
the real omitted region as a fixture after durable packaging/source-use review,
and independently labeled synthetic plus other-source fixtures. No automatic
note/tie insertion, theory waiver, detector confidence claim or song-specific
coordinates in production. Source coordinates/IDs belong only to fixtures.

Within that milestone, use controlled temporary XML/OSMD capability fixtures to
assess mixed-size half/eighth chord rendering and endpoint attachment without
editing the live score or accepted system-layout implementation. Source-match
Verify policy and semantic patch paths are separately scoped dependencies before
an end-to-end recovered-score acceptance claim.

| Acceptance case | Cùng Đem Tin Mừng check | Generalized counterexample |
| --- | --- | --- |
| Omitted hollow head | Surface distinct A4 and smaller C5 observations near “đây.” with raw provenance; no automatic patch | Different pitches/staves/clefs, large/small ratios, filled/open heads, independent voices |
| Count/dedup | Treat 2246/2248/2383 overlap as evidence for source objects, not three notes | Fragmented heads, merged stem/head masks and composite variants |
| Duration independent of meter | Source half duration supported by head/stem; onset remains unknown until supported | Same image notation under changed printed meter, under/overfill and unknown capacity: candidate facts unchanged |
| No plausibility inference | No invented completion/accidental/voice | Missing two beats with no head yields no note; plausible harmony with no pixels yields no pitch |
| Small-note timing | C5 remains duration-bearing; small is not grace | Genuine grace, explicit cue and small secondary ordinary notes side by side |
| Ties and slurs | Lower A arc targets surviving head 590; upper C arc separately resolved/confirmed | Same-pitch slur, different-pitch slur, overlapping arcs, broken curves, cross-system continuations and duplicate endpoints |
| Following event preservation | Existing e-16 A4 eighth and e-17 C5 chord member remain at m5 onset 0; “Loan” stays attached to G4 e-18 | Missing predecessor followed by a different lyric/pitch pattern; no lyric used as timing evidence |
| Serialization | Controlled small duration-bearing XML keeps duration/type/size/chord and sound/visual tie bindings | Separate-voice backup/forward, namespaces, unknown ornaments, dots/tuplets; unrelated XML unchanged |
| OSMD visibility | Mixed normal/small heads and arcs must be visible and correctly selectable | Reversed chord order, stems, zoom, narrow panes; same semantics across all views |
| Layout regression | Preserve accepted 1–5 / 6–10 / 11–17 | Variable system sizes/multiple pages and missing grouping safe fallback |
| Theory confirmation (later policy) | Explicitly compare any unusual source structure without rewriting it | Confirm real overfill, reject malformed XML, invalidate stale decisions and preserve conflicts on export |
| Lifecycle (later mutation milestone) | Undo/Redo source-backed insertion/arc/decision; verify exact current XML | Expiry/revision races, reject candidate, reimport, transpose 0/+2/−2 without timing/size/arc loss |

The actual current real capture should remain a negative fidelity fixture:
measure 4 has no semantic events or A/C ties despite visible source notation.
The next read-only milestone passes by exposing supported evidence and unknowns,
not by claiming it has repaired that negative fixture. Full score metrics require
annotation beyond this local region. Existing unrelated lyric OCR errors must
be compared to source, not “corrected” by assuming a word from context.

## 14. GO / NO-GO and documentation validation

**GO:** the evidence-only milestone above, preserving the current pipeline and
accepted source-system rendering. Source-supported missing-note and small
secondary-note reconstruction is feasible in principle; real source pixels
survive. Human-confirmed recovery can follow once a local XML plan has explicit
fields and provenance. Tie/slur recovery is feasible only with classified arcs
and unambiguous individual-head endpoints or explicit human confirmation.

**NO-GO now:** generalized raw-glyph automatic recovery, meter-based reconstruction,
full mixed-size OSMD fidelity claims, a blanket Verify-error waiver, song-specific
patches or a renderer migration. Recognition fragments do not supply a complete
semantic event today. No production change is authorized by this document.

This audit changes only this Markdown file. Verification uses a SHA-256 snapshot
of all 168 pre-existing tracked/untracked repository files and confirms they are
unchanged, including the accepted renderer and existing uncommitted work.
`git diff --check` and `git status --short` are the necessary final repository
checks; no suites/build/lint are rerun for this documentation-only task. MusicXML
links were checked against official W3C references; installed OSMD behavior was
inspected read-only. No live detector experiment, recognition invocation, browser
acceptance, production recovery, Phase 4F.2 work, staging, commit or push occurs.
