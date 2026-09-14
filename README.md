# Music Sheet Transposer

A web-based application for importing, viewing, and transposing sheet music.

The project is designed with a clean separation between the web interface, backend API, and core music-processing logic so that future features such as OMR, MusicXML rendering, transposition, PDF export, and mobile applications can be added without redesigning the foundation.

---

## Project Status

**Current Phase: Phase 4 — MusicXML Foundation ✅**

The project has completed the initial application foundation and the first version of the internal music model and MusicXML processing layer.

### Completed

- [x] Project specification and architecture
- [x] Git/GitHub repository
- [x] Backend FastAPI foundation
- [x] `/api/v1/health` API endpoint
- [x] Backend automated tests
- [x] React + TypeScript + Vite frontend
- [x] Frontend/backend API integration
- [x] Frontend development proxy
- [x] Responsive application shell
- [x] Internal music data model
- [x] MusicXML parser foundation
- [x] MusicXML exporter foundation
- [x] MusicXML round-trip test
- [x] 9 backend tests passing

### In Progress

- [ ] Improve MusicXML fidelity
- [ ] Add complete note duration/type handling
- [ ] Add MusicXML rendering/viewer
- [ ] Implement transposition engine
- [ ] Implement OMR integration
- [ ] Add file upload workflow

---

# Architecture

The application follows a layered architecture.

