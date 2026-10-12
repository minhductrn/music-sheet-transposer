# Phase 4F notation-editor architecture review

Architecture spike, 2026-10-04. Baseline: `3a4e548` plus the existing uncommitted
Phase 4F implementation. This document proposes changes; it implements none.
It supersedes the acceptance recommendation in `PHASE4F_VISUAL_REVIEW.md` for
this product direction. Existing code, tests and that implementation record stay
intact. No recognition, browser acceptance or renderer migration was performed.

**Decision: C — an XML-backed semantic editor with OSMD rendering and an
application-owned interaction adapter. NO-GO on continuing the current
architecture unchanged or accepting it as the initial notation editor.**
OSMD need not become preview-only. A richer canonical semantic contract is
needed, but it should grow the existing review projection rather than become a
second independently mutable score or a lossy MusicXML generator.

## 1. Current architecture and evidence

Today: PDF/image → recognition MusicXML plus optional `.omr` → preserved XML
`Document` → `EditableScore` projection → React review controls and OSMD →
revision-checked preservation patches → validation → human verification →
existing preservation transposer/export.

Primary inspected sources:

- `app/music/review/{document,models,importer,patcher,ties,service,storage}.py`;
  `app/api/v1/reviews.py`;
  `app/music/recovery/{omr,models,musicxml,service}.py`.
- `frontend/src/components/{MusicSheetViewer,RecognitionReview,VisualNoteEditor,
  EventInspector,SourceViewer}.tsx`, `frontend/src/utils/{scoreInteraction,
  visualReview}.ts`, `frontend/src/pages/Home.tsx`, API/types and regression tests
  (frontend paths are relative to the repository root).
- Installed OSMD **2.1.2**, its declarations under
  `frontend/node_modules/opensheetmusicdisplay/build/dist/src`, bundled JavaScript,
  package metadata and license. Bundled VexFlow is **1.2.93**. Findings concern
  these installed versions, not a claim about all future versions.
- Existing synthetic `.omr` fixture
  `tests/music/fixtures/semantic_omr_sheet.xml`, parser and recovery report flow.
- Read-only `javap -c -p` inspection of installed
  `/opt/audiveris/lib/app/audiveris.jar`, `PartwiseBuilder` and its `MeasurePrint`
  class. This inspected exporter bytecode; it did not run Audiveris.
- Complete tracked Phase 4F diff and new visual editor, utilities, fixture,
  regression tests and documentation. The previous validation record is 627
  backend tests and 50 frontend regressions, lint/build passing. Those counts
  are prior results, not newly run tests for this documentation-only spike.

`Document` keeps original bytes and the complete safely parsed XML tree with
stable review references. Supported edits clone and patch that tree. XML without
edits can be exported byte-for-byte; serialization after edits preserves
unsupported elements but does not promise original whitespace, prefixes,
attribute quoting or document-type formatting. History includes document and
manual-change/issue metadata. Sessions are bounded, expiring process memory.

OSMD is a derived view, never the authoritative edited score. The new selection
adapter resolves OSMD source semantics against backend events and binds SVG
heads. Visual and Advanced modes share selection, API, revision and history.

## 2. Problems exposed by real OMR correction

The reported Cùng Đem Tin Mừng comparison supplies product requirements: 2/4,
missing adjacent duration-bearing notes, ties, Vietnamese lyric OCR mistakes,
source/OSMD system mismatch and an overly technical event inspector. These are
observations supplied by the user, not a reconstructed real-score ledger.

The expired real review/XML is unavailable. The exact cause of the reported
measure-5 duration `7/2` remains unknown. Synthetic tests prove generic behavior,
not that this real song has a particular incorrect barline, voice, onset or note
ownership. No song-specific rule follows from those tests.

Proven existing behavior: sequential insertion stays in the explicitly requested
measure; chords do not double-count advancing duration; ties do not change time;
tied notes remain distinct duration-bearing events; correction-induced overfill
is ERROR and blocks verification. An anchor-only editor cannot correct an
incorrect measure boundary or express arbitrary musical placement. Source layout
is not currently retained as a complete review organization.

## 3. Desired product model

Build an **OMR correction editor**, not a full notation application. Recognition
is a draft whose pitch, timing and structure may be wrong. The user should select
a note or musical position, understand its local meter/staff context, correct it,
and see validation without manipulating event IDs or rational onset strings.

Separate three domains:

1. Musical semantics: parts, staffs, measures, context changes, voices, events,
   relationships and authoritative timing.
2. Source evidence: physical pages, systems, staff geometry, recognized barlines,
   confidence, source hashes and correspondences. Evidence can disagree with edits.
3. Engraving: OSMD pages, systems and graphical coordinates computed for a viewport.
   These are disposable view objects, not source geometry or musical ownership.

An invalid draft must remain representable and undoable. “Canonical” means one
consistent semantic identity/contract, not that every OMR draft is already valid.

