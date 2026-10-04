# Music Sheet Transposer

A full-stack application for importing MusicXML or PDF/image sheet music, reviewing and correcting recognition results, transposing MusicXML, previewing scores, and downloading corrected or transposed MusicXML.

The current implementation includes Audiveris OMR, Vietnamese/English OCR, evidence-based semantic recovery, and a preservation-based MusicXML transposer. Recognition produces a draft for human comparison; it does not guarantee a faithful transcription of every source.

## Architecture

React + TypeScript provides the browser workspace and OpenSheetMusicDisplay (OSMD) preview. FastAPI exposes versioned REST APIs, with recognition, recovery, review, and transposition in separate backend modules. Frontend HTTP calls are centralized in `frontend/src/services/api.ts`.

The production/default recognition provider is **Audiveris 5.11.0** (`RECOGNITION_PROVIDER=audiveris`).

```text
PDF / Image
     |
     v
Audiveris 5.11
     |
     +--------------------+
     |                    |
     v                    v
Baseline MusicXML     .omr evidence
     |                    |
     +---------+----------+
               v
       Semantic Recovery
               |
               v
       Musical Validation
               |
               v
       Confidence Decision
          /           \
         v             v
 HIGH confidence    AMBIGUOUS / uncertain
 Auto Recovery      Review Required
          \           /
           v         v
     Validation / Human Review
               |
               v
      Corrected MusicXML
               |
               v
    Explicit Source Verification
               |
               v
    Preservation Transposer
               |
               v
      OSMD Preview / Export
```

Audiveris `.omr` archives can retain richer head, stem, chord, geometry, and timing evidence than exported MusicXML. Semantic recovery correlates that evidence with the baseline XML to recover some information lost during export. Automatic changes require strong, corroborated evidence and musical validation. Ambiguous candidates remain `REVIEW_REQUIRED`; the application avoids silent guessing. Visual small size alone does not imply grace-note timing.

Semantic interpretation is enabled by default. The separate small-head **analysis pass is opt-in**, disabled by default, and supplies evidence without replacing the normal export. The Phase 4D.2 benchmark below used this additional pass; its recovery results are not a promise for default recognition. See [OMR integration](backend/OMR.md) and [semantic recovery](backend/SEMANTIC_RECOVERY.md).

Direct MusicXML imports enter the transposition/preview workflow without OMR or recognition-review gating.

## Implemented features

- Import MusicXML; recognize PDF, PNG, JPEG, and WEBP sheet music through Audiveris.
- Select recognition profiles and source-quality overrides; inspect recognition and timing diagnostics.
- Use Tesseract `vie+eng` for Vietnamese/English text and lyrics in the default vocal and SATB profiles. Other profiles default to `eng`; OCR quality still depends on the source and language data.
- Retain bounded `.omr` artifacts and expose semantic recovery candidates with confidence and source boxes.
- Compare the original PDF/image with OSMD preview; correct events, lyrics, titles, printed credits, and harmony/chord symbols.
- Validate corrections, undo/redo edits (including automatic recovery), explicitly verify against the source, and download original or corrected MusicXML.
- Transpose by integer semitones, preview the result, and download transposed MusicXML.
- Run optional, isolated OMR benchmarks; SMT remains outside the normal production workflow.

### Preservation-based transposition

```text
Original MusicXML
        |
        v
Preservation-based transposer
        |
        v
Modify note pitches, key signatures, and related accidentals
        |
        v
Preserve unrelated score structure
        |
        v
Transposed MusicXML -> OSMD / Download
```

The MusicXML endpoint modifies a preserved XML document rather than rebuilding it through the smaller internal score model. Current code/tests demonstrate preservation of lyrics, dynamics/directions, ties/slurs, articulations, tempo, metadata, chord membership, voices/staves, backup/forward timing, and existing layout information. Harmony/chord-symbol XML is retained unchanged; its roots are **not automatically transposed** by this endpoint.

Zero-semitone transposition returns the original bytes after document checks. Nonzero transposition preserves the document structure but can change XML serialization. Supported musical values are validated; this is not universal MusicXML support. The separate JSON score-model transposition API remains available.

### Recognition review

`RecognitionReview`, `EventInspector`, and `SourceViewer` provide measure/voice/event navigation, source comparison, candidate inspection, and explicit corrections. Supported edits include pitch, duration, voice, staff, display size, grace status, note/rest insertion or deletion, and simultaneous chord-note addition. Small display size and grace timing are separate controls.

Reviews begin as drafts. Validation errors block verification; warnings still require musical judgment. The user must confirm source comparison before marking a score `VERIFIED`. The frontend then uses verified corrected XML for transposition. Edits and undo/redo invalidate verification; candidate evidence records import-time findings and is not silently reevaluated after manual edits.

Review sessions and bounded history are stored in process-local memory. Run one backend worker; a restart discards sessions and a browser reload loses local workspace state. Download corrected XML before leaving. See [review API, lifecycle, and correction limits](backend/REVIEW.md).

