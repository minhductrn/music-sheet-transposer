# Default frontend switch — 2026-10-25

Status: **TECHNICALLY VERIFIED**. The Product Owner approved the proposal to make frontend-v2 the default run/build target, keep the legacy frontend for reference, verify and commit/push the change. This is configuration/documentation work; it does not introduce new score-editing behavior or imply new functional acceptance.

## Scope

- Root package.json/package-lock.json supply default development, build, typecheck, lint, unit and browser-test commands that delegate to frontend-v2. `npm start` is an alias for the v2 development UI, with the backend started separately as documented. Arguments are forwarded to v2.
- `npm run setup:frontend` explicitly installs the existing locked v2 dependencies; no install hook or dependency migration is added. The root package itself has no runtime dependencies.
- Root README now describes the accepted MusicXML workflow, v2 commands, output frontend-v2/dist, backend address variable AI_SDF_BACKEND_URL, and the already accepted standalone Task 03 pilot. It distinguishes historical backend OMR capability from the current v2 accepted scope.
- The previous README is retained verbatim after a historical notice in README_LEGACY.md. No legacy frontend, backend, v2 application source, frozen design, or pilot archive was modified. No CI/hosting deployment configuration exists in this repository to migrate; external hosting was not changed.

## Verification

All checks used the actual root commands:

- `npm run typecheck`: PASS.
- `npm run lint`: PASS.
- `npm test`: 44 tests PASS.
- `npm run build`: PASS; existing large-bundle warning remains. All 14 emitted web/font assets match the accepted Task 03 bundle SHA256 values.
- `npm run test:e2e -- --list`: PASS; resolves the existing 49 v2 browser cases. The complete browser suite was not rerun for these aliases; its prior 49-pass Task 03 evidence remains historical evidence.
- `npm run dev -- --port 5185`: started v2 from the repository root. Isolated backend on 8815; real synthetic MusicXML import rendered all 9 mapped heads with read-only source and real working score. PASS. Only owned test processes were stopped; the user's 5174/5180 sessions were not replaced.
- Root lock generation ran offline with scripts/audit disabled; no frontend install or dependency update was needed. setup:frontend was not rerun because existing installed dependencies were reused.
- 619 pre-existing dirty/untracked files remained byte-identical, and historical README content equals the prior committed README. The build and smoke evidence remain in ignored frontend-v2/evidence/default-frontend/.

## Technical Lead review

Reviewed the root command delegation, argument forwarding, lockfile, README links and startup/build destinations. The change preserves PC-03/04/05 musical data and stage boundaries by leaving application logic untouched; PC-07 is supported by the root checks and accepted build hash equality. PC-08 is respected: approval authorizes this bounded configuration switch; prior Task 01/02/03 acceptance remains unchanged. No OMR, agents, Docker, dependency upgrades, production deployment, or unrelated architectural changes were introduced.

## Use

From the repository root, start the backend as shown in README, then `npm run dev` (or `npm start`); open http://localhost:5174. `npm run build` emits frontend-v2/dist. Existing pilot startup at localhost:5180 remains unchanged. The legacy frontend remains available only by deliberately entering frontend/ and running its historical commands.
