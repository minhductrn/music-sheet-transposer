# P0.3 — real benchmark evidence audit

Diagnostic only, 2026-10-06. No fix implemented. Builds on [the regression RCA](P0_3_SMALL_NOTE_REGRESSION_RCA.md); its historical investigations are not repeated here.

## Findings

For this fresh run, **the first demonstrated missing-note stage is the original Audiveris graph**, including both upper small G4 notes across “Mừng” and both across “Trời”. At “ta” and “cùng”, the upper small notes are present, but their recognized graph shapes already identify them as ordinary heads. Their geometry survives; their intended small display classification does not.

All 51 recognized graph heads reach original MusicXML, recovery, final review, the canonical model, and OSMD's source reader. Raw, recovered, and final XML are byte-identical. There is no demonstrated application note deletion, accidental grace conversion, chord collapse, serialization omission, or OSMD source-reader loss in this run. Actual browser SVG visibility and curve geometry were not measured; this is not browser acceptance.

The user's previous successful normal-size recognition remains important evidence. This run establishes today's failing stages, **not the historical cause of that regression**. The older affected session, before/after raw artifacts, running server settings, and bundle identity are unavailable. Identical-input historical application replay below does not reproduce a downstream regression; it cannot rule out different native settings, inputs, or an older rendering path in that session.

## Reproduction and artifact provenance

Verified source: `/mnt/c/Users/dtran/Downloads/BaihatCN/CN25 Thuong Nien - Nam A/cungdemTinMung.pdf`.

- One page, 35,886 bytes, 595.22 × 842 PDF points.
- SHA-256: `30df9a6988ecc7752c2a89dcd84bcc87b44259b88803e2636f817ede7b15b81a`.
- Audiveris 5.11.0, commit `9e1e55cd2746037d059345881c53e6a6754bffbd`; Java 25.0.3+9-LTS; Tesseract 5.5.2.
- Existing launcher discovered at `/opt/audiveris/bin/Audiveris`. The earlier RCA's PATH lookup did not find it. A temporary `audiveris` symlink and subprocess PATH resolved the existing configured name; no engine configuration or persistent environment was changed.
- Actual existing recognition service/provider, default resolved Settings: VOCAL_SONG, Synthetic, vie+eng, smallHeads=false, smallBeams=false, semantic recovery enabled, optional analysis disabled. Full constants and invocation are captured, not reconstructed guesses.
- The sandbox attempt exited before producing a score. Its initialization log is retained at `/tmp/p03-real-benchmark-audit.IiFOlU/`; it is not a recognition accuracy result. The unchanged native invocation succeeded outside that sandbox in 23.72 seconds.
- A new isolated MemoryReviewStore/ReviewService received the production frontend handoff (`baseline_musicxml or musicxml`, PDF, OMR, evidence OMR). No existing user session was read or overwritten. Final isolated revision: 1.

Successful diagnostic directory: `/tmp/p03-real-benchmark-audit-run2.Azd3Sg/`. Temporary artifacts are not durable repository fixtures; retain them before OS cleanup if needed.

| Artifact | Evidence |
|---|---|
| `source.pdf` | Exact source copy |
| `rasters/sheet#1_GRAY.png`, `sheet#1_BINARY.png` | Native source-page rasters, 2480 × 3508; the grayscale raster was visually inspected |
| `audiveris.omr` | Original native graph, before application extraction/recovery |
| `omr-xml/`, `omr-members.json` | Unpacked original graph/book XML and archive inventory |
| `audiveris-original.mxl`, `audiveris-original.musicxml` | Untouched native export and extracted XML |
| `post-recovery.musicxml` | Actual recognition-service recovery output |
| `final-review.musicxml`, `final-review.json` | Isolated review-service output and canonical projection |
| `run.py`, `run-config.json`, `provider-command.json`, `logs/`, `completion.json` | Reproduction settings, command, native logs, completion |
| `stage-trace.json`, `stage-counts.json`, `events.txt` | Every note's identity, pitch, exact rational timing, voice/staff, size, grace, lyrics, XML ties, and correlated graph heads |
| `graph-counts.json`, `extracted-evidence.json`, `correlations.json` | Raw/extracted head accounting and correspondence |
| `raw-tie-endpoints.json`, `raw-inters-in-source-regions.json`, `crops/` | Original tie endpoints, absence checks, source crops |
| `historical-real-replay.json`, `replay.py` | Same real XML/OMR through historical application code |
| `osmd-inputs.json`, `osmd-probe.cjs`, `osmd-result.json` | Actual OSMD source reader probe; no browser/SVG |
| `artifact-manifest.json`, `workspace-before.json`, `workspace-preservation.json` | Artifact checksums and preservation audit |

