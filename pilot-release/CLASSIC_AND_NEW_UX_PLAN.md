# Classic and New UX Version Separation

Date: 2026-10-29. Product Owner requested preservation of the accepted UI, an independent UX candidate, and deployment of the accepted UI for user feedback.

## Preserved Classic baseline

Classic is the accepted Task 06 package, including the accepted PDF improvements. It is not the older Task 05 package. Task 05 remains independently preserved.

Installation: `/home/dtran/music-sheet-transposer-releases/music-sheet-transposer-classic-task06`.
Archive: `/home/dtran/music-sheet-transposer-releases/music-sheet-transposer-classic-task06.tar.gz`.
SHA-256: 6ca19a222c1d899f5ec9a27bcdb5b059041fbded86a9d1173669fc33b965ce8a.

From Ubuntu WSL:

```sh
python3 -B /home/dtran/music-sheet-transposer-releases/music-sheet-transposer-classic-task06/start.py --check
python3 -B /home/dtran/music-sheet-transposer-releases/music-sheet-transposer-classic-task06/start.py --port 5181
```

Open http://localhost:5181. Keep the terminal open. If the port is occupied, do not stop another user's session; select an unused port explicitly. No new server was started as part of freezing the package. Existing sessions were not stopped.

The package retains its original internal candidate version and manifest for byte integrity. Classic is an operational alias, not an invented release tag. The separate Task 06 acceptance record identifies the exact accepted bytes. Source checkpoint is 47286f983c953bfa06ede32cafd602fa1bb06e89 plus the five PDF files recorded in the package manifest. Task 06 is not yet recorded in a new Git commit or GitHub release.

## New UX candidate

The new UX must start from the accepted Classic application hashes in an independent development checkout/build directory. Never build Classic from the dirty current checkout. Never replace Classic web assets, backend, runtime, manifest or archive.

Proposed development version: `ux-next-preview.1`, not a released or accepted version. Reserve port 5230 for its isolated localhost service, with its own backend process and sessions. The independently implemented and technically verified candidate is ux-next-preview.8 at /home/dtran/music-sheet-transposer-releases/music-sheet-transposer-ux-next-preview8. Launch: `python3 -B /home/dtran/music-sheet-transposer-releases/music-sheet-transposer-ux-next-preview8/start.py --port 5230`. It remains pending Product Owner acceptance. The independent source and English report are under /home/dtran/music-sheet-transposer-ux-next.

Preserve all approved tools and behavior in Concert, instrument, Compare and Edit Only. Include all rest durations, accidentals, dot actions, source-key save confirmation/suggestion and Concert Key Up/Down. The visual redesign only rearranges existing commands. Any genuinely new command requires separate scope review. Correct Key Signature must expose the existing explicit correction without silently transposing notes.

No shared mutable work/session state between Classic and UX Next. Use separately named MusicXML output files/directories during testing; opening the same saved master is read-only until the user explicitly saves. No automatic migration or overwrite. Port separation alone is not data isolation: confirm backend storage behavior before starting both candidates. Do not run Git branch, add, commit, push, reset, clean or stash without explicit authorization. A future release requires functional parity evidence and Product Owner acceptance.

## Deployment direction confirmed by the Product Owner

The Product Owner confirmed local personal/WSL operation first. After acceptance of the final version, deliver both a personal WSL package and a Cloudflare-based public-access edition. The current launcher remains localhost-only; online deployment is future work, not completed or authorized for immediate publication.

For local use: use the preserved package, confirmed Ubuntu/Python ABI and existing Audiveris/OCR prerequisites; save MusicXML documents explicitly. Unsaved browser/review sessions are not durable user storage.

For future online use: offer free access to the engine; users explicitly download MusicXML/PDF to their own devices. Do not create hosted score libraries, user-file backups, persistent score storage or score-content analytics. Backend processing may require temporary per-session data; design explicit deletion on completion, cancellation and expiry, including interrupted sessions, before claiming non-retention. Do not log uploaded file contents or extracted score/lyric content. Session isolation, HTTPS, processing limits and predictable operating costs remain deployment requirements. Free access for end users is not a claim of zero hosting cost.

The current backend and Java/Audiveris engine need a compatible execution environment; uploading only the static frontend to Cloudflare does not deploy that engine. Select the exact Cloudflare/backend arrangement in a later bounded deployment design. No new infrastructure, container technology or cloud account is selected or installed now.

Local and cloud editions should use the same accepted application version with environment-specific launch/deployment packaging. Save remains a user-directed local file operation. Reuse accepted musical behavior and preserve Classic rollback. Do not expose the current local service publicly or claim production readiness before verifying these deployment requirements.

No production deployment, public access, dependency installation, source implementation, Git commit or push was performed in this preservation step. No accepted package was modified. Documentation is English; user discussion may be Vietnamese.
