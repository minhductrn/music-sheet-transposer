# Music Sheet Transposer - Project Specification

## 1. Authority and baseline

This specification describes the accepted Release 1.0.0, tag `v1.0.0`, source commit `ad7cdb8eaba5d993b51abbeca8043a545f14e01c`. It supersedes the original project-start specification and its obsolete foundation instructions. The Product Constitution and Acceptance Criteria remain authoritative. The Product Owner approves scope and final acceptance; the Technical Lead defines bounded designs and reviews evidence; Codex implements authorized work. Passing tests is not Product Owner acceptance.

Release 1.0 remains the production baseline. Changes require a separately verified candidate; never overwrite a sealed package or move the published tag. Documentation and interface labels use English. User-entered musical text supports Unicode.

## 2. Product purpose

Provide a web-based, local workspace to import a score, correct and compose on editable MusicXML, optionally change its Concert key, generate independent written saxophone scores, and retain MusicXML/PDF on the user's computer. User intent takes precedence over recognition guesses. This is not a promise of full MuseScore or Symphony Pro feature parity.

## 3. Supported deployment and data ownership

The accepted deployment is personal Ubuntu WSL on Windows. A loopback Uvicorn process serves React/TypeScript UI and FastAPI backend. The bundle includes built frontend and Python libraries; matching Linux/Python ABI, Audiveris, Java and English/Vietnamese OCR models are existing external prerequisites. The launcher installs nothing. A universal Windows installer is not provided.

There is no durable score database, account system or hosted score storage. Reviews, sources, variant caches and Undo history are bounded process-memory state and can expire. Users must retain Concert and desired instrument MusicXML files separately. Restart recovery imports the last retained MusicXML; unsaved session recovery is not guaranteed. Keep original PDFs separately.

Public/cloud deployment is outside Release 1.0. Any later hosting design must be separately approved, including OMR execution and the requirement not to retain user data on hosting.

## 4. Input and recognition

Supported input is PDF, PNG, JPG/JPEG, MusicXML/XML and supported compressed MXL. Validate input formats, sizes and XML representation; do not execute uploaded content. Recognition uses the local Audiveris integration behind the recognition service boundary. PDF/image recognition creates an OMR draft, not a final authoritative score.

OMR may misread key signatures, accidentals, durations, voices, lyrics, verses and marks. Do not infer missing musical content or silently add expressions. Recognition failure may offer explicit manual reconstruction. No general OMR accuracy certification is claimed. Original source remains read-only, and comparison is manual; automatic note-to-image alignment is not claimed.

Direct camera capture and Web Share API integration are excluded from the continuing scope by Product Owner decision on 2026-11-01. Do not retain them as pending requirements. Importing existing image files and downloading output files remain supported. Email/messaging integrations are also outside this scope.

## 5. Canonical workflow

1. Home presents application identity, file import and recognition profile.
2. Open MusicXML or recognize PDF/image into a draft.
3. Stage 1: compare with the original and correct the Working Score.
4. Optionally transpose the Concert score.
5. Retain the canonical Concert MusicXML before generating from changed content.
6. Stage 2: create independent written Alto, Soprano or Tenor scores.
7. Edit and retain each desired instrument output as MusicXML and/or PDF.

An unchanged imported Concert MusicXML with sufficient key context may proceed to instrument generation without a redundant Save. PDF drafts require current-revision comparison confirmation before canonical saving. If source key/mode needs confirmation, the user may use the recommendation or choose another key. Recommendations do not override the user. Confirmed key context persists in saved MusicXML.

## 6. Workspace and direct editing

Original Source is read-only; Working Score is editable. Compare shows both with independent zoom, Fit and scrolling. Edit Only hides only the original, retaining the same editor. Supported composition tools are available in Stage 1 and Stage 2 Working Scores and Edit Only. Actions and contextual controls operate directly on the score; dismissible notices must not push the score out of view.

Supported tools include note/rest addition, deletion, pitch/octave and duration changes; augmentation dots; explicit accidentals; voice/staff selection; selected-note Normal/Small; grace notes; expressions; tie/slur creation, direction and deletion; supported tuplets/beams; area selection and multi-note deletion; Add measure within supported structure; Unicode lyrics and verses; score text; user-authored chord symbols. Undo/Redo applies to commands in the active workspace.

Small affects only the selected head, including a chord member. Verse identifies a lyric row and is distinct from voice. Users can add/edit lyrics, add verses, move a syllable to a chosen note, correct OCR text, and remove supported unwanted marks. Chord symbols can be typed at a chosen position and edited, moved or removed. The system does not choose harmony.

Explicit accidentals follow musical scope for the same step/octave/staff within the measure until replaced or key context changes. Resolved tied chains remain pitch-consistent; unrelated following-bar notes are not changed. Ambiguous or inconsistent relationships are reported rather than guessed. Optional Validate reports rhythmic issues without automatically composing or correcting the score.

## 7. Concert-key transposition

Provide editable/prefilled Source key, Major/Minor mode, source confirmation, signed interval, Destination and Up/Down. Each minus/plus step is one semitone (0.5 tones). Same-key Down permits an octave-lower register. Preview is read-only, readable and cancellable; Apply changes the actual working score. Transpose supported notes, key changes and chord roots/basses while preserving rhythm, lyrics and relationships. Report unsupported spellings or range limits.

