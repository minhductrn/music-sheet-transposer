# Phase 4F.1 real source-system investigation

Status: **real-artifact investigation complete; renderer fix implemented; repeat
real browser acceptance pending**.
Root-cause classification: **D — the rendering clone has the correct breaks, but
OSMD adds an intermediate system break**. The initial investigation made no
layout fix; the subsequently authorized renderer implementation is described below.
Phase 4F.2 has not started.

## Capture and scope

The reviewer performed one controlled fresh recognition of the real PDF
`/mnt/c/Users/dtran/Downloads/BaihatCN/CN25 Thuong Nien - Nam A/cungdemTinMung.pdf`.
The untouched new review is `-Z7DrCMLUEL4Y6YgbpMvZV3wJ9LsTEhi`, revision 1.
The previous expired session `UJXU8CXbicjhJoFLDocoWb6x-6qyCaf7` remains unavailable;
this fresh capture does not establish what happened in that earlier session.
These findings use real captured artifacts, not synthetic reproductions.

Artifacts are retained outside the repository at
`/tmp/music-sheet-transposer-phase4f1-cungdemtinmung/`:

- `source.pdf`, `source-metadata.json`: original source copy and identity.
- `recognized.omr`: original Audiveris archive, including `book.xml`,
  `sheet#1/sheet#1.xml`, and its source images.
- `audiveris-export.musicxml`, `recognition.musicxml`, `review.musicxml`.
- `review-id.txt`, `recognition-response.json`, `review-response.json`.
- `source-evidence.json`, `structural-score.json`, `source-system-mapping.json`.
- `rendering-clone.musicxml`, `renderer-loaded.json`, `renderer-rendered.json`:
  actual browser load/render capture, including OSMD options and graphical groups.
- Artifact hashes and `investigation-trace.json`: derived ledger, barlines and
  hashes for independent comparison.

The capture tapped development proxy responses and read the actual viewer's
render document and graphical systems. It did not modify authoritative bytes,
recognition settings, heuristics or requests. Temporary Vite/viewer hooks were
removed by restoring their exact pre-capture snapshots. No backend restart,
additional recognition, musical correction, staging, commit or push occurred.
`/tmp` is a local diagnostic location, not durable storage across cleanup/reboot.

## A–D: real archive, bounds, ownership and measure grouping

Audiveris 5.11.0 identifies one sheet/page, 2480 × 3508 sheet pixels, and **three
systems**. The archive and retained sidecar agree. Visual inspection of the archive's
`GRAY.png` source-page raster independently confirms three staff systems and
the same 5 / 5 / 7 source measure groups. The raster is also retained as
`source-audiveris-gray.png`. Sidecar diagnostics are empty.
Each system has physical part 1, mapped by the book to logical part 1, and one
staff. The archive does **not** provide a system bounding rectangle; sidecar
`structure.bounds` is null. The following bounds are explicitly **derived staff
line extents**, not system rectangles or full notation/lyric extents:

| System | Staff | X extent | Y extent | Source stack IDs / MusicXML measure numbers |
| --- | --- | --- | --- | --- |
| 1 | 1 | 361–2302 | 614–696 | 1–5 |
| 2 | 2 | 224–2302 | 973–1055 | 6–10 |
| 3 | 3 | 224–2302 | 1378–1461 | 11–17 |

All coordinates above are Audiveris sheet pixels. Staff line Y coordinates:
1: 614, 634, 655, 675, 696; 2: 973, 993, 1014, 1035, 1055;
3: 1378, 1399, 1420, 1440, 1461.

Source stacks retain these horizontal boundaries (left–right):

- System 1: 1 360–861; 2 861–1268; 3 1268–1692; 4 1692–1863;
  5 1863–2302.
- System 2: 6 223–717; 7 717–1241; 8 1241–1463; 9 1463–2018;
  10 2018–2302.
- System 3: 11 223–584; 12 584–766; 13 766–1330; 14 1330–1591;
  15 1591–1939; 16 1939–2138; 17 2138–2302.

Staff barline inter IDs in left-to-right archive order are:
1: 2, 4, 10, 16, 18, 20;
2: 22, 26, 30, 34, 36, 42, 44;
3: 46, 48, 52, 60, 62, 64, 68, 72, 74.
Double/final barline components explain why barline counts need not equal stack
count plus one. Exact inter bounds and staff references are in the retained
trace. No guessed barline-to-measure reconstruction was used.

## E–G: mapping and MusicXML clone

