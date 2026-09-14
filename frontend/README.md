# Frontend

The frontend for the Music Sheet Transposer web application.

The frontend is responsible for the user interface, navigation, user interaction, and communication with the backend API. Music-processing logic should remain outside the UI layer.

## Technology

* React
* TypeScript
* Vite
* React Router
* ESLint

## Requirements

* Node.js 24+
* npm
* WSL2 / Ubuntu development environment

The project uses NVM for Node.js version management.

Check the installed versions:

```bash
node -v
npm -v
```

## Setup

From the frontend directory:

```bash
cd ~/music-sheet-transposer/frontend
```

Install dependencies:

```bash
npm install
```

## Environment Configuration

The frontend uses a Vite environment variable for the backend URL.

Copy the example configuration if needed:

```bash
cp .env.example .env
```

Default configuration:

```text
VITE_BACKEND_URL=http://127.0.0.1:8000
```

Do not commit `.env` files containing environment-specific configuration or secrets.

## Development

Start the Vite development server:

```bash
npm run dev
```

The development server normally runs at:

```text
http://localhost:5173/
```

If port 5173 is already in use, Vite automatically selects another available port.

## Backend Connection

During development, Vite proxies `/api` requests to the FastAPI backend.

Example:

```text
Frontend
    │
    │ /api/v1/health
    ▼
Vite Proxy
    │
    ▼
FastAPI :8000
```

The backend must be running for API-dependent frontend features to work.

## Build

Create a production build:

```bash
npm run build
```

## Lint

Run ESLint:

```bash
npm run lint
```

## Source Structure

```text
src/
├── components/    # Reusable UI components
├── pages/         # Route-level pages
├── services/      # Backend/API communication
├── types/         # TypeScript types
├── App.tsx        # Application routes
├── index.css      # Global styles
└── main.tsx       # Application entry point
```

## Development Principles

* Keep API calls inside `services/`.
* Keep reusable UI components inside `components/`.
* Keep route-level UI inside `pages/`.
* Use TypeScript types for API responses and application data.
* Do not put music-processing logic directly inside UI components.
* Keep frontend changes small and testable.
* Avoid committing `.env`, `node_modules`, or `dist`.

## Current Status

**Phase 3 — Frontend Foundation: Complete**

Implemented:

* React + TypeScript + Vite
* React Router
* Application layout
* Home page
* Backend health connection
* Vite API proxy
* Environment configuration
* Production build
* ESLint validation

Future frontend work will integrate MusicXML, transposition, recognition, rendering, and export capabilities as the corresponding backend services are developed.