## Real-world benchmark: Phase 4D.2

**Cùng Đem Tin Mừng** was evaluated with normal Audiveris recognition plus an opt-in LINKS evidence pass on 2026-10-03. Analysis evidence contained **53 heads, including 4 explicit small heads**.

| Metric | Baseline Audiveris MusicXML | After semantic recovery |
|---|---:|---:|
| Pitched notes | 51 | 53 |
| Chord groups | 9 | 11 |
| Ties | 16 | 16 |
| Explicit small-display notes | 0 | 2 |
| Grace notes | 0 | 0 |

Recovery added two duration-bearing small-display notes with **zero grace-note conversions**.

| Source location | Observed result |
|---|---|
| “ta” — A4 + C5 | Simultaneous structure and duration retained. C5 visual small-size evidence remains uncertain; review required. |
| “cùng” — F4 + A4 | Simultaneous structure and duration retained. A4 visual small-size evidence remains uncertain; review required. |
| “đem” — G4 + B-flat4 | B-flat4 was absent from baseline XML and recovered automatically from Audiveris evidence. It is visually small, shares G4's onset and quarter-note duration, and remains duration-bearing rather than a grace note. |
| Measure 6 — G4 + B-flat4 | Another missing small B-flat4 was recovered with the same simultaneous, duration-bearing semantics. |