## 4. OSMD capability assessment

| Question | Evidence from installed API/implementation | Consequence |
| --- | --- | --- |
| Graphical-to-semantic notes? | `GraphicalNote.sourceNote`, `Note.SourceMeasure`, `ParentStaff`, `ParentVoiceEntry`, pitch and length exist. Current adapter matches part/measure/staff/voice/onset/duration/pitch/grace uniquely. | Good basis for selection; no guaranteed intrinsic mapping to our IDs. Ambiguous unisons, normalization and nonnumeric voices must fail safely. |
| Staff coordinates to position? | `StaffLine`, staff-line geometry, `PositionAndShape`, `BoundingBox`, active clef and `ClefInstruction` expose necessary ingredients. | Feasible adapter work, not an existing tested pixel-to-semantic pitch operation. Must account for scale, page, clef line/octave and staff. |
| X to timestamp? | `GraphicalMusicSheet` exposes `tryGetTimestampFromPosition`, nearest staff/voice-entry methods and DOM/SVG/OSMD coordinate conversions. | A hit/interpolation hint, not an authoritative empty-space beat grid or voice decision. Snap against canonical onsets and subdivisions. |
| Measure/staff bounds? | Graphical measures/staff lines expose inherited bounding boxes and source/parent objects. | Feasible hit regions; bounds must be validated with real rendering, zoom and resize. |
| XML system/page breaks? | `OSMDOptions` has `newSystemFromXML`, `newSystemFromNewPageInXML`, `newPageFromXML`; documented defaults are false. Page layout also depends on `PageFormat`. | Explicit breaks can be honored when enabled; width can cause additional breaks. No pixel-identical or exact measure-group guarantee. |
| Interactive repositioning? | Graphical pitch/position methods and VexFlow objects exist. | Moving view objects is cosmetic and overwritten by rerender. No exposed editor transaction supplies timing, XML preservation, validation or history. |
| Efficient refresh? | `load`, `updateGraphic`, `render` exist; current component reloads the entire XML per corrected Blob and rerenders on resize. | Functional refresh with cancellation guards. Incremental editing latency on large scores is unmeasured; benchmark before promising drag responsiveness. |
| Renderer or editor? | API centers on MusicXML reading, graphical calculation, engraving and cursors. Current application supplies all mutation/history/export semantics. | OSMD is the renderer and useful hit surface; it cannot own the editor's musical contract. |

`getNoteheadSVGs()` returns heads of the shared VexFlow chord; the adapter uses
`vfnote[1]`/`vfnoteIndex` to select the individual head. This version-dependent
boundary should remain isolated and tested. Shared unison heads are deliberately
not arbitrarily assigned. Backend IDs survive view recreation; SVG identity does
not. Rational quarter units become OSMD whole-note fractions via factor four;
frontend floating-point matching is only a view association, never validation.

Exact unresolved runtime questions: reliability of bounds/conversions on multiple
pages and CSS zoom; timestamp behavior in empty measures, grace groups and sparse
voices; head identity across clef/key changes and unsupported notation; behavior
of forced breaks at narrow widths; full-refresh latency on representative scores.
These require controlled renderer/browser fixtures, not a replacement decision
based on assumptions. Installed API evidence is sufficient for this recommendation;
no external provider research is needed at this stage.

## 5. OMR and `.omr` structural evidence

| Information | Available evidence | Current retained review information / gap |
| --- | --- | --- |
| Time signature | MusicXML attributes; Audiveris exporter has `processTime`; `.omr` stack expected/duration and recognized time inters can corroborate. | XML meter projected; stack capacity and structural time inters are not published as review structure. |
| Key signature | MusicXML attributes; exporter `processKey`; recognized key inters may exist in sheet graph. | Measure/event key snapshots retained; no structural key evidence mapping. |
| Clef | MusicXML clefs; exporter `processClef`; `.omr` clef inters. | XML preserved, no editor clef projection; `.omr` clefs used to derive candidate pitch, not retained as editable context. |
| Barlines / boundaries | MusicXML measures/barlines; exporter `processBarline`; `.omr` stacks, physical-part measures and graph relations. | Measure IDs and left/right evidence available; complete editable barline/source-boundary model absent. |
| Pages / systems | Book/stub logical-part mappings; sheet page/system hierarchy; exporter `Print.setNewSystem`, `setNewPage`. | Parser flattens systems across sheet pages, omits page IDs; full hierarchy does not reach review payload. |
| Staff geometry | Staff IDs, staff lines/points, picture dimensions, interline. | Lines used for pitch interpolation, not retained as polylines; candidate staff/position and selected sheet metadata survive. |
| Measures per system | System contains stacks/part measures. | Parser has system measure organization, but recovery payload is not a complete structural sidecar. |
| Head/stem/beam geometry | Graph inter bounds and relations; synthetic fixture demonstrates head/chord/stem/beam bounds. | Candidate head bounds survive; stem/beam IDs retained without their complete geometry. Ordinary heads are not all published as review issues. |
| X/onset correspondence | Slots have `time-offset`, and fixture has `x-offset`. | Quarter-unit onsets retained for candidate voice starts; slot X discarded. |
| Source identity | Archive hash, member/inter provenance, binary hashes, sheet dimensions. | Useful guarded registration; not proof that every recognized object maps uniquely to XML. |

