# Task 03 — Independent local pilot packaging

Application baseline: bcac2d889da59406cefb0824a589ce20564b699a (accepted Task 01/02).

## User handoff

Use USER_GUIDE_VI.md. Final verified artifact is `frontend-v2/evidence/task03/music-sheet-transposer-pilot-task03-v0.1-r1.tar.gz`; the adjacent extracted directory can run directly. Evidence and runtime artifacts remain local and ignored by Git. Source implementation is confined to this folder; application source is unchanged.

## Build

On the current Ubuntu WSL host, with Node 24 on PATH and the existing installed backend/frontend dependencies:

    backend/.venv/bin/python -B pilot-release/build.py --output /absolute/path/to/a-new-pilot-folder

The builder reads the accepted Git object, builds its frontend in a temporary checkout, copies its backend app, and snapshots the installed runtime dependency closure including distribution metadata/licenses. It never stages, commits, pushes, or edits existing source. Existing output is refused. A failed build may leave its new partial output; choose a new output name. The generated lock and manifest describe actual versions and host ABI; identical builds on different environments are not claimed.

The bundle runs with system Python on the matching Ubuntu/Python ABI, serves built assets and API on localhost:5180, and requires no Node, original repository, Internet, virtualenv activation, or development server at runtime. It is not a native Windows installer or a production deployment.

## Verification

`verify_restart.mjs` accepts repository, archive, and evidence directory arguments; it extracts the archive into a separate temporary directory and uses existing Playwright Firefox only as a test tool. It saves actual Concert/instrument files, closes browsers and the packaged backend, starts both fresh, and checks exact MusicXML, semantic projection, and PDF re-export.

`playwright.task03.config.cjs` runs the existing 49 browser cases against the packaged server on port 5183. Set MST_TASK03_BUNDLE to an extracted bundle path; optional AI_SDF_TASK02_SAMPLE enables the approved private sample tests without bundling that file. Run from frontend-v2 using `npx playwright test --config ../pilot-release/playwright.task03.config.cjs`.

See TASK_03_REPORT.md for evidence, technical review and PO acceptance status.