This is a **specific benchmark result, not a general OMR accuracy percentage**. Other notation, pitch, or lyric errors can remain. Matching a historical note count does not establish accuracy. See [benchmark evidence and recovery decisions](backend/SEMANTIC_RECOVERY.md#real-cùng-đem-tin-mừng-benchmark-2026-10-03).

### SMT: experimental / benchmark only

**Sheet Music Transformer (SMT) is EXPERIMENTAL / BENCHMARK ONLY**, with `SMT_ENABLED=false` by default. It is not part of normal production recognition and is not an automatic fallback for Audiveris.

This project's Phase 4D.1 benchmark of the `smt-grandstaff` checkpoint on the same score found:

- Whole-score CPU inference timed out after 600 seconds.
- A bounded excerpt returned 9 pitched tokens and 2 rests.
- The target simultaneous structures were not preserved, and malformed symbolic spine structure prevented reliable timing.

These results did not justify replacing Audiveris. They concern this checkpoint, input preparation, and environment, and do not establish that SMT is generally poor. The experimental worker retains symbolic output; it does not provide a MusicXML converter. See [SMT setup and benchmark decision](backend/SMT.md).

## Technology stack

| Area | Technologies |
|---|---|
| Frontend | React, TypeScript, Vite, React Router, OpenSheetMusicDisplay, CSS |
| Backend | Python, FastAPI, Pydantic / Pydantic Settings, Uvicorn |
| Validation and tests | pytest, HTTPX / FastAPI TestClient, ESLint, TypeScript compiler |
| Recognition | Separately installed Audiveris 5.11.0, Tesseract language data, MusicXML |
| Input handling | pypdf, Pillow |
| Optional experiments | Isolated SMT worker and dependencies |

Dependency declarations live in [frontend/package.json](frontend/package.json), [backend/requirements.txt](backend/requirements.txt), and [the isolated SMT requirements](backend/smt_worker/requirements.txt). The frontend lockfile records resolved versions; most backend dependencies are not pinned.

## Project structure

```text
backend/
  app/
    api/                  Versioned health, transpose, recognition, and review APIs
    core/                 Environment-based configuration
    music/
      musicxml/           Parser/exporter and preservation-based XML transposer
      models/             Internal score model
      transposition/      Model-based pitch/key/score operations
      recognition/        Providers, upload validation, diagnostics, benchmarks
      recovery/           .omr evidence, correlation, conservative XML recovery
      review/             Editable projection, patches, validation, session history
    schemas/              API request/response schemas
  tests/                  Backend regression tests and synthetic fixtures
  smt_worker/             Optional isolated experimental inference worker
frontend/
  src/
    components/           OSMD viewer, review workspace, inspector, source viewer
    pages/                Application workspace
    services/             Centralized backend API client
    types/                Typed API and music/review data
```

## Installation and development

### Core app requirements

Use Python 3.12+ and Node.js 22 (22.13+) or 24+ with npm (compatible with the locked Vite/ESLint toolchain). Audiveris and SMT are unnecessary for direct MusicXML transposition and mocked backend tests.

From the repository root, start the backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

In another terminal, from the repository root:

```bash
cd frontend
npm ci
cp .env.example .env
npm run dev
```

Open the URL printed by Vite. The development server proxies `/api` to `http://127.0.0.1:8000`; set `VITE_BACKEND_URL` in `frontend/.env` to change that proxy target. The health endpoint is `GET /api/v1/health`; interactive backend API documentation is at `http://127.0.0.1:8000/docs`.

### PDF/image OMR requirements

Install **Audiveris 5.11.0 separately**, including its required runtime/native components, following [the repository's OMR installation guide](backend/OMR.md#install-audiveris-outside-the-virtual-environment). The adapter targets Linux/WSL and POSIX process handling. Set `AUDIVERIS_EXECUTABLE` to its launcher if `audiveris` is not on `PATH`.

Install compatible Tesseract **`vie` and `eng` language data** explicitly. For Ubuntu packages:

```bash
sudo apt install tesseract-ocr tesseract-ocr-vie tesseract-ocr-eng
```

Set the following before starting the backend, adjusting paths to your installation:

```bash
export AUDIVERIS_EXECUTABLE=/path/to/audiveris-launcher
export AUDIVERIS_TESSDATA_PATH=/path/to/tessdata
export AUDIVERIS_OCR_LANGUAGES=vie+eng
export RECOGNITION_PROVIDER=audiveris
export SMT_ENABLED=false
```

The backend passes the selected language directory to Audiveris and checks for required model files; it never downloads them automatically. System Tesseract CLI installation is useful for checking language availability, while Audiveris uses its bundled OCR integration. See [Vietnamese OCR configuration](backend/OMR.md#vietnamese-ocr).

| Backend environment variable | Default / purpose |
|---|---|
| `RECOGNITION_PROVIDER` | `audiveris` |
| `AUDIVERIS_EXECUTABLE` | `audiveris`; one executable path |
| `AUDIVERIS_TESSDATA_PATH` | Unset; falls back to inherited `TESSDATA_PREFIX`, then Audiveris's default directory |
| `AUDIVERIS_OCR_LANGUAGES` | Profile-dependent; `vie+eng` for VOCAL_SONG and SATB |
| `AUDIVERIS_INPUT_QUALITY` | Profile-dependent; request overrides server setting |
| `AUDIVERIS_SEMANTIC_RECOVERY_ENABLED` | `true` |
| `AUDIVERIS_SEMANTIC_ANALYSIS_ENABLED` | `false`; optional additional evidence pass |
| `SMT_ENABLED` | `false`; experimental only |

Backend settings read exported environment variables; `.env` files are not automatically loaded. Detailed bounds, timeouts, and review storage settings are documented in [OMR](backend/OMR.md), [semantic recovery](backend/SEMANTIC_RECOVERY.md), and [review](backend/REVIEW.md).

### Optional experimental SMT requirements

Normal development does not require SMT, Torch, GPU hardware, or model downloads. Deliberate SMT experiments use a separate Python environment, pinned upstream source/model, and explicitly enabled configuration. Follow [backend/SMT.md](backend/SMT.md); keep those dependencies out of the core backend environment.

## Testing

From `backend`, with its virtual environment installed:

```bash
env -u PYTHONPATH PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q
```

From `frontend`:

```bash
npm run lint
npm run build
```

The **Phase 4D.2 validation checkpoint** recorded **544 backend tests passed with 2 existing dependency warnings**, frontend lint passed, and production build passed. This is the milestone checkpoint, not a permanent guarantee or a fresh test run for this README update. Tests cover preservation, recognition boundaries, evidence parsing/recovery, conservative confidence handling, review corrections, verification, and undo; inference is mocked and requires no Audiveris or SMT execution.

## Milestones and next direction

| Milestone | Status | Outcome |
|---|---|---|
| Phase 4B | Complete | Preservation-based real-world MusicXML transposition |
| Phase 4C | Complete | Audiveris OMR, Vietnamese OCR, diagnostics/review foundation |
| Phase 4D.1 | Complete | SMT proof of concept; retained as experimental and disabled by default |
| Phase 4D.2 | Complete | Audiveris semantic recovery |

Next direction: improve the product-level **Review → Correct → Verify → Transpose → Export** experience. These steps have an existing implementation; further Phase 4E refinements are future work.

## Limitations

- OMR is not guaranteed to be perfect; source quality and notation complexity affect results. Unusual or ambiguous notation may require human review.
- Mixed-size notation depends on available OMR evidence. The benchmark's “ta” and “cùng” visual-size cases remain review-required.
- OSMD currently has a mixed-size chord rendering limitation; preserved XML semantics do not guarantee an identical visual preview.
- Semantic recovery supports corroborated simultaneous-note additions and small-display preservation, not arbitrary missing-note or rhythm repair. Unsupported evidence and ambiguous mappings remain for review.
- Structural validation cannot prove transcription accuracy or complete MusicXML schema compliance. Complex or unsupported musical values can be rejected.
- Harmony symbols are preserved but are not automatically transposed by the MusicXML transposer.
- Review storage is temporary and limited to one backend process; persistent accounts/shared storage are not implemented.
- SMT remains experimental, disabled by default, and outside the production recognition path.

## License

License information will be added when the project licensing decision is finalized.