Exporter bytecode also sets system margins/distances, staff distance and default
page layout. This proves the installed exporter can emit these fields, not that
the unavailable real score contained correct usable breaks. A future review must
inspect that specific MusicXML's `<print>` elements and page metadata.

The `.omr` parser currently targets an observed graph format (not a universal,
version-independent schema). `semantic_omr_sheet.xml` is explicitly **synthetic**;
it proves parser paths for demonstrated fields, not every Audiveris output shape.
Time/key/barline inter varieties need real versioned archive fixtures before a
structural extractor can claim support. Recovery currently publishes selected
candidate evidence and summaries, not the full `EvidenceSheet/System/Measure`
graph or raw archive in the review session. Original downloaded archives are not
destroyed, but structural information is lost at the review projection boundary.

## 6. Meter and rhythm assessment

Current importer uses exact `Fraction` quarter-note units. MusicXML duration is
`duration / divisions`. Meter stores beat/beat-type strings, including additive
beats and multiple pairs. Capacity is the sum of `beats * 4 / beat_type`:

| Meter | Capacity in quarter units | Meter-aware interpretation |
| --- | --- | --- |
| 2/4 | 2 | Two quarter pulses |
| 3/4 | 3 | Three quarter pulses |
| 4/4 | 4 | Four quarter pulses |
| 6/8 | 3 | Common compound grouping: two dotted-quarter pulses; not three quarter pulses |

Quarter-unit arithmetic is sufficient for exact capacity, durations and ties.
It is insufficient by itself for metrical grouping, beat labels, subdivision
snapping and explicit pickup policy. Retain exact fractions; add meter/grouping
metadata, not a different timing unit. MusicXML divisions are serialization units,
not a beat definition. Duration needs both sounding length and notation spelling
(type, dots, tuplet ratio) for editing; do not infer all spelling from one number.

The importer processes backup/forward cursor movements, retains voice/staff and
chord membership, advances ordinary notes/rests, excludes grace advancement and
uses maximum temporal extent rather than summing parallel voices. Rhythm checks
exclude chord members from advancing spans, detect voice overlap and underfill.
Forward handling suppresses some underfill warnings; it is not a complete editable
occupancy map. Differing staff meters or mid-measure meter changes can make
capacity unknown and yield warnings; do not pretend these are simple measures.

`implicit="yes"` permits short measures without the ordinary mismatch warning;
this does not distinguish an approved pickup from an erroneous OMR short measure.
Final partial measures can produce warnings; there is no explicit pickup/final
partial pairing or user-confirmed capacity model. Overfill is not exempted by
implicit status. Add explicit partial status, capacity and confirmation/provenance.

Important policy boundary: service projection adds blocking `measure_overfilled`
when recovery exists or a measure is marked with manual event changes. Phase 4F
now marks duration/grace edits as timing changes, closing their validation gap.
Plain imported XML without those conditions can retain the older mismatch warning
policy. A canonical structural milestone must make draft overfill policy explicit
and uniform; it must not describe today's validator as universally blocking all
uncorrected imports. Strengthen/error-audit that policy rather than weaken the
existing correction error. Unknown rhythm must be visible, never assumed valid.

Meter edits must not silently reinterpret duration, redistribute notes, move an
overflow across a barline or “fix” capacity by enlarging the meter. Measure moves,
split/merge and time insertion require explicit user intent and atomic validation
of affected voices, context changes, relationships and adjacent measures.

## 7. System/staff layout assessment

Current `MusicSheetViewer` config sets SVG rendering, title and cursor options,
with custom resize handling. It does **not** enable XML system/page break options;
responsive `updateGraphic`/`render` can reorganize measures. Preserved `<print>`
markup therefore does not imply the preview honors it. This is a concrete
configuration gap, separate from invalid rhythmic ownership.

Practical review layout should first honor trusted existing XML breaks; when they
are absent/incorrect, a provenance-bearing source-layout sidecar can provide
ordered source systems and mapped measure/staff IDs. Derive temporary review
MusicXML break hints from that sidecar without silently editing the exported
preserved document. User changes to exported breaks must be explicit commands.
Use a stable review width/page policy, with horizontal scrolling or an explicit
responsive fallback, and show when width forces additional systems. Test before
promising exact source grouping.