Original OMR SHA-256: `9fba6efe85d2ee7c1dda11469afae8c2c9e486b214daffd115af313a29bec678`.

All three XML stages SHA-256: `4ba12b25b9d42254c3fa52782c23b53526471aca09e7ee836c01258428289299`.

## Per-measure stage comparison

Every row below has the same raw XML, recovered XML, final XML, canonical, and OSMD pitched-note count. Graph evidence has the same per-measure counts. All exported notes are normal-sized, duration-bearing, non-grace, staff 1. “Simultaneous” counts events sharing exact measure/onset with another event, including across voices; it does not count unique onset groups. “Possible” is only a geometric evidence hint, not an exported small classification.

| Measure | Graph / each downstream stage | Voice counts | Simultaneous / sequential events | Possible-small graph hints |
|---|---:|---|---|---:|
| 1 | 6 | v1=5, v2=1 | 6 / 0 | 2 |
| 2 | 4 | v1=4 | 2 / 2 | 1 |
| 3 | 5 | v1=5 | 2 / 3 | 1 |
| 4 | 0 | none | 0 / 0 | 0 |
| 5 | 5 | v1=5 | 2 / 3 | 0 |
| 6 | 4 | v1=4 | 2 / 2 | 0 |
| 7 | 5 | v1=5 | 2 / 3 | 0 |
| 8 | 2 | v1=2 | 2 / 0 | 0 |
| 9 | 5 | v1=5 | 2 / 3 | 0 |
| 10 | 2 | v1=2 | 0 / 2 | 0 |
| 11 | 2 | v1=2 | 0 / 2 | 0 |
| 12 | 1 | v1=1 | 0 / 1 | 0 |
| 13 | 4 | v1=4 | 0 / 4 | 0 |
| 14 | 2 | v1=2 | 0 / 2 | 0 |
| 15 | 2 | v1=2 | 0 / 2 | 0 |
| 16 | 1 | v1=1 | 0 / 1 | 0 |
| 17 | 1 | v1=1 | 0 / 1 | 0 |

Totals: 51 graph HeadInter objects; 51 extracted evidence notes; 51 pitched notes at each downstream stage; 47 NOTEHEAD_BLACK and 4 NOTEHEAD_VOID; zero explicit small shapes, zero small XML notes, zero cue/grace notes, nine XML chord members. Four geometric candidates were REVIEW_REQUIRED/AMBIGUOUS; none was automatically applied. Measure 4 is empty, not silently replaced with a rest. Structural timing warnings for measures 1, 4, 17 remain advisory; nothing was composed to fill them.

## Targeted source-to-event traces

Timing is in quarter-note units, relative to the measure. Source sizes and pitches below were read from the native raster, not inferred from lyric text or meter. Missing-note timings describe the visible shared stem/rhythmic position; no canonical events were invented. A shared stem supports a simultaneous group but does not by itself assign a numeric voice. Numeric voice/staff in the table comes from exported semantics. All surviving rows have identical properties through XML, recovery, final review, and OSMD source parsing.

