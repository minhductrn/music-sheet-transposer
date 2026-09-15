# Music Sheet Transposer

A web application for importing, viewing, and transposing sheet music.

The project is designed with a clear separation between the web interface and the core music-processing engine so that the same music-processing capabilities can later support a mobile application or other clients.

## Project Status

The project is currently in the foundation stage.

### Completed

- Project architecture and development specification
- FastAPI backend foundation
- Backend health-check API
- React + TypeScript + Vite frontend foundation
- Frontend-to-backend API communication
- React Router foundation
- Responsive base UI
- MusicXML domain-model foundation
- MusicXML parser and exporter foundation
- Measure timing persistence support
- VS Code Python interpreter configuration
- Automated backend tests
- Frontend build and lint validation

### Planned

- MusicXML validation
- MusicXML-based transposition
- Sheet-music rendering
- PDF and image import
- Optical Music Recognition (OMR)
- MusicXML export
- File sharing
- Mobile support

## Vision

The application will allow a user to:

1. Import sheet music from a PDF, image, or camera.
2. Recognize the musical notation.
3. Convert recognized notation into MusicXML.
4. Validate the musical structure.
5. Represent the score in an internal music model.
6. Transpose the music.
7. Render the transposed score.
8. Export or share the result.

The architecture is intentionally separated into recognition, music modeling, transposition, rendering, storage, and presentation layers.

## Architecture

The planned processing pipeline is:

```text
PDF / Image / Camera
        |
        v
Optical Music Recognition (OMR)
        |
        v
MusicXML
        |
        v
Validation
        |
        v
Internal Music Model
        |
        v
Transposition
        |
        v
Internal Music Model
        |
        v
MusicXML
        |
        v
Rendering / Export

The web application is separated from the music-processing core:
                    +----------------------+
                    |      Frontend        |
                    | React + TypeScript   |
                    +----------+-----------+
                               |
                               | REST API
                               v
                    +----------------------+
                    |       Backend        |
                    |       FastAPI        |
                    +----------+-----------+
                               |
              +----------------+----------------+
              |                |                |
              v                v                v
        Music Model        Recognition      Services
              |
              v
        Transposition
              |
              v
          MusicXML

This separation allows the music-processing layer to evolve independently from the user interface.

Technology Stack
Frontend
React
TypeScript
Vite
React Router
CSS
Node.js
npm
Backend
Python 3.12+
FastAPI
Pydantic
Pydantic Settings
Uvicorn
pytest
HTTPX
Development
Windows 11
WSL2
Ubuntu
VS Code
Git
GitHub
GitHub Copilot


Project Structure
music-sheet-transposer/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       └── health.py
│   │   ├── core/
│   │   │   └── config.py
│   │   ├── music/
│   │   │   ├── models/
│   │   │   │   ├── pitch.py
│   │   │   │   ├── note.py
│   │   │   │   ├── measure.py
│   │   │   │   ├── time_signature.py
│   │   │   │   ├── part.py
│   │   │   │   └── score.py
│   │   │   ├── parser/
│   │   │   │   └── musicxml_parser.py
│   │   │   └── exporter/
│   │   │       └── musicxml_exporter.py
│   │   ├── schemas/
│   │   │   └── health.py
│   │   └── main.py
│   ├── tests/
│   │   ├── fixtures/
│   │   │   └── simple_score.musicxml
│   │   ├── test_health.py
│   │   └── ...
│   ├── requirements.txt
│   └── ...
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
│   │   ├── main.tsx
│   │   └── index.css
│   ├── .env.example
│   ├── package.json
│   ├── package-lock.json
│   └── vite.config.ts
│
├── .vscode/
│   └── settings.json
│
├── .gitignore
├── PROJECT_SPEC.md
└── README.md

Backend API

The backend uses a versioned API structure:

/api/v1/

The current health endpoint is:

GET /api/v1/health

Example response:

{
  "status": "ok"
}

The API version prefix is centralized in the backend configuration so that future API changes can be introduced without coupling route definitions to the application configuration.

Frontend API Communication

Frontend HTTP communication is centralized in:

frontend/src/services/api.ts

Pages and components do not construct backend URLs directly or call fetch() for backend API operations.

During development, Vite proxies /api requests to the FastAPI backend.

The backend URL can be configured through:

frontend/.env.example

Example:

VITE_BACKEND_URL=http://127.0.0.1:8000

Environment files containing local configuration are excluded from Git.

MusicXML Foundation

MusicXML is the interchange format used as the boundary between recognized sheet music and the application's internal music model.

The internal model is designed to represent musical concepts such as:

Pitch
Note
Measure
Time signature
Part
Score

The goal is to avoid making the transposition engine depend directly on XML parsing details.

The intended flow is:

MusicXML
   |
   v
Parser
   |
   v
Internal Music Model
   |
   v
Music Processing
   |
   v
Internal Music Model
   |
   v
Exporter
   |
   v
MusicXML

This makes the core processing logic easier to test and allows the application to support other input or output formats later.

Timing and Measure Persistence

MusicXML does not require divisions and time signatures to be repeated in every measure.

For example, Measure 1 may define:

<attributes>
    <divisions>1</divisions>
    <time>
        <beats>4</beats>
        <beat-type>4</beat-type>
    </time>
</attributes>

If Measure 2 does not define new timing information, it continues using the timing established by Measure 1.

The internal model represents this distinction using None:

None = no new timing value declared in this measure

This does not mean that the measure has no timing information.

Instead, the measure continues using the previously established timing context until a later measure explicitly changes it.

Because MusicXML allows timing information to be declared once and then carried forward, Measure 2 does not need to repeat the same divisions and time signature. The application treats these values as inherited from Measure 1 unless a later measure explicitly changes them.

This approach preserves MusicXML semantics and prevents the exporter from unnecessarily repeating unchanged timing information.

Transposition

Transposition will operate on the internal music model rather than directly modifying MusicXML text.

The planned process is:

Input Score
    |
    v
Parse MusicXML
    |
    v
Internal Score Model
    |
    v
Apply Transposition
    |
    v
Updated Score Model
    |
    v
Export MusicXML

This design keeps musical logic independent from XML serialization.

Instrument-specific transposition can later be represented through configurable transposition intervals.

Examples include:

Alto Saxophone     -1.5 whole steps
Soprano Saxophone  +1 whole step

The exact implementation will be validated against musical notation and MusicXML semantics before being finalized.

Recognition

The planned recognition pipeline is:

PDF / Image / Camera
        |
        v
Image Processing
        |
        v
Optical Music Recognition
        |
        v
MusicXML
        |
        v
Validation

Recognition is intentionally separated from transposition.

This allows the application to replace or improve the OMR implementation without changing the transposition engine.

Rendering

The application will eventually render the score in the browser.

A MusicXML rendering library such as OpenSheetMusicDisplay may be evaluated during the rendering phase.

Rendering is treated as a presentation concern and will remain separate from the internal music model.

Testing Strategy

Testing is organized by responsibility.

Backend

Backend tests use:

pytest
FastAPI TestClient
HTTPX

Current tests include the API health endpoint.

Example:

cd ~/music-sheet-transposer/backend
PYTHONPATH=. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -v
Frontend

Frontend validation currently includes:

cd ~/music-sheet-transposer/frontend
npm run lint
npm run build

Future frontend testing will use:

Vitest
React Testing Library
Music Processing

Music-processing tests will focus on:

MusicXML parsing
MusicXML exporting
Timing inheritance
Pitch representation
Note representation
Measure structure
Transposition
Round-trip MusicXML behavior
Local Development
Backend

From the project root:

cd ~/music-sheet-transposer/backend

Start the development server:

uvicorn app.main:app --reload

The API will be available at:

http://127.0.0.1:8000

Health check:

curl http://127.0.0.1:8000/api/v1/health

Expected response:

{"status":"ok"}
Frontend

Open another terminal:

cd ~/music-sheet-transposer/frontend
npm install
npm run dev

Vite will display the local development URL in the terminal.

The frontend communicates with the backend through the /api proxy.

Environment Variables

Local environment configuration should not be committed to Git.

The frontend provides:

frontend/.env.example

Example:

VITE_BACKEND_URL=http://127.0.0.1:8000

The actual .env file is ignored by Git.

Never commit:

Passwords
API keys
Access tokens
Private credentials
Production secrets
Development Principles

The project follows several principles:

1. Separate UI from music processing

The frontend should not contain core musical-processing logic.

2. Use an internal music model

MusicXML is an interchange format, not the application's complete internal representation.

3. Keep services replaceable

External capabilities such as recognition, storage, and rendering should be isolated behind clear interfaces where appropriate.

4. Make small changes

Each implementation step should be focused and independently testable.

5. Test before expanding scope

New functionality should include appropriate tests before moving to the next major phase.

6. Avoid premature complexity

Database, authentication, cloud storage, mobile support, and advanced OMR features should be introduced only when they are required by the current development phase.

Planned Service Abstractions

The architecture may introduce the following service interfaces as the project grows:

MusicRecognitionService
        |
        v
MusicXML / Internal Music Model

TranspositionService
        |
        v
Internal Music Model

StorageService
        |
        v
Files / Database / Cloud Storage

These abstractions will allow implementation details to change without requiring major changes to the rest of the application.

Development Roadmap
Phase 1 — Foundation
 Repository structure
 Project specification
 Development environment
 Git and GitHub setup
Phase 2 — Backend Foundation
 FastAPI application
 API versioning
 Configuration
 Health endpoint
 Backend tests
Phase 3 — Frontend Foundation
 React + TypeScript
 Vite
 React Router
 Base layout
 API service layer
 Backend connection status
 Build and lint validation
Phase 4 — MusicXML
 Internal music model foundation
 MusicXML parser foundation
 MusicXML exporter foundation
 Measure timing support
 Validation
 More complete MusicXML coverage
 Round-trip testing
Phase 5 — Transposition
 Pitch transformation
 Note transposition
 Score transposition
 Instrument transposition
 Transposition tests
Phase 6 — Recognition
 PDF import
 Image import
 Camera input
 OMR integration
 MusicXML generation
 Recognition validation
Phase 7 — Export and Sharing
 MusicXML export
 PDF export
 Image export
 Sharing workflow
Phase 8 — Refinement
 Improved UI
 Error handling
 Performance optimization
 Accessibility
 Mobile-oriented architecture
 Production deployment
Git Workflow

The project uses Git for version control.

Typical workflow:

git status
git add .
git commit -m "describe the change"
git push origin master

Changes should be committed in small, meaningful units.

Examples:

feat: add MusicXML parser
feat: add transposition service
test: add MusicXML round-trip tests
fix: preserve measure timing context
docs: update project architecture
GitHub Copilot Working Rules

When using GitHub Copilot on this project:

Read PROJECT_SPEC.md before making architectural changes.
Prefer the smallest change that satisfies the requirement.
Keep frontend and backend responsibilities separate.
Add or update tests with functional changes.
Do not introduce unnecessary dependencies.
Do not commit secrets.
Avoid scope creep.
Explain the intended file changes before large implementation tasks.
Validate the result after each meaningful change.
Current Objective

The immediate objective is to build a reliable music-processing foundation before adding advanced recognition and user-facing features.

The project should first establish a stable path from:

MusicXML
    |
    v
Internal Music Model
    |
    v
Music Processing
    |
    v
MusicXML

Once this foundation is reliable, PDF/image recognition, rendering, transposition workflows, export, and sharing can be added incrementally.

License

License information will be added when the project licensing decision is finalized.