No pixel reconstruction is required. Source staff polylines and raster coordinates
belong to source evidence; OSMD staff positions belong to rendered layout. A PDF
page can differ from an Audiveris sheet/logical page: record coordinate space,
page identity, dimensions, crop/rotation and validated transforms. Existing source
image highlights depend on trustworthy matching dimensions; native PDF viewing
has limited overlays. Never fabricate geometry for a manually inserted event.
Structural edits may require one-to-many source-to-edited-measure correspondence.

## 8. Minimum canonical score model

Extend the existing backend projection into a versioned semantic contract bound
to the preserved XML and stable IDs. Frontend consumes a revision snapshot and
submits commands; it does not maintain a second authoritative mutable score.

| Entity | Minimum useful contents |
| --- | --- |
| Score | Revision, part order, metadata, preserved-document binding, diagnostics and confirmed/draft status |
| Page / System | Source page identity and coordinate space; ordered source-system measure/staff correspondences; separate derived renderer page/system IDs |
| Part / Staff | Stable IDs, staff number, notation kind, staff line count, effective context and source links |
| Measure / Barline | Stable ID, display number distinct from order, explicit boundaries, barline kind/repeats preserved, capacity/partial policy and source correspondence |
| TimeSignature | Staff scope, onset, beats/denominators, compound/additive grouping, effective inheritance and user confirmation |
| KeySignature / Clef | Staff/onset scope, traditional/custom key data, clef sign/line/octave, inherited and explicit values |
| Voice / onset | Stable voice label, exact rational onset and occupancy/gaps within a measure; cross-staff identity retained |
| Note / Rest / Chord | Stable event IDs, pitch/rest kind, staff/voice, grace status; explicit simultaneous chord grouping and shared advancing timing |
| Duration / Accidental | Exact sounding length, XML divisions binding, type/dots/tuplet spelling; written alteration and display accidental distinguished |
| Tie | Source/target IDs plus sound `<tie>` and notation `<tied>` bindings; adjacency/pitch validation, no duration merging |
| Lyrics / Harmony | Existing verse/segment IDs and attachment; Unicode, syllabic/elision/extend preserved; harmony roots/kinds/text and opaque unsupported extensions |
| Geometry / provenance | Source archive/member/inter IDs, hashes, confidence, bounds/polylines, coordinate transforms, uncertain correspondence and manual changes |

Do not flatten unsupported notation into these fields. Maintain opaque XML nodes
and bindings. Missing or ambiguous facts stay unknown. Source metadata must be
optional for MusicXML-only reviews and must not override human corrections.

## 9. Preservation-MusicXML integration

Use one transaction boundary:

```text
Preserved XML + bound semantic projection + source/layout sidecar
  → expected-revision semantic command
  → clone affected document/metadata
  → plan explicit local XML patches
  → reproject and validate resulting score
  → atomic revision/history update
  → OSMD view refresh
  → explicit human verification
  → unchanged preservation transposer / corrected XML export
```

Existing simple commands remain supported. Future position/move/barline commands
must specify measure/staff/voice/onset and policy: add time, replace a rest, create
a chord, or move an event are different actions. XML planners may need local
backup/forward changes, context relocation or divisions changes; these need
preservation tests and explicit support limits. Refuse unsupported complex edits
rather than regenerate unrelated XML or guess a voice layout. Avoid gratuitous
renumbering of every measure/ID.

Representable invalid drafts can be committed with ERROR diagnostics for human
repair; impossible/ambiguous patch plans are rejected atomically. Any mutation,
including structure/layout metadata relevant to verification, invalidates
verification and derived transposition. Undo/redo restores document and sidecar
state using increasing revisions and never silently restores VERIFIED. Existing
transposition must consume only the current verified corrected bytes. Preserve
unrelated XML subtrees; do not promise byte identity after serialization.

## 10. Interaction feasibility matrix

Classification describes present support and the minimum next dependency; it
is not a promise that API declarations alone establish browser correctness.

