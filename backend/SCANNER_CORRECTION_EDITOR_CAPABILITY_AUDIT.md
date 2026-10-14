# Scanner Correction Editor capability audit

Date: 2026-10-04. Scope: current working tree, including uncommitted Phase 4F/4F.1 work. Architecture and capability audit only; no production behavior changed.

## 1. Finalized product and workspace contract

The product reconstructs an authoritative source image/PDF, supports human correction and source comparison, verifies a corrected master, then transposes and exports. It is not a composition application or a theory repair engine. Unusual source notation remains correct when faithfully represented. No automatic meter normalization, speculative note creation, or relationship inference is authorized.

The fixed workspace has two panes: immutable original source on the left; recognized, corrected, verified, or transposed score on the right. Direct notation selection plus explicit commands is the primary interaction. Advanced Review is fallback/debugging, not the normal correction path. No third permanent transpose pane, drag-and-drop, or workspace redesign is required.

Canonical musical and visual properties are authoritative. OSMD and SVG supply rendering and interaction only. Pitch, onset, duration, accidental, voice/part, size, grace, and relationships are independent properties; small secondary notes can have ordinary duration.

## 2. Reconciliation and current two-pane lifecycle

Read together: [recovery architecture](SCANNER_FIDELITY_RECOVERY_ARCHITECTURE.md), [notation architecture](PHASE4F_NOTATION_EDITOR_ARCHITECTURE.md), [half-note diagnostic](PHASE4F1_SOURCE_FIDELITY_HALF_NOTE_DIAGNOSTIC.md), [layout diagnostic](PHASE4F1_SOURCE_LAYOUT_DIAGNOSTIC.md), and [visual review](PHASE4F_VISUAL_REVIEW.md).

The user's subsequent browser acceptance supersedes earlier pending-acceptance language: trusted source systems render **1–5 / 6–10 / 11–17**. Historical fixed-width explanations and test totals do not describe a new requirement or fresh test run. Preserve the accepted source-engraving adapter unchanged: trusted grouping determines engraving, then Fit/zoom determines presentation.

`RecognitionReview.tsx` renders the immutable `SourceViewer` beside a corrected `MusicSheetViewer`. `Home.tsx` stores transposed output separately and renders another viewer below review. Thus source/corrected comparison exists, but **corrected/transposed switching in the same right pane does not**. The separate result viewer also lacks the review score/layout props used for trusted source grouping and selection.

Recommended future routing: one explicit corrected/transposed right-pane view selector, retaining the original left pane. Edit only the corrected master; transposed output can initially be read-only. Clear derived output on correction/revision changes. Reuse existing transpose/export endpoints. Do not map transposed pitches against an untransposed semantic projection; use a derived correspondence or read-only rendering. Presentation of transposed source grouping needs integration and regression coverage, without changing the accepted renderer algorithm.

## 3. Current canonical and editing architecture

The backend `Document` retains original bytes, a preservation-based XML tree, stable review references, and manual review metadata. The semantic projection is rebuilt from patched XML; there are not two independently writable score databases. Edits clone the document, validate references and representation, apply an atomic patch, project, and commit under a revision check/lock. SVG changes never become edits.

Relevant implementation: `backend/app/music/review/{models,importer,patcher,service,storage,ties,structure}.py`; `frontend/src/components/{RecognitionReview,VisualNoteEditor,EventInspector,SourceViewer,MusicSheetViewer,ReviewScoreViewport}.tsx`; `frontend/src/utils/{scoreInteraction,scoreRenderer,sourceEngraving,visualReview}.ts`; `frontend/src/pages/Home.tsx`; `frontend/src/services/api.ts`.

Events already carry pitch, onset, rational duration, divisions, voice, staff, measure, chord membership, grace, display size, ties, accidental/notated-duration metadata, and lyric references. Measures project meter, keys, clefs, barlines, context changes, and rhythm diagnostics. Lyrics/harmonies are modeled. This is sufficient for ordinary note/rest property corrections and a bounded same-chord example; it is not a complete writable structural or relationship model.

Targeted extensions are needed for explicit musical-position commands and timeline policies, secondary-part ownership, slur relationships, editable structural context scope, richer accidental/cue distinctions, source provenance, and scoped source-confirmation decisions. Onset already exists; adding an insertion command does not require replacing the whole model. Preserve one XML-backed authority and stable identities.

