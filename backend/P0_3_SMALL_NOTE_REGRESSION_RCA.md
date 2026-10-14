# P0.3 — small-note recognition regression RCA

Diagnostic only, 2026-10-06 (America/New_York). No fix implemented.

## Finding

**The user's report of formerly visible normal-size notes disappearing after small-note distinction is credible regression evidence, but its exact failing stage is not established by the artifacts available today.** Controlled comparisons found no loss of existing notes in application classification, recovery, serialization, canonical projection, or OSMD source parsing. They did reproduce the application's small-display spelling being interpreted as a cue note by OSMD.

There are two distinct mechanisms to investigate, not one assumed recognition failure:

1. **Documented historical upstream loss:** an experimental Audiveris run with smallHeads/smallBeams enabled exported 49 notes versus 53 in its normal baseline. The regular G4 was also classified small and its chord was omitted. These numbers are recorded historical evidence, not a reproduced current run.
2. **Reproduced downstream semantic mismatch:** a duration-bearing display-small note without cue/grace XML becomes OSMD IsCueNote=true. The source note remains present with unchanged onset/duration and IsGraceNote=false. Graphical conversion can subsequently use a GraceNote constructor for the entire entry according to its first pitch-sorted graphical note. Actual hidden/disappeared SVG heads in the user's browser were not reproduced.

The current P0.2.2 viewing adapter already mitigates the second path in the editable Working Score. Whether the affected browser ran that adapter, an older bundle, or different recognition settings is unknown. Neither mechanism alone proves the cause of the user's current report.

## Available evidence and limits

The original benchmark **is available**, outside the repository:

- PDF: /mnt/c/Users/dtran/Downloads/BaihatCN/CN25 Thuong Nien - Nam A/cungdemTinMung.pdf
- 35,886 bytes; SHA-256: 30df9a6988ecc7752c2a89dcd84bcc87b44259b88803e2636f817ede7b15b81a
- Its hash matches the earlier reports.

However, these recorded capture directories no longer exist:

- /tmp/phase4d2-cungdem-real/
- /tmp/phase4d2-cungdem-recovered/
- /tmp/music-sheet-transposer-phase4f1-cungdemtinmung/

No matching OMR/MusicXML artifacts were found in the repository, the inspected /tmp locations, or the source PDF's directory. Current review storage is process-local memory; no affected live session capture is available here. The configured executable is audiveris, but executable lookup on this diagnostic process's PATH returns none. Consequently no fresh native benchmark, same-PDF historical/native rerun, or real-browser SVG comparison was performed. No executable was installed and no configuration was changed.

Equivalent XML/OMR fixture inputs were compared across safely exported historical source snapshots. These isolate application code behavior; they are **not replacement benchmark recognition runs**. A minimal XML-reader interface was used to call the actual installed OSMD MusicSheetReader without a browser. That measures source-note parsing, not SVG visibility.

The previous P0.2.2 report's “benchmark unavailable” statement was about artifacts located during that implementation. This investigation located the PDF at its older documented external path; the essential saved before/after OMR/XML/browser artifacts remain unavailable.

## Last known working behavior and first relevant changes

The strongest evidence for the user's last known working browser behavior is the user's firsthand observation. No exact revision, saved session, raw XML, profile, or browser bundle hash accompanies it, so it cannot be assigned to a Git commit.

Repository history gives these narrower boundaries (Eastern time):

| Revision | Date/time | Relevant change |
|---|---|---|
| 1d7ec03 | Oct 3, 18:22:10 | Audiveris recognition/profiles and retained artifacts. Profiles explicitly disable smallHeads/smallBeams. OMR.md already records the historical 53→49 experimental switch-enabled regression and mixed-size renderer limitation. |
| c3b794e | Oct 3, 22:09:54 | First committed preserved-XML review importer/patcher, including display_size() and size_patch(). Small spelling is type size="cue" plus notehead font-size="small"; duration remains present. The commit title mentions SMT but the diff also introduces the review workflow. |
| f9bb78c | Oct 3, 23:21:35 | Semantic small-head extraction, correspondence, classification, display preservation, simultaneous recovery, and opt-in LINKS evidence pass. Baseline export remains separate. |
| 3a4e548 (HEAD) | Oct 4, 18:24:27 | Interactive review workflow and richer evidence/report integration. Recovery classifier/patch decisions are unchanged from f9bb78c except added sheet dimensions in reporting. |
| Current uncommitted work | No reliable Git timestamp | Source layout/evidence, correction controls, ties, same-onset insertion, per-note duration scope, and P0.2.2 renderer mitigation. Phase reports provide intent, not individually bisectable revisions. |