| Target | Classification | Assessment |
| --- | --- | --- |
| 1. Click note | SUPPORTED WELL BY CURRENT PHASE 4F for uniquely mapped heads | Keep semantic matching and keyboard selection; ambiguous heads need a choice/fallback. Real SVG runtime still unaccepted. |
| 2. Vertical pitch drag | REQUIRES CANONICAL SCORE MODEL; FEASIBLE WITH CURRENT OSMD INTERACTION LAYER | Effective clef/key/accidental context plus validated staff-coordinate adapter; preview then one semantic command on release. |
| 3. Click position to insert note/rest | REQUIRES CANONICAL SCORE MODEL; FEASIBLE WITH CURRENT OSMD INTERACTION LAYER | Bounds/timestamp hint plus exact meter grid, voice/gap policy and XML placement planner; current anchor controls cannot express this. |
| 4. Musical duration picker | SUPPORTED WELL BY CURRENT PHASE 4F for supported values | Retain patcher-derived options; future occupancy policies must be explicit. |
| 5. Delete note/rest | SUPPORTED WELL BY CURRENT PHASE 4F at mutation/Advanced level | Current deletion shifts following sequential timing. Editor must distinguish deleting time from replacing with rest; visual rest targeting needs runtime proof. |
| 6. Source→target tie | SUPPORTED WELL BY CURRENT PHASE 4F for mapped compatible endpoints | Keep backend target policy and proper XML semantics; no visual-only tie. |
| 7. Lyrics | SUPPORTED WELL BY CURRENT PHASE 4F through selected note | Direct rendered-lyric click is FEASIBLE WITH CURRENT OSMD INTERACTION LAYER (`getLyricsSVGs`), with verse/segment ambiguity handled. |
| 8. Barline / measure ownership repair | REQUIRES CANONICAL SCORE MODEL | Explicit move/split/merge commands, voice/context/tie repair and source mapping; not an OSMD graphic displacement. |
| 9. Undo/Redo | SUPPORTED WELL BY CURRENT PHASE 4F | Reuse transaction/history lifecycle; extend snapshots to new metadata. |

None of these nine requirements currently demonstrates a need for different
rendering technology. Arbitrary engraving drag, broad complex-tuplet repair,
beam/slur shaping and complete melisma reconstruction are OUT OF SCOPE FOR INITIAL
NOTATION EDITOR; preservation remains mandatory.

## 11. Current Phase 4F KEEP / REFACTOR / REPLACE / DEFER matrix

All existing files stay unchanged during this spike. “Replace” below means a
future primary interaction, not deletion of working code now.

| Current work / files | Classification | Future treatment |
| --- | --- | --- |
| `VisualNoteEditor.tsx` orchestration | KEEP / REFACTOR | Reuse controls; route through app-owned editor commands and explicit placement/context state. |
| `scoreInteraction.ts`; direct OSMD selection | KEEP / REFACTOR | Keep renderer adapter and safe ambiguity fallback; isolate version assumptions and add bounds/coordinate/identity fixtures. |
| `visualReview.ts` semantic matching, timing helpers | KEEP / REFACTOR | Keep pure functions; unify timing conversion, richer context and typed command construction. |
| Pitch step buttons / explicit accidentals | KEEP / REFACTOR | Preserve accessible alternative to drag; move effective clef/key/accidental policy into semantic contract. |
| Duration picker; service `duration_options` | KEEP / REFACTOR | Retain representability checks; add occupancy policy and benchmark repeated per-event patch probing. |
| Anchor insertion as sole primary placement | REPLACE as primary UX; KEEP as fallback | Future musical-position insertion; retain before/after/chord controls until replacement is proven. |
| Visual tie workflow | KEEP AS-IS for current supported cases | Use existing compatible target IDs and sound/notation patches under future controller. |
| Lyric editor; lyric API/service support | KEEP AS-IS | Reuse Unicode/verse/segment operations, provenance and history; rendered lyric hit adapter can follow later. |
| Undo/Redo / verification / transposition invalidation | KEEP AS-IS | Extend metadata snapshots when structural sidecar exists; keep lifecycle invariants. |
| Friendly diagnostics | KEEP / REFACTOR | Preserve underlying severity; add measure-aware context and structural explanations. |
| Advanced Review / `RecognitionReview.tsx` | KEEP / REFACTOR | Keep synchronized escape hatch; separate view modes from editor controller as structure grows. |
| Expiry handling / local corrected download | KEEP AS-IS | Existing process-memory limitation remains; persistence is a separate later decision. |
| `MusicSheetViewer.tsx` | KEEP / REFACTOR | Retain load cancellation/resize cleanup; separate render adapter and controlled source-break policy. |
| `Home.tsx`; `services/api.ts`; CSS | KEEP / REFACTOR | Retain MusicXML review entry, optional source and corrected revision routing; accommodate editor controller without changing lifecycle. |
| Backend `models.py` / `importer.py`; frontend `types/review.ts` | KEEP / REFACTOR | Grow existing semantic projection, preserve event-level key context and rational timing. |
| Timing correction validation in `service.py` | KEEP AS-IS | Keep newly blocked duration/grace overfill; separately audit uniform imported-draft overfill policy. |
| `api/v1/reviews.py` lyric DELETE / provenance | KEEP AS-IS | No new API design needed for lyric support. |
| `tests/test_phase4f_lyrics.py`, `tests/test_review_api.py`, synthetic `visual_review.musicxml` | KEEP AS-IS | Keep legitimate regressions, including corrected warning fixture; maintain explicit synthetic labeling. |
| `visual-review.test.mjs`, `review-lifecycle.test.mjs` | KEEP AS-IS | Retain all regressions; extend with renderer integration tests, not substitute doubles for browser proof. |
| `README.md`, `REVIEW.md`, `PHASE4F_VISUAL_REVIEW.md` | KEEP / REFACTOR later | Retain implementation record; this architecture decision overrides its acceptance direction. Update product scope in implementation milestone. |
| Drag, empty-position placement, structural repair, complex layout reconstruction | DEFER | Plan after semantic/geometry contracts; pixel-perfect reconstruction stays outside scope. |

