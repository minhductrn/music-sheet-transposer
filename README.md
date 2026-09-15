# Music Sheet Transposer

A web application for importing, viewing, and transposing sheet music.

The project separates the web UI from the core music-processing layer so that the music-processing capabilities can eventually be reused by web and mobile applications.

---

## Project Status

**Phase 4 — MusicXML Foundation**

The project currently has:

- FastAPI backend foundation
- React + TypeScript + Vite frontend
- Music-domain models
- MusicXML parser
- MusicXML exporter
- Multiple-measure support
- MusicXML timing support
- Notes and rests
- Round-trip testing

### Current Test Status


12 passed, 2 warnings

The next MusicXML improvements are:

Dotted notes
Ties
Expanded rest handling
Changing time signatures
Additional MusicXML fidelity
More comprehensive round-trip tests

After the MusicXML foundation is stable, the next major feature will be music transposition.

Future application features include:

Sheet music viewer
MusicXML import/export
PDF import
Image import
Camera capture
Optical Music Recognition (OMR)
Transposition
Export and sharing
Architecture
                    Music Sheet Transposer
                             │
             ┌───────────────┴───────────────┐
             │                               │
        Frontend                         Backend
             │                               │
      React + TypeScript                 FastAPI
             │                               │
             └───────────────┬───────────────┘
                             │
                    Music Processing
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
       MusicXML           Internal          Transposition
       Parser             Music Model          Engine
          │                  │                  │
          └──────────────────┼──────────────────┘
                             │
                       MusicXML Export
                             │
                       Future OMR Layer
Music Processing Pipeline

The long-term processing pipeline is:

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
 Viewer / Export / Share

The UI layer is intentionally separated from the core music-processing layer.

This allows the music-processing functionality to evolve independently and potentially be reused by future mobile applications.

MusicXML Foundation

The current implementation provides the first functional MusicXML foundation.

The internal model is designed to represent musical information independently from the XML format.

Current Music Model
Score
 └── Part
      └── Measure
           ├── TimeSignature
           └── Note
Score

Represents the complete musical score.

Current responsibilities include:

Score title
Parts
Part

Represents an individual musical part.

Current responsibilities include:

Part ID
Part name
Measures
Measure

Represents one musical measure.

Current properties include:

Measure number
divisions
Time signature
Notes
TimeSignature

Represents the time signature.

Current properties include:

Beats
Beat type

For example:

4/4

is represented as:

beats = 4
beat_type = 4
Note

Represents an individual musical event.

Current properties include:

Pitch
Duration
Note type
Rest state

Pitch contains:

Step
Octave
Optional alteration

Example:

C4 quarter note
MusicXML Parser

The parser converts MusicXML into the internal music model.

Current parser functionality includes:

Score title
Parts
Part names
Multiple measures
Measure numbers
Notes
Rests
Pitch
Duration
Note type
divisions
Time signatures

Example:

<measure number="1">
    <attributes>
        <divisions>1</divisions>
        <time>
            <beats>4</beats>
            <beat-type>4</beat-type>
        </time>
    </attributes>

    <note>
        <pitch>
            <step>C</step>
            <octave>4</octave>
        </pitch>
        <duration>1</duration>
        <type>quarter</type>
    </note>
</measure>

The parser converts this into the internal representation instead of allowing the rest of the application to depend directly on XML structures.

Timing and Measure Persistence

MusicXML attributes such as divisions and time signatures do not necessarily need to be repeated in every measure.

For example:

<measure number="1">
    <attributes>
        <divisions>1</divisions>
        <time>
            <beats>4</beats>
            <beat-type>4</beat-type>
        </time>
    </attributes>
</measure>

<measure number="2">
    ...
</measure>

Measure 2 may omit the attributes because they continue from measure 1.

The internal model therefore distinguishes between:

None

and an actual timing value.

None means:

No new value was declared in this measure.

It does not mean:

The score has no effective timing information.

This preserves the semantics of MusicXML declarations and allows the exporter to avoid unnecessarily repeating attributes.

MusicXML Exporter

The exporter converts the internal music model back into MusicXML.

Current exporter functionality includes:

MusicXML 4.0 Partwise format
Score title
Part list
Part names
Multiple measures
Measure numbers
divisions
Time signatures
Notes
Rests
Pitch
Duration
Note type

The exporter is designed to preserve the distinction between newly declared attributes and inherited attributes.

Round-Trip Testing

The current MusicXML foundation includes round-trip testing:

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
MusicXML