## 4. Complete capability matrix

Each row has exactly one primary state. ALREADY SUPPORTED means a safe current normal workflow for the stated scope. PARTIALLY SUPPORTED includes restricted commands, Advanced-only controls, or unproven visual interaction. MISSING means no implemented correction command/workflow. Backend preservation alone does not count as support.

Impact columns describe work still needed, not work implemented by this audit. “None” means reuse existing contract; “UI” work may still require behavioral tests. P0 = required for normal scanner-fidelity correction; P1 = important beyond the first bounded practical path; P2 = convenience. P0 does not imply every item belongs in one implementation milestone.

| Capability | Current State | Canonical Change | XML/Patch Change | API Change | Renderer Change | UI Change | Priority |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Add note at musical position | PARTIALLY SUPPORTED | Position/timeline policy | Explicit onset placement beyond anchors | Position command beyond existing anchors | Empty-measure/position targeting | Normal empty-measure and position controls | P0 |
| Delete note | PARTIALLY SUPPORTED | Deletion timing policy | Preserve-time option; relationship safety | Policy beyond shifting delete | None for bound heads | Explain/select time policy | P0 |
| Change pitched-note pitch | ALREADY SUPPORTED | None | None | None | None | Existing steps/alterations; direct letter picker optional | P0 |
| Change note duration | PARTIALLY SUPPORTED | Independent-voice policy if needed | Existing shared-chord duration; broader timing cases | Scope/policy for broader cases | None | Explain chord scope; grace conversion path | P0 |
| Change accidental | PARTIALLY SUPPORTED | Explicit written/cautionary accidental | Create/change printed accidental independently | Written-accidental command | None | Printed accidental controls | P0 |
| Normal ↔ small | PARTIALLY SUPPORTED | None for ordinary size | Preserve independent size semantics | None for existing size patch | Mixed-size OSMD limitation | Normal toolbar size control | P0 |
| Grace ↔ duration-bearing | PARTIALLY SUPPORTED | None for supported chord scope | Existing conversion; explicit duration required | None for bounded scope | Check resulting identity | Normal control and scope explanation | P0 |
| Size/grace independence end to end | PARTIALLY SUPPORTED | Separate true cue identity where conflated | Retain distinct cue/size/grace representation | Expose distinctions if edited | Mixed-entry per-head sizing issue | Independent controls | P0 |
| Add rest | PARTIALLY SUPPORTED | Position policy | Existing anchor/empty add; broader onset planning | Position extension | Empty/position targeting | Normal add-rest command | P0 |
| Delete rest | PARTIALLY SUPPORTED | Timing policy | Existing generic delete; preserve-time option | Policy as above | Prove actual rest binding | Normal selection/delete | P0 |
| Change rest duration | PARTIALLY SUPPORTED | None for bounded cases | Existing generic duration patch | None for bounded cases | Prove actual rest binding | Normal rest properties | P0 |
| Add tie | PARTIALLY SUPPORTED | Source-supported boundary/provenance | Relax theory-derived restriction only with explicit evidence/confirmation | Scoped source-boundary support | Existing target binding | Existing click targets; unusual-boundary review | P0 |
| Remove tie | ALREADY SUPPORTED | None | None for supported safe ties | None | None | Existing Remove tie | P0 |
| Change tie endpoint | PARTIALLY SUPPORTED | Same boundary/provenance needs | Existing atomic retarget limited to safe targets | Same extension as add | Existing target binding | Existing Tie target mode; broader source cases | P0 |
| Add slur | MISSING | Stable slur edges/numbering | Paired endpoints and continuations | Slur commands | Endpoint selection | Normal slur command | P1 |
| Remove slur | MISSING | Slur edge identity | Safe paired removal | Slur command | Endpoint/relationship selection | Normal remove command | P1 |
| Change slur endpoints | MISSING | Slur edge identity | Safe atomic retarget | Slur command | Endpoint selection | Normal retarget | P1 |
| Edit lyrics via selected note | ALREADY SUPPORTED | None | Existing verse/segment-preserving patch | None | Direct lyric hit optional | Existing visual lyric editor | P0 |
| Edit harmony/chord symbol | PARTIALLY SUPPORTED | Richer writable harmony fields/scope | Extend limited root/kind/text patch | Richer commands as needed | Harmony selection | Move basic controls out of Advanced | P1 |
| Correct voice / secondary-part assignment | PARTIALLY SUPPORTED | Part membership and independent timing policy | Replan voice timeline/part ownership | Beyond voice label patch | Rebind voice/part identities | Normal source-based ownership controls | P0 |
| Correct staff assignment | PARTIALLY SUPPORTED | Existing staff sufficient in declared part | Existing bounded staff patch | None for declared staff | Regression for cross-staff identity | Normal staff control | P0 |
| Correct measure ownership | MISSING | Ownership/timeline command | Atomic move with source/target timeline | Move command | Target measure selection | Explicit destination/time controls | P0 |
| Correct barline | MISSING | Writable structural identity/scope | Barline/repeat preservation patch | Structure command | Barline target or measure selection | Structural properties | P1 |
| Correct clef | MISSING | Writable context/scope | Context patch without reinterpretation | Structure command | Staff/context selection | Structural properties | P1 |
| Correct key signature | MISSING | Writable context/scope | Key patch without respelling existing pitches | Structure command | Context selection | Structural properties | P0 |
| Correct time signature | MISSING | Writable context/scope | Meter patch without retiming notes | Structure command | Context selection | Structural properties | P0 |
| Direct score selection | PARTIALLY SUPPORTED | None for bound notes | None | None | Rest/empty/context/text bindings incomplete | Non-note selection paths | P0 |
| Musical-position insertion independent of extant note | MISSING | Position command | Deterministic timeline planning | Explicit position contract | Safe target region/coordinate conversion | Position picker | P0 |
| Undo | ALREADY SUPPORTED | None | None | None | Existing rerender | Existing Undo | P0 |
| Redo | ALREADY SUPPORTED | None | None | None | Existing rerender | Existing Redo | P0 |
| Validation diagnostics | ALREADY SUPPORTED | Diagnostic categorization extension for Verify | No normalization | Decision APIs separately below | None | Distinguish technical/theory diagnostics | P0 |
| User verification under source-fidelity policy | PARTIALLY SUPPORTED | Scoped source-match decisions/fingerprints | No musical patch for acknowledgment | Decision and Verify policy | None | Per-discrepancy source confirmation | P0 |
| Corrected MusicXML export | ALREADY SUPPORTED | None | None | Existing verified export | None | Existing export/download | P0 |
| Absolute verified-master transposition | ALREADY SUPPORTED | None | None | Existing guarded transpose | None for master safety | Existing request routing | P0 |
| Corrected/transposed views in same right pane | MISSING | None for read-only result | None | None | Pass safe view/layout correspondence | Right-pane view selector; remove extra result viewer | P0 |
| Source-region candidate correction | PARTIALLY SUPPORTED | Unanchored candidates/provenance | No automatic glyph reconstruction | Read-only evidence/decision contract | Empty region correspondence | Integrated plain-language candidates | P0 |
| Drag-and-drop / advanced engraving controls | MISSING | Not needed now | Not needed now | Not needed now | Later convenience only | Later convenience only | P2 |