| Source location | Source note | Raw graph / canonical identity | Onset; duration; exported voice/staff | First discrepancy |
|---|---|---|---|---|
| m1 “ta” lower | A4 normal, eighth | head 570 / e-2 | 1/2; 1/2; v1/s1 | None observed |
| m1 “ta” upper | C5 small, eighth, same stem | head 543 / e-3; ordinary BLACK shape, 22×20 | 1/2; 1/2; v1/s1 | Graph normal classification; XML normal; possible-small recovery deferred |
| m1 “cùng” lower | F4 normal, eighth | head 632 / e-4 | 1; 1/2; v1/s1 | None observed |
| m1 “cùng” upper | A4 small, eighth, same stem | head 572 / e-5; ordinary BLACK shape, 22×22 | 1; 1/2; v1/s1 | Graph normal classification; XML normal; possible-small recovery deferred |
| m2 “Mừng” lower | C4 normal, eighth, tied onward | head 644 / e-10 | 3/2; 1/2; v1/s1 | Extra upper curve wrongly attached to this pair in raw graph |
| m2 “Mừng” upper | G4 small, eighth, tied onward | No HeadInter / no event | Shared 3/2; 1/2; numeric voice unavailable | Already absent in original graph |
| m3 following lower | C4 normal, eighth, tie stop | head 648 / e-11 | 0; 1/2; v1/s1 | Receives both raw tie stops |
| m3 following upper | G4 small, eighth, tie stop | No HeadInter / no event | Shared 0; 1/2; numeric voice unavailable | Already absent in original graph |
| m6 “Trời” lower | C4 normal, eighth, tied onward | head 751 / e-24 | 3/2; 1/2; v1/s1 | Extra upper curve wrongly attached to this pair in raw graph |
| m6 “Trời” upper | G4 small, eighth, tied onward | No HeadInter / no event | Shared 3/2; 1/2; numeric voice unavailable | Already absent in original graph |
| m7 following lower | C4 normal, eighth, tie stop | head 755 / e-25 | 0; 1/2; v1/s1 | Receives both raw tie stops |
| m7 following upper | G4 small, eighth, tie stop | No HeadInter / no event | Shared 0; 1/2; numeric voice unavailable | Already absent in original graph |

These source groups are duration-bearing, not grace notes. No grace interpretation was introduced. “ta” and “cùng” have no ties. Source lyric OCR spelling differs in places (for example “cũng”); locations were verified against the image.

Original graph absence was checked directly, not merely through the recovery parser: the upper Mừng rectangles intersect a stem/chord/upper slur but no head; the upper Trời rectangles likewise contain no head. `raw-inters-in-source-regions.json` records exact rectangles and intersecting Inter objects. All original graph heads were extracted, excluding an evidence-parser head filtering explanation here.

Other visually checked mixed-size groups corroborate both behaviors:

| Measure/group | Source observation | Current result / first failing stage |
|---|---|---|
| 2 “đem” | G4 normal + B♭4 small | G4 e-7 survives; upper absent in graph |
| 2 “Tin” | F4 normal + A4 small | e-8/e-9 both survive; upper head 576 classified normal, possible-small review deferred |
| 3 “đi” | F4 normal + A4 small | e-12/e-13 both survive; upper head 582 classified normal, possible-small review deferred |
| 3 “khắp”, “đó” | G4/B♭4 and B♭4/D5 normal/small pairs | Lower e-14/e-15 survive; upper heads absent in graph |
| 4 “đây.” | A4 normal + C5 small open half-note group | Both absent in original graph; no head/chord/voice/slot in that measure |
| 5 initial continuation | A4 normal + C5 small | e-16/e-17 survive, both classified/exported normal |
| 5 subsequent three G4 groups | G4 normal + B♭4 small | e-18/e-19/e-20 survive; upper heads absent in graph |
| 6 initial “tin” | G4 normal + B♭4 small | e-21 survives; upper absent in graph |
| 6 “Chúa” | E4 normal + A4 small | e-22/e-23 survive; upper 23-pixel width stays normal |
| 7 “yêu”, “thương” | G4 normal + B♭4 small | e-26/e-27 survive; upper heads absent in graph |
| 7 “loài” | F4 normal + A4 small | e-28/e-29 survive; upper 23-pixel width stays normal |
| 8 “người.” | F4 normal + A4 small, open half notes | e-30/e-31 survive, both normal; upper VOID 24×20 not flagged by BLACK-only geometry heuristic |
| 9 opening continuation | F4 normal + A4 small | e-32/e-33 survive, both normal; independent ties from m8 survive |

The missing normal open head in measure 4 establishes that omissions are not exclusively small notes. These source observations are diagnostic annotations, not authorized score corrections or proposed automatic rhythm filling.

## Later Voice 1 / Voice 2 examination

The visible “1.” and “2.” in the later sections label **lyric verses**, not two independently proven musical voices. Measures 9–17 export voice 1 only, with lyric number 1 and 2 attached to the melody; do not create voice 2 from verse labels. Measure 9's opening small A4 remains a simultaneous chord member above F4 but appears normal.