## 8. Independent instrument scores

Generate from the canonical Concert input without rerunning OMR or overwriting Concert. Each instrument/direction keeps independent session edits. Direction changes select/generate that variant without another instrument click. Retain outputs separately.

| Instrument | Standard Up | Readable Down |
| --- | --- | --- |
| Alto Saxophone E-flat | +9 semitones | -3 semitones |
| Soprano Saxophone B-flat | +2 semitones | -10 semitones |
| Tenor Saxophone B-flat | +14 semitones | +2 semitones |

Tenor readable Down uses the same written register as Soprano Up; on Tenor it sounds one octave below Concert. These are instrument written/sounding relationships, not concert vocal Tenor ranges. Preserve instrument transposition metadata.

## 9. Advanced Editing v1

Select complete contiguous measures in a single-part, single-staff score, including its voices. Choose explicit key/mode and interval, preview, then copy and transpose the passage to the end. Existing measures remain unchanged. The appended section has the destination key signature and separating double barline; supported chord roots/basses transpose. Apply is an atomic Undo/Redo command with revision checks. A corrected PDF draft must first be retained as MusicXML.

Arbitrary middle insertion/overwrite, partial-measure copying, in-place passage transposition, general repeat/ending copying and arbitrary clipboard destinations are not implemented in v1. Unsupported boundary relationships must be resolved or included in the selection rather than silently removed.

## 10. MusicXML, saving and Home

Canonical MusicXML is the durable musical representation. Stable identities and supported note, lyric, voice, staff, harmony, tie/slur, key and tuplet relationships must survive supported edits, save/export and reimport. Display/export geometry must not rewrite musical data.

Save/Save As uses the available browser file workflow or a download with retention acknowledgement. Canceling a save is not success. Home permits Save, Continue editing or explicit Discard and exit. PDF is not a substitute for MusicXML recovery.

## 11. PDF export

Release 1.0 supports portrait A4, preview of the exact generated PDF, one-page fit or multiple pages, Auto or Standard margins, page numbering and cancel/close. Long scores forced onto one page may print small. Auto margins already exist; internal engraving quality remains a known limitation. Release 1.0 does not promise a fixed number of measures per line.

All earlier PDF spacing/reflow experiments were canceled and are not part of the accepted release. They must not be restored as implied requirements.

Accepted maintenance releases 1.0.1 and 1.0.2 center each lyric horizontally beneath its associated notehead and use 85% of the original lyric font size. Release 1.0.2 also sets OSMD SoftmaxFactorVexFlow to 3 instead of 15 only for PDF printing, moderating duration-driven horizontal spacing differences between notes/rests. The Product Owner accepted this as the current practical result until a future update. Preserve all musical content, other font sizes, workspace rendering and existing page-layout/margin options. The bounded spacing setting supersedes the earlier no-spacing-change restriction only for this setting. Other canceled reflow trials remain excluded. General collision-free engraving is not claimed.

Published/sealed 1.0.0 and 1.0.1 remain unchanged. Current production maintenance version is 1.0.2; its acceptance and verification records are in docs/release-1.0.2/.

## 12. Architecture

React/TypeScript/Vite and OSMD render the workspace; PDF.js previews PDFs, and jsPDF/svg2pdf generate exports. FastAPI services own recognition, canonical review state, music processing and interval transposition. MusicXML remains the interchange authority. Derived graphical state is separate from original bytes and canonical edits. Use bounded temporary storage and command history; do not introduce SQLite, S3, authentication or automatic agents as assumed Release 1.0 requirements.

Current maintained application source is `frontend-v2/` and `backend/app/`. Legacy frontend isolation does not make it an active deliverable. Exact runtime limits and startup prerequisites are documented in `docs/release-1.0/ARCHITECTURE.md` and `OPERATIONS.md`.

## 13. Explicit limitations and future scope

- Nested and cross-measure tuplet authoring are unsupported.
- General Stage 2 multipart and multipart/multistaff Add measure remain limited.
- Advanced Editing is bounded to the v1 contract above.
- OMR quality requires user correction; broader accuracy evaluation is not complete.
- PDF lyric collisions/spacing remain reported quality limitations; only the accepted centering/font and bounded rhythmic-spacing maintenance above is included.
- Unsaved process state and Undo history are not durable recovery.
- Cloud deployment, wider platform packaging and additional composition capabilities require separate scope approval.
- Direct camera capture and Web Share API are excluded, not deferred backlog.

## 14. Verification and acceptance

Use relevant automated checks, build/lint and technical source review. For musical changes, verify supported persistence and relationships. For presentation-only PDF changes, verify unchanged musical content, note geometry and source MusicXML, plus final PDF rendering. Recorded Release 1.0 test results are historical evidence, not proof that a new candidate passed. Final acceptance remains with the Product Owner.

Published release documents and acceptance/verification receipts under `docs/release-1.0/` preserve the historical 1.0 baseline. Maintenance evidence is recorded under its own version directory and must not overwrite historical acceptance records. Commit/push and release publication require Product Owner authorization.
