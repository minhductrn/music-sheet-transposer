# Music Sheet Transposer

A local application for importing scores, editing notation directly, changing Concert key, and preparing independent saxophone written scores. **`frontend-v2/` is the default interface.** The legacy `frontend/` remains available for historical reference.

Conversation may use Vietnamese or English. Project documentation is maintained in English; older documents may retain historical filenames or language until explicitly migrated.

## Current status

**The Product Owner accepted Task 04 on October 27, 2026**, within the scope and limitations documented in the [Task 04 report](frontend-v2/TASK_04_REPORT.md). The accepted application source checkpoint is [`56e798e`](https://github.com/minhductrn/music-sheet-transposer/commit/56e798ecae8ac3c17317b421f873f59db4c8cbcc).

- Import real MusicXML, or recognize PDF/PNG/JPEG sources with local OMR to create an editable draft.
- Keep Original Source read-only on the left; make user-directed corrections in Working Score on the right. Edit Only provides the same tools while hiding the original.
- Edit supported notes, pitches, durations, accidentals, rests, augmentation dots, voices, measures, beams and tuplets; select multiple notes with the mouse.
- Add and edit Unicode lyrics across verses, text, chord symbols and ties/slurs; delete supported incorrectly recognized OCR objects directly on the score.
- Change Concert key across key changes within the piece. Declare a missing initial key when saving. **Same key + Down** lowers all pitched notes by one octave; same key + Up retains their pitch. Undo/Redo is available.
- Generate and edit independent Alto, Soprano and Tenor scores. Readable defaults are Alto −3 semitones, Soprano +2 and Tenor +2 relative to Concert. The accepted Tenor option uses Soprano-like notation and sounds an octave below Concert when played on B♭ Tenor; it is a register choice rather than the standard Tenor +14-semitone written transposition.
- Save and reopen MusicXML; export portrait A4 PDF with compact system, lyric and note spacing and automatic pagination for longer scores.
- Fit to pane width, zoom and scroll independently; return Home by saving, continuing editing or explicitly discarding unsaved changes.

OMR can omit or misread notation. Users compare and correct its draft; the application does not compose missing material. The Task 04 workflow uses no AI agents, LLM API calls or Docker.

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

## Accepted standalone bundle

The accepted local archive is **`music-sheet-transposer-task04-accepted-2026-10-27.tar.gz`**. Archives and runtime files remain local; cloning GitHub does not download a prebuilt bundle.

Extract the archive into a new directory and run in Ubuntu WSL:

```bash
python3 -B /path/to/extracted-bundle/start.py --check
python3 -B /path/to/extracted-bundle/start.py --port 5180
```

Replace `/path/to/extracted-bundle` with the actual directory. Open **http://localhost:5180**. Choose another port with `--port` if necessary, keep the terminal open, and press Ctrl+C to stop the server.

The bundle includes built frontend assets and Python libraries. System Python must match the ABI recorded in `manifest.json`. Node, Codex and development servers are not required at runtime. OMR still requires the local tools listed above. This is a local pilot, not a native Windows installer or production deployment.

- [Current Task 04 guide and limitations](pilot-release/TASK_04_GUIDE_VI.md)
- [Implementation, verification and acceptance report](frontend-v2/TASK_04_REPORT.md)
- [Earlier Task 03 guide](pilot-release/USER_GUIDE_VI.md) and [Task 03 packaging notes](pilot-release/README.md) are historical references, not replacements for the current Task 04 guide.

The current builder is `pilot-release/build_task04.py`. On the packaging host with installed dependencies and the protected Tenor runtime cache, run from the repository root:

```bash
python3 -B pilot-release/build_task04.py --accepted --output /absolute/path/to/new-bundle-directory
```

The builder refuses to overwrite existing output. It needs the local accepted Tenor runtime cache, which is not distributed in Git; a fresh clone alone is insufficient to reproduce the bundle. Use `--accepted` only for scope accepted by the Product Owner.

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

The Task 04 checkpoint recorded **1,122 backend tests passed, 3 skipped; 55 frontend unit tests passed**, with lint, type checking and build passing. Browser verification has separately documented scope. These results do not certify perfect OMR accuracy.

`npm run test:e2e` uses Playwright and requires ports 5174/8812 to be available. The current configuration contains the Firefox path used on the verified WSL host; other hosts must adjust it. Some tests use unpublished private fixtures or local evidence; inspect their skip conditions and paths. Do not run tests against a session containing unsaved user edits.

## Limitations and private data

- Recognition is not guaranteed for every symbol, legacy font, voice or lyric. No universal recognition-accuracy percentage is claimed.
- Encrypted PDFs are unsupported. Multiple score outputs are not automatically selected or merged.
- Editing and tuplet coverage is bounded by the report; this is not full MuseScore/Symphony Pro parity. Stage 2 remains single-part; Add measure retains its single-part/single-staff restriction.
- A transposed section requiring more than seven sharps/flats needs an explicitly chosen supported enharmonic spelling. Musical choices are not silently overridden.
- Long scores still use multiple A4 pages; the exporter does not force every score onto one page.
- Personal PDF/MusicXML inputs, runtimes, archives and private evidence remain local and are excluded from Git. Unrelated legacy changes are preserved separately.

## Structure and governance

| Directory | Purpose |
| --- | --- |
| `frontend-v2/` | Default interface, Task 04 report and tests |
| `backend/` | Recognition, review/editing and MusicXML transposition APIs |
| `pilot-release/` | Standalone builder, launcher and guides |
| `frontend/` | Legacy interface retained for reference |

The [legacy README](README_LEGACY.md) preserves older documentation; historical status does not establish current acceptance. A GitHub source checkpoint is not a production deployment.

Governance: [Product Constitution](PRODUCT_CONSTITUTION.md) and [Acceptance Criteria](ACCEPTANCE_CRITERIA.md). The Product Owner retains acceptance authority; passing tests do not replace that approval.
