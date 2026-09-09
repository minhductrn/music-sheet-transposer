# Music Sheet Transposer — Project Specification

## 1. Project Overview

Build a web-first music sheet application that can:

1. Import music sheets from PDF, image, or camera.
2. Recognize notation and convert it into structured digital music.
3. Display a clean music sheet in the browser.
4. Transpose music by musical interval.
5. Transpose for instruments such as Alto Saxophone and Soprano Saxophone.
6. Export the result.
7. Share the result using email, messaging apps, or supported browser sharing.

The web application is the MVP. A future mobile application should reuse the same backend and music-processing services.

## 2. Development Environment

- Host: Windows 11
- IDE: Visual Studio Code
- Linux environment: WSL2 + Ubuntu
- AI coding assistant: **GitHub Copilot only**
- Browser: Chrome or Microsoft Edge

Run the development toolchain inside WSL2:

- Git
- Python 3.12+
- Node.js / npm
- FastAPI
- React / Vite
- pytest
- Vitest

Store the project inside the WSL filesystem, not `/mnt/c/`.

Recommended location:

```text
~/music-sheet-transposer/
```

Open from WSL:

```bash
cd ~/music-sheet-transposer
code .
```

VS Code should be connected to the WSL/Ubuntu environment.

### GitHub Copilot

GitHub Copilot is the project's designated AI coding assistant because the project already has a Copilot subscription.

Use Copilot for:

- Code generation
- Code explanation
- Refactoring
- Test generation
- Debugging
- Documentation
- Code review
- Checking implementation against `PROJECT_SPEC.md`

Do not introduce Cursor or another AI coding assistant unless the project requirements are explicitly changed later.

## 3. Technology Stack

### Frontend

- React
- TypeScript
- Vite
- React Router
- Tailwind CSS or lightweight CSS
- OpenSheetMusicDisplay (OSMD)
- Vitest
- React Testing Library

### Backend

- Python 3.12+
- FastAPI
- Pydantic
- pytest

### Music

- MusicXML as the main interchange format
- Internal structured music model for processing

### Database

- SQLite for MVP
- Repository layer so PostgreSQL can be introduced later

### Storage

- Local filesystem for development
- S3-compatible storage later

## 4. Music Processing Architecture

```text
PDF / Image / Camera
        ↓
      OMR
        ↓
   MusicXML
        ↓
    Validation
        ↓
Internal Music Model
        ↓
  Transposition
        ↓
   MusicXML
        ↓
Rendering / Export
```

Use service abstractions:

```text
MusicRecognitionService
TranspositionService
StorageService
```

## 5. OMR / Music Recognition

OMR means Optical Music Recognition.

Create a `MusicRecognitionService` abstraction so the OMR engine/provider can be changed later. A mock recognition service is acceptable during early development.

## 6. File Import

Supported:

- PDF
- PNG
- JPG/JPEG
- Camera image

Backend must validate MIME type, extension, file size, and filenames. Uploaded content must never be executed.

## 7. Music Sheet Viewer

Use OpenSheetMusicDisplay to render MusicXML in the browser.

Support zoom, page navigation, responsive display, and clean rendering.

## 8. Transposition Engine

Transposition must use real musical intervals, not arbitrary pitch values.

Support:

- Up/down by semitone
- Configurable intervals
- Key signature changes
- Correct note spelling where practical
- Rhythm and measure preservation

Core concept:

```text
transpose(score, interval)
```

The engine must be independent from the UI and covered by automated tests.

## 9. Instrument Transposition

Do not implement instrument transposition as arbitrary values such as “decrease 1.5 pitch” or “increase 1 pitch.”

Use explicit concert-pitch/written-pitch relationships and one consistent convention throughout the application.

### Alto Saxophone

- E-flat transposing instrument

### Soprano Saxophone

- B-flat transposing instrument

Example configuration:

```json
{
  "alto_saxophone": {
    "name": "Alto Saxophone",
    "transposition": "Eb"
  },
  "soprano_saxophone": {
    "name": "Soprano Saxophone",
    "transposition": "Bb"
  }
}
```

Instrument transposition must have automated tests.

## 10. Frontend User Flow

```text
Home → Upload Music Sheet → Processing → Music Preview → Transpose → Review → Export / Share
```

## 11. Export and Sharing

MVP:

- Download MusicXML
- PDF export where technically supported
- Web Share API where available
- Download fallback for email/messaging apps

Do not build custom integrations for every messaging platform in the MVP.

## 12. API

Use `/api/v1/`.

Example endpoints:

```text
GET  /api/v1/health
POST /api/v1/scores/import
GET  /api/v1/scores/{id}
POST /api/v1/scores/{id}/transpose
GET  /api/v1/scores/{id}/export
```

Use Pydantic models.

## 13. Database and Storage

MVP database: SQLite.

Potential entities:

```text
User
Score
ScoreVersion
UploadedFile
ProcessingJob
```

Use repositories rather than putting database queries directly into business logic.

Storage abstraction:

```text
StorageService
```

MVP: `LocalStorageService`; future: `S3StorageService`.

## 14. Security

- Validate uploaded files
- Limit file size
- Sanitize filenames
- Never execute uploaded content
- Use generated IDs for stored files
- Store secrets in environment variables
- Never commit API keys
- Add `.env` to `.gitignore`
- Provide `.env.example`

## 15. Error Handling

Handle unsupported/corrupt files, OMR failures, invalid MusicXML, unsupported notation, transposition failures, export failures, and storage failures.

User-facing errors should be understandable and must not expose stack traces.

## 16. Testing

Backend: pytest for file validation, MusicXML validation, transposition, instrument transposition, API endpoints, and repository layer.