## 5. Note insertion, deletion, and property gaps

`VisualNoteEditor` adds before/after/simultaneously with an existing pitched anchor. Sequential insertion inherits ownership; simultaneous insertion shares anchor rhythm. It cannot supply an arbitrary onset, select an empty measure for insertion, or normally insert from a rest anchor. The Advanced empty-measure adder exists, but it is not the required normal path. Backend `EventAdd` accepts measure and anchor identities, not an explicit onset/time policy.

Sequential insertion/deletion shifts later events and retains existing backup/forward structure. This can change timing relative to another voice. A scanner correction needs explicit insert-time versus fill/replace-at-position behavior and delete-shift versus preserve-time behavior. Do not invent rests as a default substitute or silently move notes across measures. Preview consequential timing changes and reject unsupported representations atomically.

Pitch steps and common alterations are available visually. Durations use named supported values, rational backend values, and shared-chord scope; unsupported representation is rejected rather than rounded. Duration changes apply to the shared chord. Independent secondary voices require separate timing representation, not merely changing a chord member's label.

Pitch alteration and a printed accidental are distinct. The pitch patch updates an existing `<accidental>`, but does not provide a general independent written/cautionary accidental creation command. Therefore semantic sharp/flat selection alone does not establish full source accidental fidelity.

## 6. Normal/small and grace independence: complete path

