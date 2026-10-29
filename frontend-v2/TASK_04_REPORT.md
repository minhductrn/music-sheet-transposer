# Task 04 — PDF recognition and manual score completion

Date: 2026-10-25 (America/New_York). Current status: ACCEPTED for the consolidated Task 04 checklist, confirmed by the Product Owner on 2026-10-27 through candidate v0.26. Earlier verification and pending-acceptance entries below are historical. The input/notation exclusions remain unresolved and are not certified as supported. The Product Owner authorized implementation after pre-Task04 checkpoint 5b1e8e4. No Task04 commit/push is performed by this implementation turn.

## Objective and boundary

PDF/image → one real OMR draft → source comparison → explicit manual reconstruction/correction → saved MusicXML → Concert Key and independent instrument transposition. Editing and durable user corrections take precedence over OMR accuracy. Never replace failed recognition with demo music. No agents, LLM calls, Docker or automatic recognition retries.

The immutable accepted Tenor v0.3 package and prior checkpoint remain protected. Legacy frontend changes are outside scope. PDF originals, private MusicXML and generated evidence remain local and excluded from publication.

## Implementation and source contract

App.tsx now sends PDF/PNG/JPEG to the real workspace, with explicit Vocal/SATB/Piano/General profile selection. recognizeSource posts once to the existing recognize endpoint, then creates one review with baseline_musicxml_base64 (when supplied), original upload, omr_artifact and optional semantic_evidence_artifact. It does not resubmit already recovered XML with the same evidence. Recognition failures remain failures.

The left pane retains the original file as a revocable browser object URL, displayed by bundled PDF.js canvas pages or an image element (the native Firefox viewer failed visual verification and was replaced); the right pane edits authoritative review MusicXML. PDF navigation remains manual and no invented note/image alignment is claimed. Initial correction/history uses the existing backend review. The document-correction endpoint preserves session/source/evidence, original bytes and sidecar identities for existing identity-bearing nodes; notes cannot be inserted/deleted or moved between measures through that endpoint. Existing event commands handle additions/deletions. The atomic review edit mechanism, revision preconditions, quotas and Undo/Redo are reused. Source confirmations are invalidated on document corrections.

Save requires an explicit comparison checkbox for PDF/image drafts, cleared by subsequent content edits or history moves. Existing technical errors still block verification. Download retention is separately confirmed. A retained MusicXML file is the durable source; source PDF/evidence and undo history are transient review context. Stage2 uses only saved Concert XML and never reruns recognition.

An explicit “Create empty working score from this source” action is available after OMR failure. It creates an empty staff with a clearly stated 4/4/C/G-clef starting context that the user must correct, not invented recognized notes. Original source validation still applies, so encrypted PDFs remain unsupported by this action.

## Editing coverage and theory-based comparison

