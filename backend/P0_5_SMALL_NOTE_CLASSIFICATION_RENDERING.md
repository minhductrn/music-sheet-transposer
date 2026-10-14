# P0.5 — Small note classification and rendering

2026-10-10, America/New_York. Evidence-driven diagnostic outcome with regression coverage. **Automatic classification correction stopped at the evidence boundary; no production correction implemented. Browser visual acceptance: NOT VERIFIED.**

## 1. Root cause and decision

Read the P0.3 real benchmark evidence audit, Music Semantics/Voice Mapping audit and Small Note Regression RCA before investigation. Their temporary captures are no longer present, so a fresh run used the installed `/opt/audiveris/bin/Audiveris` through the existing recognition service/provider. No recognition constants or persistent settings changed. The resolved existing profile retains smallHeads/smallBeams disabled; optional analysis remains disabled.

The source upper heads at “ta” and “cùng” are visibly smaller in the native source raster. Both already have ordinary `NOTEHEAD_BLACK` classifications in the native graph and no size hints in native MusicXML. **The earliest observed misclassification is Audiveris graph classification.** Recovery extracts their narrow bounds as `possibly_small`, produces ambiguous proposals and deliberately leaves their display unchanged. This is an evidence-confidence limitation, not demonstrated note loss or a serialization defect.

There is no reproducible evidence that promoting all narrow heads, changing the 0.88 threshold, assigning voice 2, using stem direction or lyric verse would reliably separate small and normal notes. These rules would risk normal notes. Per the task's stop condition, no speculative automatic rule was introduced. Existing explicit per-note size editing is the safe supported correction path; diagnostic corrections below were applied only in isolated memory sessions, not to user sessions or benchmark files.

## 2. Source and stage evidence

Source: `/mnt/c/Users/dtran/Downloads/BaihatCN/CN25 Thuong Nien - Nam A/cungdemTinMung.pdf`.

SHA-256: `30df9a6988ecc7752c2a89dcd84bcc87b44259b88803e2636f817ede7b15b81a` (35,886 bytes), matching P0.3. The source was read only. The OMR archive contains the 2480 × 3508 source raster. Its pickup/ta/cùng crop was visually inspected. Dimensions below are the graph's source-raster bounding boxes, not independent pixel segmentation measurements.

| Source note | Measure / staff / voice | Pitch | Onset / duration, quarter beats | Head ID; raster bounds (x,y,w,h) | Source appearance | Native graph / project evidence | Native, recovered and review size |
|---|---|---|---|---|---|---|---|
| ta lower | 1 / 1 / 1 | A4 | 1/2 / 1/2 | 570; 673,654,26,22 | normal | NOTEHEAD_BLACK / normal | normal, no size hint |
| ta upper | 1 / 1 / 1 | C5 | 1/2 / 1/2 | 543; 678,633,22,20 | small | NOTEHEAD_BLACK / possibly_small | normal, no size hint |
| cùng lower | 1 / 1 / 1 | F4 | 1 / 1/2 | 632; 776,675,26,22 | normal | NOTEHEAD_BLACK / normal | normal, no size hint |
| cùng upper | 1 / 1 / 1 | A4 | 1 / 1/2 | 572; 781,654,22,22 | small | NOTEHEAD_BLACK / possibly_small | normal, no size hint |

Both upper events are existing chord members, e-3 and e-5. Lower events are e-2 and e-4. All remain duration-bearing and non-grace. Pickup C5 in explicit voice 2 has a normal 26 × 22 box, further illustrating that voice does not determine size.

Fresh native graph: 51 extracted heads. Native XML, recognition recovery output and isolated ReviewService output each retain 51 pitched notes, 9 chord members, 52 lyric records, voices 1/2, zero grace and zero semantic cue notes. All three XML stages have identical bytes:

`ce6213fdc50f3c9646a4e5eded76caaf4e041c30097b2f2bcafcce241aa9af1e`.

This is a fresh native export, not the old P0.3 artifact; its different export hash is not a claim of musical change. No historical native replay was attempted.

## 3. Before/after diagnostic correction and OSMD

The installed OSMD 2.1.2 `MusicSheetReader` was invoked directly using a minimal XML-reader interface over parsed XML. This executes the actual source parser, not layout, VexFlow drawing or browser SVG. Measure numbering below uses XML order; OSMD fractions are whole-note units (e.g. duration 1/8 = 1/2 quarter beat).

| Input | Pitched notes | ta/cùng upper size hints | OSMD upper IsCueNote / IsGraceNote | Timing/pitch/voice |
|---|---:|---|---|---|
| Native export | 51 | absent | false / false | baseline |
| Recovery output | 51 | absent | false / false | unchanged |
| Review output | 51 | absent | false / false | unchanged |
| Isolated explicit small edits | 51 | type size="cue" + notehead font-size="small" | true / false | unchanged |
| Existing Working Score adapter-equivalent view | 51 | type size removed in view clone; small head hint retained | false / false | unchanged |

Explicit size edits serialize standard MusicXML visual attributes without adding `<cue/>` or `<grace/>`. Canonical `display_size` correctly reparses as small with ordinary duration. OSMD conflates visual `type@size=cue` with its cue flag, as P0.3 reported; this is a downstream interpretation limitation independent of the native classification defect.

