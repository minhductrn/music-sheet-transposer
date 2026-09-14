# Backend

The backend for the Music Sheet Transposer application.

The backend provides the API and will eventually contain the core music-processing services. It is intentionally separated from the frontend so that the same processing capabilities can later support multiple clients.

## Technology

* Python
* FastAPI
* Pydantic
* pytest
* Uvicorn

## Requirements

* Python 3.12+
* Python virtual environment

## Setup

From the backend directory:

```bash
cd ~/music-sheet-transposer/backend
```

Create a virtual environment if one does not already exist:

```bash
python3 -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Development Server

Start the FastAPI development server:

```bash
PYTHONPATH=. uvicorn app.main:app \
  --host 127.0.0.1 \
  --port 8000 \
  --reload
```

The API is available at:

```text
http://127.0.0.1:8000
```

## Health Check

The current API provides:

```text
GET /api/v1/health
```

Example:

```bash
curl http://127.0.0.1:8000/api/v1/health
```

Expected response:

```json
{
  "status": "ok"
}
```

## API Structure

```text
app/
├── api/
│   └── v1/
│       └── health.py
├── core/
│   └── config.py
├── schemas/
│   └── health.py
└── main.py
```

API routes are versioned under:

```text
/api/v1/
```

This allows future API changes without unnecessarily breaking existing clients.

## Testing

Activate the virtual environment:

```bash
source .venv/bin/activate
```

Run the test suite:

```bash
PYTHONPATH=. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -v
```

The current test suite verifies the health endpoint.

## Planned Architecture

The long-term backend architecture will support the following pipeline:

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

## Music Transposition

The application will use explicit concert-pitch and written-pitch relationships.

Initial target instruments:

* Alto Saxophone — E♭
* Soprano Saxophone — B♭

Transposition logic will be implemented as a dedicated service rather than being embedded in API routes or UI code.

## Development Principles

* Keep business logic separate from API routes.
* Keep music-processing services independent from FastAPI.
* Use Pydantic schemas at API boundaries.
* Version public API routes under `/api/v1/`.
* Add automated tests for backend functionality.
* Keep processing logic modular and testable.
* Avoid committing `.venv`, Python caches, credentials, or other environment-specific files.

## Current Status

**Phase 2 — Backend Foundation: Complete**

Implemented:

* FastAPI application
* Application configuration
* Versioned API structure
* Health endpoint
* Pydantic health response
* Automated health test

The backend is ready for the MusicXML foundation in Phase 4.