The 11 PDFs are representative, not exhaustive. Official reference patterns were inspected in [MuseScore note/rest editing](https://handbook.musescore.org/basics/editing-notes-and-rests), [MuseScore lyrics](https://handbook.musescore.org/text/lyrics), and the [Symphony Pro manual](https://symphonypro.net/manual). They motivate explicit pitch/duration, voice, lyric ownership and custom-tuplet controls. This task does not copy their code or promise full product parity. Their automatic rest filling is not adopted; this application's explicit timing-preservation contract remains authoritative.

| Musical element | Implemented/reused Task04 correction | Limit |
| --- | --- | --- |
| Notes/rests and dotted rhythm | Existing edit/add/delete, pitch/accidentals; Whole through 64th; Dot and Double dot; exact divisions refinement | No silent rhythmic repair; maxima/long/breve/128th+ not exposed in palette |
| Chords/polyphony | Existing explicit same-onset chord insertion; selected event voice/staff edits; explicit insertion location with new voice | Staff count correction is bounded 1–8; no automatic voice assignment or part merging |
| Grace vs small notes | Grace before and slashed grace before, editable pitch; Small remains display size only; grace head binding corrected | Grace chords and all ornamental notation are not universally supported |
| Tuplets | Existing mixed3:2 and equal ratios 3:2,2:3,5:4,6:4,7:4,9:8; each pitch independently editable | Existing nested or ambiguous membership is not guessed; mixed patterns beyond approved3:2 are not added |
| Beams/ties/slurs | Existing explicit beam2/3/4/5/6/8, tie/slur creation/removal/direction; preserved by review/history | No automatic engraving rewrite |
| Meter/key/clef/measure | Explicit selected measure correction, key signature without pitch transposition, clef on selected staff, staves, partial intent, right barline; Add measure exposed in Stage1 | Add measure retains existing single-part/single-staff restriction; mid-measure context changes preserved, not edited by beginning-of-measure tool |
| Lyrics | Existing Unicode input/add/delete/verse; added movement to an explicitly chosen note/verse; segmented lyrics edited individually; next/previous lyric restricted to same part/voice/staff | No guessed legacy-font conversion; PO-disabled hyphen/melisma controls stay disabled |
| Expressions | Explicit fermata, staccato/tenuto/accent/strong-accent/staccatissimo/breath-mark; dynamics add/replace/remove at selected note stream position | Full repeat/volta/ornament editing and arbitrary engraving are not provided; imported unknown notation preserved |
| Persistence/output | Existing local save/reopen, MusicXML and PDF, Concert Key and sax outputs | Multi-part Concert remains editable/savable; Stage2 single-part restriction remains explicit |

## Real sample recognition results

Exactly one engine attempt per provided original was made, without retrying. All originals retained their hashes. Counts below describe draft objects, not ground-truth accuracy.

| PDF | Draft parts/events/lyrics | Result |
| --- | --- | --- |
| 01 TienBuocVaoNhaChua_hn | 1 / 131 / 52 | Draft created |
| 02 DangTrongTinhYeu_pxc | 1 / 89 / 134 | Draft created |
| 03 ThapSangTrongCon | 2 / 109 / 123 | Draft created; multipart limitation applies to Stage2 |
| 04 An Tinh Khong Doi Thay | 1 / 126 / 131 | Draft created |
| 05 Chua Nhat28 Thuong Nien | — | AES-encrypted PDF; backend lacks crypto decoding and rejects encrypted sources. The misleading initial generic damaged-PDF error was clarified. |
| 06 chungcon-venoiday | 1 / 130 / 119 | Draft created |
| 07 DangHonXac_hl | 1 / 132 / 103 | Draft created |
| 08 dangme_hd | 1 / 95 / 141 | Draft created |
| 09 MotNiemTinThac_ga | 1 / 127 / 152 | Draft created |
| 10 THANH VINH22 THANH LAM | — | The provider did not return exactly one score. Its existing error covers both zero and multiple outputs; the retained evidence does not establish which occurred. Manual reconstruction is available; no score was automatically selected or merged. |
| 11 ConGiDangNgai_px | 1 / 78 / 105 | Draft created |

Nine drafts are not nine accurate transcriptions. Meter mismatches, missing material and imperfect lyrics still require correction. No complete ground-truth MusicXML exists for these PDFs, and no invented recognition-accuracy percentage is reported. Multi-page/scanned inputs are not represented by these 11 one-page PDFs.

## Verification and unresolved evidence

- Backend final: 1085 PASS, 3 skipped, two existing dependency deprecation warnings. The heavyweight recognition benchmark was excluded; actual engine attempts are recorded separately above.
- Frontend unit: 46 PASS; typecheck, lint and build PASS at packaging. Large JS bundle warning remains. npm audit also reports three pre-existing development-test dependency advisories (Vitest/@vitest/mocker/tinypool); PDF.js is not listed. No forced unrelated major upgrade was applied. These development dependencies are absent from the standalone runtime.
- Targeted browser PDF handoff/save and explicit manual reconstruction tests were exercised using captured real OMR output or deliberate failure responses. This replay does not itself rerun Audiveris or establish recognition accuracy.
- Final package broad run: 56 PASS and one Tenor header synchronization assertion failed while key detection was pending. The assertion was changed to wait for the resolved key; a targeted rerun is recorded below. Earlier r2 broad package run: 57 PASS. No application change was made for the assertion correction.
- Preliminary development runs retained failures: old expectations that low divisions reject short notes were updated to verify exact refinement and Undo; the default Tenor test now preserves rest entries during octave comparison; 3:2 keeps its accepted actual-number display. Development hot reload occurred during a broad run; that run is not final package evidence.

Private evidence: frontend-v2/evidence/task04/real-omr-results.json, PDF-*-recognition.json and review projections, backend-regression-final.log, recognition-handoff tests, document-context/tuplet tests, and production-results.json. Original sample content is not published.

## Candidate delivery

Standalone candidate: frontend-v2/evidence/task04/music-sheet-transposer-task04-v0.1-r3/ and adjacent tar.gz/SHA256. It bundles frontend/backend/runtime and a Task04 Vietnamese guide, retains the previous runtime ABI and requires the already installed external Audiveris plus vie/eng models. start.py uses an omr_enabled manifest flag; old frozen Task03/Tenor bundles remain MusicXML-only and byte-identical.

Run `python3 -B /home/dtran/music-sheet-transposer/frontend-v2/evidence/task04/music-sheet-transposer-task04-v0.1-r3/start.py --port 5184`, then http://localhost:5184. No existing user server is replaced. The builder refuses overwriting existing package outputs.

PC-01/02: draft-only OMR, explicit corrections and no invented content. PC-03/04/05: authoritative saved Concert, independent written instrument files, preserved identities/provenance/history and XML relationships. PC-06: user-selected musical decisions and comparison. PC-07: existing regression protection. PC-08: final Product Owner acceptance remains pending.

This is not a claim of complete support for every notation or all 11 input files. The two recognition exclusions and bounded editor limitations above must be considered in the Product Owner decision; do not label the overall unrestricted objective complete solely from test PASS.


## Final package review

Candidate r3 archive SHA256: `64d1707a217ac0f89d636b7d2b034d7f55a8ba610a49251ba05b5f8a5fdee8b1`.

Real packaged HTTP pipeline on PDF11: PASS. The packaged Audiveris engine created a 78-event draft; an explicit test pitch/Unicode verse correction survived Undo/Redo, verification, MusicXML save and reimport. Alto/Soprano/Tenor outputs retained that lyric; the saved Concert bytes remained unchanged, and the retained source PDF matched the upload. This is automated correction evidence, not manual confirmation that the transcription matches the source.

Visual source review found that the first native PDF iframe could not display the original in Firefox. It was replaced with bundled PDF.js and a local worker, with cancellation/cleanup, responsive width Fit and a 40-million-pixel display budget. The final screenshot was visually checked and shows the actual source notation alongside the editable working score. Tests now wait for rendered page content instead of accepting iframe presence as proof.

Technical Lead source review inspected import/recognition-to-review handoff, identity-preserving corrections, revision and history behavior, source-confirmation invalidation, save/download authority, per-note grace/tuplet rhythm, verse/voice ownership, package isolation and source protection. Source code and artifacts were reviewed in this turn; no separate AI agent or external reviewer was used. The unresolved PDF05/PDF10 cases and broader notation limits above remain explicit, so no unrestricted all-input completion or Product Owner acceptance is claimed.

Protection recheck: all 619 pre-existing dirty/untracked files, all 11 PDF inputs and the accepted Tenor archive remained byte-identical. Git HEAD remains pre-Task04 checkpoint 5b1e8e4; index remains empty. The Task04 application runs separately at http://localhost:5184; existing user application processes were not replaced.


Final targeted production rerun: **4 PASS, zero failures/skips** (three Task04 workflows and Tenor register). Together with the unchanged final-package broad run's 56 passing cases, all 57 unique browser cases have passing evidence; the intermediate failed synchronization assertion and its correction remain recorded, not hidden. Final typecheck/lint PASS after the test correction. Backend 1085 PASS/3 skipped and frontend unit46 PASS remain as stated above. Evidence: production-r3.log and production-targeted-final.log.


## Sample10 OMR diagnostic follow-up — actual two-score output confirmed

The Product Owner requested inspection of the OMR report after identifying sample10. One bounded diagnostic rerun used the same SATB profile and existing Audiveris/model paths, with retained output and console logs. No application source or accepted runtime was modified. The original PDF checksum remained 164bff6eaf1f6122c4f36b02fcb109a9275872577a6053a414fe7b99ce9ab829.

Audiveris exited successfully (code0, 73.98 seconds). The engine log explicitly says `Created scores: [{Score 1}, {Score 2}]` and exported exactly two MXL documents:

- input.mvt1.mxl: two Voice parts, each with 5 recognized measures and29 note elements; corresponds to the initial two-staff SATB response. These are recognized counts, not certified correct bar/note counts.
- input.mvt2.mxl: one Voice part with14 recognized measures and45 note elements; corresponds to the later single-staff verses.

The retained book.xml independently declares two scores: the first has two logical parts, the second one. The physical PDF has a two-staff response followed by single-staff verse systems. Thus the output split is established; explaining why Audiveris split them at the changed layout is an inference consistent with those artifacts.

The immediate application rejection is the existing `len(scores) != 1` guard in backend/app/music/recognition/audiveris.py, not an Audiveris process failure or total absence of recognized music. Do not choose the first file automatically, discard the lower staff, or silently concatenate differing part structures.

Additional recognition issues remain: MeasureFixer reports no target duration for the four subsequent systems (local measure IDs1–14), requesting time-signature checking. Recognized lyrics contain incorrect Vietnamese text and verse numbers. Both movement drafts therefore require musical/voice/verse review; engine exit0 does not certify transcription accuracy.

Private retained evidence: evidence/task04/sample10-diagnostic/result.json, audiveris-console.log, output/input.omr, two original MXL exports, converted movement1/2 MusicXML drafts and validation.json. These artifacts are diagnostic drafts only and do not change the canonical Concert Score.

The Product Owner separately excluded sample5 encrypted-PDF support from Task04 scope in the preceding follow-up. Sample10 remains a real multi-output handoff issue for future correction, now with concrete evidence rather than an ambiguous error. No implementation change or Git operation was made during this follow-up.


## Product Owner correction follow-up — key, lyrics, objects and E7 dots

Implementation in progress on the next isolated v0.2 candidate; acceptance remains pending. The Product Owner supplied concrete evidence of an initial three-sharp signature being displayed incorrectly, direction text being mistaken for lyrics, objects that could not be selected/deleted, missing chord symbols, and a missing dotted-quarter chord under E7. These instructions authorize the bounded corrections below, not invented musical recovery.

- The original PDF01 MusicXML contains its first key instruction (three sharps) only at measure17. The renderer had applied it to the initial section. A disposable rendering-only XML adapter makes the initial neutral signature explicit before the first instruction and preserves all subsequent key changes. It does not change saved XML, pitch, alter or accidental. The header no longer guesses C/Am tonality from chord labels when initial key data is absent. An inline XML declaration is retained so OSMD does not interpret serialized XML as a URL. Reference distinction: [MusicXML key](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/key/) encodes key signatures separately from individual note pitch/accidental data.
- Raw PDF01 output stores the long misrecognized first lyric lines under direction/words. Font substitution cannot create lyric ownership. The new text-to-lyrics tool requires explicit user-corrected syllables, destination notes and verse numbers; no note assignment is proposed automatically. Original text removal is an explicit checkbox. Conversion is atomic, refuses collisions and supports Undo/Redo/export/reimport. Existing lyric hit mapping is restricted to actual part/staff/voice/onset.
- Text uses independent hit rectangles over its rendered bounds; duplicate render copies with the same sole canonical owner remain selectable without guessing among different XML objects. Select selects text; Text edits it. Delete removes the selected text and retains unrelated notes. Pedal marks have explicit revision-bound identities and an object picker; a scoped renderer adapter identifies the actual native SVG instance during its single draw, restores all hooks, and permits direct selection. Zero-size native pedal boxes are not guessed. Stale mark selection cannot delete another object after a revision change.
- Rest now exposes Whole/Half/Quarter/Eighth/16th/32nd/64th rest glyphs. Selecting a gap in Rest mode no longer switches silently to Notes. Explicit insertion retains voice/staff/timing ownership.
- Chord symbols can be added at a selected note, edited, moved or deleted using existing harmony XML with bounded new move/delete commands. Root, accidental, quality and suffix are user choices, including explicit Bm(b5) spelling; no missing chord is inferred.
- Both single notes and chord members support Dot. The confirmed E7 source case is measure26: first B4/D5 chord lasts1 beat, the following eighth chord starts at1 and lasts½ beat, leaving the bar at1½ instead of2. The dedicated “Missing dot +½” correction sets the first chord to1½ and advances the following eighth chord to onset1½, yielding exactly2 beats. Pitches/accidentals remain unchanged. Ordinary Dot continues to preserve existing onset placements; the explicit missing-dot action corrects the imported stream. Single-note and chord cases both have data-level Undo tests.
- Repeated recognition warnings are collapsed/grouped by type, with affected parts/measures when supplied. They are advisory and never auto-correct notation.

New backend verification: six focused correction tests PASS, including atomic lyric mapping, pitch/accidental/voice preservation, E7 single/chord timing, pedal deletion with shared text preserved, harmony add/move/delete and stale mark rejection. Broader backend run before the final stale-mark guard:1090 PASS,3 skipped; final six-case rerun covers that guard. Frontend targeted correction verification and frozen-package results are recorded when complete below. Intermediate render failures were retained: missing XML declaration caused URL interpretation; native pedal markers expose no useful bounding box/ID unless captured at actual draw; direct focus on duplicated glyph text was replaced with dedicated hit targets. No failed attempt is called PASS.


### Additional PO direction — composition first (2026-10-26)

PO requested rectangle selection of multiple notes, deletion/conversion of groups, freely correcting pitch/accidentals/missing notes, removing false OMR expressions, and rhythm warnings under Validate. Implemented bounded additions: a mouse rectangle selects exact rendered note identities; one atomic delete command removes that selection with one Undo while preserving unselected timing and source; selected IDs can enter the existing Groups workflow. Existing explicit staff/onset/voice insertion, pitch/accidental controls and tuplets are reused. Dynamics, wedges, metronome/segno/coda and pedals have revision-scoped selectable/deletable identities in the OCR object picker. No automatic composition or chord-based accidental inference. Recognition/rhythm warnings are shown under Validate, without interrupting editing. Technical XML parse/ownership protection remains to avoid corrupt files; musical measure-completeness warnings are advisory.

PC-01/02/05/06 apply directly; PC-03/04 saved Concert and instrument isolation retained; PC-07 regressions and PC-08 PO acceptance remain mandatory. OMR accuracy on arbitrary key signatures, system layout, voices/verses is not certified by these editor changes. PDF-02 retained recognition is evidence of imperfect initial OMR, not a correct final score. No unsupported claim that all MuseScore/Symphony Pro features exist.

Intermediate verification: v0.2 broad run57/60 passed; two summary selectors needed disambiguation and a curve drag crossed the bottom of the900px viewport. Follow-up revealed a real-PDF test must wait for Redo to settle before its next correction. v0.3 added rectangle and symbols; tests identified Add measure must remain first in the accepted rail. Final candidate results follow below; failures are not treated as accepted.


### Final frozen candidate v0.4 — 2026-10-26

Status: **TECHNICALLY VERIFIED for the bounded correction follow-up; Product Owner acceptance pending.** This does not certify OMR transcription accuracy across all sources, and does not accept Task04 as a whole.

- Frozen package: `frontend-v2/evidence/task04/music-sheet-transposer-task04-v0.4.tar.gz`; SHA256 `ff3d802ec144c38b2d5205e9faf4f008a4aa6938d0e8125b38c3b824cc85a85c`.
- Candidate running at `http://localhost:5185`; health200. Existing5184 session retained, also health200. No migration or overwrite of its unsaved score.
- TypeScript typecheck, ESLint, production build PASS;46 unit tests PASS.
- Backend full suite:1105 PASS,3 skipped,2 existing dependency deprecation warnings. Evidence `followup-backend-final.log`. The first broad run had9 comparison failures because new mark identities include a current-revision prefix; the final test compares full musical data plus stable mark suffix and asserts each prefix matches its review revision. No note identity or XML check was removed.
- Frozen-package Firefox suite:61/61 PASS in4.9min, including real PDF replay, E7 missing-dot timing, text/lyrics/harmony edits, mouse rectangle selection/delete/Undo, false dynamics deletion, MusicXML persistence, Stage2, PDF, Fit/zoom, Home and prior accepted Tenor behavior. Evidence `followup-production-final.log`, `followup-production-results.json`. Curve drag tests now scroll the curve into the viewport before a35px drag; prior release crossed outside the900px browser viewport and never delivered pointerup. Add measure remains first in the Edit rail.
- Actual PDF-02 retained OMR XML: measure26 group e-63..e-67 deleted together, all unselected musical events unchanged, one Undo restores original XML bytes exactly. Tie candidate lists correctly drop deleted IDs; these lists are available choices, not actual tie links. Evidence `sample02-selection-proof.json`. It also identifies editable p and ff directions. No OMR rerun or edits to the user's open score.
- Protected619 preexisting files unchanged; accepted Tenor archive and11 original PDF hashes unchanged. Frozen manifest source hashes match current application and launcher/guide. Git HEAD remains5b1e8e44f981cf54c4d7ccf0461f10e6435f278a; Git index empty. No commit/push performed.

Technical Lead source review: batch deletion runs on a cloned document, validates all selected IDs before mutation, removes chord followers before advancing heads, preserves surviving timing, and commits one history entry. Rectangle hit testing uses rendered note bounds and canonical IDs; it is disabled in read-only source. Existing Groups receives the explicit selection; no automatic tuplet, pitch, chord or expression inference. OCR mark deletion is limited to supported direction elements, rejects stale revision identities, and preserves other direction content. Validate only reveals diagnostics; the edit path does not enforce musical measure completion. Original PDF/Concert and instrument independence remain protected. Unknown/unsupported MusicXML structures may still need explicit correction; this is not feature parity with full notation editors. PDF05 exclusion and PDF10 multiple-output limitation remain documented above.


### Composer text selection follow-up — v0.5 (2026-10-26)

PO reported that “Nguyén” cannot be selected in Text mode. Actual PDF01 retained XML contains identical `creator type=composer` and `credit-type composer/credit-words` values (“Héi Nguyén”). The renderer's ambiguity guard excluded both. The fix recognizes only the unique explicit metadata/printed-composer pair, gives its rendered copies one editable printed-credit owner, and patches that exact pair together in one Undo step. Unrelated repeated text is not guessed or rewritten. Original PDF and notes remain unchanged (PC01/02/05/06/07).

Typecheck, ESLint and production build PASS. Nine focused backend tests PASS; three focused frozen-package browser tests PASS, including direct composer click, Vietnamese Unicode edit, Undo/Redo, export with both composer values corrected and prior text/lyric editing. Earlier invocation from frontend failed collection due to backend import path; rerunning from backend passed. Initial packaging invocation lacked Node PATH; rerunning with the configured runtime passed. No full-suite rerun claimed for v0.5; previous v0.4 suite61 browsers/1105 backend remains the broader baseline.

Frozen package `music-sheet-transposer-task04-v0.5.tar.gz`, SHA256 `f525e82281663d10ae050b198731c0106f286e15fead83afb40e1145db6ae5af`. Source manifest matches current application, protected619 files unchanged. New app at5186;5185 retained to protect unsaved edits. Technical source review confirms explicit paired ownership, no generic duplicate-text inference, and atomic history. PO acceptance pending; no commit/push.


### Title selection follow-up — v0.6 (2026-10-26)

PO reported the PDF01 title cannot be selected in Text mode. Actual retained source has identical movement-title and untyped credit-words. The same duplicate guard excluded it. Extended only the unique title metadata/printed-credit combination (one printed/untyped credit, distinct movement/work-title roles, identical text); unrelated equal direction text remains excluded from guessing. Patching that explicit title group updates the displayed and persisted title together in one Undo, without touching notes or composer. PC02/05/06/07 apply.

Typecheck/build, ESLint,10 focused backend tests and4 focused frozen-package Firefox tests PASS. Browser evidence covers direct click, Vietnamese title correction, Undo/Redo, saved XML containing both corrected title values, unchanged accidentals and composer/text regression. No new full-suite result claimed. Frozen archive music-sheet-transposer-task04-v0.6.tar.gz SHA256 `10fefe3e4cad93ba0afec7f5dc64e8122548732192d97e1a13664e8f57ae4e15`; source manifest matches and619 protected files unchanged. App5187 includes both composer and title fixes; old user sessions remain untouched. Technical review: limited explicit pairing, no generic text flattening or automatic OCR rewriting. PO acceptance pending; no commit/push.


### Composition controls and shared-direction deletion — v0.8-r1 (2026-10-26)

Latest PO steering is incorporated: user controls harmony and its position, Shift+mouse rectangle is an alternative to Select area, Dot/Double dot are grouped, and false OCR words/pedal/dynamics must be removable. No automatic harmony suggestion or rewriting.

- Text deletion now retains an empty words anchor when its direction contains independent sound/extensions; the visible unwanted text is removed while original playback data remains. Pedal/dynamics deletion uses an empty direction-type/words anchor for the same case. No print-object attribute is invented on words (checked against MusicXML4 reference https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/words/). The initial v0.7 draft used that unsupported attribute; v0.7-r1 and later removed it before handoff.
- Pedal hit targets cover the complete rendered bounding area; hollow glyph centers no longer miss mouse clicks. Dynamics get explicit canonical mark hit targets by measure/staff/onset. Selecting a text/mark clears a stale voice-choice popup.
- Shift+drag and Select area both select canonical note IDs for one atomic delete/Undo, including chord members; read-only source is not editable.
- Dots are one collapsible Edit group. Chords has an Edit-rail entry. Existing note anchors remain supported; user can instead choose any measure and rational beat-from-start, including empty areas, then add, edit, move or delete a harmony. Fractional placement refines divisions exactly without changing musical note timing. Chord roots/qualities/suffixes are explicit user choices; no key-based harmony rewriting.
- Actual retained PDF01 proof `actual-pdf01-marks-proof.json`: delete and Undo PASS for pedal m-1, pedal m-5, sf m-7, pp m-19. Each deletion keeps every note XML node unchanged; Undo restores original bytes. No recognition rerun or edits to the user's live review.
- Eight focused browser cases PASS on v0.8 (composition-targeted.log), including both rectangle modes, pp direct click, Ped. shared sound, free G placement and editing, title/composer, Unicode and export. v0.8-r1 only additionally clears stale voice menus; full-suite results follow. The prior Ped. browser attempt failed because its hollow SVG center intercepted mouse clicks; the new transparent hit rectangle resolves it. One old backend test expected refusal to delete final text sharing sound; updated it to require deletion with sound preserved, matching PO's new requirement. The failure is retained in composition-backend.log.

The received edited Task01 checklist records historical UX/demo acceptance only; it is not treated as acceptance of Task04 OMR or these changes. PC01/02/05/06/07/08 remain applicable. No commit/push; acceptance remains pending.


#### Final consolidated candidate v0.8-r2

Archive SHA256 `8c7743e63d50f9c9a83a779708d272920e13c72df2a421d9329628540d3461f0`; current source manifest matches,619 protected files unchanged. Running at5188; user's5185 remains untouched. The private unpublished5188/r1 process was replaced with r2 after checking its exact PID/command.

Full r1 backend suite1110 PASS,3 skipped. Full r1 Firefox suite64 PASS/1 failure: an instrument tie-render assertion returned0 during one run; isolated rerun of both related Fit/Up-Down tie tests2/2 PASS with no source change (composition-ties-rerun.log). This timing-sensitive failure remains recorded, not silently relabeled as a clean full pass. All eight focused correction-browser cases PASS in both r0 and r2. Final r2 backend-focused suites30 PASS, including shared words/sound deletion, pedal sound flag removal and user-chosen fractional harmony placement; production build/typecheck and prior lint PASS. Final r2 change only removes symbol-owned sound attributes (damper-pedal for pedal, dynamics for dynamics) when no same-kind mark survives, preserving independent tempo and other sound properties. This matches actual PDF01's damper-pedal=yes alongside false Ped. and avoids reappearance from playback metadata. Final targeted browser test now explicitly uses damper-pedal=yes and verifies its removal with other sound values preserved. No final full-suite rerun claimed after that bounded change.

Technical Lead review: explicit revision ownership; no automatic musical decisions; one Undo per command; structural empty anchors have no invented visible symbols; refinement preserves note timing; direct mark hit areas avoid hollow-glyph misses and note/voice popup conflicts. Relevant correction workflows are technically verified; broader OMR acceptance is pending PO review and the retained intermittent instrument rendering test is a regression-test limitation. Original PDF, Concert and instrument isolation retained. No commit/push performed.


### Mandatory direct-editing design and unchanged MusicXML input — v0.9-r6 (2026-10-26)

PO explicitly requires visual editing on Working Score as a mandatory design criterion, the same composition tools in all stages, and Edit Only differing solely by hiding Original Source. PO also authorizes instrument generation directly from an unchanged imported MusicXML without an extra Save. Changes are implemented within the shared RealWorkspace; no parallel editor/workflow or new technology.

- Removed the four auxiliary rows from score layout. They are hidden in an optional floating More panel. Common actions use direct object hits: note tools beside selection, inline text/lyric edits, small Delete action beside text/marks, direct harmony clicks, Chords then click a note/staff position to write harmony. Right-click a staff opens its measure/meter/key/clef tools with the measure preselected. Right-click is excluded from note/curve/box gestures, so it cannot accidentally create a Slur. Concert Key also opens as a floating panel. Advanced OCR recovery remains optional, not required for ordinary edit/delete.
- Note tools are fixed overlays, repositioned from current rendered note bounds after zoom and kept usable after dragging/duration changes. Auxiliary panels close after insertion/measure commands. Short-screen score viewports have bounded heights; a721x590 Edit Only test checks the score top does not move when tools open (direct-edit-only-narrow.png).
- Edit Only available for both Concert and instrument editors. It only hides source/divider and expands Working Score; selection, tools, committed/unsaved edits and history stay in the same component/document.
- Added a separate imported-file baseline, not a fake saved receipt. An unchanged MusicXML is an existing durable input and can generate instrument outputs immediately. Edited XML or applied Concert-Key changes still require Save. PDF/image OMR does not receive this bypass. Opening another MusicXML replaces the baseline and displayed source without a reload. Source files are not written. Labels distinguish unchanged imported file from a newly saved version. This is the PO-authorized bounded clarification of the saved-input rule; it does not allow unsaved corrections into transposition.

Verification: typecheck/lint/build PASS;46 unit tests PASS in the v0.9 series. Initial full r2 browser run59 PASS/8 failures, retained in direct-full.log. Actual regressions included context tools closing after drag/duration and floating-panel position after zoom; fixed in r4. Test issues included dragging a tuplet outside the900px viewport, choosing an unchanged octave, and5s backend waits under load; corrected to visible centered targets, a different octave and bounded waits. r4 targeted regression20 PASS/3 failures (direct-regression-final.log), followed by6/6 PASS including all remaining failed cases (direct-last-rerun.log), with actual MusicXML, concert transposition, save/reimport, PDF and OMR replay. No claim of a clean final full-suite run is made.

Direct r4 acceptance-flow tests4/4 PASS, including a second Open MusicXML with zero verify/Save calls. r5 right-click testing exposed the nonprimary pointer gesture collision; fixed in r6. Final frozen r6 direct tests4/4 PASS (direct-handoff-final.log): no score layout shift, direct dynamics/text/harmony actions, right-click without Slur creation, Compare/Edit Only state retention, instrument Edit Only with all tools, pristine MusicXML direct transpose, short screen and fresh input baseline. The prior backend remains unchanged from v0.8-r2's30 focused PASS and broad1110 PASS/3 skipped baseline; no backend rerun is claimed for these frontend-only changes.

Technical review: source remains read-only; shared component preserves stage isolation and note ownership; overlays do not insert document-flow rows; each mutation still supports original history/export contracts; the imported snapshot is only eligible when XML is unchanged; raw file bytes retained and no new Save asserted. More preserves recovery paths for ambiguous OMR objects without automatic guessing. Relevant changed workflows are technically verified; Task04 and OMR accuracy still require PO acceptance.

Final archive `music-sheet-transposer-task04-v0.9-r6.tar.gz`, SHA256 `b78f2aea82af9459d8a67617c4c7448989ccb8e18b8233fbca65d8ca478c0354`. Manifest source hashes match current source/guide;619 protected files unchanged; Git index empty, no commit/push. Candidate running at5189;5185 retained. Full-source glyph/transcription accuracy on all PDFs remains outside these editor checks; PDF05 exclusion and PDF10 multi-output limitation remain as documented.


### Explicit discard before Home — v0.10 (2026-10-26)

PO authorizes leaving without Save. The Home dialog now offers Save routes, Continue editing (default focus), and explicit “Discard changes and go Home”. Discard exits the shared workspace and drops unsaved Concert and all instrument variants through normal unmount/session cleanup; it performs no Save, export or file write. Dialog explains the scope and keeps saved files unchanged. Busy edits, active save receipts and inline text/lyric drafts cannot be bypassed. Escape/Continue editing preserves the session. This is explicit user control under PC02/05/06, not silent loss. No automatic discard or extra confirmation loop.

Typecheck, ESLint and frozen production build PASS. Six Home browser tests PASS on v0.10 (home-discard-browser.log): four prior Home/save/failure/busy cases and two explicit-discard cases for Concert and Up/Down instrument variants. Tests assert zero verify/Save calls and zero downloads on discard, Home import shown, fresh import without old edits, and normal Save/Continue paths retained. No full-suite/backend rerun claimed for this bounded frontend change.

Technical review: guarded onExit only after explicit discard click; existing cleanup removes transient sessions, never saved files. Home from instruments exits the parent workspace, so no hidden variant remains. Final archive SHA256 `637a48d1a950c1d0505fca8c4041e806e3ece381a28a79eb4bd0d25639e8db07`; manifest source hashes and619 protected files PASS. App5190; user's5189 retained. PO acceptance pending; no commit/push.


## 2026-10-27 — Direct Add Chord and merged OCR text (v0.11-r2)

PO requested Add Chord → choose score position → type the harmony; existing symbols open inline editing. Replaced the normal long harmony form with a small inline input (Enter commits, Escape cancels, direct Delete for existing symbols); kept detailed tools optional. Bm, G, E7 and literal suffixes use the existing canonical harmony endpoints. No harmony is inferred from OMR or selected automatically. Note-position insertion uses the existing note anchor, avoiding OSMD ignoring a bar-start offset. The separate arbitrary empty-time offset path remains available but was not independently verified in this revision. Slash-bass notation is explicitly rejected by the inline parser rather than silently stored with incorrect bass semantics; no new bass implementation is claimed.

OSMD merges adjacent direction words into a single SVG label. Added unique literal-fragment hit geometry for canonical direction words, preserving independent original IDs; no fuzzy OCR matching or automatic lyric classification. Verified the retained PDF01 “2. Nên…” fragment can be deleted directly and restored with Undo without changing note projection. Other source fragments remain independent.

Verification: lint PASS; typecheck/build PASS (existing large-bundle warning); Vitest 48 PASS; final Firefox direct suite 6 PASS, including Bm/E7 MusicXML export-byte reimport and canonical onset preservation, Edit Only tools, Stage2 independent editing, unchanged MusicXML direct transpose, narrow viewport, merged text fixture and actual retained PDF01. Initial candidate had 3/5 failures: new chord offset rendering, stale test label after rename, and unsuitable merged-word fixture; repaired and final rerun passed. Backend unchanged; no claim of a new full backend rerun. 619 protected files unchanged; frozen source manifest matches. Previous user port 5190 remains untouched. Candidate v0.11-r2 on port 5193. No commit/push; Task04 acceptance remains PENDING. Addresses PC01/02/05/06/07/08 and applicable Gates1–3 within this correction scope; PO acceptance is separate.


## 2026-10-27 — Text-mode Delete object and active session renewal (v0.12)

User screenshot on5193 shows an expired/missing review error while editing OCR words in Text mode. Evidence: MemoryReviewStore uses a fixed3600second lifetime, without renewal; RealWorkspace only displayed Delete object in Select mode, while Text opened an input without deletion. Added explicit existing-session POST keepalive, called once and every60seconds while the editor document is visible, also on visibility return. Renewal changes only expiry; it preserves XML, revision, source, sequence and undo/redo, remains quota bounded and cannot resurrect an expired session. Hidden or closed editors do not keep renewing. No reimport, OMR, automatic replay of edits, or fabricated restoration occurs. An already expired5193 server session is not recovered by this update; its browser and process remain untouched.

Added Delete object beside the direct Text input, preventing pointer-induced blur/accidental PATCH. Failed text deletion now retains its input/selection rather than hiding the controls before server success. No new advanced panel or score layout displacement.

Checks: backend test_review_api.py plus test_task04_lyric_conversion.py61PASS (two preexisting deprecation warnings); frontend48unitPASS; lint, typecheck, buildPASS (existing chunk-size warning); final frozen-bundle Firefox7PASS, including Text-mode delete with zero blur PATCH, Undo, initial keepalive, literal merged OCR text and retained PDF01. Initial build caught test TypeScript errors (fixed). Initial browser run6PASS/1failure because its synthetic fixture combined words+dynamics in one direction-type, which OSMD did not display; corrected the fixture to visible independent words and reran all7PASS. Source manifest matches;619protectedfiles unchanged. Candidate runs5194;5193preserved. No commit/push. PC02/05/06/07/08 apply. Technical review: minimal additive expiry renewal; no content/history mutation, no stale-session resurrection; actual failed operation remains reported. PO acceptance pending.


## 2026-10-27 — Direct sf glyph selection at zoom (v0.13)

User reported an incorrect OMR sf symbol must be deletable. Reproduced on retained PDF01 at50%: clicking the visible glyph did not show Delete object. The earlier geometry used estimated OSMD logical coordinates scaled by zoom; the actual SVG label position differed. Changed dynamics hit geometry to the exact semantic expression Label.SVGNode bounding box transformed through its owning SVG screen matrix. Canonical measure/staff/onset identity matching remains; no fuzzy matching, blanket removal or note change. Direct click now opens Delete object independently of note tools.

Evidence: initial real-glyph test FAILED onv0.12; v0.13 frozen Firefox direct suite8PASS. Additional real-PDF sf deletion testPASS verifies canonical note projection unchanged and Undo restores sf. Lint/typecheck/buildPASS (preexisting bundle-size warning). No backend changes this revision.619protectedfiles unchanged; source manifest matches. Candidate5195; older5193/5194remain untouched. No commit/push; PO acceptance pending. PC02/05/06/07 apply. Technical review: actual native glyph coordinates replace estimated geometry; server mark-only deletion and optimistic revision handling retained.


### 2026-10-27 — Saved/reopened PDF01 Tâm tư line follow-up

PO screenshot remains on5193 and shows a reopened MusicXML score. Added targeted Firefox regression against frozenv0.13: import retainedPDF01XML, reopen serialized MusicXML, zoom60%, click the actual visible “Tam tu’ con…” SVG text, Delete object, confirm line absent. PASS1/1 (tam-text-results.json). No application source change or new candidate required. Opened5195 in a new Codex browser tab; prior5193 untouched. This verifies the retained sample and roundtrip, not the user's unseen current in-memory document. PO acceptance pending.


## 2026-10-27 — Explicit Concert Key confirmation with missing initial key and modulation (v0.14)

PO screenshot shows A minor explicitly confirmed but Apply fails because the XML lacks an initial key. Inspected engine also rejected later key changes in the retained sample. Changed the explicit confirmed transpose path only: it materializes the user-confirmed initial signature/mode in the independent output when absent, never infers mode from chords, and moves later traditional key signatures by the same fifths delta while preserving their own declared/absent modes. All pitches and chord roots/basses retain the same chromatic/diatonic transposition algorithm. Source XML stays immutable. Inspection now reads an explicit initial key despite later modulation; it still refuses missing initial key without confirmation. Incompatible initial signatures, conflicting parts/staves, unsupported modes/metadata and resulting signatures beyond seven sharps/flats still fail explicitly. No automatic OMR pitch correction or silent respelling of key changes. No-op output byte identity retained.

Verification:47 backend Concert Key/workspace testsPASS, including confirmed missing-initial-key synthetic modulation in Up/Down, unchanged unrelated notation and reimport. Initial regression caught no-op serialization change; restored exact byte no-op and reranPASS. Frozen Firefox retainedPDF01 Apply Am→Cm and UndoPASS. Lint/typecheck/buildPASS (existing large chunk warning).619protectedfiles unchanged; source manifest matches. Candidate5196 includes preceding sf/Text/keepalive fixes; previous ports untouched. PC02/03/05/06/07/08 apply. Technical review: explicit confirmation gates missing-key completion; later keys keep relative signature and mode, no supported-range overflow hidden. No Git mutation; PO acceptance pending.


## 2026-10-27 — Inline lyric verse selection (v0.15)

PO could only find verse1 while typing directly on score. Added Lời1/Lời2/... selector and +Lời inside the same anchored lyric input. Verse2 is available before any verse2 exists; switching commits the current syllable to its own number before opening the other verse. Tab retains selected verse and note voice/staff navigation; Escape cancels. Existing per-note tools remain. Lyric command failures retain the input instead of clearing it before success. Source/voice are not inferred or reassigned.

Verification:48unitPASS; lint/typecheck/buildPASS (existing bundle warning). Final frozen Firefox direct suite11PASS including switching uncommitted verse1 to2, independent syllables on same note, Tab within verse2, reopening verse1, +verse3, and MusicXML byte reimport retaining verse numbers and note association. Initial compile caught nullable review checks; fixed. Initial test raced the prior save; added wait for enabled editor and reran.619protectedfiles unchanged; source manifest matches. Candidate5197 contains Concert Key and prior deletion fixes. No Git changes/PO acceptance implied. PC02/05/06/07/08 apply.

### Dotted-rhythm OMR comparison raised while verse work completed

Inspected retained raw PDF01 XML against PO screenshots, without mutating any live user review. Divisions4: measure15 “Danh Chúa” durations3,2,2,2 (dotted8th+8th+8th+8th) totals9/4quarterbeats rather than2. Source screenshot shows dotted8th+16th then two8ths. Reference measure17 correctly has duration3+1+2+2 with matching chord members. Measure21 similarly3+2+2+2; measure23 starts2+1+2+2, missing the leading dot seen in source. Measure19 has five chord groups3+2+2+1+1, requiring full source comparison rather than blindly copying a two-note pattern. These are OMR recognition errors, not declared accepted or automatically corrected. No claim that this verse UI update improves recognition accuracy. Manual rhythmic correction UX and actual onset behavior remain to be verified before claiming this family resolved; no automatic inference from reference annotation3 applied.


## 2026-10-27 — Direct note-duration correction for confirmed OMR rhythm errors (v0.16)

PO could not perform the proposed note-duration correction. Added a visible Trường độ selector within the selected-note popover, with Vietnamese note-value labels. Selecting a value explicitly calls the existing canonical event duration edit with preserve_onsets=false, so subsequent sequential events in the current measure advance according to the corrected duration; existing rail palette's preserve-onsets behavior is unchanged. Chord-scope remains the backend default, so aligned members change together. No new automatic OMR correction or hidden validation-driven change.

Verified actual retained PDF01 measure15 (Danh Chúa) and chord measure21 by mouse: Select→notehead→Trường độ→Móc kép. Before3/4+1/2+1/2+1/2; after3/4+1/4+1/2+1/2 with onsets0,3/4,1,3/2. Actual measure duration2quarterbeats, pitches unchanged, Undo and exported-byte reimport checked. Browser's generic SVG scrollIntoView did not scroll the score viewport; initial tests failed outside viewport. Test now explicitly scrolls the actual working viewport and clicks the visible notehead, with no keyboard/forced-click substitute. Final frozen Firefox full direct suite13PASS, including verse2, Concert Key, sf/text deletion and duration fixes. Lint/typecheck/buildPASS (existing chunk warning). Backend unchanged; explicit positioned events still follow existing backend positioning semantics; no universal timeline-reflow claim for every polyphonic XML arrangement.619protectedfiles unchanged and manifest source match. Candidate5198 includes all preceding fixes, older sessions preserved. PC02/05/06/07/08; technical review limited to explicit sequential imported-note/chord correction, not automatic recognition accuracy. No Git commit/push or PO acceptance implied.


## 2026-10-27 — Lyric input anchored to score and scroll retained (v0.17)

PO reported inline verse input detached from the edited line and editing later lyrics scrolled the score to the start. RenderedScore now snapshots its own viewport scroll before removing SVG content and restores it after rendering; explicit Fit still resets its own view intentionally. Lyric focus uses preventScroll. The input resolves the selected event/verse's actual lyric SVG label (notehead fallback for a missing lyric), updates position on scroll/resize and after render, and brings only an offscreen destination note into the working view during navigation. Source pane scroll remains independent. No musical content, voice, verse or persistent data rewritten by positioning.

Verification: new Firefox regression on retainedPDF01 at1338x590 begins at lower notee42, edits+Tabs through e43/e44/e45, checks nonzero retained working scroll, destination visibility, input movement on manual scrolling, focus retained and source scroll unchanged. Final frozen direct suite14PASS.48unitPASS; lint/typecheck/buildPASS (existing large-bundle warning). First targeted2casesPASS; first long-suite8PASS/6fail due review-store max8 reached by unclosed test sessions, not a lyric rendering failure. Added per-test response tracking and teardown DELETE restricted to that test page's own IDs, then reran14PASS; no user/live-session deletion.619protectedfiles unchanged and source manifest match. Candidate5199 (health200),5198retained. Backend unchanged; PC02/05/06/07/08 apply. Technical review: view-only state and canonical event/verse anchors, explicit Fit preserved; no arbitrary source-to-note mapping. No commit/push; PO acceptance pending.


## 2026-10-27 — Original-key declaration on Save, optional suggestion and Alto signature (v0.18-r2)

PO reported Alto output with changed pitches/harmonies but no initial key signature, then directed that missing source keys be chosen by the user before saving MusicXML, with an optional recommendation or manual override. Root cause: instrument transposition changed only explicit key nodes; a missing initial key stayed absent while notes/harmonies moved. Implemented the PO-directed source declaration instead of guessing or automatically inserting a Concert key.

Save now opens a compact original-key dialog only for a Concert source missing its initial key. Major/minor and tonic begin blank. Optional Dùng gợi ý fills a tentative key from a supported major/minor chord exactly at onset0 in the first measure, with the opening-chord basis shown; absent, late, dominant or unsupported roots yield no suggestion. The user can override both fields. The confirmation writes only missing initial key fifths/mode through canonical document correction, preserving note/lyric identities, source, history and all pitch/duration data; it is not concert transposition. Existing source-comparison requirement remains. Explicit source metadata is saved before verifying/downloading; picker selection remains initiated from the user click. Stage2 remains direct for unchanged MusicXML with an initial key, but a missing-key source must first be declared/saved. Backend instrument generation rejects undeclared missing initial key rather than exporting a misleading written score. Written-key label now respects an explicit mode from canonical data when the concert-only inspection endpoint rejects instrument metadata.

Checks:71backendPASS/3private-sampleSKIP (two existing deprecation warnings), including AltoUp+9/Down-3 signatures3 and Soprano/Tenor equivalents;50unitPASS; lint/typecheck/buildPASS (existing chunk warning); frozen Firefox direct suite15PASS. New end-to-end test uses retainedPDF01XML: Save dialog, suggestionAm, manual override then explicitAm, downloaded canonical key0/minor, unchanged notes+lyrics, Stage2 Alto signature3 and F♯minor label. Initial test selected dialog+field ambiguously (fixed exact selector); first implementation unconditionally prepended an XML declaration and failed document correction (fixed serializer-declaration detection, rerun passed). Guide updated.619protectedfiles unchanged; frozen source manifest matches. Candidate5200; prior user ports untouched. PC01/02/03/04/05/06/07/08 apply. Technical review: recommendation remains a weak visible suggestion, never a key assertion or auto-applied mutation; user declaration is distinct from transposing pitches; canonical source authority and written metadata retained. No Git operation or PO acceptance implied.


## 2026-10-27 — Editing added/overlapping chords (v0.19-r2)

PO requested editing mistakenly added chords. Existing direct editing only bound a native label when exactly one harmony matched its timestamp, leaving overlapping harmonies unselectable. Added an anchored, compact explicit chooser for multiple canonical candidates; each choice opens the existing free-text editor and individual Delete chord action. No large advanced form. Some OSMD versions ignore harmony offsets: if a canonical onset is unresolved in that measure's native chord entries, show that exact measure's candidate IDs instead of incorrectly assigning another harmony. Actual gap placement is not claimed fixed by this edit-access fallback. Clear candidates when changing tools/selecting notes. Expanded common existing suffix formatting (maj7/m7/6/m6/9 etc.) so prefilled values preserve those qualities.

Frozen v0.19-r2 direct suite17PASS;50unitPASS; lint/typecheck/buildPASS (existing bundle warning). New regressions edit D→Bm among Am/D/E/E, delete exactly one E, preserve all notes/other chords, Undo and MusicXML reimport; gap-offset chord edit preserves its onset1/2 and other G at0.619protectedfiles unchanged, manifest matched. Candidate5201; no Git mutation or PO acceptance.

## 2026-10-27 — Alto A-major section uses F♯ major consistently (v0.20)

PO screenshot on5200 identifies the later A-major section and notee47. Root cause: generic key transposition selected an enharmonic G♭-major signature while written chord roots used F♯, yielding inconsistent printed spelling. Added an optional instrument-only preferred fifths delta to the generic XML engine; Alto uses+3, Soprano/Tenor+2 when the resulting signature is within the existing supported±7 range. Notes are then spelled against that destination signature by the existing engine. Outside that range the prior generic enharmonic fallback remains; no universal fixed-diatonic spelling guarantee is added. Generic API behavior is unchanged without the optional argument. No Concert source mutation, interval/register/metadata changes, or automatic OMR correction.

Verification:94backendPASS/3private-sampleSKIP (two existing deprecation warnings), including Alto A-major→F♯-major6 for Up/Down, source A→F♯, C♯→A♯ and exact MIDI offset preservation; preservation and Concert regressions included. An initial command named a nonexistent test path and ran no tests; reran actual test_musicxml_preservation.py successfully. Frozen v0.20 actual retainedPDF01 Save/Alto testPASS: initialAm→F♯minor, later key3→6, notee47A♯5Up/A♯4Down, source notes/lyrics unchanged by key declaration. Frontend unchanged from v0.19-r2's17PASS suite; lint/typecheck/buildPASS.619protectedfiles unchanged; v0.20 source manifest matches. Candidate5202 includes chord editing and all previous fixes; prior ports remain untouched. PC02/04/05/06/07/08 apply. Technical review: instrument preference fixes the reported in-range enharmonic conflict without modifying default generic behavior. PO acceptance pending; no Git commit/push.


## 2026-10-27 — PO readable written-register defaults (v0.21)

PO explicitly selected Alto−3semitones, Soprano+2 and Tenor+2 for readable written notation. App Stage2 now chooses per-instrument direction defaults: AltoDown, SopranoUp, TenorDown. Card interval labels use each instrument's own chosen direction, avoiding a shared global direction misleading the other cards. Explicit Up/Down overrides remain and are remembered per instrument during the session; selection no longer carries AltoDown into Soprano as−10. Direction becomes available after instrument selection. Existing backend/API standard defaults, transposition metadata and interval variants remain; the application sends explicit PO-preferred directions. Guide documents the written-register and octave implications; Concert source unchanged.

Frozen Firefox2targetedPASS: actual retained sample original-key Save and Alto sectionF♯signature6/e47A♯ in Up/Down; separate default/override test verifies C4→A3Alto, D4Soprano and D4Tenor, correct card intervals, and a manual AltoUp override surviving a switch to Soprano and back. Lint/typecheck/buildPASS (existing chunk warning). Broader prior17-case suite passed onv0.19-r2; no claim of rerunning every case onv0.21. Backend unchanged fromv0.20's94PASS/3skip.619protectedfiles unchanged and frozen source manifest match. Candidate5203 contains prior chord editing, source-key Save, lyric anchoring and AltoF♯ fixes; previous ports untouched. PC04/05/06/07/08 apply. No Git mutation or PO acceptance implied.


## 2026-10-27 — Concert Key preflight for later-key signature overflow (v0.22)

PO screenshot5200 chooses A minor→G♯minor Up and reports Concert Key unavailable. Existing backend correctly rejects the later A-major section's theoretical8-sharp key (source3+delta5). Instead of silently respelling only that section or broadening unsupported key ranges, added a view-only whole-score preflight. It checks every projected key plus the confirmed initial key; when the chosen target overflows±7, disables Apply with an explanation and offers an enharmonic target±12fifths only if it represents every section. For this sample the explicit alternative is A♭minor(-7), giving the later A♭major(-4). User must click the alternative and then Apply; no automatic target switch, backend mutation or hidden pitch adjustment. Up/Down keeps exactly the same chromatic interval for equivalent spellings. If no whole-score equivalent fits, the UI states another target is needed; literal G♯minor with a later theoretical8-sharp section remains unsupported.

Checks:52unitPASS (including range/alternative and no-unsafe-suggestion cases), lint/typecheck/buildPASS (existing chunk warning). Frozen Firefox existing Am→Cm casePASS and new overflow/explicitA♭minor casePASS; final new-case rerun also verifies Instrument Scores disabled until the changed Concert is saved. Backend unchanged.619protectedfiles unchanged and frozen source match. Candidate5204; old5200andotherports preserved. PC02/03/04/05/06/07/08 apply. Technical review: explicit user choice and complete-section range validation, no automatic OMR or enharmonic rewriting. No Git operation or PO acceptance implied.


### 2026-10-27 — A4 PDF export candidate v0.23

- Export uses portrait A4 (210 × 297 mm), 12 mm margins, proportional notation and page counters. Page breaks follow complete systems and avoid lyric text; trailing blank canvas is trimmed. Source/editor zoom and MusicXML are unchanged by export.
- Verification: lint/typecheck/build passed; 55 unit tests passed. Frozen v0.23 browser PDF suite: 3 passed (short Concert: 1 page; long Concert: 7 pages; Alto: 4 pages). Physical A4 page sizes, all numbered lyric tokens without duplicates, title and page counters were verified. Initial long-fixture readiness timeouts were resolved by a bounded 30-second readiness wait; final results are in evidence/task04/pdf-a4-r2-results.json.
- Visual inspection: all 12 output pages (short 1, long 7, instrument 4) rendered with Poppler and inspected; margins, Unicode text, system boundaries and footers were intact. Poppler emitted Adobe-Identity-H collection warnings but rendered the inspected pages. These synthetic fixtures do not establish exhaustive tie/slur coverage.
- Original-key reopen investigation: two actual same-name local files differ. Downloads copy contains initial fifths=0/mode=minor; older music sample copy has no initial key. Two browser tests passed, including reopening actual Downloads bytes and saving without another key prompt. No source change was needed for this finding.
- Acceptance remains pending Product Owner review. No commit/push performed. Existing user app sessions were preserved.


### 2026-10-27 — Compact A4 engraving v0.24-r2

PO requested closer systems, verse rows and notes so the supplied two-page export can fit one A4 sheet like the original. PDF-only rendering now uses a 1100 px engraving canvas and explicit compact OSMD spacing (system minimum 4 vs 7, verse gap 0.25 vs 0.5, lyric horizontal gap 0.15 vs 0.2, minimum note spacing 1.5 vs 2). Editor engraving and canonical MusicXML are unchanged (PC-03,05,06,07; acceptance gates 1–3). No OMR or pitch changes.

Lint, typecheck/build and 55 unit tests passed. Four frozen-bundle browser PDF tests passed: short one page, long three pages, Alto two pages, and actual local Downloads/TienBuocVaoNhaChua_hn.musicxml one page. Numbered synthetic lyrics remain complete and unique, with zero document correction requests during export. All seven generated pages visually inspected with Poppler; system boundaries/footers intact. Actual MusicXML is a separate local source, not a reconstruction of the attached PDF; existing lyric/chord content and any errors in that source are preserved. No guarantee every long/complex score fits one page; safe multi-page breaks remain.

Source manifest matched; all 619 protected files matched. Intermediate v0.24 was superseded by v0.24-r2 after the spacing request. No commit/push; Product Owner acceptance pending.


### 2026-10-27 — Dismiss Concert Key panel v0.25

Added an accessible Close Concert Key (×) button at panel top-right and Escape dismissal, including when a key selector has focus. Closing restores focus to the Concert Key trigger without applying transposition. Existing trigger toggle and Keep Original remain. Scope: PC-05/06/07, acceptance gates 1–3; PO acceptance pending. Lint, typecheck and frozen build passed. Firefox smoke passed: close button, Escape from selector, focus restoration and zero score mutation requests. Source manifest and 619 protected file hashes matched. No Git operations. Existing app instances preserved; new candidate on port 5207.


### 2026-10-27 — Same-key Down register correction v0.26

PO explicitly confirmed same-key Down should lower the written Concert register for readability. Backend now lowers every supported pitched note exactly one octave when source and target fifths match and direction is Down; spelling, harmony, key changes, durations, lyrics, voices and links remain unchanged. Up with identical key retains previous no-op behavior. UI states the exact same-key behavior before Apply; source confirmation remains required. Octave underflow rejects the whole operation before replacing the score. PC-03/05/06/07, gates 1–3; acceptance pending.

49 relevant backend tests passed, including all-element comparison except octave and range rejection. Updated prior same-key no-op assertion to Up deliberately. Lint/typecheck/build and 55 frontend unit tests passed. Frozen v0.26 browser smoke passed: explanatory text, confirmation, successful same-key Down request and Undo available. Source manifest and 619 protected files matched. No Git operations; old sessions preserved, new app at 5208.


### 2026-10-27 — Product Owner acceptance of Task 04 checklist

Status: ACCEPTED for the scope of the Task 04 checklist presented in this conversation, through candidate v0.26. The Product Owner explicitly replied: "xac nhan da thuc hien tat ca cac hang muc tren" after the consolidated list of pending acceptance items. This records the Product Owner's confirmation, not an inference from automated test results (PC-08 / Gate 4).

Accepted checklist scope: PDF/OMR draft and original comparison; manual note/rhythm/rest/accidental/dot/measure corrections; mouse multiselection and supported tuplets; voices and lyric verses; supported OCR text/mark editing and deletion; chord editing; ties/slurs with zoom/Fit and transposition; Concert key declaration/persistence and section transposition; independent instrument scores; MusicXML save/reopen and A4 PDF export; Compare/Edit Only and navigation/scroll behavior. Same-key Down octave lowering is included.

Existing documented technical limitations remain: OMR is a fallible draft requiring user correction; this acceptance does not claim perfect recognition, exhaustive notation coverage or one-page output for arbitrarily long scores. Earlier pending-acceptance entries are historical and are superseded for the above accepted scope by this PO confirmation. No source changes, new tests, commit or push were performed for this acceptance record. GitHub synchronization requires a separately authorized action.


### 2026-10-27 — Accepted delivery checkpoint

Product Owner authorized packaging, commit and GitHub synchronization after acceptance. Commit scope: 60 explicit files under backend application/relevant tests, frontend-v2 application/tests/report and pilot-release launcher/builder/guide. The 619 preexisting protected files, legacy frontend, unrelated reports and private source/evidence are excluded. No broad staging or cleanup is used.

Final checkpoint checks: backend 1122 passed, 3 skipped, 2 existing dependency deprecation warnings (`pytest -q --ignore=tests/music/test_recognition_benchmark.py`); no recognition engine rerun. Frontend 55 unit tests passed; lint, typecheck and production build passed (existing large-chunk warning). Recent frozen-browser evidence remains the four A4 exports and Concert panel/octave smoke runs recorded above; no claim of a new full browser-suite run. Private-fixture tests now explicitly skip when absent.

Accepted archive: `music-sheet-transposer-task04-accepted-2026-10-27.tar.gz`. SHA-256: `d933e5e0691bc7203a991b20b925d4ac02e6b0d43e38bcbd6beeaf21951d3dd9`. Bundled runtime integrity and Python ABI check passed; all package-file and source hashes verified. Manifest marks ACCEPTED, and the guide reflects PO acceptance, current key/register behavior, direct editing and A4 export. OMR/notation exclusions documented above remain. Prior accepted Tenor archive and live user sessions are preserved.

Remote master was verified at pre-Task04 checkpoint 5b1e8e44f981cf54c4d7ccf0461f10e6435f278a before committing. The resulting Git commit is the durable source checkpoint; archive is retained locally, not uploaded as private evidence.


### 2026-10-28 — Authorized tuplet extension and instrument history fix (acceptance pending)

This extension does not change the previously accepted Task 04 checkpoint. PO authorized implementation following the tuplet review, then reported global Undo unavailable after dragging a Stage 2 pitch. New work is TECHNICALLY VERIFIED within the bounded scope below; PO acceptance and commit/push remain pending. PC-02/03/05/06/07/08 apply.

Implemented: 4:3 and 8:6 ratio choices; explicit division of one note/chord/rest duration; applying a ratio to contiguous written mixed-value note/chord/rest selections; editing one complete non-nested group or removing its ratio; explicit number/ratio/hidden number, bracket visibility and above/below placement. Commands reuse revision preconditions, atomic review edits, Undo/Redo and canonical MusicXML. Original event identities, pitches, accidentals, lyrics and unrelated notation are retained; only additional divided positions are explicitly created. Existing material outside the selection retains its musical onset. Supported normal-type/normal-dot metadata identifies the written tuplet unit; existing duration patching now permits supported explicit normal-type values. Unrepresentable units, partial/nested membership, unsupported values and actual collisions with unselected events are rejected atomically rather than guessed. Meter mismatch remains a Validate warning rather than automatic composition.

The interface offers Divide selected duration, Apply to written selection and Remove selected tuplet under Groups. Ratios still require compatible written units; e.g. divide a quarter into 3:2 eighths, or a dotted quarter into 2:3 eighths. Mixed patterns must total a representable written unit for the chosen ratio. Cross-measure/nested tuplets remain outside scope; arbitrary custom ratios are not exposed. The older equal/mixed commands remain for regression compatibility.

Instrument history: the global header Undo/Redo now delegates to the currently mounted instrument editor and reflects its history availability. The child editor retains its independent review/history. Concert history and XML are not used or changed by instrument Undo. Mounted-editor cleanup clears stale header actions when changing variants.

Verification: final backend 1138 passed, 3 skipped, two preexisting dependency deprecation warnings; recognition benchmark excluded and OMR not rerun. Frontend 55 unit tests passed; lint/typecheck/build passed (existing chunk-size warning). Frozen bundle browser suite: four passed (notes, rests, instrument tuplet editing; actual mouse pitch drag plus global Undo/Redo with exact Concert XML unchanged). New API tests cover all eight offered ratios, explicit base units, rest/chord splitting, original IDs/lyrics, partial-group rejection, expansion collision, history and export/reopen.

Development failures retained: initial rest mouse test timed out because hollow glyph centers lacked a reliable hit surface; transparent SVG rest hit rectangles resolved it. Initial TypeScript SVG cast was corrected with a runtime SVG type guard. Two old tests expected all explicit normal-type duration edits to be rejected; their expectations were deliberately updated for supported values, while unsupported 128th normal-type still rejects. First drag browser check attempted offscreen coordinates; scrolling the target into view resolved the test setup. A retry config initially referenced a nonexistent bundle path and was corrected. None of these intermediate failures is reported as a final PASS.

Technical review: new commands validate complete ownership before editing and preserve all unrelated nodes; rational divisions refinement retains exact musical time. Only user-requested groups are changed, with no auto-filled notes/rests or new agents/technologies. The accepted archive and all 619 protected files verified unchanged. Final candidate: music-sheet-transposer-tuplets-undo-v0.1; bundled/source hashes match and ABI/integrity checks pass. Existing user app sessions are preserved. No commit/push or PO acceptance is inferred from testing.


## 2026-10-28 — Cross-stage editor availability audit (acceptance pending)

The implemented composition tools share the same RealWorkspace editor in Concert Stage 1 and the independent instrument Stage 2. Compare and Edit Only retain the same editing commands; Edit Only hides the read-only source. Source panes remain read-only.

Coverage includes note/rest insertion and deletion, pitch, accidentals, duration, augmentation dots, normal/small display, grace notes, voice/staff assignment, ties/slurs, groups/tuplets, lyrics/verses, text/score marks, chord symbols, contextual structure corrections, Undo/Redo, validation, save and export. Small was verified by reduced SVG notehead width while preserving pitch and duration in all four stage/view combinations.

Corrections made during this audit:
- Global Undo/Redo, Validate, Save, Save As and saved MusicXML export delegate to the active instrument editor at Stage 2. Concert data remains unchanged.
- Normal/Small exposes pressed state and feedback. Note popovers stay clear of the EDIT rail on narrow screens.
- Save dialogs and additional tools render above the selected-object toolbar, which previously intercepted save confirmation and chord-update clicks.

Verification evidence:
- Backend regression: 1,138 passed, 3 skipped; recognition benchmark excluded, no OMR rerun.
- Frontend unit tests: 55 passed. ESLint, TypeScript and production build passed. Existing large-chunk build warning remains.
- Broad browser audit, r2: 88 passed, 7 skipped, 4 failed. Two failures were stale test assumptions (default register and explicitly confirmed initial key); two exposed overlay interference. Earlier broad-run evidence is retained.
- Final r3 targeted browser run: 20 passed, 1 failed due to a detached notehead during initial rendering. The test now waits for the instrument editor to be ready and uses a retriable click; its targeted rerun passed. All 21 final targeted cases have passing evidence across those runs. This is not reported as a single clean 99-test run. Seven optional private-fixture cases remain skipped.
- Protected baseline: all 619 recorded file hashes unchanged. Accepted Task 04 archive SHA-256 remains d933e5e0691bc7203a991b20b925d4ac02e6b0d43e38bcbd6beeaf21951d3dd9.
- Candidate: music-sheet-transposer-editor-parity-v0.1-r3; packaged file integrity and source hashes verified.

Limits remain shared across views: nested/cross-measure tuplets are unsupported; structural add-measure and instrument generation retain their existing part/staff restrictions. Availability of implemented tools does not claim full MuseScore feature parity. Concert key transposition is a Concert workflow action; instrument selection/direction is a Stage 2 action. Instrument PDF export is in the instrument editor toolbar.

This extension and audit remain pending Product Owner acceptance. No new commit or push was performed.


## 2026-10-28 — General PDF one-page fit (acceptance pending)

Export PDF now opens a small layout dialog shared by Concert and instrument workspaces. Fit in 1 A4 page is the default for any score length. It uniformly reduces the complete notation, lyrics and marks without changing XML. Multiple A4 pages preserves the existing system-aware pagination for readability. Cancellation creates no download and no success notice.

The supplied original Dieu Ran PDF has one Letter-size page (612 x 792 points); the supplied Alto export had two A4 pages, with only the final system on page two. The supplied G and Gb MusicXML files each contain 38 measures, 180 note elements and three lyric verses. Re-exported Gb Concert and Alto Down candidates each have one portrait A4 page (595.28 x 841.89 points), verified visually and by PDF inspection. Existing OCR text is retained unchanged.

Verification: 56 frontend unit tests passed; lint, TypeScript/build and package integrity passed. Six PDF browser tests passed on the first candidate, covering short/long/instrument pagination and private local samples. The final candidate additionally passed both sample exports and cancellation (3 tests). All 619 protected baseline hashes remain unchanged. No backend code changed, no OMR rerun, no commit/push.

Candidate: music-sheet-transposer-pdf-fit-v0.1-r2, port 5211. One-page fit may reduce text size for very long scores; users can explicitly choose multiple pages. Paper margins remain fixed at 12 mm. Automatic content-aware top/bottom/left/right margins are a proposed follow-up, not implemented or claimed in this candidate. Product Owner acceptance remains pending.


## 2026-10-28 — English editor UI and ratio-aware tuplet instructions (acceptance pending)

Add Chord remains the visible and accessible command name. Remaining Vietnamese editor UI strings were translated to English: duration labels, lyric verse controls, original-key confirmation/suggestion, Concert transposition notices, and overlapping-chord choice. Imported score text and lyrics are unchanged.

The Groups explanation and divide/apply button captions now show the selected ratio. Fixed mixed quarter/eighth 3:2 and beam commands are explicitly identified as independent of that selection. Eight ratio choices were checked. Selecting a ratio configures the next command; it does not silently rewrite existing notes.

Verification: ESLint, TypeScript/production build and package integrity passed. Eight targeted browser tests passed, including English duration labels, all ratio explanations/commands, note/rest/instrument tuplets, Undo/Redo, Small in both stages/views, and instrument global actions. The initial browser run had three ambiguous test locators after adding the explanation label; exact dropdown matching resolved those test-only failures. All 619 protected file hashes and packaged source hashes are unchanged/matching.

Candidate: music-sheet-transposer-editor-english-v0.1, port 5213. Previous sessions remain running. No commit/push; Product Owner acceptance pending.


## 2026-10-28 — Technical tuplet verification, dismissible notices and composer header

Technical verification covers all eight exposed ratios: 3:2, 2:3, 4:3, 5:4, 6:4, 7:4, 8:6 and 9:8. Actual/normal duration semantics were checked against the W3C MusicXML 4.0 time-modification reference (https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/time-modification/). Additional parameterized tests prove splitting keeps the complete original span and each resulting pitch remains independently editable without losing its tuplet timing. Existing tests cover notes/rests/chords, exact durations, normal-type metadata, save/reopen, appearance, Undo/Redo and rejection of partial/overlapping/unsupported representations. Divide preserves the selected span; Apply scales written values by normal/actual and can change the span. Nested and cross-measure tuplets remain unsupported; not every arbitrary selected span has a representable supported written unit.

Notification banners now have an accessible Dismiss notification button. The button explicitly accepts pointer events while the remaining toast remains non-intercepting. Empty notices are hidden. Initial mouse tests exposed the inherited pointer-events:none rule; the final packaged test passed after correction.

The private G Dieu Ran MusicXML contains no creator metadata for its author: Lm. Bui Ninh is actually stored as direction words in measure 4. No name detection or automatic semantic rewriting was added. Users can select a direction text and choose Move to composer header from Select or Text editing. A revision-checked atomic backend operation moves that text to composer metadata, preserves independent sound information, note data and text identity, and supports Undo/save/reopen. Existing composer metadata prevents duplicate creation. The author then scales with the page but no longer follows measure reflow.

Verification: 41 targeted backend tests passed (24 tuplet tests and 17 score-text tests). Eight existing targeted browser cases passed on r2; the final r3 notification/header case passed, including zoom out/in and Undo. Lint and TypeScript/build passed. All 619 protected hashes and final package/source hashes match. No source sample was modified; no OMR rerun; no commit/push. Candidate music-sheet-transposer-editor-review-v0.1-r3, port 5214; Product Owner acceptance pending.


## 2026-10-29 — Per-note Small in shared chords (acceptance pending)

The backend already stores Small on the selected XML note only, but OSMD can propagate a cue-sized type to the entire shared chord. The disposable rendering XML now suppresses that visual cue-size instruction only for notes explicitly marked Small; mapped SVG noteheads are scaled individually. Genuine cue/grace semantics and original XML are retained. Other noteheads at the same onset keep their normal size. This is a visual notehead-size correction, not a voice reassignment.

Verification: production build/typecheck, lint and 56 unit tests passed. Existing single-note Small cases passed for Concert and instrument, covering Compare/Edit Only. New shared-chord cases verified the selected member shrinks, the leader's measured SVG width remains unchanged, backend display_size changes only for the selected ID, and Normal restores the member across all four stage/view combinations. The first new run hit transient null bounds during redraw; the tests now wait safely for actual rendered bounds and both targeted reruns passed. All protected baseline/source hashes checked unchanged/matching.

Candidate music-sheet-transposer-small-member-v0.1, port 5216. No commit/push, acceptance pending. Chat checklist squares were static symbols, not interactive controls; acceptance can be recorded by item numbers in user replies.


## 2026-10-29 — Product Owner acceptance and authorized GitHub checkpoint

Status: **ACCEPTED** for the additional items listed in the conversation and the Small per-note correction in the tested port-5216 candidate. The Product Owner explicitly stated: “xac nhan cac hang muc tren nghiem thu”, then authorized commit/push and an English README update. Prior pending labels above describe historical candidate status and are superseded for this bounded scope by this acceptance record.

Technical Lead review: the extension follows PC-02 (user-directed editing), PC-03/PC-05 (canonical persistence, export and Undo), PC-04 (independent instrument output), PC-06 (explicit musical choices), PC-07 (regression checks), and PC-08 (Product Owner acceptance). Automated verification alone was not used as acceptance. Gate 1 implementation, Gate 2 scoped automated verification, Gate 3 source/evidence review, and Gate 4 explicit Product Owner acceptance are recorded. No new production-deployment claim is made.

Final checkpoint validation:
- Backend: `.venv/bin/python -B -m pytest -q --ignore=tests/music/test_recognition_benchmark.py` — **1,147 passed, 3 skipped**, two existing dependency deprecation warnings, 133.59 seconds. OMR was not rerun.
- Frontend: `npm run lint`, `npm test -- --run`, `npm run build` — **PASS**, 56 unit tests; TypeScript is part of the build. Existing large-chunk warning remains.
- Browser evidence remains scoped to the audit and targeted reruns documented above; no new clean full-browser-suite result is claimed.
- English README updated with accepted features, operation semantics, PDF choices, historical/current local package distinction and explicit limitations.
- The 619 preexisting protected files, legacy frontend, private samples, local archives/runtimes and unrelated working changes are excluded from staging. Their hashes are checked before and after the checkpoint.
- Commit scope is limited to the accepted backend/frontend-v2 implementation, its tests, this consolidated report and README. Existing user sessions remain running.