Existing `scoreRenderer.reviewDocument` normalizes this specific ordinary small-note spelling in a view-only clone. Existing `scoreInteraction.bindScore` scales uniquely mapped heads by 0.65. This task adds no overlay or rendering transformation. The normalizer and binding are gated by an onSelect callback in MusicSheetViewer, so read-only views can follow another path. No browser observation demonstrates missing SVG heads or proves curve/selection alignment. Blindly broadening the normalizer without also validating the mapped display path could yield normal-sized heads in those views.

Smallest rendering follow-up: use the existing ordinary rhythmic adapter and existing mapped display handling consistently in score-backed viewing modes, after real SVG verification of mixed heads, ties, selection, resizing and zoom. Preserve true cue/grace handling and authoritative XML. Do not introduce a second drawing overlay.

## 4. Implementation and affected files

No production source changed. In particular, P0.4 chord validation, recognition thresholds/profiles, recovery logic, XML serializer and renderer remain untouched.

Added:

- `backend/tests/music/fixtures/p05_benchmark_raw.musicxml`: untouched fresh native export, with the hash above. Original source PDF and OMR are not rewritten. This durable fixture preserves the independently observed benchmark input rather than manufacturing a classifier's expected output.
- `backend/tests/test_p05_small_note_preservation.py`: five regressions, four using the real export and one using the existing explicitly labelled native-small synthetic graph.
- This report.

The benchmark tests apply source-confirmed explicit size corrections at ta, cùng, both together and the existing upper tied A4 at measure 8. All 51 event pitches, exact durations/onsets, voices, staffs, chord membership, lyric references, ties, cue/grace flags and all unselected sizes remain unchanged. A raw XML tree comparison masking only intended size attributes/nodes verifies all other notation, including independent m8→m9 tie endpoints, slurs and lyrics. Undo returns original bytes; Redo returns corrected bytes; subsequent normal-size editing works. The synthetic native-small graph verifies normal A4 and small C5 stay distinct through recovery, serialization and review at the same onset without grace/cue conversion.

These tests validate explicit editing and supported size preservation; they do **not** claim automatic classification of ordinary graph shapes succeeds. Source labels come from the image/audit, and synthetic explicit shape labels come from an existing hand-authored graph fixture, not from the heuristic under test.

## 5. Validation results

Focused backend first, from `backend/`:

`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_p05_small_note_preservation.py tests/test_chord_duration_validation.py tests/test_semantic_recovery.py -q`

**66 passed, 0 failed**, including the unchanged P0.4 regressions.

Complete backend, exactly the requested command:

`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q`

**732 passed, 0 failed**, two FastAPI/Starlette deprecation warnings, 27.41 seconds. The five new cases account for the increase from the accepted 727 baseline. FastAPI-containing runs executed outside the sandbox, following the established TestClient execution requirement. An initial focused invocation from the repository root failed collection because `app` was outside Python's import path; rerunning from backend resolved it.

Frontend:

`node --test frontend/tests/score-renderer.test.mjs frontend/tests/visual-review.test.mjs frontend/tests/score-ties.test.mjs frontend/tests/review-lifecycle.test.mjs frontend/tests/source-engraving.test.mjs`

**5 test files passed, 0 failed** (Node reports these as five top-level tests). These cover mocked renderer/mapping, tie handling, review lifecycle and source grouping, not browser visual fidelity.

`npm run build` from frontend: **passed** TypeScript and Vite production build. Existing large-chunk warning remains (1,625.16 kB main JS); no build failure.

Actual OSMD reader probes: **51 pitched notes in each of five variants**, no parsed pitch/duration/onset/voice changes. Project structural/timing validation of raw, recovered, review and explicitly corrected XML found **no errors** and the same three existing warnings (two duration mismatches and an empty measure). This validation is not full XSD validation or source-accuracy acceptance.

`git diff --check`: passed.

## 6. Remaining limitations and acceptance

**Browser acceptance: NOT VERIFIED.** No local browser executable or installed browser automation package was found in the inspected Linux environment. No SVG screenshot, head bounding-box comparison, tie-curve spacing, selection alignment or zoom acceptance was obtained. XML/unit/parser results must not be described as visual acceptance.

Classification remains unresolved for ordinary-shaped source-small heads. Reliable automatic correction needs independently labelled source evidence and representative normal/small examples, or trustworthy explicit native shape evidence. Two visually confirmed heads are insufficient to validate a general geometry rule. Normal heads and ambiguous evidence remain unchanged. The existing manual size path is validated; no live score has been corrected automatically.

Fresh diagnostic artifacts/scripts are in `/tmp/p05-small-note/`: source copy, raw OMR, native rasters/crop, raw/recovered/review XML, extracted head/correlation data, native metadata, explicitly corrected XML, OSMD XML-reader inputs/results and the reproduction scripts. These temporary artifacts can disappear at OS cleanup. The repository retains the unmodified raw XML fixture and the source/hash/correspondences in this report.

Existing uncommitted work was preserved; no reset, restore, clean, stash, stage, commit or push occurred. Build output is generated frontend output. No benchmark source file or live user session was changed.

## 7. Recommendation for P0.6

Keep missing upper Mừng/Trời notes separate from size-only corrections. The P0.3 raw-graph absence and wrong doubled lower tie associations require source-grounded endpoint/event evidence. Capture source regions and native artifacts, distinguish an absent recognized head from a retained normal-sized head, and require explicit trusted pitch/timing/ownership choices. Do not infer missing notes from lyric verses, meter, chord membership or the small-size flag, and do not globally remove duplicate-looking original ties. This task did not add any missing notes or modify those ties.