Most of the implementation is reusable: all preservation mutations, tests,
history, verification/transposition routing, lyrics, ties, duration controls and
selection foundation. No defensible line-count reuse percentage follows from
this architecture review; the principal change is responsibility and structural
coverage, not wholesale replacement.

## 12. Alternative technology assessment

No renderer migration is justified by the demonstrated gaps. The missing pieces
are musical state/commands and source-layout organization. OSMD already exposes
semantic objects, bounds, hit helpers and explicit-break options. The relevant
alternative at this stage is an application-owned editing layer over OSMD.

| Criterion | OSMD + application-owned semantic editor | Direct bundled VexFlow as replacement |
| --- | --- | --- |
| Rendering quality | Existing MusicXML engraving; source fidelity requires testing | Existing underlying primitives, but application would rebuild layout/import coverage |
| Interactive editing | App commands plus OSMD graphical adapter | App commands and hit regions still required |
| MusicXML import/export | OSMD reads; preserved Python XML exports | No replacement import/export pipeline demonstrated locally |
| Semantic selection | Source-note mapping available | App must supply canonical identity throughout primitives |
| Coordinate mapping | Staff/measure bounds and conversion helpers available | App would own complete hit/layout geometry |
| Notation support | Existing supported rendering with opaque XML retention | Primitive support does not establish equivalent MusicXML coverage |
| TypeScript/web | Already integrated | Already underneath OSMD; direct integration is new work |
| Licensing | Installed OSMD BSD-3-Clause | Installed VexFlow MIT |
| Maturity | Locally deployed renderer with existing tests; editor contract still ours | Installed legacy 1.2.93; not evidence about modern standalone releases |
| Migration cost | Focused contract/adapter extension | High: parser, layout, identity, coverage and rendering integration |
| Python compatibility | Existing API and preservation patcher | Can use same backend, but no semantic benefit removes required backend work |

Direct VexFlow is not recommended. Do not start broad provider shopping. If the
controlled OSMD spike fails, first identify an exact blocking requirement and
then evaluate a narrow candidate with primary-source evidence for that specific
requirement, XML coverage, license and maintenance. No claim is made here about
uninspected external editors or their capabilities.

## 13. Recommended final architecture

**C: preservation-backed canonical semantics + source-evidence/layout sidecar +
application editor controller + OSMD render/hit adapter.**

```text
MusicXML recognition draft ───► preserved XML Document
.omr/source ─► optional structural evidence / correspondence sidecar
                                  │
                       bound semantic projection
                                  │
                  application-owned editor controller
                     │                         │
          semantic patch commands      OSMD render/hit adapter
                     │                 (selection + geometric hints)
           validate / history / revision
                     │
              verified corrected XML
                     │
          existing transposer and exports
```

OSMD can remain the primary visible score surface. The controller and semantic
model own editing decisions. A separate canvas/editor renderer is optional only
if a measured requirement later proves impossible with OSMD; it is not necessary
now. OMR evidence proposes structure, human commands correct it, validation checks
it, and preservation XML remains the durable musical payload.

## 14. Migration from current uncommitted Phase 4F

Preserve the current work as the starting point. First formalize existing IDs,
units, inherited context, partial status and command invariants. Extend projection
and metadata with additive fields; retain old endpoints/Advanced controls while
new contracts gain regression coverage. Keep one revision authority.

Next isolate OSMD integration behind render/bind/hit/coordinate capabilities.
Add source grouping and explicit-break policy without changing musical events.
Then implement a narrowly supported position operation planner and structural
commands; keep anchor controls as fallback. Finally add pitch drag and direct
text hits using proven semantic operations. Do not combine this migration with
recognition heuristics, transposer redesign or persistence deployment.

## 15. Initial notation-editor scope

Structure: effective clef, key, time signature; stable staffs/voices/measures;
basic barlines and explicit measure ownership correction; source-system grouping
where evidence is trustworthy. Context edits must specify scope and whether
written pitches/timing remain unchanged, rather than silently reinterpret notes.

Notes: pitched notes/rests, pitch and explicit accidentals, standard/dotted values,
simple chords and supported polyphony, real ties and human placement. Text:
Unicode lyric add/edit/remove with preserved verse/syllabic metadata; harmony
preservation and existing simple controls. Editing: visual/keyboard selection,
pitch movement, duration, explicit add/delete policies, tie, lyrics and Undo/Redo.
These are staged capabilities, not a commitment to deliver every structural
operation in one milestone.