Actual exported voice 2 occurs in measure 1's pickup: e-1 (v1) and e-6 (v2), both C5, onset 0, duration 1/2. Their graph heads 541 and 2044 share bounds (558,633,26,22). The source has a shared visible pickup head with two opposite stems/flags. Thus two semantic voice instances can correspond to one physical head; note counts are not automatically physical-dot counts, and this is not established as an erroneous duplicate. The full later-note ledger below records pitch, rational timing, and voices instead of assuming voice assignment from display size.

## Tie relationship trace

| Location | Original graph ties/endpoints | XML and canonical result |
|---|---|---|
| Mừng m2→m3 | Lower 2091 and upper 2117 both attach head 644→648 | e-10 has two sound starts and visual starts (under/over); e-11 has two stops |
| Trời m6→m7 | Lower 2093 and upper 2111 both attach head 751→755 | e-24 has two starts (under/over); e-25 has two stops |
| m8→m9 | 2087: 735→739 (F4); 2097: 763→701 (A4) | Distinct e-30→e-32 and e-31→e-33 pitch relationships, one start/stop per note |

The two source curves at Mừng/Trời correspond visually to lower and upper pairs, but missing upper heads leave the graph with two relationships assigned to the lower pair. **The first wrong endpoint association is already in Audiveris**, not introduced by recent manual-tie logic. Recovery and review retain those original XML nodes byte-for-byte. Canonical direction summaries deduplicate start/stop labels; they do not delete raw markup. The affected ambiguous pairs have no resolved manual `tie_relationship`/`tie_target_id`; no user-authored second tie was synthesized. The raw graph uses `tie=true`; these curves are not newly inferred slurs.

OSMD's source reader reports eight tied note objects across all stages. Its internal per-note tie representation does not demonstrate two independent rendered curves for the doubled lower pair. Curve separation, curve count, head collision offsets, and Fit/zoom require browser SVG examination; no claim of successful parallel engraving is made. Do not remove duplicate-looking original nodes automatically: source evidence and explicit user correction must resolve the endpoints.

## Same-input historical replay and renderer limits

Using safely exported historical snapshots from the previous RCA, the **new real benchmark XML and OMR** were replayed through c3b794e (pre-recovery import), f9bb78c, 3a4e548/HEAD, and the current working code. All four produced the same 51 event identities/properties; all serialized bytes retained the same SHA-256 above. No native recognition settings were changed and no historical engine rerun was substituted. This isolates downstream application behavior under identical recognized inputs.

Historical documentation's 53-note normal run, 49-note small-switch run, and later 51→53 separate-evidence recovery are different native runs/settings/evidence. They cannot be compared as though a display edit alone removed notes. Their old raw artifacts remain unavailable, so the user's last known working session cannot be causally attributed to a commit. The previous RCA documents the first relevant commits; this audit adds real-input replay rather than repeating its fixture tests.

Actual installed OSMD 2.1.2 MusicSheetReader was invoked with a minimal XML-reader interface: 51 pitched notes, zero cue/grace, unchanged onset/duration/voice per stage. The probe maps measures by XML/source-array order: OSMD labels the pickup 0 and subsequent measures one less than the XML number; this numbering difference is not a missing measure. No browser engine was available for SVG inspection. The current `scoreRenderer.ts` view clone only removes the cue-size marker for duration-bearing display-small notes and adds source-system print hints; this fresh XML has no such size marker, so that mitigation cannot explain its upstream omissions. The earlier RCA's cue/grace graphical-constructor concern remains relevant to manually corrected or older small-spelled XML, but was not triggered by this run. Same-onset insertion, drag, explicit ties, Undo/Redo were not invoked in the isolated new session, and their prior implementation was not modified.

## Confirmed causes, unresolved hypotheses, minimal recommendations

Confirmed:

1. Target upper G4 heads at Mừng/Trời are absent before XML export. Application recovery cannot recover these from HeadInter evidence because no corresponding recognized head exists. Native internal segmentation/template rejection is not localized by this end-state graph.
2. Surviving source-small heads have ordinary graph shapes and no MusicXML size annotation. Source geometry is retained, but size classification is wrong first at graph classification. Recovery deliberately does not auto-change size from geometry alone: all four possible-small candidates remain ambiguous; its strong condition requires explicit small shape plus other evidence.
3. The nominal black-head width is 26 pixels; the 0.88 hint cutoff is 22.88. Widths 21/22 qualify, 23 do not. Open heads are outside this BLACK-only heuristic. These boundaries explain why some visible small survivors are not even candidates; they do not justify globally lowering thresholds or inventing note events.
4. Wrong doubled lower tie endpoints at Mừng/Trời originate in the raw graph. The independent m8→m9 pairs show the pipeline can retain two genuine relationships when native endpoints exist.
5. No notes disappear downstream in this fresh run or identical-input historical replay.