| Stage | Current evidence / behavior | Gap or constraint |
| --- | --- | --- |
| Source | Small C5 and normal A4 open half-note heads in real raster; duration-bearing source notation | Do not infer grace from size |
| OMR/recovery | Missing recognized heads/chords in source measure 4; raw fragments survive; current recovery did not reconstruct them | Read-only evidence can guide manual correction; automatic reconstruction remains unresolved |
| Review state | Separate display size, grace, duration, onset, chord/voice/staff | Cue identity is not fully independent in the existing size vocabulary |
| MusicXML patches | Small ordinary notes use size metadata while retaining duration; grace conversion separately removes/adds duration; true cue is guarded | No `<cue>`/`<grace>` workaround for ordinary small notes |
| OSMD | Mixed normal/small chord members may share first-note graphical-entry scaling | Correct XML does not guarantee per-head visual fidelity |
| Human correction | Advanced offers size and grace independently; visual add defaults ordinary duration-bearing notes | Normal toolbar lacks independent size/grace controls |
| Verified XML | Current verified export retains patched document | Theory blockers can prevent faithful unusual source from reaching verified state |
| Transposition | Operates on verified corrected XML; preservation tests cover size/grace/chord timing | Preserve metadata; do not derive from rendered appearance |
| Export | XML output preserves semantic/size distinction for supported representations | Renderer screenshot is not proof of XML fidelity |

A shared-duration A4+C5 chord is representable now if source evidence establishes simultaneity and ownership. Source evidence, not visual size, determines whether C5 is a separate voice/part. Do not invent a voice to work around OSMD. Full secondary-part correction requires timeline/ownership support beyond existing voice relabeling.

## 7. Rest editing

Backend generic event add/delete/duration supports rests in bounded anchor/empty-measure cases. Advanced exposes rest creation and properties. The visual toolbar lacks a complete add-rest path. `scoreInteraction` uses notehead SVG bindings; inspected tests establish chord note selection, not a real-browser rest hit path. Rest selection must be demonstrated before calling visual rest delete/duration fully supported. Use the same canonical commands, with explicit timeline behavior, rather than a second rest database.

## 8. Ties and slurs

`ties.py` maintains both sound `<tie>` and notation `<tied>` endpoints atomically for supported ties. Visual target mode supports add/retarget; Remove tie supports removal. Safe targets require compatible pitch, voice, staff, part, known timing, and non-grace/non-cue semantics. Cross-measure targeting currently requires source-end equal to the measure's expected duration and next-measure onset zero. Insert-and-tie has further rhythm checks. Thus meter can restrict source-faithful unusual ties even when no notes are normalized.

The concrete missing half in empty 2/4 measure 4 can fit that boundary once correctly inserted; this does not prove unusual-boundary support generally. Future source-confirmed relationships need explicit endpoints/timing and provenance, never musical-plausibility invention.

Slur XML can survive preservation patches, but there is no typed writable slur graph or add/remove/retarget API/UI. Preservation is not slur editing. Deleting a note carrying opaque slur endpoints is not demonstrated as a general safe slur-repair operation. Model numbering, continuation and endpoint identity before adding commands.

## 9. Lyrics and harmony

The visual lyric editor works through a selected note, supports Unicode, verse/segment selection and removal, and preserves syllabic/elision metadata. Direct lyric glyph selection is an optional extension, not required for the present note-based path.

`HarmonyEditor` inside `RecognitionReview.tsx` is Advanced-only. Existing operations cover limited root alteration, kind, displayed text and anchored addition. Preserved bass/degrees/other XML do not imply writable complete chord-symbol correction. Normal harmony selection/controls plus targeted richer fields are needed; avoid recreating symbols and dropping opaque notation.

## 10. Voice, staff, and measure ownership

Advanced can change voice IDs and declared staff. Voice changes affect a shared chord and relabel it; they do not replan backup/forward, split independent voices, or move to another part. Staff changes are bounded to a declared staff and apply to the selected head. Neither is exposed as a complete normal source-correction command.

Measure ownership is projected but not editable through EventPatch. Moving between measures/parts requires an atomic ownership/timing plan, stable references, relationship handling and history. A displayed source location is not authority to move an event automatically. Source-confirmed assignment should describe the user's chosen measure/staff/part in musical terms, without manual event IDs.