Advanced tuplets, cross-staff/complex multi-voice reflow, unusual/custom notation,
beams, slurs, ornaments, dynamics, articulations, repeats/volta structure and
complex melisma remain preservation-only unless a specific operation has proven
safe support. Existing unaffected notation must survive every supported edit.

## 16. Explicit non-goals

No Symphony Pro clone, automatic missing-note recognition, Audiveris changes,
semantic-recovery heuristic changes, SMT work, transposer rewrite, automatic
barline overflow movement, speculative song repairs, full engraving application,
pixel-perfect PDF reconstruction or wholesale MusicXML regeneration. No drag,
canonical model implementation, production behavior change or browser acceptance
occurs in this architecture spike.

## 17. Risks and unresolved facts

- XML-to-model drift: always reproject after patches and compare supported
  semantic invariants; never independently edit frontend and XML authorities.
- Draft structure may be wrong or unknown: explicit confidence/confirmation,
  invalid draft diagnostics and guarded unsupported-operation errors are needed.
- Structural edits can affect context, backup/forward, ties, lyrics and source
  correspondence beyond one note; local planners need atomic preservation tests.
- `.omr` schema/version and source-sheet/PDF-page registration can differ; archive
  hashes and known coordinate transforms are necessary, not sufficient by themselves.
- OSMD normalized identities, chord SVG indexing and responsive extra breaks are
  version-coupled; test pinned installed behavior and ambiguous fallbacks.
- Current history/source metadata design needs extending together; process expiry
  still loses session provenance/history even when corrected XML was downloaded.
- Repeated payload duration probing and full-score renderer refresh may limit
  responsiveness. No latency measurements currently establish efficient dragging.
- Actual real-song meter/barline ownership and original exported break markup are
  unavailable; no architectural diagram or synthetic example resolves that fact.

## 18. Proposed implementation phases

1. **Structural contract and source-layout foundation (next milestone):** extend
   the existing XML-bound projection for clef, meter grouping/partial policy,
   staff and barline identity; define uniform blocking rhythm policy; retain
   versioned page/system/staff evidence and uncertain correspondences. Add
   read-only OSMD geometry/identity fixtures and controlled explicit-break mode.
2. **Position-based commands:** explicit onset/voice note/rest placement and
   deletion policies for supported simple rhythms; safe local backup/forward
   planning, context and tie validation, sidecar history and preservation tests.
3. **Scoped structure correction:** explicit measure ownership moves and selected
   boundary/context edits with declared limits; no silent spillover. Define safe
   split/merge support before exposing it.
4. **Notation interaction:** vertical pitch drag with keyboard alternative,
   snapped insertion feedback, direct lyric hits and app-owned interaction modes.
5. **Browser acceptance/checkpoint:** renderer geometry, source grouping, timing,
   history and verified corrected-byte workflows on synthetic and available real
   references. Commit only under separate user authorization.

Each phase is a proposal needing a scoped implementation request. This spike does
not begin phase 1 or promise all phases as one Phase 4F change.

## 19. Browser acceptance strategy

Do not run the current acceptance now. Automated 627/50 results validate existing
behavior, not the revised notation-editor architecture or real OSMD runtime.
After the structural/adapter milestone, use explicitly synthetic fixtures for
2/4, 3/4, 4/4, 6/8 grouping, pickup/final partials, rests/chords/voices,
backup/forward, clef/key changes, ties across measures and Vietnamese lyrics.
Include source-shaped system groups, XML page/system breaks, narrow widths,
zoom/resize, ambiguous unisons and multiple source pages.

Check that visual and Advanced identities agree; source/render coordinates remain
separate; placement never crosses a barline silently; invalid drafts remain ERROR
and cannot verify; unsupported context does not produce guessed pitch/onset.
Check full undo/redo, expired-session local download, exported preservation,
verification invalidation and transposition of the exact corrected revision.
Inspect real browser engraving, focus, tie endpoints, downloads and latency;
semantic/SVG doubles cannot prove them. Available real sources supplement these
cases with recorded facts, not unlabeled synthetic reconstructions of expired
sessions. Initial exploratory render tests are technical evidence, not product
acceptance of the unchanged architecture.

## 20. GO / NO-GO

**NO-GO** on continuing the current architecture unchanged as the desired notation
editor, and **NO-GO** on browser acceptance of that product before the structural
contract/adapter refactor. The current code remains useful, tested correction
infrastructure and must not be discarded.

**GO recommendation for a separately authorized next milestone:** grow the
existing preservation-bound canonical semantic contract and source-layout
foundation, retaining OSMD and current selection/controls. Defer dragging and
arbitrary position/structural editing until their musical and coordinate contracts
are demonstrated. Keep all existing overfill, verification, history and corrected
transposition invariants.

## SOURCE FIDELITY CONTRACT — implemented Phase 4F.1 foundation

1. Source evidence first; retain observations separately from interpretation.
2. Recognition is a draft, including incorrect or ambiguous musical structure.
3. No invented notation: missing notes/rests remain missing without trustworthy
   explicit evidence or a human command.
