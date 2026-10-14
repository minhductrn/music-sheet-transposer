# Phase 4F.1 source fidelity: “đây.” → following A → “Loan”

Status: **trace complete; no fix implemented**. Classification **A — Audiveris
recognition loss**, at the persisted recognized-object graph, before MusicXML
export. The source raster and unclassified glyph fragments remain in the archive;
this does not mean the half note or its tie exists as recognized notation.
The internal recognition step that failed or removed interpretations is unknown.

The user reports that source-system layout browser acceptance **PASSED** with
**1–5 / 6–10 / 11–17**. The renderer fix is unchanged. This is a separate source
notation fidelity failure, not an instruction to normalize a measure to 2/4.
Phase 4F.2 has not begun.

## Artifacts, identity and limits

This trace reads the retained real capture at
`/tmp/music-sheet-transposer-phase4f1-cungdemtinmung/`, review
`-Z7DrCMLUEL4Y6YgbpMvZV3wJ9LsTEhi`, revision 1. It does not start recognition,
modify a review, or assume a new browser session has the same correction history.
The rendering clone and OSMD captures there predate the accepted renderer fix;
they prove the captured payload chain, not a new post-fix browser state.

Source PDF: `cungdemTinMung.pdf`, 35886 bytes, SHA-256
`30df9a6988ecc7752c2a89dcd84bcc87b44259b88803e2636f817ede7b15b81a`.
Audiveris archive: `recognized.omr`, software 5.11.0, SHA-256
`f0535f8110376ae7eeb7164494faa16408446ca31232f0886073b83b2d7c46d2`.
The retained `source-audiveris-gray.png` is the archive's source-page raster,
2480 × 3508 pixels. It was visually inspected, including a magnified crop at
source coordinates `(1660,560)`–`(2080,850)`. The crop is retained at
`/tmp/phase4f1-note-trace/source-detail.png`.

Derived raw-object/hash ledger:
`/tmp/music-sheet-transposer-phase4f1-cungdemtinmung/source-fidelity-half-note-trace.json`.
Extracted raw XML: `/tmp/phase4f1-note-trace/sheet#1/sheet#1.xml`.
These are diagnostic files, not production assets. `/tmp` is not durable storage.
No intermediate Audiveris recognition history/provider logs are present in this
capture. Do not infer a particular detector, threshold or internal meter rule.

As established in the layout diagnostic, `audiveris-export.musicxml` is a labeled
copy of the recognized bytes, not an independently fetched export. The recognition
response provides no separate baseline because recovery changed no bytes. Its
provider baseline hash and zero auto-recovery corroborate this export identity.

## Exact source note and target

| Property | Source half note | Immediately following tied A |
| --- | --- | --- |
| Pitch | A4, lower open head | A4, lower filled head |
| Written duration | Half: **2 quarter-note units** | Eighth: **1/2 quarter-note unit** |
| Sheet / source system / physical part / staff | 1 / 1 / 1 / 1 | 1 / 1 / 1 / 1 |
| Source measure/stack | **4**, x=1692–1863 | **5**, x=1863–2302 |
| Source image location | Lower open head near x=1770, y=665; shared downward stem near x=1757 to y=732 | Recognized head bounds `[1926,654,26,22]`, center `(1939,665)` |
| Tie | Lower source arc connects the open A4 to this next A4 across the barline | Right endpoint of that source arc |
| Recognized semantic ID | **None** | Head **590**, chord **2057**; review **e-16**, measure **m-5** |

The first column's head/stem coordinates are approximate visual observations,
not invented OMR object bounding boxes. The measure boundaries are explicit
archive stack/barline observations: barline inter 16 at `[1691,613,3,85]`,
barline inter 18 at `[1862,613,3,85]`. The source visibly places the open heads
between them. Staff lines are near y=614,634,655,675,696, and the source G clef
identifies the lower head as A4. Duration comes from the open head with stem,
**not** from the displayed meter or expected stack duration.

The following A is **not the G4 carrying “Loan”**. The source sequence is the
half-note chord at “đây.”, then the tied A4/C5 eighth chord immediately after the
barline, then G4 at “Loan”. Review event e-18 is that G4, onset 1/2, lyric l-10.
The surviving A4 e-16 is onset 0 in m-5 and has no lyric in exported XML.

## Real `.omr`: pixels, raw glyphs and recognized objects

Inspecting `sheet#1/sheet#1.xml` directly, rather than relying only on our parser:

```xml
<stack id="4" left="1692" right="1863" expected="1/2" duration="0"/>
<measure id="4">
  <right-barline><staff-barlines>2029</staff-barlines></right-barline>
</measure>
```