## 11. Barline, clef, key, and time signature

The projection/preservation layer exposes and retains structural context. There are no correction endpoints for these four properties. Add narrow context commands with stable target and scope: at which measure/onset/staff the context changes, what following context inherits it, and which XML elements survive.

A key correction must not automatically transpose/respell pitches; a meter correction must not retime durations or add/remove events. Clef correction must preserve explicit pitches. Barline/repeat edits must preserve unrelated attributes and boundary ownership. These are scanner corrections, not theory repair.

## 12. Undo/redo, validation, and verification

History retains previous documents including manual metadata; undo/redo restores XML/projection and advances revision. It resets state to REVIEW_REQUIRED rather than restoring a historical VERIFIED authorization. Mutations require expected revision and are atomic. History/session storage is bounded and process-local; this is not a durable archived verified master. Expired sessions can retain local XML but not server-side source/verification authority.

Current Verify requires source comparison and no blocking errors/unresolved candidates. Overfill is an ERROR that blocks Verify. Underfill is generally a WARNING, but there is no scoped recorded “matches source” disposition. Voice-overlap/timing errors need classification by cause: broken representation versus faithfully unusual source. Current policy is therefore only partial support for the finalized contract. Candidate acceptance/global source-comparison checkbox is not a theory-diagnostic waiver.

Proposed policy, not implemented:

- Technical failures remain blocking: malformed XML, invalid representation/reference, dangling relationships, impossible internal state, invalid patch.
- Theory discrepancies remain visible and reviewable. Add a scoped source-match decision keyed to diagnostic kind, affected event/context identities, revision/content fingerprint and evidence or explicit user comparison.
- A decision acknowledges the discrepancy; it does not patch durations, meter, notes or rests. Unrelated/new diagnostics cannot inherit it. Relevant edits invalidate it; history restores content/decision metadata but still requires fresh Verify authorization.
- Verify checks unresolved technical failures, candidate dispositions and current source-match decisions separately. Do not broadly downgrade all ERRORs or use a global “ignore validation” switch.

The same classification must govern tie eligibility where theory-derived boundaries currently suppress source-supported relationships. This requires deliberate validator/API/UI work, not changing the score until it passes 2/4.

## 13. Raw evidence integrated into visual correction

Keep read-only raw-evidence extraction/candidate review. It should surface “possible missing note” or “uncertain tie” with a source crop and musical location, not require users to understand glyph IDs. Expert evidence can remain collapsible. Uncertain evidence does not authorize automatic reconstruction.

Existing candidates can identify an extant event/anchor and source location. “Inspect related event and source” depends on such an event, so it cannot complete the missing-empty-measure case. `SourceViewer` highlights compatible image geometry, limited by page/aspect/bounds checks. PDF display uses an iframe and does not provide equivalent registered rectangle highlighting. Aspect-ratio compatibility is not a proven source-to-raster affine registration.

`scoreRenderer` exposes measure regions and overlap-safe hit utilities, but they are not wired into actual viewer insertion clicks. Future interaction must transform client/SVG coordinates through viewBox, Fit, zoom and scrolling into the adapter coordinate system. A geometric x-coordinate is not a musical onset. Select a trusted measure/staff region, then use an explicit musical-position command when onset cannot be determined safely.

Add unanchored candidates attached to known source measure/staff regions, with confidence/provenance and an explicit unresolved state. Use registered crops or overlays within the existing source pane, retaining access to the immutable original. Do not fabricate source geometry for manual notes or pretend PDF coordinates are registered without proof. Candidate dismissal/confirmation and correction history must remain distinct from automatic recovery.

## 14. Verified corrected master → transpose lifecycle

**Already safe for the current reviewed workflow.** `Home.handleTranspose` requires VERIFIED and calls `transposeVerifiedReview(review, semitones)`. The request carries expected revision. `ReviewService.transpose` locks/checks revision, obtains verified current document XML and calls the pure XML transposer. It returns derived bytes without replacing the document or writing a new master.

Each requested offset is absolute from the master: +2 followed by +3 invokes two independent master-input transposes; it does not apply +1 to +2. Edits clear displayed result and verification; the outer busy state prevents normal correction during a request, and server revision checks guard stale requests. Direct MusicXML upload transposition is a separate non-review route, not a shortcut around an open scanner review.