All 17 source stack IDs match the ordered MusicXML measure numbers 1–17, with
complete groups **1–5 / 6–10 / 11–17**. The review's actual layout origin is
`MUSICXML_PRINT`, mode `SOURCE_REVIEW`, `geometry_available: false`.
Its groups are `m-1`–`m-5`, `m-6`–`m-10`, `m-11`–`m-17`.
These agree with the archive; the importer did not use the OMR fallback here.
XML-print precedence remains a general implementation limitation, but it is not
the cause demonstrated by this capture.

Recognized XML has an initial `<print>` in measure 1 and
`<print new-system="yes">` in measures **6 and 11**. No `new-page="yes"`
instruction occurs. The actual rendering clone has exactly the same instructions;
there is no XML break before measure 5. Expected grouping is therefore three
systems on one page: **1–5 / 6–10 / 11–17**.

The response has no separate baseline XML: the recognition service supplies a
baseline only when recovered bytes differ from provider bytes. The diagnostic
`audiveris-export.musicxml` is therefore a labeled copy of the recognized bytes,
not a separately fetched export. Audiveris-export, recognition and review XML
are byte-identical, SHA-256:
`d62ed3c645b9a0d8eae7612d15dae046e426ee963c7814abb033874c796e36ee`.
The browser-serialized clone has a different byte hash because of XML
serialization. All four have the same canonical XML SHA-256:
`6c900da43d71c7396131591056b87400fca6af39c5fb156228dfaef20f947981`.
No musical or structural XML difference was introduced by the clone.

## H–I: actual OSMD configuration and rendered grouping

The captured OSMD 2.1.2 instance used a **1000px** engraving container:
`newSystemFromXML`, `newSystemFromNewPageInXML`, `newPageFromXML` all true;
`pageFormat: A4_P`; rules confirm XML system/page breaks enabled, page size
210 × 297, and `fixed_measures_per_system: 0`.
Fit/zoom is a later CSS transform and does not change this engraving width.

The real `GraphicSheet.MusicPages` contains one page and **four** systems:

| Rendered system | Source indices | MusicXML measure numbers | System position, OSMD units |
| --- | --- | --- | --- |
| 1 | 0–3 | 1–4 | (5, 17.75) |
| 2 | 4 | 5 | (5, 33.85) |
| 3 | 5–9 | 6–10 | (5, 49.05) |
| 4 | 10–16 | 11–17 | (5, 68.55) |

Source indices were resolved against the captured MusicXML, rather than using
OSMD's `MeasureNumber` directly: that field is 0–16 in this instance while XML
measure numbers are 1–17. The captured clone has no break at index 4, proving
that this intermediate break is introduced after XML loading by the renderer.

Installed `OSMDOptions.d.ts` documents that XML break options coexist with OSMD's
own layout and can produce a one-measure system. The installed layout code also
checks width capacity independently of explicit break flags. Enabling these flags
therefore preserves requested breaks without guaranteeing exact source ownership.
The observed extra break is consistent with that width-driven layout path.
The capture establishes D; it does not measure the precise minimum width needed
to keep the first five measures together, nor prove a particular replacement page
format or width would be sufficient.

## Concrete “Loan — tin — loan” ownership trace

The reviewer’s isolated line is exactly MusicXML measure **5**, zero-based source
index **4**, not an approximate multi-measure region. Captured lyric records
`l-10`, `l-11`, `l-12` attach “Loan”, “tin”, “loan” to events `e-18`, `e-19`,
`e-20` in structural measure `m-5`, part `p-1`.

The raw archive places stack 5 in sheet 1, **system 1**, physical part 1,
**staff 1**, horizontal interval 1863–2302. The source-page image places this
material at the end of its first system. The structural projection retains
`m-5` in the first XML-origin group `m-1`–`m-5`. Recognition, review XML and the
actual rendering clone all contain those three lyric texts in measure 5, with
**no print instruction in that measure**. The next explicit break is measure 6.
OSMD alone assigns source index 4 to its second graphical system, with no other
measure in that system.

This directly connects the browser observation to classification **D**. The large
unused horizontal space is an outcome of that isolated measure assignment;
the defect is source-system ownership fidelity, not a Fit/zoom acceptance issue.
No measure count was guessed and no musical correction or layout fix was made.

## Decision and remaining limits