Unresolved: why the earlier normal-size session had more visible notes; whether its native switches/evidence/profile differed; whether an older cue-rendering path hid a retained note; native processing step responsible for each missing head; actual browser head/curve visibility and spacing. No saved before/after session exists to resolve these. Do not label all prior behavior an Audiveris failure solely from this fresh result.

Minimal recommended fixes, **not implemented**:

- For existing notes, expose/retain explicit per-note user size correction and reviewable source-region size proposals, including open heads; do not treat size as grace or infer another voice. Geometry-only proposals should remain advisory without trusted evidence/user confirmation.
- For absent heads, use explicit source-anchored add-note at the selected exact onset and explicit pitch/duration/voice/staff choices. A future pixel-evidence diagnostic/proposal path must distinguish unrecognized heads from missing XML correspondence; never fill from meter or lyrics.
- Resolve wrong original tie endpoints only with trusted source correspondence or explicit user choice; retain unrelated XML and avoid blanket deduplication.
- To investigate the historical regression conclusively, capture the affected and formerly working sessions' original OMR/XML, recovery/final XML, native command/settings, input hashes, and browser bundle/SVG. No global Audiveris switch change is recommended from this audit; the documented switch-enabled run itself lost notes.

Required future regression coverage: real benchmark graph/XML correspondence for ta/cùng/Mừng/Trời; explicit small black/open-head display with duration retained and no cue/grace conversion; absent-head evidence versus retained normal-sized notes; exact same-onset per-note pitch/duration/voice identity; independent and ambiguous tie endpoints; no automatic duplicate stripping; later lyric verses versus actual voices; source systems 5/5/7, Fit/zoom, SVG head count and parallel ties; read-only Check score; correction, drag, Undo/Redo and unsupported XML preservation. These are recommendations, not new tests or production changes in this diagnostic task.

## Full surviving-note ledger

Each row applies identically to raw/recovery/final canonical stages. All rows: staff 1, normal size, grace=false, duration-bearing. “start×2”/“stop×2” describes original XML node multiplicity, not two authored manual relationships. XML accidentals and lyric numbers/text remain untouched; full markup/provenance is in `stage-trace.json`.

