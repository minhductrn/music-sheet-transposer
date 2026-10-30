# Music Sheet Transposer

## UX Next checkpoint — October 30, 2026

This branch, **ux-next/checkpoint-2026-10-30**, preserves the independent UX Next work. It does not replace the Classic installation or the default branch.

**Scoped Product Owner acceptance:** the simplified Home and accidental/tie editing have been accepted. The complete UX redesign remains a candidate; this is not a new production release or approval of advanced editing.

- Home displays the application title and import controls. Editing tools appear after opening a score.
- Stage 1 and Stage 2 use the same editing commands in Compare and Edit Only; original sources remain read-only.
- **Remove accidental** restores the preceding accidental context or key signature.
- An explicit accidental command applies to later notes with the same step, octave and staff within the measure, ending at an explicit replacement or changed key context.
- Resolved tie chains retain their connections, directions and durations while their pitches are corrected together, including cross-bar continuations. Unrelated notes in the next bar are not changed.
- Ambiguous, incomplete or originally pitch-mismatched ties are reported rather than guessed.

### Verification and acceptance

The latest targeted suite passed **47 backend tests**, plus a browser check of tied-note accidental entry, removal and Undo. Production build, TypeScript and package integrity checks passed. XML serialization/reimport and exact Undo/Redo were verified. The Product Owner additionally reported testing tied notes and notes sharing a chord position. Stage 2/PDF user checks were reported on the preceding accidental-scope revision; automated Stage 2/PDF checks were not rerun for preview.13.

See the [scoped acceptance record](pilot-release/UX_NEXT_ACCIDENTAL_TIE_ACCEPTANCE.json), [implementation and verification report](pilot-release/UX_NEXT_REPORT.md), [English UX guide](pilot-release/UX_NEXT_USER_GUIDE_EN.md), and [baseline provenance](UX_NEXT_BASELINE.json).

### Run independently

On the existing WSL installation:

- Classic: `python3 -B /home/dtran/music-sheet-transposer-releases/music-sheet-transposer-classic-task06/start.py --port 5181`
- UX Next preview.13: `python3 -B /home/dtran/music-sheet-transposer-releases/music-sheet-transposer-ux-next-preview13/start.py --port 5233`

These are local package paths, not files included in a fresh clone. A clone uses the development setup below. Keep Classic and UX Next in separate checkouts and processes; do not copy UX Next over Classic. The package builder requires the preserved local Classic baseline. Release archives, dependencies, private scores and OMR evidence are not committed here.

### Next scope

Advanced editing has not started. Copy/paste of a selected passage and selective transposition require a separate bounded design and authorization. Cloud deployment is deferred. OMR remains a draft recognition tool requiring user correction.

---

A local application for importing scores, editing notation directly, changing Concert key, and preparing independent saxophone written scores. **`frontend-v2/` is the default interface.** The retired `frontend/` is preserved in a local source archive and excluded from Git tracking. Historical committed versions remain in Git history.

Conversation may use Vietnamese or English. Project documentation is maintained in English; older documents may retain historical filenames or language until explicitly migrated.

## Current status