There are no head-chords, small-chords, voice entries or slots in this measure.
System 1 has 20 recognized heads, all `NOTEHEAD_BLACK`; **no NOTEHEAD_VOID head**
exists there. No recognized head, head-chord, stem or slur occupies the missing
half-note location. Thus the A half note, its recognized notehead, stem/duration
assignment and tie relations are absent from the persisted semantic graph.

The archive still contains the source pixels and lower-level glyph run tables:

| Raw glyph ID | Bounds `[left,top,width,height]` | Persisted interpretation |
| --- | --- | --- |
| 2246 | `[1757,636,18,97]` | Unclassified free SYMBOL fragment in the open-head/stem region |
| 2247 | `[1769,640,10,11]` | Unclassified free SYMBOL fragment near upper open head |
| 2248 | `[1772,657,15,19]` | Unclassified free SYMBOL fragment near lower open head |
| 2373 | `[1757,613,53,120]` | Unclassified composite glyph overlapping heads/stem/upper arc region |
| 2383 | `[1757,636,30,97]` | Unclassified composite glyph overlapping heads/stem region |
| 2100 | `[1790,659,130,28]` | Unclassified run-table glyph overlapping lower source tie arc |
| 2107 | `[1775,605,161,31]` | Unclassified run-table glyph overlapping upper source tie arc |
| 2120 | `[1775,610,30,25]` | Unclassified arc-region fragment |
| 2121 | `[1866,659,54,28]` | Unclassified arc-region fragment |

None of these IDs is referenced by a recognized inter's `glyph` attribute in
system 1. Spatial overlap supports retained pixel evidence; it does not provide
an assigned pitch, duration, voice, onset, tie identity or validated endpoint
relation. In particular glyph 2100 is **not** a persisted `SlurInter`/tie object.
Do not promote these fragments to notes through a musical plausibility rule.

The only recognized slurs in system 1 are **2093** and **2119**, both `tie=true`,
connecting head **644** to head **648** in measures 2→3. Their bounds are
`[1187,732,139,17]` and `[1193,654,119,21]`. They are unrelated to “đây.” and
must not be reused as evidence for the missing A tie. No slur-head relation
connects the surviving A head 590 to the missing-note region.

The target is well represented:

- Head **590**: pitch position 1, `NOTEHEAD_BLACK`, staff 1, glyph **589**,
  bounds `[1926,654,26,22]`, contextual grade .954.
- `590 → 1123`: head-stem relation; `2057 → 590`: containment.
- Stem **1123**: glyph **137**, bounds `[1950,577,4,81]`.
- `2057 → 1123`: chord-stem; `407 → 1123`: beam-stem.
- Chord **2057** also contains upper C5 head **549** (glyph **548**,
  bounds `[1931,633,23,20]`). Measure 5 owns chord 2057, voice 1 BEGIN at
  slot 1; stack slot time-offset 0.

## Export, recovery, review and rendering chain

| Stage | A4 half at “đây.” | Following A4 eighth | This A→A tie |
| --- | --- | --- | --- |
| Source raster | Present, open head + stem | Present | Present, visible lower arc |
| `.omr` recognized graph | **Absent**; raw pixels/fragments survive | Head 590 / chord 2057 | **Absent**; arc-region raw glyphs survive |
| Audiveris exported XML | **Absent**, measure 4 empty | Present, m5 first note | **Absent**: no tie or tied at either endpoint |
| Semantic recovery result | Not reconstructed; no candidate for it | Unchanged | Not reconstructed |
| Review projection | m-4 voices=[], actual_duration=0 | e-16, A4, duration=1/2, grace=false | ties=[], tie_target_id=null |
| Captured rendering clone | Measure 4 empty | Same A4/duration/type | Absent |
| OSMD input | No half note to engrave | Receives A4 eighth | No missing tie to engrave |

Exact exported fragments, effective divisions **2**:

```xml
<measure number="4" width="81"/>
<!-- First note of measure 5: -->
<note default-x="30">
  <pitch><step>A</step><octave>4</octave></pitch>
  <duration>1</duration><voice>1</voice><type>eighth</type>
  <stem default-y="18">up</stem><beam number="1">begin</beam>
</note>
```

No `<tie>` or `<notations><tied>` is present on this target; measure 4 has no
note on which a tie start could occur. Other XML ties exist (including duplicated
C4 ties at measures 2→3); their presence does not establish this missing A tie.

Export-copy, recognized and review XML are byte-identical, SHA-256
`d62ed3c645b9a0d8eae7612d15dae046e426ee963c7814abb033874c796e36ee`.
All three and the captured rendering clone share canonical XML SHA-256
`6c900da43d71c7396131591056b87400fca6af39c5fb156228dfaef20f947981`.
There is no later XML mutation explaining this loss. The clone differs only
in serialization bytes in this capture. No new OSMD runtime probe was performed;
the input is already insufficient, so renderer behavior cannot be the first loss.

## Semantic recovery and meter audit