| Measure | Event | Pitch | Voice | Onset | Duration | Original sound ties | Lyric text (number) |
|---|---|---|---|---|---|---|---|
| 1 | e-1 | C5 | 1 | 0 | 1/2 | — | — |
| 1 | e-2 | A4 | 1 | 1/2 | 1/2 | — | ta (1) |
| 1 | e-3 | C5 | 1 | 1/2 | 1/2 | — | — |
| 1 | e-4 | F4 | 1 | 1 | 1/2 | — | cũng (1) |
| 1 | e-5 | A4 | 1 | 1 | 1/2 | — | — |
| 1 | e-6 | C5 | 2 | 0 | 1/2 | — | Chúng (1) |
| 2 | e-7 | G4 | 1 | 0 | 1 | — | dem (1) |
| 2 | e-8 | F4 | 1 | 1 | 1/2 | — | Tin (1) |
| 2 | e-9 | A4 | 1 | 1 | 1/2 | — | — |
| 2 | e-10 | C4 | 1 | 3/2 | 1/2 | start, start | Mừng (1) |
| 3 | e-11 | C4 | 1 | 0 | 1/2 | stop, stop | — |
| 3 | e-12 | F4 | 1 | 1/2 | 1/2 | — | đi (1) |
| 3 | e-13 | A4 | 1 | 1/2 | 1/2 | — | — |
| 3 | e-14 | G4 | 1 | 1 | 1/2 | — | khẽ“ĩp (1) |
| 3 | e-15 | B♭4 | 1 | 3/2 | 1/2 | — | đó (1) |
| 5 | e-16 | A4 | 1 | 0 | 1/2 | — | — |
| 5 | e-17 | C5 | 1 | 0 | 1/2 | — | — |
| 5 | e-18 | G4 | 1 | 1/2 | 1/2 | — | Loan (1) |
| 5 | e-19 | G4 | 1 | 1 | 1/2 | — | tin (1) |
| 5 | e-20 | G4 | 1 | 3/2 | 1/2 | — | loan (1) |
| 6 | e-21 | G4 | 1 | 0 | 1 | — | tin (1) |
| 6 | e-22 | E4 | 1 | 1 | 1/2 | — | Chl’la (1) |
| 6 | e-23 | A4 | 1 | 1 | 1/2 | — | — |
| 6 | e-24 | C4 | 1 | 3/2 | 1/2 | start, start | Tr6i (1) |
| 7 | e-25 | C4 | 1 | 0 | 1/2 | stop, stop | — |
| 7 | e-26 | G4 | 1 | 1/2 | 1/2 | — | yêu (1) |
| 7 | e-27 | G4 | 1 | 1 | 1/2 | — | thương (1) |
| 7 | e-28 | F4 | 1 | 3/2 | 1/2 | — | bài (1) |
| 7 | e-29 | A4 | 1 | 3/2 | 1/2 | — | — |
| 8 | e-30 | F4 | 1 | 0 | 2 | start | ngư€›’i. (1) |
| 8 | e-31 | A4 | 1 | 0 | 2 | start | — |
| 9 | e-32 | F4 | 1 | 0 | 1/2 | stop | l. (1) |
| 9 | e-33 | A4 | 1 | 0 | 1/2 | stop | — |
| 9 | e-34 | F4 | 1 | 1/2 | 1/2 | — | Ne`1y (1) / hồng (2) |
| 9 | e-35 | G4 | 1 | 1 | 1/2 | — | muôn (1) / Người (2) |
| 9 | e-36 | A4 | 1 | 3/2 | 1/2 | — | ưc'ỉ<: (1) / trung (2) |
| 10 | e-37 | B♭4 | 1 | 0 | 3/2 | — | h6i (1) / tin (2) |
| 10 | e-38 | D5 | 1 | 3/2 | 1/2 | — | hãy (1) / vẫn (2) |
| 11 | e-39 | C5 | 1 | 0 | 1 | — | ca (1) / luôn (2) |
| 11 | e-40 | B♭4 | 1 | 1 | 1 | — | khen (1) / vững (2) |
| 12 | e-41 | A4 | 1 | 0 | 2 | start | Ngưêĩi. (1) / Bên. (2) |
| 13 | e-42 | A4 | 1 | 0 | 1/2 | stop | — |
| 13 | e-43 | C4 | 1 | 1/2 | 1/2 | — | Này (1) / Tmh (2) |
| 13 | e-44 | E4 | 1 | 1 | 1/2 | — | ngêln (1) / Người (2) |
| 13 | e-45 | F4 | 1 | 3/2 | 1/2 | — | dém (1) / thu’dng (2) |
| 14 | e-46 | G4 | 1 | 0 | 3/2 | — | (ii (1) / ta (2) |
| 14 | e-47 | B♭4 | 1 | 3/2 | 1/2 | — | ủy (1) / dén (2) |
| 15 | e-48 | A4 | 1 | 0 | 1 | — | tung (1) / muôn (2) |
| 15 | e-49 | G4 | 1 | 1 | 1 | — | hô (1) / muôn (2) |
| 16 | e-50 | F4 | 1 | 0 | 2 | start | Ngư<`5i. (1) / (161. (2) |
| 17 | e-51 | F4 | 1 | 0 | 1/2 | stop | — |

## Verification and safety

The actual pipeline run, direct raw graph inspection, canonical per-event trace, identical-input historical replay, and OSMD source-reader probe completed. Existing production tests were not rerun because this task changes no production code; these diagnostic observations are not replacement browser acceptance. `git diff --check` and the new report's whitespace check passed.

All pre-existing tracked/nonignored working files were hashed before the run and compared after report creation: no existing file was changed or deleted. Only this report was added to the repository by this audit. All diagnostic scripts and generated score artifacts stayed under `/tmp`; no user corrections or live review sessions were overwritten. Source PDF bytes remain unchanged. No production code, Audiveris configuration, or prior report was modified. No files were staged, committed, or pushed.