The round-trip tests verify that important musical information is preserved, including:

Score title
Part
Part name
Multiple measures
Measure numbers
Timing information
divisions
Time signatures
Notes
Pitch
Duration
Note type
Rest state

The current fixture contains two measures.

The first measure includes:

divisions = 1
4/4 time signature
C quarter note
D half note
E quarter note

The second measure contains:

F whole note
No new timing attributes

The second measure therefore inherits the effective timing context from the previous measure.

Project Structure
music-sheet-transposer/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       └── health.py
│   │   │
│   │   ├── core/
│   │   │   └── config.py
│   │   │
│   │   ├── music/
│   │   │   ├── models/
│   │   │   │   ├── pitch.py
│   │   │   │   ├── note.py
│   │   │   │   ├── measure.py
│   │   │   │   ├── time_signature.py
│   │   │   │   ├── part.py
│   │   │   │   └── score.py
│   │   │   │
│   │   │   ├── parser/
│   │   │   │   └── musicxml_parser.py
│   │   │   │
│   │   │   └── exporter/
│   │   │       └── musicxml_exporter.py
│   │   │
│   │   ├── schemas/
│   │   │   └── health.py
│   │   │
│   │   └── main.py
│   │
│   ├── tests/
│   │   ├── fixtures/
│   │   │   └── simple_score.musicxml
│   │   ├── test_health.py
│   │   └── ...
│   │
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   └── Layout.tsx
│   │   │
│   │   ├── pages/
│   │   │   └── Home.tsx
│   │   │
│   │   ├── services/
│   │   │   └── api.ts
│   │   │
│   │   ├── types/
│   │   │   └── health.ts
│   │   │
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── index.css
│   │
│   ├── .env.example
│   ├── package.json
│   └── vite.config.ts
│
├── .vscode/
│   └── settings.json
│
├── .gitignore
├── PROJECT_SPEC.md
└── README.md
Technology Stack
Frontend
React
TypeScript
Vite
React Router
CSS

Future frontend technologies may include:

OpenSheetMusicDisplay
React Testing Library
Vitest
Backend
Python
FastAPI
Pydantic
Pydantic Settings
pytest
HTTPX
Music
MusicXML
Internal Python music model
Future OMR integration
Future transposition engine
Development Tools
Windows 11
WSL2
Ubuntu
VS Code
Git
GitHub
GitHub Copilot
Node.js managed with NVM

Current Node environment:

Node.js 24.21.0
npm 11.19.0
Development Environment

The project is developed on:

Windows 11
    │
    ▼
WSL2
    │
    ▼
Ubuntu
    │
    ├── Python
    ├── FastAPI
    ├── Node.js
    ├── npm
    └── Git

Node.js is managed with NVM rather than the system package manager.

Backend Development

From the project root:

cd backend

Activate the Python virtual environment:

source .venv/bin/activate

Run the development server:

uvicorn app.main:app --reload

The API is available at:

http://127.0.0.1:8000

Health endpoint:

http://127.0.0.1:8000/api/v1/health

Expected response:

{
  "status": "ok"
}
Backend Testing

Run:

cd backend
PYTHONPATH=. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -v

Current result:

12 passed, 2 warnings

The two warnings are related to the test environment/plugin configuration and do not represent failing tests.

Frontend Development

From the project root:

cd frontend
npm install
npm run dev

The Vite development server normally starts on:

http://localhost:5173

If that port is already in use, Vite automatically selects another available port.

Frontend Validation

Build the frontend:

npm run build

Run linting:

npm run lint

Both currently pass successfully.

API Design

The backend API uses versioned routes:

/api/v1/

Current endpoint:

GET /api/v1/health

Future API areas may include:

/api/v1/musicxml
/api/v1/transposition
/api/v1/recognition
/api/v1/export

The exact API structure will evolve as the corresponding application features are implemented.

Frontend API Architecture

Frontend components and pages should not directly construct backend URLs or call fetch() for application APIs.

Backend communication is centralized through:

frontend/src/services/

The current API service is:

frontend/src/services/api.ts

The Vite development server proxies:

/api/*

to the FastAPI backend.

This keeps the frontend independent from the backend host configuration.

Future Service Architecture

The project is intended to introduce service abstractions as the application grows.

Potential services include:

MusicRecognitionService
TranspositionService
StorageService

Possible architecture:

              Application Layer
                      │
        ┌─────────────┼─────────────┐
        │             │             │
 Recognition     Transposition    Storage
  Service          Service        Service
        │             │             │
        ▼             ▼             ▼
       OMR         Music Model     Database

This will allow individual implementations to change without coupling the rest of the application to a specific provider or technology.

Planned Features
MusicXML
Dotted notes
Ties
Expanded rest handling
Changing time signatures
Additional MusicXML elements
Better validation
Higher-fidelity round-trip conversion
Transposition
Transpose by semitone
Transpose by interval
Instrument-specific transposition
Preserve rhythm and duration
Generate transposed MusicXML
Viewer
Render MusicXML
Zoom
Page navigation
Playback support
Responsive layout
Import

Future input formats:

MusicXML
PDF
Image
Camera
Optical Music Recognition

Future OMR pipeline:

Image / PDF
     │
     ▼
Image Processing
     │
     ▼
Music Recognition
     │
     ▼
MusicXML
     │
     ▼
Validation
Export

Future export options may include:

MusicXML
PDF
Image
Shareable files
Development Phases
Phase 1 — Foundation

Completed.

Repository
Project specification
Basic architecture
Development environment
Phase 2 — Backend Foundation

Completed.

FastAPI
Configuration
API versioning
Health endpoint
Testing foundation
Phase 3 — Frontend Foundation

Completed.

React
TypeScript
Vite
Routing
Layout
Backend connectivity
Responsive styling
Phase 4 — MusicXML Foundation

In progress / foundation completed.

Music models
MusicXML parser
MusicXML exporter
Multiple measures
Timing information
Rests
Round-trip tests
Phase 5 — Transposition

Planned.

Pitch transformation
Interval handling
Instrument transposition
Transposed MusicXML
Phase 6 — Recognition

Planned.

PDF processing
Image processing
OMR
MusicXML generation
Phase 7 — Export and Sharing

Planned.

PDF export
Image export
MusicXML export
Sharing workflows
Phase 8 — Refinement

Planned.

UI improvements
Performance
Error handling
Testing
Security
Mobile preparation
Testing Strategy

Testing will be expanded as functionality grows.

Backend
Unit tests
API tests
Music model tests
Parser tests
Exporter tests
Round-trip tests
Transposition tests
Frontend

Future tests will cover:

Components
Pages
API service behavior
User interactions
Error states
Music Processing

Special attention will be given to preserving musical meaning during transformations.

For example:

Input MusicXML
      │
      ▼
    Parser
      │
      ▼
Internal Model
      │
      ▼
Transformation
      │
      ▼
Internal Model
      │
      ▼
   Exporter
      │
      ▼
Output MusicXML
Git Workflow

The repository uses Git and GitHub.

Remote repository:

git@github.com:minhductrn/music-sheet-transposer.git

Main development branch:

master

Development principles:

Make small changes.
Validate changes before committing.
Keep commits focused.
Avoid unrelated changes.
Push stable checkpoints to GitHub.
Keep generated files and secrets out of Git.
Use clear commit messages.
Development Principles

The project follows these principles:

1. Separate UI from music processing

The UI should not contain core music-processing logic.

2. Keep the internal model independent

Music processing should operate on the internal music model rather than directly manipulating UI components or raw XML whenever possible.

3. Make small changes

Each feature should be implemented incrementally and validated before moving to the next feature.

4. Test musical behavior

Tests should verify musical meaning, not only XML syntax.

5. Preserve MusicXML semantics

The parser and exporter should preserve information that affects musical interpretation.

6. Avoid premature complexity

Only introduce additional architecture when it provides a clear benefit to the project.

7. Keep future mobile support in mind

The backend and core music-processing layer should remain reusable for a future mobile application.

Current Checkpoint

The project has reached a stable Phase 4 MusicXML foundation.

Current status:

Backend                  ✅
Frontend                 ✅
Music Models             ✅
MusicXML Parser          ✅
MusicXML Exporter        ✅
Multiple Measures        ✅
Timing Information       ✅
Notes and Rests          ✅
Round-Trip Testing       ✅
Backend Tests            ✅ 12 passed
Frontend Build           ✅
Frontend Lint            ✅

The current next step is to improve MusicXML fidelity with:

Dotted Notes
     ↓
Ties
     ↓
Expanded Rest Handling
     ↓
Changing Time Signatures
     ↓
Additional MusicXML Fidelity
     ↓
Transposition

The project will continue to evolve incrementally from a reliable MusicXML foundation toward a complete sheet-music import, viewing, transposition, and export application.

```text