The retained evidence sidecar has **zero candidates in source measure 4**,
matching the raw graph. It contains target head 590 in source measure 5.
The recovery report examined 51 heads, zero explicitly small heads, four
possibly-small heads. Its only decisions concern heads **543,572,576,582** in
measures 1–3, all ambiguous `PRESERVE_SMALL_DISPLAY_SIZE` proposals. None concerns
this half note or tie. `auto_recovered=0`; before/after rhythm maps are identical.

Code audit: `recovery/omr.py` extracts candidate notes from persisted `head`
inters and their containment/stem relationships; it does not recognize arbitrary
raw glyph fragments. `recovery/service.py` considers small/possibly-small heads
and supports corroborated simultaneous-note recovery or display-size preservation.
It is not a sequential half-note detector or a missing tie detector. Here the
missing head never entered its candidate stream, so it was **not discarded,
reinterpreted as grace, or suppressed by our meter/rhythm gate**.

Our recovery code does have rhythm gates on other automatic proposals, including
an unchanged-extent check and a valid-rhythm requirement for missing simultaneous
heads. Those general restrictions are not the executed cause here. This case
provides no evidence that a proposed A half note reached such a gate.

The retained rhythm ledger says m-4 expected=2, actual=0, no voices, with
`empty_measure` and `measure_underfilled` warnings. Review likewise labels m-4
UNDERFILLED/CONFLICT. The validator reports an omission; it does not insert rests,
change durations, delete notes, move ownership or reconstruct ties. m-5 has
expected=actual=2 in this untouched capture. These numbers are observations of
the recognized draft, not a source-fidelity acceptance criterion.

**Meter contribution:** none demonstrated in our recovery/projection/validation.
Whether Audiveris internally rejected an earlier interpretation because of
rhythm/meter is **unknown** without intermediate history/logs. Final graph alone
cannot distinguish an initial detection miss from later recognition cleanup.

## Small-note rule audit

The source crop also shows a **smaller upper C5 open half-note head** adjacent
to the A4, sharing the downward stem, and an upper visible arc to the following
C5 filled head. That upper half note is also absent from the recognized graph
and XML. This is collateral source evidence, not authorization to implement a
second correction in this trace.

Visual size and duration are independent. An open, stemmed small head remains
duration-bearing; source size does not justify `<grace/>`, zero duration or
removal. No secondary voice/part is assigned merely from size. The following C5
survives as e-17, duration 1/2, chord_member=true, grace=false, but display_size
normal. Its independent small appearance is not faithfully represented; that
size limitation is separate from losing the half-note chord and ties.

No grace-chord or small-chord inter exists in system 1. The captured provider
metadata says `small_heads_enabled=false`, `small_beams_enabled=false`,
`semantic_analysis_retained=false`; exported grace/cue counts are both zero.
The known earlier small-head-enabled runs documented in OMR.md are **different
runs** and do not explain this capture. Our importer derives grace from explicit
`<grace>`, independently of display size; recovery uses explicit grace/chord-grace
or matched XML grace evidence, not geometry alone. This trace shows recognition
omission, not an evidenced small→grace conversion.

## Classification and smallest evidence-based next fix

**A — Audiveris recognition loss.** The first semantic disappearance of the A4
half note and its tie is source → persisted `.omr` recognized graph. Raw raster
and glyph survival does not make this B (export loss). There is no evidence for
C, D or E, and no demonstrated multi-stage deletion supporting F. Recovery's
inability to reconstruct unrecognized source material is a coverage limit,
not evidence that it deleted a recognized note.

The smallest source-supported correction is an **explicit human-reviewed** A4
half-note insertion in existing source measure 4, duration 2 quarter units,
staff 1, with confirmed voice/onset and a tie start/stop to existing A4 e-16 in
measure 5. Keep the target's eighth duration and ownership. Such a correction
must remain source-backed even if validation subsequently reports unusual
rhythm. Do not infer onset/voice from meter capacity. A complete correction of
this source chord would additionally require explicit handling of the visible
C5 half note, its visual size and its separate source arc.

There is **not enough recognized semantic OMR evidence** for the current recovery
adapter to implement this as an automatic sequential-note/tie patch. A future
automatic fix would first need a validated source-pixel/recognition path yielding
actual hollow heads, stem/duration evidence and correctly bound tie endpoints;
then a bounded preservation patch could consume that evidence. Merely changing
our meter validator, enabling small-head switches globally, moving barlines or
relaxing rhythm gates cannot restore the missing source objects safely.

No fix, renderer change, recognition run, musical mutation, Phase 4F.2 work,
staging, commit or push occurred. Verification for this documentation-only trace:
raw XML/object and endpoint inspection, artifact hashes, canonical XML equality,
recovery before/after equality and `git diff --check`. Full suites were not rerun
because production code and tests were not changed.