4. **NO SILENT RHYTHMIC REPAIR:** importing, projecting, validating and arranging
   review layout do not change durations/onsets, notes/rests, measure ownership,
   barlines, meter, ties or voices. There is no overflow redistribution.
5. Music theory validates; it does not compose.
6. Conflicts are valid review state. Overfill is blocking; underfill is visible,
   never padded. First/final position alone never authorizes a pickup/partial.
7. User correction is explicit, revision-checked and provenance-tracked.
8. Only user-verified corrected review XML proceeds as trusted input to reviewed
   transposition/verified export. Draft downloads remain explicitly unverified.

Phase 4F.1 grows the existing XML-bound projection rather than rebuilding XML.
It exposes event measure ownership, inherited/event clef context, explicit context
changes, staff IDs, barline metadata, sounding and notated duration, accidental
markup, unchanged meter pairs, compound subdivision context, explicit partial
status and rhythm/conflict state. Unknown rhythm stays structurally ambiguous.
All imported overfill now reaches the existing blocking validator, regardless of
whether evidence/recovery or a manual timing edit exists. Existing underfill
warning policy is retained; warnings require human source comparison.

The independent evidence sidecar is retained even when semantic recovery is
disabled. It preserves archive/version diagnostics, sheet/page/system ordering,
staff polylines, stack edges/capacity observations/slots, head candidates, other
structural inters and relationships, with bounded ZIP/XML parsing and session
memory accounting. Raw `.omr` recognized objects are evidence of recognition,
not proof of musical truth. Existing semantic-recovery decisions are unchanged;
this phase adds no geometry-driven musical correction.

Explicit MusicXML print breaks supply review groups. A complete, unique ordered
`.omr` measure-number/part match may supply view-only groups when XML breaks are
absent and archive diagnostics are clear; incomplete/ambiguous evidence remains
unbound. This correspondence is explicitly `ORDERED_RECOGNITION_MATCH`, not a
verified source identity or authority to move events. No source coordinates are
fabricated. Source evidence is immutable import provenance, outside correction
history; XML-bound projection/layout is recomputed after every undo/redo.

The OSMD adapter enables explicit breaks only for source review, on a stable-width
scrollable page. It adds `.omr` break hints only to a renderer-document clone;
preserved/exported XML is unchanged. Normal preview stays responsive. Empty-rest
filling and automatic multi-rest aggregation are explicitly disabled. Selection
uses the existing safe semantic/SVG adapter; measure bounding boxes expose
OSMD-unit hit hints with ambiguous hits rejected. No onset/pitch command is
created from geometric hints in this phase.

### Phase 4F.1 limits and next steps

Source grouping does not guarantee pixel spacing. The renderer fix now derives
engraving capacity from trusted groups and XML width hints, checks actual OSMD
group ownership, and widens within a bounded limit before presentation Fit/zoom.
Unresolved renderer grouping is reported explicitly. Supported Endless page
format retains explicit page breaks without paper-height pagination; PDF crop/rotation registration, direct PDF overlays and exact
multi-page alignment remain unimplemented. `.omr` system/page bounds remain null
when absent. Structural inter varieties are retained generically, not interpreted
as editable clef/key/meter commands. Partial status uses explicit XML `implicit`,
not a inferred pickup/final-partial pairing. Complex/additive meter pairs are kept;
compound grouping metadata only classifies supported simple numeric cases.

OSMD may normalize unsupported or inconsistent notation internally. The backend
conflict ledger is authoritative; ambiguous/generated continuations are not editable
anchors. Real renderer behavior for overfilled drafts, ties, multi-staff grouping,
focus and resize still requires later browser acceptance; the synthetic regression
suite does not establish pixel-level source fidelity.

Next work before Symphony-style drag/position editing: validated DOM/SVG/staff
coordinate transforms, complete effective accidental/clef policies, an exact
meter/voice occupancy grid, explicit onset placement/deletion policies and safe
local backup/forward patch planning. Measure moves/split/merge remain explicit
future commands. The unchanged-architecture NO-GO above is historical; Phase 4F.1
addresses the foundation and is ready for a separately requested foundation
browser acceptance after its checks pass, not acceptance of drag/position editing.

### Foundation validation checkpoint

Complete backend suite: **641 passed**, two existing dependency warnings.
Complete frontend regression suite: **55 passed** (`node --test
--test-isolation=none tests/*.test.mjs`). Frontend lint and production build pass;
the existing OSMD bundle-size warning remains. `git diff --check` passes. Tests
cover import byte preservation, 2/4–6/8 capacities, no padding/ownership movement,
explicit corrections/history, clef inheritance, ambiguous meter, evidence retention
with recovery disabled, two-system grouping and renderer-only break hints.
No browser acceptance, staging, commit, push or recognition invocation was done.
