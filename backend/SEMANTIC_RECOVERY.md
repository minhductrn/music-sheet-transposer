# Phase 4D.2 — Audiveris semantic recovery

Audiveris remains the production/default provider. Recovery consumes its preserved
MusicXML and provider-specific `.omr` evidence. It does not reconstruct the score,
change the preservation transposer, use lyric text, or run SMT.

```text
PDF/image → normal Audiveris → baseline MusicXML + .omr
                                  ↓
                 evidence parsing and correlation
                                  ↓
           semantic classification + musical validation
                      /                     \
             HIGH confidence             uncertainty
             preservation patch          review candidate
                      \                     /
               existing review → verification → transposition
```

## Actual Audiveris 5.11.0 format

Both historical archives were inspected before implementation. Each is a ZIP with
`book.xml`, `sheet#1/`, `sheet#1/BINARY.png` and `sheet#1/sheet#1.xml` (about 600 KiB
of sheet XML). Book records contain versions, sheets/pages, logical parts and source
paths. Source paths are never followed or included in projected evidence.

Sheet XML stores picture dimensions, scale/interline, pages/systems, physical
parts/staves, measure stacks, a glyph index and a `sig` graph:

- `sig/inters/head` has numeric ID, glyph, shape, intrinsic/contextual grade,
  staff, pitch position and `bounds` (`x`, `y`, `w`, `h`). Pitch is staff position,
  not MIDI: in treble 0=B4, -1=C5, +1=A4. Clef and staff polylines corroborate it.
- `head-chord`, `small-chord`, `stem` and `beam` have separate IDs and geometry.
- `sig/relations/relation` has source/target IDs and typed children. Observed
  relations include containment (chord → head), head-stem, chord-stem, beam-stem,
  head-head, mirror, slur-head and no-exclusion.
- Physical staff IDs differ from part-local MusicXML staff numbers. Book page/
  system/part records establish logical-part mapping after PAGE.
- Measure stacks carry bounds and, after RHYTHMS, whole-note durations and slots.
  Measure voice/slot entries link BEGIN chords to voice IDs and time offsets.
  Evidence converts these offsets to exact quarter beats.

Historical baseline: 53 head interpretations, no explicit small heads. Historical
small-head run: four actual `head shape="NOTEHEAD_BLACK_SMALL"` interpretations
and two small-chords. Two other matching `head-seed` records are template settings,
not notes. MusicXML has no shared HeadInter IDs. Archive IDs cannot correlate
different runs or exported notes solely by sequential index.