size_patch() and display_size() have the same relevant small-size logic in c3b794e, HEAD, and the current tree. There is no uncommitted change to recognition provider/service/profiles, recovery service/musicxml correlation, application configuration, or frontend dependency manifests/lockfile. The installed OSMD is 2.1.2.

Historical versions were read with git show and exported with git archive into /tmp/p03-small-note-rca.9YOmul/. No checkout/reset touched the working tree.

## Before/after comparison

### Recorded real benchmark results — separate runs

These values come from [OMR.md](OMR.md), [SEMANTIC_RECOVERY.md](SEMANTIC_RECOVERY.md), and [the prior source trace](PHASE4F1_SOURCE_FIDELITY_HALF_NOTE_DIAGNOSTIC.md). Their raw captures are unavailable for rechecking.

| Recorded run | Raw/export pitched notes | Corrected pitched notes | Size/timing evidence |
|---|---:|---:|---|
| Historical normal baseline | 53 | Not recorded here | Small appearance absent from XML |
| Historical smallHeads/smallBeams-enabled export | 49 | Not recorded here | Four small heads in two small chords; zero exported small/grace/cue notes; measures 2 and 6 shortened |
| Later normal VOCAL_SONG baseline plus separate LINKS evidence | 51 | 53 | Baseline 51 heads; LINKS 53 heads; two added small duration-bearing chord members; zero grace notes |
| Later Phase 4F1 captured review | 51 heads reported | No automatic recovery | Zero explicit small heads, four possible-small heads; missing half-note location in source measure 4 already lacks recognized head/chord/stem/voice/slot data |

The 53-note normal historical export and later 51-note baseline are **different native runs**, not evidence that application recovery removed two notes. The switch-enabled full export and separate LINKS-only evidence pass are also different inputs to downstream code. The latter is never exported as the working baseline by the current provider.

The Phase 4F1 trace establishes an upstream omission for its specific half-note location around “đây.”. It does not establish the stage of the newly reported omissions at “Mừng”, “Trời”, or elsewhere. Total note count alone does not establish source fidelity.

Current local Settings resolve to VOCAL_SONG, Synthetic, vie+eng, semantic recovery enabled, optional semantic analysis disabled. Profile constants explicitly set smallHeads=false and smallBeams=false. These reflect this diagnostic process, not a captured affected server's runtime settings. Settings do not automatically load a .env file. No settings were changed.

### Controlled identical fixture inputs

Snapshots tested: c3b794e (pre-recovery), f9bb78c, HEAD, and current working code. The semantic fixture graph has heads 10 (normal A4) and 11 (small C5), both measure 1, voice 1, onset 0, chord 20, stem 30.

| Case/stage | Pitched notes | Normal | Small | Same-onset notes | Grace |
|---|---:|---:|---:|---:|---:|
| Missing-small baseline XML | 1 | 1 | 0 | 0 | 0 |
| Recovery in f9bb78c / HEAD / current | 2 | 1 | 1 | 2 | 0 |
| Corrected serialization and re-import | 2 | 1 | 1 | 2 | 0 |
| Both heads already in XML as normal | 2 | 2 | 0 | 2 | 0 |
| Classification/display preservation | 2 | 1 | 1 | 2 | 0 |
| Already-small XML, repeat recovery | 2 | 1 | 1 | 2 | 0 |
| Explicit size-only edit and re-import, all four versions | 2 | 1 | 1 | 2 | 0 |

In the existing-normal case, e-1=A4 and e-2=C5 retain onset 0, duration 1, voice 1, staff 1; e-3 remains the rest at onset 1. Only C5 display size changes. In the missing-note case the new internal identity is recovery-1; all original reference IDs survive the recovery clone. Fresh XML re-import assigns ordinal IDs again: an original following rest can receive a different ID when an earlier note was inserted. This is expected identity rebinding across independent imports, not note deletion; ordinal IDs must not be compared as cross-run physical identities.