Frontend: Vitest + React Testing Library for upload UI, processing states, viewer state, transposition controls, and export/share actions.

Critical music logic must have automated tests.

## 17. Project Structure

```text
music-sheet-transposer/
├── README.md
├── PROJECT_SPEC.md
├── .gitignore
├── .env.example
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── repositories/
│   │   └── core/
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── hooks/
│   │   ├── types/
│   │   └── utils/
│   └── tests/
├── docs/
└── data/
```

## 18. Git Strategy

Use small, meaningful commits, for example:

```text
chore: initialize project structure
feat: add FastAPI backend
feat: add React frontend
feat: add MusicXML viewer
feat: add transposition service
test: add transposition tests
feat: add file upload
```

## 19. MVP Development Phases

### Phase 1 — Project Foundation

- Create project directory
- Configure WSL2
- Configure VS Code
- Configure Git
- Verify GitHub Copilot
- Create README, `.gitignore`, and `.env.example`

### Phase 2 — Backend Foundation

- FastAPI
- Health endpoint
- Pydantic configuration
- Basic tests
- API versioning

### Phase 3 — Frontend Foundation

- React
- TypeScript
- Vite
- Basic routing
- Upload page
- API connection

### Phase 4 — MusicXML

- MusicXML validation
- OpenSheetMusicDisplay integration

### Phase 5 — Transposition

- Musical interval engine
- Key signature handling
- Instrument transposition
- Unit tests

### Phase 6 — Recognition

- PDF/image upload
- OMR service abstraction
- Initial OMR integration
- Processing status

### Phase 7 — Export and Sharing

- MusicXML download
- PDF export if supported
- Web Share API
- Download fallback

### Phase 8 — Refinement

- Error handling
- UI improvements
- Performance
- Security
- Documentation

# 20. FIRST STEP — Create Project Directory and Start with VS Code + GitHub Copilot

**Start here. Do not build application features yet.**

### Step 1 — Open Ubuntu / WSL

Open Ubuntu in Windows and verify:

```bash
wsl --version
lsb_release -a
```

### Step 2 — Create the project directory

```bash
cd ~
mkdir -p music-sheet-transposer
cd music-sheet-transposer
pwd
```

Expected pattern:

```text
/home/<your-user>/music-sheet-transposer
```

Do NOT create the project under `/mnt/c/`.

### Step 3 — Initialize Git

```bash
git init
git status
```

### Step 4 — Open in VS Code

```bash
code .
```

Confirm VS Code is connected to WSL/Ubuntu. The lower-left corner should show the WSL environment.

### Step 5 — Verify GitHub Copilot

In VS Code:

1. Open Extensions.
2. Search for **GitHub Copilot**.
3. Install/enable the official GitHub Copilot extension.
4. Sign in to the GitHub account with the existing Copilot subscription.
5. Open Copilot Chat.

First test prompt:

```text
Read PROJECT_SPEC.md and summarize the project architecture.
Do not create or modify any files.
```

### Step 6 — Create the initial files

Create only:

```text
PROJECT_SPEC.md
README.md
.gitignore
.env.example
```

Do not create OMR, database, authentication, or advanced music-processing code yet.

### Step 7 — Initial Git commit

```bash
git add PROJECT_SPEC.md README.md .gitignore .env.example
git commit -m "chore: initialize music sheet transposer project"
git status
```

The working tree should be clean.

# 21. SECOND STEP — Backend Foundation

Only after the project foundation is committed.

```bash
cd ~/music-sheet-transposer
mkdir backend
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn pytest
```

Initially implement only:

```text
GET /api/v1/health
```

Expected response:

```json
{"status": "ok"}
```

# 22. THIRD STEP — Frontend Foundation

After the backend foundation works:

```bash
cd ~/music-sheet-transposer
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm run dev
```

Initially create only a home page, basic routing, backend health check, and basic layout.

# 23. GitHub Copilot Working Rules

Before generating significant code, Copilot should:

1. Read `PROJECT_SPEC.md`.
2. Inspect the existing project structure.
3. Check existing implementations.
4. Avoid duplicate services/components.
5. Make the smallest reasonable change.
6. Add/update tests for important logic.
7. Avoid unnecessary dependencies.
8. Never hard-code secrets.
9. Keep frontend and backend responsibilities separate.
10. Avoid expanding the requested scope.

Recommended prompt:

```text
Read PROJECT_SPEC.md and inspect the existing project.

Implement only the next task:
[describe one task]

Constraints:
- Follow PROJECT_SPEC.md.
- Do not implement unrelated features.
- Reuse existing code where possible.
- Add tests where appropriate.

Before making large changes, explain which files you plan to create or modify.
```

# 24. Important Product Principle

Keep these responsibilities separate:

```text
Music Recognition
        ↓
Music Representation
        ↓
Music Processing / Transposition
        ↓
Rendering
        ↓
User Interface
```

The UI must not contain the core music-processing logic.

The architecture should allow future replacement of the OMR provider, database, storage, web frontend, or mobile frontend without rewriting the core transposition engine.

# 25. Current Starting Point

```text
Windows 11
    ↓
WSL2 / Ubuntu
    ↓
~/music-sheet-transposer/
    ↓
VS Code
    ↓
GitHub Copilot
    ↓
Git
```

Immediate checklist:

```text
[ ] Create ~/music-sheet-transposer
[ ] Open it with VS Code through WSL
[ ] Initialize Git
[ ] Add PROJECT_SPEC.md
[ ] Create README.md
[ ] Create .gitignore
[ ] Create .env.example
[ ] Verify GitHub Copilot
[ ] Make initial Git commit
```

**Do not start OMR, database, authentication, or advanced music processing until the foundation is successfully created and committed.**