The [official SmallChordInter source](https://github.com/Audiveris/audiveris/blob/5.11.0/app/src/main/java/org/audiveris/omr/sig/inter/SmallChordInter.java)
distinguishes general small-head chords from dedicated GraceChordInter structures.
SmallChord alone is not sufficient grace evidence. The
[official CLI source](https://github.com/Audiveris/audiveris/blob/5.11.0/app/src/main/java/org/audiveris/omr/CLI.java)
supports a target step independently of full transcription/export.

## Evidence and safety

`app/music/recovery/models.py` defines a separate sheet/system/measure/candidate
projection. Candidates retain ID, bounds/center, staff/position, written step/octave,
explicit linked accidental, visual size/shape, chord/stem/beam references, optional
voice/onset, grade, relationships and hash/member/ID provenance. These are evidence,
not musical truth. Normal-template width discrepancies become `possibly_small`.

No files are extracted. Shared ZIP checks reject traversal, duplicates, symlinks,
encryption, unsupported compression and conflicting paths. All members' CRC/local
headers are verified, including unused images. XML rejects DTDs/entities and bounds
depth/nodes across book/sheets. Unknown elements are tolerated; relationship names
are retained. Dangling links and unfamiliar versions reduce confidence.

Defaults: 20 MiB combined retained artifacts, 64 MiB expanded OMR, 128 ZIP members,
200,000 evidence XML nodes, depth 64 and 128 candidates. MusicXML uses existing
review byte/node limits. Parser/optional projection failure retains valid baseline
XML with structured diagnostics. Evidence reports count toward review memory quotas.

## Correlation and classification

Correlation combines logical part, measure, part-local staff, written pitch and
available voice/onset. It compares physical x with MusicXML default-x using measure
bounds and interline/10 scaling; measure width must corroborate that scale. A
unique geometric match, supported staff position and contextual grade ≥0.8 yields
HIGH. Missing coordinates, weak evidence or multiple matches remain AMBIGUOUS;
absent pitches are UNMATCHED. EXACT is reserved for a future verified shared identity,
not invented from coincidentally equal numeric IDs. Grades are not accuracy percentages.

Visual size and rhythmic semantics are independent:

- GRACE requires explicit grace-chord/relation or exported grace semantics.
- CUE requires exported `<cue>` semantics; visual font/type reduction does not suffice.
- SIMULTANEOUS_VARIANT requires one shared chord/stem, aligned heads, compatible
  staff/voice/onset and a uniquely correlated duration-bearing non-grace/non-cue
  anchor. Peers must agree on chord, onset, duration, voice and staff.
- UNCERTAIN covers absent/conflicting relationships or insufficient context.

Automatic changes require explicit small-head shape, grade ≥0.8, corroborated pitch,
timing and format/registration. Geometry-only size hints always require review.
Contradictory baseline/analysis sizes never automatically shrink an existing note.
Spelling uses clef/staff position, linked accidental, inherited MusicXML key and
applicable prior staff/pitch accidentals. Conflicting accidentals, unsupported key/
clef context, mid-measure keys and octave shifts require review. No lyric or benchmark
pitch is used by recovery.

## Rhythm and patches

The existing review projection interprets ordered divisions, meter, notes/rests,
grace, chords, voices, backup and forward with exact fractions. Added validation
detects under/overfilled measures, impossible durations, broken chords and invalid
voice overlap. Partial voice coverage is a warning; implicit pickups are respected.
Underfill alone never proposes a missing note. Additions require valid measure
rhythm; display-only changes can preserve existing rhythm despite underfill warnings.

Implemented operations: ADD_SIMULTANEOUS_NOTE and PRESERVE_SMALL_DISPLAY_SIZE.
Standalone RESTORE_MISSING_NOTE and broad pitch/rhythm corrections are not inferred.
Missing heads with slur/tie/mirror complications require review.

The existing patcher inserts a member after the original chord group, copying only
justified duration/type/dots/tuplet/stem and staff/voice. It preserves written pitch,
alter and octave. `<type size="cue">` and `<notehead font-size="small">` encode
visual reduction without inserting grace or cue timing. Unrelated lyrics, harmony,
directions, layout, ties, slurs, articulations, comments and unsupported XML survive.
Changed XML is serialized by the review preservation tree: formatting, DTD declarations
and namespace prefixes are not byte-identical. Unchanged documents return verbatim.

Each clone patch is revalidated; new errors, changed extent or byte/node overflow
cause rollback. Duplicate evidence/pitches cannot cause duplicate additions.
AUTO_RECOVERED records modifications; REVIEW_REQUIRED exposes uncertainty without
patching; NO_RECOVERY means no applicable change. Human source comparison remains required.

## Execution and existing review

`AUDIVERIS_SEMANTIC_RECOVERY_ENABLED=true` enables interpretation by default.
Normal recognition keeps smallHeads/smallBeams=false, existing OCR settings, and
one Audiveris process. `AUDIVERIS_SEMANTIC_ANALYSIS_ENABLED=false` is the default.
An explicit opt-in runs a separate `-batch -step LINKS -save` pass with small heads/
beams enabled, isolated output/preferences and no transcription/export. Its timeout
defaults to 120 seconds, with process-group termination. Combined artifacts remain
bounded; failure retains baseline output. Both passes share the existing job slot.

Real LINKS archives lack logical-part mappings and voice/slot timing. Registration
requires identical binary page-image hashes, dimensions, scale and uniquely matching
system/physical-part/staff/measure geometry. Only logical-part/measure mapping is
borrowed: head shapes, pitches, graph IDs and rhythm are not copied. Different source
pixels, unavailable baseline evidence or incomplete registration prevent automatic
recovery from analysis.

The extra JVM/image-analysis pass costs substantial time; it is never enabled globally
merely to expose small heads. Normal archives provide geometry hints but insufficient
explicit missing-head evidence here. The opt-in job bound is normal timeout plus
analysis timeout; per-pass performance was not separately measured.

Recognition JSON carries the report, optional analysis archive and untouched baseline
XML when changed. The frontend passes baseline and archives to the existing review's
optional bounded `omr`/`analysis_omr` multipart fields. Candidates show confidence,
source boxes and related-event selection in the existing inspector. Original XML
is retained and automatic changes can be undone. Evidence is an import-time record;
manual edits are not silently reevaluated. Current rhythm errors block verification.
OSMD's existing mixed-size chord rendering limitation remains; XML semantics do not
guarantee an identical preview. No frontend layout/CSS redesign was introduced.

## Real Cùng Đem Tin Mừng benchmark, 2026-10-03

Fresh normal VOCAL_SONG recognition plus a LINKS pass completed in **55.4 seconds**
on this WSL host, with unchanged vie+eng OCR. Saved archives were reevaluated offline
after registration was added; Audiveris was not rerun. PDF SHA-256:
`30df9a6988ecc7752c2a89dcd84bcc87b44259b88803e2636f817ede7b15b81a`.

| Metric | Fresh baseline | Corrected |
|---|---:|---:|
| Pitched notes | 51 | 53 |
| Measures | 17 | 17 |
| Chord groups | 9 | 11 |
| Ties | 16 | 16 |
| Grace notes | 0 | 0 |
| Explicit small-display notes | 0 | 2 |

Baseline evidence: 51 heads, zero explicit small heads, four geometry hints. LINKS:
53 heads, four explicit small heads, four geometry hints. Twelve candidates across
both sources yielded **two auto recoveries and ten review candidates**. B-flat4 is
added beside G4 in measures 2 and 6 using the original baseline quarter-note timing.

| Original location | Outcome |
|---|---|
| “ta”: measure 1, onset 1/2 quarter beats | A4+C5 survive, voice 1/staff 1, duration 1/2 each, non-grace. C5 remains regular-size; size requires review. |
| “cùng”: measure 1, onset 1 quarter beat | F4+A4 survive, voice 1/staff 1, duration 1/2 each, non-grace. A4 remains regular-size; size requires review. |
| “đem”: measure 2, onset 0 | Regular G4 retained; small B-flat4 added, voice 1/staff 1, duration 1 each, same chord/onset, non-grace. Staff position 0 and the one-flat key establish B-flat4. |

These locations were checked against the retained original binary page. Exact “cùng”/
“đem” strings were not exported by OCR, so geometry/musical location established them;
OCR text was not repaired. Analysis misclassified regular G4 as small, so it was not
shrunk. No original XML event was removed or retimed; existing rhythm warnings remain.
This is partial recovery, not perfect OMR. Other pitch/notation/lyric errors can remain.
Matching a historical note count does not prove accuracy.

Raw real artifacts: `/tmp/phase4d2-cungdem-real/`. Final offline report/corrected XML:
`/tmp/phase4d2-cungdem-recovered/`. These are local temporary development artifacts,
not repository fixtures. The independent Audiveris-only CLI writes bounded baseline,
evidence, decisions, corrected metrics and lyric locations; it never invokes SMT:

```bash
# From backend, with a new output directory.
env -u PYTHONPATH AUDIVERIS_EXECUTABLE=/opt/audiveris/bin/Audiveris \
  AUDIVERIS_TESSDATA_PATH="$HOME/.config/AudiverisLtd/audiveris/tessdata" \
  .venv/bin/python -m app.music.recovery.benchmark \
  --source '/path/to/score.pdf' --output /tmp/new-semantic-benchmark --analysis-pass
```

## Validation and limits

Tests use synthetic JAXB-shaped ZIPs and structural XML assertions; installed
Audiveris is unnecessary. They cover archive/XML safety, unknown elements, graph/size
extraction, ambiguous correlation, source registration, spelling, grace/cue distinction,
timing, preservation, idempotence, review/undo and optional subprocess failures. Run
backend pytest, frontend lint/build and git diff --check. All existing tests remain.

Other Audiveris versions are review-only. Unusual clefs/staves, nontraditional keys,
cross-system accidental/tie inheritance, reordered measure labels, ambiguous parts
and complex missing-note notation are not automatically recovered. Coordinates rely
on unchanged export layout/image scale. There is no source-size classifier, full-schema
validator or guarantee of complete OMR. SMT remains EXPERIMENTAL / BENCHMARK ONLY,
disabled by default, with its implementation and dependency isolation unchanged.