A/B/C are not the demonstrated source of this grouping mismatch: archive groups,
review groups and clone instructions agree. **D is established by the real
rendered graph diverging from the unchanged clone.** No speculative width change,
fixed measure count, score-specific rule, automatic repair or recognition change
was applied. Raw system rectangles remain absent, but staff/stack ownership is
sufficient to establish the grouping and does not explain the extra rendered
system. This result does not claim recognition is musically correct.

The next layout task should preserve variable source groups while addressing
OSMD's additional breaks, with authoritative XML held fixed. Width/page experiments
and focused regressions should test that established renderer cause; fitting the
paper into the viewport must remain a separate display operation. No such fix or
experiment was performed in this investigation. Repeat layout browser acceptance
after a separately authorized fix; current source-layout acceptance still fails.

## Previous validation after diagnostic cleanup

Complete backend suite: **641 passed**, with two existing dependency warnings.
Complete frontend regression suite: **61 passed**. `npm run lint`, `npm run build`
and `git diff --check` passed. The existing OSMD bundle-size warning remains.
That diagnostic stage added no implementation or regression test; it established
the real cause and removed capture instrumentation. The follow-up fix is below.

## Phase 4F.1 renderer fix (acceptance pending)

The diagnostic above remains the real pre-fix capture. The renderer now retains
supported XML system/page break options and uses OSMD's supported `Endless` page
format, avoiding automatic paper-height pagination while retaining explicit page
breaks. These options alone do not disable width-driven intermediate systems.
No undocumented OSMD rule or fixed measures-per-system setting is used.

`frontend/src/utils/sourceEngraving.ts` accepts only complete, unique, sequential
measure partitions with compatible grouping across parts and a known layout
origin. Missing/ambiguous grouping uses responsive rendering without synthesized
OMR hints. The initial engraving width is the maximum sum of MusicXML measure
width hints across the trusted systems/parts, plus an engraving margin. A 160px
per-measure seed floor and 120px margin are capacity heuristics, not musical rules
or assertions about source pixels. When geometry is absent, grouping still seeds
capacity. The completed OSMD graphical systems are resolved through source-measure
identity and compared to the trusted variable partition. The renderer doubles
capacity only on mismatch, using at most eight renders and a 32760px width cap.
An unresolved mismatch is explicitly reported; exact layout is not silently
claimed. This bounded search need not find the minimum sufficient width.

The engraving container receives that width before each layout/render pass. Only
after the completed render is selection bound and the measured surface fitted.
Source-review pane resizing and Fit/manual zoom use CSS presentation transforms;
they do not request OSMD reflow. Responsive previews retain their resize path.
SVG-head selection uses semantic identity and DOM event targets, independent of
scaled pointer coordinates. Explicit OMR break hints remain clone-only. Uploaded
Blob/XML, structural projection, validation conflicts and musical events are not
written by the engraving search. In particular, the separate measure-5 2/4
acceptance item is not repaired or resolved by this layout change.

For the retained real XML, the derived initial surface is **1367px**; the
completed renderer graph determines whether further widening is needed. This
number is calculated from the variable groups, not hard-coded.

Expected real grouping remains **1–5 / 6–10 / 11–17**, with measure 5 in source
system 1. Automated boundary/graph doubles cover capacity search, variable explicit
breaks, narrow-pane Fit/zoom, ambiguous correspondence, clone preservation,
semantic selection under scaling and unchanged validation/musical fields. They
are not a new real OSMD/browser capture. Repeat real browser acceptance against
the retained XML/source artifacts, including explicit pages, selection and zoom.
Pixel spacing, source raster registration and complex part disagreement remain
outside this fix. Phase 4F.2 has not begun.

Renderer-fix validation: **641 backend tests passed** (two existing dependency
warnings), **72 frontend regressions passed**. The restricted backend run stalled
at the first FastAPI TestClient test; the complete run outside the sandbox passed
in 13.12 seconds. Lint, production build and `git diff --check` pass. The existing
OSMD bundle-size warning remains. `git status --short` confirms all work remains
uncommitted and includes the new renderer utility/regressions. No staging, commit,
push, recognition invocation or post-fix real browser acceptance was performed.


## Renderer-fix validation

Complete backend suite: **641 passed**, with two existing dependency warnings.
Complete frontend regressions: **73 passed**. `npm run lint`, `npm run build`,
and `git diff --check` passed; the existing bundle-size build warning remains.
No backend validation implementation changed in this renderer task. Existing
measure/voice overfill and verification conflicts remain authoritative, including
the separate real-score 2/4 acceptance question. No staging, commit or push.