**The Product Owner accepted the latest editor and PDF-export additions on October 29, 2026**, including per-note Small rendering. The original Task 04 baseline was accepted on October 27, 2026 at [`56e798e`](https://github.com/minhductrn/music-sheet-transposer/commit/56e798ecae8ac3c17317b421f873f59db4c8cbcc). Scope, verification evidence and remaining limitations are recorded in the [Task 04 report](frontend-v2/TASK_04_REPORT.md).

- Import real MusicXML, or recognize PDF/PNG/JPEG sources with local OMR to create an editable draft.
- Keep Original Source read-only on the left; make user-directed corrections in Working Score on the right. Edit Only provides the same tools while hiding the original.
- Edit supported notes, pitches, durations, accidentals, rests, augmentation dots, voices, measures, beams and tuplets; select multiple notes with the mouse. Small changes only the selected notehead, including one member of a shared chord; other members retain their size. It does not change pitch, duration or voice.
- Add and edit Unicode lyrics across verses, text, chord symbols and ties/slurs; delete supported incorrectly recognized OCR objects directly on the score.
- Change Concert key across key changes within the piece. Declare a missing initial key when saving. **Same key + Down** lowers all pitched notes by one octave; same key + Up retains their pitch. Undo/Redo is available.
- Generate and edit independent Alto, Soprano and Tenor scores. Readable defaults are Alto −3 semitones, Soprano +2 and Tenor +2 relative to Concert. The accepted Tenor option uses Soprano-like notation and sounds an octave below Concert when played on B♭ Tenor; it is a register choice rather than the standard Tenor +14-semitone written transposition.
- Save and reopen MusicXML. Export PDF defaults to **Fit in 1 A4 page**, uniformly scaling the complete score. Choose **Multiple A4 pages** for readable pagination of long scores. Margins remain 12 mm; automatic content-aware margins are not implemented.
- Fit to pane width, zoom and scroll independently; return Home by saving, continuing editing or explicitly discarding unsaved changes.

### Accepted editor additions

- Concert and instrument Working Scores share the editing tools in Compare and Edit Only. Edit Only hides the source; the source remains read-only. Stage 2 global Undo/Redo, Validate, Save, Save As and saved MusicXML export target the active instrument score.
- The interface uses English labels; imported lyrics and score text keep their own language. Notification messages can be dismissed with the close button.
- **Add Chord** accepts user-directed chord entry. Select a measure-attached author text and choose **Move to composer header** to move it into page-level composer metadata. This is explicit, supports Undo, and does not automatically classify other OCR text.
- Groups supports **3:2, 2:3, 4:3, 5:4, 6:4, 7:4, 8:6 and 9:8**. Instructions and commands follow the selected ratio. **Divide duration** preserves the selected span; **Apply to selection** scales written values by the ratio and may change the span. Select the complete group to remove its tuplet notation. Resulting pitches remain individually editable.
- Fixed mixed quarter/eighth 3:2 and beam tools are separate from the selected ratio. Unsupported nested/cross-measure tuplets or unrepresentable written units are reported rather than silently rewritten.

OMR can omit or misread notation. Users compare and correct its draft; the application does not compose missing material. The Task 04 workflow uses no AI agents, LLM API calls or Docker.

## Release stabilization

The Product Owner accepted Task 05 package **1.0.0-rc2** on **October 29, 2026**: **106 packaged browser tests passed, 0 failed, 0 skipped**, with restart/round-trip and one real OMR pipeline check completed. The [acceptance record](pilot-release/TASK_05_ACCEPTANCE.json) identifies the exact immutable archive hash. See the [Task 05 release plan and subsequent roadmap](pilot-release/TASK_05_RELEASE.md) and [English standalone guide](pilot-release/USER_GUIDE_EN.md). Existing accepted checkpoints and archives remain unchanged. The Task 05 GitHub checkpoint records this bounded release acceptance.

## Development setup

Use Ubuntu WSL, Node 24 and a Python version compatible with the backend dependencies. For a new clone, prepare the backend once:

```bash
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cd ..
```

Run the API in one terminal:

```bash
cd backend
.venv/bin/python -B -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In a second terminal, from the repository root:

```bash
npm run setup:frontend
npm run dev
```

Open **http://localhost:5174**. Run `setup:frontend` only when installing or updating dependencies. `npm start` also starts the v2 development interface. Keep both terminals open; use Ctrl+C to stop them. Do not start another instance on a port already used by an active session.

The frontend proxies `/api` to `http://127.0.0.1:8000` by default. To use another backend address:

```bash
AI_SDF_BACKEND_URL=http://127.0.0.1:8001 npm run dev
```

Do not use the legacy frontend's `VITE_BACKEND_URL` setting for frontend-v2.

### OMR prerequisites

PDF/image recognition requires Java, Audiveris and suitable OCR language data installed locally. The application bundle does not include or automatically download Java, Audiveris or OCR models. Configure `AUDIVERIS_EXECUTABLE` and `AUDIVERIS_TESSDATA_PATH` as needed; see the [Task 04 guide](pilot-release/TASK_04_GUIDE_VI.md). MusicXML import and editing do not require Audiveris. Recognition does not require an online AI service once its local tools and models are available.

## Standalone bundles and release candidates

The historical accepted Task 04 baseline archive is **`music-sheet-transposer-task04-accepted-2026-10-27.tar.gz`**. It predates the October 29 editor additions; do not use it to verify the latest features. The accepted Task 05 archive is **`music-sheet-transposer-1.0.0-rc2.tar.gz`**, built from accepted commit `945821c`. Its name and bytes are preserved; build-time pending metadata is superseded for its exact hash by the Task 05 acceptance record. The earlier Small-member package is retained as historical evidence. Archives and runtime files remain local; cloning GitHub does not download a prebuilt bundle.

Extract the archive into a new directory and run in Ubuntu WSL:

```bash
python3 -B /path/to/extracted-bundle/start.py --check
python3 -B /path/to/extracted-bundle/start.py --port 5180
```

Replace `/path/to/extracted-bundle` with the actual directory. Open **http://localhost:5180**. Choose another port with `--port` if necessary, keep the terminal open, and press Ctrl+C to stop the server.

The bundle includes built frontend assets and Python libraries. System Python must match the ABI recorded in `manifest.json`. Node, Codex and development servers are not required at runtime. OMR still requires the local tools listed above. This is a local pilot, not a native Windows installer or production deployment.

- [Current English standalone guide](pilot-release/USER_GUIDE_EN.md) and [Task 05 verification, package details and roadmap](pilot-release/TASK_05_RELEASE.md)
- [Earlier Task 04 guide and limitations](pilot-release/TASK_04_GUIDE_VI.md)
- [Implementation, verification and acceptance report](frontend-v2/TASK_04_REPORT.md)
- [Earlier Task 03 guide](pilot-release/USER_GUIDE_VI.md) and [Task 03 packaging notes](pilot-release/README.md) are historical references, not replacements for the current Task 04 guide.

The Task 05 stabilization builder is `pilot-release/build_task05.py`. It builds application code from accepted commit `945821c`, excludes unrelated working-tree code, and records source acceptance separately from pending release acceptance. On the packaging host with installed dependencies and the protected Tenor runtime cache, run from the repository root:

```bash
python3 -B pilot-release/build_task05.py --output /absolute/path/to/new-bundle-directory
```

The builder refuses to overwrite existing output. It needs the local accepted Tenor runtime cache, which is not distributed in Git; a fresh clone alone is insufficient to reproduce the bundle. Task 05 packages remain release candidates until explicit Product Owner release acceptance. Earlier `build_task04.py` output and archives are historical baselines.

## Saving and reopening

MusicXML is the editable document; PDF is print output. Use Save As to protect the original file. When the browser downloads a file, confirm retention only after checking its actual name and location, including any `(1)` or `(2)` suffix.

- Compare OMR drafts against the source and confirm that comparison before saving. Further content edits invalidate that confirmation.
- Save edited Concert content before generating Instrument Scores. An unchanged imported MusicXML document with an explicit initial key can proceed directly to Instrument Scores.
- Save each instrument score separately. Reopened written scores are independent documents; do not apply instrument transposition again unless intended.
- In-memory sessions, Undo/Redo history and unsaved variants are not automatically restored after shutdown. Returning Home does not delete saved files.

## Build and verification

From the repository root:

```bash
npm run typecheck
npm run lint
npm test
npm run build
```

Frontend output is written to **`frontend-v2/dist/`**. To check the backend:

```bash
cd backend
.venv/bin/python -B -m pytest -q --ignore=tests/music/test_recognition_benchmark.py
```

The original Task 04 checkpoint recorded 1,122 backend tests passed, 3 skipped, and 55 frontend unit tests passed. The October 29 verification recorded **1,147 backend tests passed, 3 skipped; 56 frontend unit tests passed**, with lint, TypeScript and build passing. The recognition benchmark was excluded. The later Task 05 release candidate completed a clean 106-test packaged browser run with private fixtures enabled; the Task 05 report preserves the earlier failed/skipped runs and test-only corrections. Those fixtures remain unpublished. These results do not certify perfect OMR accuracy.

`npm run test:e2e` uses Playwright and requires ports 5174/8812 to be available. The current configuration contains the Firefox path used on the verified WSL host; other hosts must adjust it. Some tests use unpublished private fixtures or local evidence; inspect their skip conditions and paths. Do not run tests against a session containing unsaved user edits.

## Limitations and private data

- Recognition is not guaranteed for every symbol, legacy font, voice or lyric. No universal recognition-accuracy percentage is claimed.
- Encrypted PDFs are unsupported. Multiple score outputs are not automatically selected or merged.
- Editing and tuplet coverage is bounded by the report; this is not full MuseScore/Symphony Pro parity. Stage 2 remains single-part; Add measure retains its single-part/single-staff restriction.
- A transposed section requiring more than seven sharps/flats needs an explicitly chosen supported enharmonic spelling. Musical choices are not silently overridden.
- Fit in 1 A4 page can make long scores very small. Choose Multiple A4 pages when readability is more important than page count. One-page fit does not repair incorrect OCR text or notation.
- Personal PDF/MusicXML inputs, runtimes, archives and private evidence remain local and are excluded from Git. Unrelated legacy changes are preserved separately.

## Structure and governance

| Directory | Purpose |
| --- | --- |
| `frontend-v2/` | Default interface, Task 04 report and tests |
| `backend/` | Recognition, review/editing and MusicXML transposition APIs |
| `pilot-release/` | Standalone builder, launcher and guides |
| `frontend/` | Retired local-only interface; excluded from Git tracking |

The [legacy README](README_LEGACY.md) preserves older documentation; historical status does not establish current acceptance. A GitHub source checkpoint is not a production deployment.

Governance: [Product Constitution](PRODUCT_CONSTITUTION.md) and [Acceptance Criteria](ACCEPTANCE_CRITERIA.md). The Product Owner retains acceptance authority; passing tests do not replace that approval.