```text
                    User
                     │
                     ▼
          ┌─────────────────────┐
          │   React Frontend    │
          │  TypeScript + Vite  │
          └──────────┬──────────┘
                     │
                     │ REST API
                     ▼
          ┌─────────────────────┐
          │    FastAPI Backend  │
          │     /api/v1         │
          └──────────┬──────────┘
                     │
          ┌──────────┴──────────┐
          │                     │
          ▼                     ▼
 ┌──────────────────┐   ┌──────────────────┐
 │  Music Services  │   │  Future Services │
 │                  │   │                  │
 │ Internal Model   │   │ OMR              │
 │ MusicXML Parser  │   │ Storage          │
 │ MusicXML Exporter│   │ Recognition      │
 │ Transposition    │   │ Rendering        │
 └──────────────────┘   └──────────────────┘

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
 Internal Music Model
        │
        ▼
    MusicXML
        │
        ▼
 Rendering / Export

 MusicXML Foundation

Phase 4 introduces the first internal representation of musical notation.

The current model contains:

Score
 └── Part
      └── Measure
           └── Note
                └── Pitch
Current models
Pitch

Represents the pitch of a note.

Pitch
├── step
├── octave
└── alter

Example:

C4
D4
F#4
Bb4
Note

Represents a musical note or rest.

Note
├── pitch
├── duration
└── is_rest
Measure

Represents a measure containing notes.

Measure
├── number
└── notes[]
Part

Represents a musical part or instrument.

Part
├── id
├── name
└── measures[]
Score

Represents the complete musical score.

Score
├── title
└── parts[]
MusicXML Parser

The current MusicXML parser supports the basic MusicXML Partwise structure.

Current functionality includes:

Score title
Parts
Part names
Measures
Measure numbers
Notes
Rests
Pitch step
Pitch octave
Pitch alteration
Note duration

Example:

from pathlib import Path

from app.music.musicxml.parser import parse_musicxml

score = parse_musicxml(
    Path("simple_score.musicxml")
)

print(score)

The parser converts MusicXML into the application's internal Score model.

MusicXML
    │
    ▼
MusicXML Parser
    │
    ▼
Internal Score Model
MusicXML Exporter

The exporter converts the internal music model back into MusicXML.

Internal Score Model
        │
        ▼
MusicXML Exporter
        │
        ▼
MusicXML file

Example:

from pathlib import Path

from app.music.musicxml.exporter import export_musicxml

export_musicxml(
    score,
    Path("output.musicxml")
)

The current exporter generates:

MusicXML 4.0 Partwise document
Score title
Part list
Part names
Measures
Basic attributes
Key
Time signature
Clef
Notes
Rests
Pitch
Duration

MusicXML fidelity will be expanded in later phases.

MusicXML Round Trip

A round-trip test verifies that the basic musical information survives a parse/export/parse cycle.

              MusicXML
                 │
                 ▼
              Parser
                 │
                 ▼
         Internal Music Model
                 │
                 ▼
              Exporter
                 │
                 ▼
          New MusicXML
                 │
                 ▼
              Parser
                 │
                 ▼
         Internal Music Model

The current round-trip test verifies preservation of:

Score title
Part
Measure
Notes
Pitch
Duration
Project Structure
music-sheet-transposer/
│
├── PROJECT_SPEC.md
├── README.md
├── .gitignore
│
├── backend/
│   ├── requirements.txt
│   │
│   ├── app/
│   │   ├── __init__.py
│   │   │
│   │   ├── main.py
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       └── health.py
│   │   │
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   └── config.py
│   │   │
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   └── health.py
│   │   │
│   │   └── music/
│   │       ├── __init__.py
│   │       │
│   │       ├── models/
│   │       │   ├── __init__.py
│   │       │   ├── pitch.py
│   │       │   ├── note.py
│   │       │   ├── measure.py
│   │       │   └── score.py
│   │       │
│   │       └── musicxml/
│   │           ├── __init__.py
│   │           ├── parser.py
│   │           └── exporter.py
│   │
│   ├── tests/
│   │   ├── test_health.py
│   │   │
│   │   └── music/
│   │       ├── fixtures/
│   │       │   └── simple_score.musicxml
│   │       ├── test_models.py
│   │       ├── test_musicxml_parser.py
│   │       └── test_musicxml_roundtrip.py
│   │
│   └── .venv/
│       └── ...
│
└── frontend/
    ├── package.json
    ├── package-lock.json
    ├── vite.config.ts
    ├── tsconfig.json
    ├── tsconfig.app.json
    ├── tsconfig.node.json
    ├── eslint.config.js
    ├── index.html
    ├── .env.example
    │
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── index.css
        │
        ├── components/
        │   └── Layout.tsx
        │
        ├── pages/
        │   └── Home.tsx
        │
        ├── services/
        │   └── api.ts
        │
        └── types/
            └── health.ts
Technology Stack
Frontend
React
TypeScript
Vite
React Router
CSS
Backend
Python
FastAPI
Pydantic
Pydantic Settings
Uvicorn
pytest
HTTPX
Music
MusicXML
Python XML processing
Pydantic internal music models
Development Environment
Windows 11
WSL2
Ubuntu
VS Code
Git
GitHub
GitHub Copilot
Node.js managed with NVM
Development Environment

The project is developed primarily inside WSL2.

Example environment:

Windows 11
    │
    ▼
WSL2
    │
    ▼
Ubuntu
    │
    ├── Python
    ├── Node.js
    ├── Git
    └── VS Code

Node.js is managed using NVM.

Current development environment uses:

Node.js v24.21.0
npm 11.19.0
Running the Backend

From WSL2:

cd ~/music-sheet-transposer/backend

Activate the virtual environment:

source .venv/bin/activate

Start FastAPI:

PYTHONPATH=. uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

The backend API is available at:

http://127.0.0.1:8000

Health endpoint:

http://127.0.0.1:8000/api/v1/health

Test with:

curl http://127.0.0.1:8000/api/v1/health

Expected response:

{
  "status": "ok"
}
Running Backend Tests

From the backend directory:

cd ~/music-sheet-transposer/backend
source .venv/bin/activate

Run:

PYTHONPATH=. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -v

Current result:

9 passed

The test suite currently covers:

API health endpoint
Music model validation
Pitch model
Note model
Rest model
Score hierarchy
MusicXML parser
MusicXML pitch parsing
MusicXML round trip
Running the Frontend

From another WSL2 terminal:

cd ~/music-sheet-transposer/frontend

Install dependencies if needed:

npm install

Start the development server:

npm run dev

Vite will display the local development URL.

The frontend uses a development proxy so /api/* requests are forwarded to the FastAPI backend.

Frontend Environment

The example environment file is:

frontend/.env.example

It contains:

VITE_BACKEND_URL=http://127.0.0.1:8000

Local environment files should not be committed.

The project .gitignore excludes:

.env
*.local
Frontend Validation

Build the frontend:

npm run build

Run ESLint:

npm run lint

Both should complete successfully before committing frontend changes.

API Design

The backend API is versioned under:

/api/v1

Current endpoint:

GET /api/v1/health

Future API areas may include:

/api/v1/files
/api/v1/scores
/api/v1/musicxml
/api/v1/transposition
/api/v1/recognition
/api/v1/export

These endpoints will be introduced only when the corresponding features are implemented.

Future Music Processing Services

The architecture is designed around service abstractions.

Potential services include:

MusicRecognitionService
TranspositionService
StorageService
RenderingService
ExportService

The goal is to keep the core music model independent from external implementations.

For example, OMR could eventually be replaced without changing the transposition engine:

             OMR Provider A
                  │
                  ▼
             MusicXML
                  │
                  ▼
       Internal Music Model
                  │
                  ▼
        Transposition Engine
                  │
                  ▼
             MusicXML

Another OMR provider could be added later without changing the core architecture.

Planned Features
Import

Future input sources:

PDF
Image
Camera
MusicXML
Recognition

Future OMR workflow:

Image / PDF
     │
     ▼
    OMR
     │
     ▼
 MusicXML
     │
     ▼
Validation
Viewing

The application will eventually provide a browser-based music sheet viewer.

Potential technology:

OpenSheetMusicDisplay
MusicXML rendering
Interactive score viewing
Transposition

The application will support pitch transposition.

Examples:

Concert Pitch
     │
     ▼
Transpose
     │
     ▼
Instrument Pitch

Potential instrument support includes:

Alto Saxophone
Soprano Saxophone
Other transposing instruments

The exact transposition rules will be implemented as part of the transposition engine rather than embedded in the UI.

Export

Future export options may include:

MusicXML
PDF
Image
Shareable files
Sharing

Future versions may support sharing through:

Email
Messaging
Download
Shareable links
Development Phases
Phase 1 — Foundation
 Project specification
 Repository structure
 Git initialization
 Development environment
Phase 2 — Backend Foundation
 FastAPI application
 API versioning
 Configuration
 Health endpoint
 Automated tests
Phase 3 — Frontend Foundation
 React
 TypeScript
 Vite
 React Router
 Application layout
 Backend connection
 Responsive styling
 Frontend build/lint validation
Phase 4 — MusicXML Foundation
 Internal music model
 Pitch model
 Note model
 Measure model
 Part model
 Score model
 MusicXML parser
 MusicXML exporter
 MusicXML fixture
 MusicXML round-trip test
Phase 5 — Transposition
 Transposition model
 Pitch transposition
 Chromatic transposition
 Instrument transposition
 Alto saxophone support
 Soprano saxophone support
 Transposition tests
Phase 6 — Music Recognition
 File upload
 PDF processing
 Image processing
 OMR integration
 MusicXML generation
 Recognition validation
Phase 7 — Export and Sharing
 MusicXML export
 PDF export
 Image export
 Sharing workflow
 Download workflow
Phase 8 — Refinement
 UI improvements
 Error handling
 Performance optimization
 Security improvements
 Additional automated tests
 Deployment
 Mobile strategy
Testing Strategy

Testing will be implemented at multiple levels.

Backend Unit Tests

Test:

Music models
Pitch calculations
Note handling
Measure handling
Transposition
MusicXML parsing
MusicXML exporting
API Tests

Test:

HTTP status codes
Request validation
Response schemas
Error handling
API versioning
Frontend Tests

Future tests will cover:

Components
Pages
API integration
User interactions
File upload
Transposition controls

Potential tools:

Vitest
React Testing Library
End-to-End Testing

Future end-to-end testing may cover:

Upload
  ↓
Recognition
  ↓
View
  ↓
Transpose
  ↓
Export
Git Workflow

The project uses Git for version control.

Check status:

git status

Review changes:

git diff

Stage changes:

git add .

Commit:

git commit -m "description of change"

Push:

git push origin master

Before committing, verify:

git status

and run the relevant tests.

Development Principles

The project follows several principles:

1. Keep the architecture simple

Implement only what is needed for the current phase.

2. Separate UI from music processing

React should handle presentation and user interaction.

The backend should handle music processing and business logic.

3. Keep the internal music model independent

MusicXML should not become the application's internal representation.

The internal model should be capable of supporting multiple input/output formats.

4. Make small changes

Each development step should introduce one logical feature.

5. Test before moving forward

New functionality should have automated tests whenever practical.

6. Avoid unnecessary dependencies

Add a dependency only when it provides clear value.

7. Protect configuration and secrets

Never commit:

.env
API keys
Passwords
Tokens
Private credentials