The current ReviewService payload retains two pitched events and unchanged serialized bytes for each two-note fixture, including the display-small variant. Chord grouping appends individual events rather than collapsing them.

The richer review_mixed_size.musicxml fixture produces identical counts in all four versions:

| Measure | Voice | Pitched | Normal | Small | Same measure/onset as another pitched event | Sequential-only |
|---|---|---:|---:|---:|---:|---:|
| 1 | 1 | 2 | 1 | 1 | 2 | 0 |
| 1 | 2 | 1 | 1 | 0 | 1 | 0 |
| 2 | 1 | 1 | 1 | 0 | 0 | 1 |

“Same onset” here counts coincident times across voices/staves within the same measure, not only chord membership. No real-benchmark per-measure/voice/size/onset count matrix can be reconstructed from the missing artifacts.

## Stage-by-stage RCA

| Stage | Observed result and boundary |
|---|---|
| Audiveris recognized graph | Controlled fixture retains both physical heads. Current omr.py structural additions do not change its head extraction/classification conditions. Heads without valid measure/staff/containment membership may be excluded from extracted evidence independently of size. Head-seed/template records are not recognized note identities. No affected real graph is available. |
| Audiveris MusicXML | Historical small-switch run documents loss by export, before our recovery. Current full export uses switches=false; optional switches=true analysis only reaches LINKS and supplies evidence. Whether the affected user input already lacks notes here is unknown. |
| Semantic Recovery | Only size preservation and bounded note addition are automatic operations. Ambiguous candidates or failed patches retain prior XML; they do not delete existing notes. Grace classification labels evidence but does not convert baseline notes to grace. Conservative gates can decline to add a missing head. Same-pitch-in-chord dedup can suppress a proposed additional unison, but does not remove a baseline event. Fixture outputs show no loss. |
| Corrected recognition XML | Document.xml() returns original bytes when unchanged or serializes the preserved tree. It does not rebuild notes from a filtered score model. XML counts survive fixture serialization. |
| Canonical review model/payload | Importer creates one event per XML note and appends chord members to voices. Explicit grace depends on the grace element, not size. structure.py enriches events and layout without filtering them. Payload counts and existing identities survive the measured cases. |
| OSMD source model | Actual MusicSheetReader retains both notes with duration 1/onset 0. Raw small XML sets C5 IsCueNote=true while IsGraceNote=false. Adapter-equivalent XML removing only the display type size makes IsCueNote=false, still two notes. |
| OSMD graphical/SVG Working Score | Static converter inspection confirms GraceNote construction can depend on the first pitch-sorted graphical note's cue flag. Mixed-size rendering is consequently entry-dependent. Actual SVG note count, clipping, collision overlap, or stale bundle effects were not measured. **This is the earliest confirmed app/renderer interpretation mismatch, not a confirmed disappearance stage.** |

OSMD probing used the same installed reader for normal, raw small, and adapter-equivalent XML. It did not invoke layout/drawing or emulate browser acceptance. Evidence/probe scripts and JSON are local diagnostic artifacts in /tmp/p03-small-note-rca.9YOmul/, not repository fixtures or durable storage.

## Recent correction changes and side effects

- Same-onset insertion now resolves an explicit anchor or exact onset. Compatible durations use chord members; longer or separately voiced notes use backup/forward streams. Semantic recovery still calls the omitted-duration chord insertion path, which retains its old anchor-duration behavior. The old/new recovery comparison exercises this path and shows identical retained counts.
- Explicit per-note duration scope affects correction requests, not recognition. Legacy chord scope remains the default. No automatic invocation occurs simply because a note is small.
- Tie edits add/remove relationship markup. The viewing clone suppresses owned tied elements, not note elements. Repeated pairs are no-ops. It does not merge simultaneous notes.
- P0.2.2 viewing normalization is gated by an onSelect callback and the specific type-size/notehead-small spelling with duration and no cue/grace element. Other small spellings, true cue/grace, and read-only views retain their renderer paths.
- The mapped small SVG head is scaled by 0.65 about its center. This changes visual extent, not note count/onset. Missing/ambiguous mappings leave it unscaled; they do not hide it. Whether existing transforms/clipping or shared-head rendering create a visibility problem requires actual SVG capture.
- Fit/source grouping only adjusts engraving width and checks ordered source systems. The reviewed code does not delete note elements. Shared-unison mapping can make a head nonselectable; that is different from a missing canonical event.
- Recovery rhythm gates and source-layout projection may affect proposal eligibility/diagnostics, but the measured existing XML notes survive all compared versions.