Tests inspected include `test_phase4e_workflow.py` mixed-size verified handoff/exports with offsets 0/+2/-2, stale verification, and failure non-mutation; frontend lifecycle tests check corrected-review routing and result invalidation. The literal +2-then-+3 UI sequence should be added as a focused regression in future implementation; this audit's guarantee is also supported by the actual fresh-master code path, not a claim that that exact test already exists.

The missing portion is presentation: corrected/transposed output must share the right pane and keep source comparison visible. Preserve absolute-master routing when integrating that view.

## 15. OSMD limitations and bounded workarounds

The accepted trusted-system renderer fix is outside this task and remains intact. Stable semantic notehead binding already supports distinct chord members and excludes ambiguous/shared/generated continuation matches. Nonnumeric voice IDs and normalized/ambiguous source identities can require fallback. Safe binding is preferable to selecting the wrong canonical event.

OSMD 2.1.2's mixed-entry cue-size behavior is a **visual-fidelity blocker**, not proof that canonical duration/size encoding is wrong. The first note's cue-size state may determine the graphical entry's scale. The current XML representation of ordinary small duration-bearing notes should remain authoritative.

Recommended decision order:

1. Preserve canonical and exported MusicXML independently of renderer behavior.
2. Evaluate a supported per-head rendering hook or narrowly isolated adapter/VexFlow correction; no adequate supported workaround is established by this audit.
3. Consider a presentation-only post-render workaround only if it preserves head/stem/beam/accidental/tie alignment and selection after Fit/zoom, with real mixed-size tests. Scaling just one SVG head is not a complete engraving solution.
4. Until proven, explicitly accept a temporary renderer limitation for a bounded correction milestone, but do not declare full mixed-size visual acceptance passed.

Do not reorder source notes, invent voices, split chords, or insert `<cue>`/`<grace>` to appease OSMD. There is no evidence here justifying a renderer migration or changing the accepted grouping fix. The limitation does not prevent correct manual XML reconstruction; it blocks claiming complete visual fidelity for the real mixed-size case.

## 16. Generalized real-score acceptance walkthrough

The captured Cùng Đem Tin Mừng artifacts are an acceptance fixture, never a production rule. The prior diagnostic establishes source measure 4/system 1/staff 1: normal A4 half (2 quarter units), small C5 half, and a lower tie to the following A4 in measure 5. Raster geometry is near (1770,665); this is fixture evidence, not a correction coordinate rule. OMR lacks recognized source-measure-4 heads/chord/slots/voices while raw fragment glyphs survive. Following A4 is recognized (head 590/chord 2057, projected e16, onset 0, duration 1/2 quarter unit); “Loan” is attached later to G4 e18. Neither missing half nor the relevant tie is preserved in exported XML/review. First loss is recognition (classification A), not renderer layout. No meter-based automatic repair is justified.

The existing recovery reports no automatic reconstruction of these missing halves; recognized-head recovery did not cover raw fragments. The small C5 must not become grace because of size. Whether secondary ownership is independent must remain source-evidence-based.

| Step | Current normal workflow | Required completion |
| --- | --- | --- |
| 1. Choose/add A4 at correct position | Not for empty measure 4; Advanced empty-measure adder exists | Normal empty-measure/position target and add command |
| 2. Set half duration | Named picker works after event exists; initial empty add uses Advanced numeric duration | Named duration during normal insertion |
| 3. Set normal display | New ordinary note defaults normal; no visual size toggle | Explicit independent normal/small control |
| 4. Add C5 at same position | Simultaneous add from A4 works once A4 exists, using pitch steps | Retain command; simple pitch choice improves flow |
| 5. Set half duration | Same-chord insertion inherits half duration | Preserve simultaneity and shared rhythm; separate voice if evidence requires |
| 6. Set small display | Advanced only | Normal size control; renderer fidelity resolution |
| 7. Keep duration-bearing, not grace | Ordinary simultaneous add has duration; explicit conversion is Advanced | Independent normal grace/duration-bearing control |
| 8. Assign secondary voice/part if source requires | Advanced voice label only; no complete independent-part move | Evidence-based ownership/timeline support |
| 9. Select first A4 | Bound distinct notehead selection exists | Test mixed-size scaling and fallback |
| 10. Tie to following A4 | Click-target tie works if compatibility/boundary checks pass; concrete half in empty 2/4 can meet boundary | Source-supported unusual boundaries must also be possible |
| 11. Compare to source | Two-pane source/corrected comparison works | Per-head size fidelity and registered candidate location |
| 12. Confirm reconstruction | Global comparison and candidate decisions exist | Scoped source-match disposition for theory discrepancies |
| 13. Verify | Works only without blocking errors/unresolved candidates | Source-fidelity policy for faithful unusual measures |
| 14. Transpose | Safe absolute verified-master route exists | Preserve routing |
| 15. Compare transposed result to source | Result currently separate below comparison panes | Transposed view in existing right pane |
| 16. Export | Verified corrected export and transposed download exist | Retain guards and distinct master/result identity |

