# Music Sheet Transposer

A web application for importing, viewing, and transposing sheet music.

The project is designed to separate the user interface from the core music-processing pipeline so that the same backend capabilities can later support web and mobile clients.

## Project Status

**Current phase: Phase 3 — Frontend Foundation ✅**

Completed:

* React + TypeScript + Vite frontend
* React Router
* FastAPI backend foundation
* Versioned API structure under `/api/v1/`
* Backend health endpoint
* Frontend-to-backend API connection
* Vite development proxy
* Environment configuration
* Backend health test
* TypeScript production build
* ESLint validation

## Architecture

```text
Browser
   │
   ▼
React + TypeScript
   │
   ▼
Frontend API Service
   │
   ▼
Vite Proxy
   │
   ▼
FastAPI
   │
   ▼
Future Music Processing Services
```

The frontend is intentionally separated from the music-processing logic.

## Project Structure

```text
music-sheet-transposer/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       └── health.py
│   │   ├── core/
│   │   │   └── config.py
│   │   ├── schemas/
│   │   │   └── health.py
│   │   └── main.py
│   ├── tests/
│   │   └── test_health.py
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   └── Layout.tsx
│   │   ├── pages/
│   │   │   └── Home.tsx
│   │   ├── services/
│   │   │   └── api.ts
│   │   ├── types/
│   │   │   └── health.ts
│   │   ├── App.tsx
│   │   ├── index.css
│   │   └── main.tsx
│   ├── .env.example
│   ├── package.json
│   └── vite.config.ts
│
├── .gitignore
└── README.md
```

## Technology Stack

### Frontend

* React
* TypeScript
* Vite
* React Router
* ESLint

### Backend

* Python
* FastAPI
* Pydantic
* pytest

### Development Environment

* Windows 11
* WSL2
* Ubuntu
* VS Code
* Git / GitHub
* GitHub Copilot

## Running the Project

### Backend

```bash
cd ~/music-sheet-transposer/backend
source .venv/bin/activate

PYTHONPATH=. uvicorn app.main:app \
  --host 127.0.0.1 \
  --port 8000 \
  --reload
```

Backend health endpoint:

```text
http://127.0.0.1:8000/api/v1/health
```

Expected response:

```json
{
  "status": "ok"
}
```

### Frontend

In a separate terminal:

```bash
cd ~/music-sheet-transposer/frontend
source ~/.bashrc
npm run dev
```

The Vite development server normally starts on:

```text
http://localhost:5173/
```

If that port is already in use, Vite automatically selects another available port.

The frontend uses the Vite proxy to forward `/api/*` requests to the FastAPI backend.

## Testing

### Backend

```bash
cd ~/music-sheet-transposer/backend
source .venv/bin/activate
PYTHONPATH=. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -v
```

### Frontend

```bash
cd ~/music-sheet-transposer/frontend
npm run build
npm run lint
```

## Planned Music Processing Architecture

The long-term music-processing pipeline is:

```text
PDF / Image / Camera
        │
        ▼
       OMR
        │
        ▼
    MusicXML
        │
        ▼
    Validation
        │
        ▼
 Internal Music Model
        │
        ▼
   Transposition
        │
        ▼
    MusicXML
        │
        ▼
 Rendering / Export
```

Planned service abstractions include:

* `MusicRecognitionService`
* `TranspositionService`
* `StorageService`

## Instrument Transposition

The application will use explicit concert-pitch and written-pitch relationships.

Initial target instruments:

* **Alto Saxophone — E♭**
* **Soprano Saxophone — B♭**

Transposition will be implemented as a musical transformation rather than an arbitrary numeric pitch adjustment.

## Development Principles

* Keep frontend and backend responsibilities separate.
* Keep music-processing logic independent from the UI.
* Make small, testable changes.
* Avoid committing secrets or environment-specific credentials.
* Add tests as backend functionality is introduced.
* Avoid implementing future-phase features prematurely.
* Keep API routes versioned under `/api/v1/`.

## Roadmap

* [x] Phase 1 — Project foundation
* [x] Phase 2 — Backend foundation
* [x] Phase 3 — Frontend foundation
* [ ] Phase 4 — MusicXML foundation
* [ ] Phase 5 — Transposition engine
* [ ] Phase 6 — Music recognition / OMR
* [ ] Phase 7 — Export and sharing
* [ ] Phase 8 — Refinement and testing

## Current Git Checkpoint

Phase 3 frontend foundation:

```text
b100e29 feat: complete frontend foundation
```

The working tree was clean at the completion of Phase 3.