## Confirmed versus hypotheses

**Confirmed in this investigation:** same-size classification/serialization fixtures retain note counts and timing; application recovery can add a small note without deleting originals; current payload retains both heads; OSMD source parsing conflates visual cue-size type with cue status; existing P0.2.2 view normalization clears that flag in the equivalent input; recognition settings/code currently keep baseline small switches disabled.

**Recorded but not reproduced today:** the historical 53→49 switch-enabled export regression; the later 51→53 selective recovery; the source-measure-4 upstream omission from the earlier capture.

**Unverified hypotheses for the user's current regression:** stale frontend bundle or alternate viewer bypassing the P0.2.2 adapter; whole-entry grace/cue construction affecting visible heads; different recognition profile/quality/native version or opt-in analysis/export behavior; retained XML heads overlapping/clipped in SVG; different prior source/session/manual corrections; an untested XML shape or recovery-candidate dedup affecting a missing unison.

No available measurement justifies declaring “Audiveris failed” as the root cause of this report, or claiming an application deletion regression is disproved for all inputs.

## Minimal recommended next action/fix

First capture the affected session's original provider MusicXML, corrected MusicXML, OMR/evidence archives, canonical payload and actual OSMD source/graphical/SVG counts, alongside the pre-small successful capture if available. Record PDF/raster hashes, provider version/command/constants, profile/quality/OCR, server options, review revision and served frontend bundle. Compare identities by part/measure/staff/voice/exact onset/pitch plus physical provenance; do not align independent runs by ordinal IDs.

Then apply the smallest fix at the demonstrated boundary:

- If XML/canonical counts are intact and SVG heads disappear, keep duration-bearing small notes on the normal rhythmic renderer path and correct only the failing renderer condition. The existing P0.2.2 mitigation should be verified before adding another adjustment.
- If notes already disappear in a switch-enabled export, retain the normal baseline and restrict that pass to evidence. Current provider code already follows this policy; correct a demonstrated bypass rather than globally changing Audiveris configuration.
- If recovery/canonical/XML comparison actually loses an existing event, repair that exact loss with a baseline event-retention invariant and preservation regression. Do not infer notes, pitches, durations, grace semantics or missing ties from meter.

Do not implement an unconditional recognition/settings change on this evidence. No recommended fix was implemented in this diagnostic task.

## Regression tests required

1. Matched normal→small classification preserves XML note count, physical correspondence, stable in-session IDs, exact onset/duration/voice/staff and unrelated markup.
2. Recovery never removes a baseline event; rejected, ambiguous, duplicate, same-pitch/unison, mismatched-analysis and quota-limited proposals preserve baseline notes.
3. Separate measured invariants at graph extraction, raw export, recovery, serialized XML, canonical payload, OSMD source model, graphical notes and SVG heads.
4. Browser fixtures for small-leading/normal-leading chords, reversed pitch order, independent unequal durations/voices, open/filled heads, accidentals, shared unisons, cue/grace controls and alternate small-size XML spellings.
5. Verify actual visible/selectable head counts and attachment at Fit/100%/zoom, scroll, source systems, pane resize, corrected/transposed switches and adapter bypass/read-only cases.
6. Same-onset insertion, independent ties/removal, per-note duration correction and Undo/Redo must preserve all other heads and identities.
7. Provider tests must distinguish small-switch full export from LINKS-only evidence and verify baseline selection under every profile.
8. Durable real-PDF captured artifacts with SHA-256 and complete settings are required for before/after native comparisons; historical total counts alone are insufficient.

Existing semantic and renderer tests cover parts of these requirements. The ad hoc probes above add diagnostic evidence but are not browser acceptance or new committed regression tests.

## Safety and completion

Only this RCA report was created in the repository. Historical exports, diagnostic scripts and results were written under /tmp. No production code, tests, dependency manifests or Audiveris configuration were edited. Existing uncommitted work was preserved. No reset, restore, clean, stash, stage, commit or push was performed. Whitespace and final preservation checks were run; work stops after this report.