This path is **not complete today** without Advanced, even where later steps already work. Do not treat dependency on a missing first step as proof that later working APIs are absent. Do not reinterpret the source to force the scenario through existing restrictions.

## 17. Minimum implementation sequence before drag-and-drop

1. **First bounded milestone: normal manual reconstruction foundation.** Reuse existing add/property/history APIs for explicit empty-measure selection, add note/rest at the supported start/anchor position, named duration, pitch, independent normal/small and grace controls. Show shared-chord scope. Integrate corrected/transposed switching into the existing right pane while preserving immutable source and guarded master routing. This is not arbitrary-onset or independent-part completeness. Include the missing-half fixture and unrelated scores; no hardcoded song/measure/geometry.
2. **Source-confirmed verification and relationship boundaries.** Categorize technical versus theory diagnostics, add scoped source-match decisions and invalidation, and support evidence-confirmed unusual tie timing. Never modify score content just to Verify. This is a prerequisite to declaring the practical unusual-source workflow complete.
3. **General musical-position/ownership correction.** Add explicit onset and timing-policy commands; time-preserving deletion; normal rest binding; independent voice/part and staff controls; atomic measure moves. Extend the current XML-backed model rather than building an SVG score database. Add written-accidental and key/meter correction with no implicit pitch/rhythm normalization.
4. **Complete relationship/text/structural correction.** Add typed slurs, normal harmony correction, barline/clef context commands, and safe relationship deletion/retargeting. These P1 items complete the broader contract after the first bounded path; their absence must remain explicit.
5. **Integrated evidence and rendering acceptance.** Add read-only unanchored candidate regions and registered source-to-score correspondence, with plain-language manual correction actions. Investigate the mixed-size rendering limitation early in parallel with design, and require its resolution before claiming full real-case visual fidelity. No generalized automatic raw-glyph reconstruction.
6. **Acceptance gate before convenience work.** Test the full generalized half/small/tie path, faithful over/underfill acknowledgment, technical-error rejection, stale decisions, history, voice ownership, semantic XML preservation, rest/empty targets under scaling, and +2→+3 from an unchanged verified master. Repeat browser acceptance for mixed size, interactions and right-pane transposed comparison. Preserve accepted system grouping. Only then consider P2 drag/drop or advanced engraving controls.

Each implementation should remain small and independently reviewable. Not every structural capability must be implemented in the first milestone; do not call a bounded first path a complete correction editor.

## 18. GO / NO-GO and audit checks

**GO** for a separately authorized, bounded manual-correction milestone following the sequence above. The current preservation-based architecture is a sound foundation; targeted additive model/API extensions are sufficient. **NO-GO** for claiming the complete scanner-correction workflow or full mixed-size visual acceptance today, or for prioritizing drag/drop/generalized automatic glyph reconstruction. This audit does not itself begin implementation or Phase 4F.2.

Inspected regression evidence includes backend `test_review_api.py`, `test_phase4e_workflow.py`, `test_phase4f_structure.py`, tie coverage, and frontend visual-review, lifecycle, workspace, score-renderer and source-engraving tests. These cover preservation, guarded handoff, selection, history and grouping subsets; they do not establish missing controls, source-match verification policy, arbitrary placement, rest-browser selection, or a same-pane transpose view.

Documentation-only checks: compare SHA-256 hashes of all 169 pre-existing tracked/untracked files against the pre-audit snapshot; check local documentation links; run `git diff --check` and `git status --short`. No backend/frontend suites, lint or build are rerun because production files and behavior are unchanged. Existing historical test totals are not new audit test totals. Final check results are reported with this document's delivery.
