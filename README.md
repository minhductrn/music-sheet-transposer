# Music Sheet Transposer 1.0.2

**Release 1.0.2 is the Product Owner-accepted local production maintenance version.** It retains the accepted UX Next and Advanced Editing v1 workflow and improves PDF presentation: lyrics centered under noteheads at 85% font size, with the accepted bounded rhythmic-spacing setting. Versions 1.0.0 and 1.0.1 remain unchanged rollback packages.

Import PDF/images through local OMR or open MusicXML directly, correct Working Score, save editable MusicXML, change Concert key, generate independent saxophone scores, and export MusicXML/PDF. Users decide musical content; OMR is a draft requiring correction.

## Download and start

Download the application, current English documentation and SHA-256 checksums from [Release 1.0.2](https://github.com/minhductrn/music-sheet-transposer/releases/tag/v1.0.2). Extract into a new directory; never over an older package.

From Ubuntu WSL:

```bash
python3 -B /home/dtran/music-sheet-transposer-releases/music-sheet-transposer-1.0.2/start.py --check
python3 -B /home/dtran/music-sheet-transposer-releases/music-sheet-transposer-1.0.2/start.py --port 5250
```

Open **http://localhost:5250**. Keep the terminal open. Save MusicXML before Ctrl+C. Use another free `--port` if occupied. Updating the app does not require a WSL-wide shutdown or Docker. The header identifies version 1.0.2.

The package needs the recorded Ubuntu/Python ABI and existing Audiveris, Java and Vietnamese/English OCR models. Node, source checkout and a development server are unnecessary at runtime. The launcher installs nothing. This is not a universal Windows installer or a cloud-hosted service.

## Current English documentation

| Document | Purpose |
| --- | --- |
| [Project specification](PROJECT_SPEC.md) | Consolidated accepted scope, exclusions and future limits |
| [User guide](docs/release-1.0.2/USER_GUIDE.md) | Import, edit, save/recover, transpose and export |
| [Product and UX design](docs/release-1.0.2/DESIGN.md) | Workflows, interactions and accepted PDF defaults |
| [Architecture](docs/release-1.0.2/ARCHITECTURE.md) | Components, contracts, data and runtime |
| [Operations](docs/release-1.0.2/OPERATIONS.md) | Prerequisites, startup, backup, updates and rollback |
| [Release notes](docs/release-1.0.2/RELEASE_NOTES.md) | Maintenance scope and known limitations |
| [Acceptance](docs/release-1.0.2/ACCEPTANCE.json) | Product Owner decision |
| [Verification](docs/release-1.0.2/VERIFICATION.json) | Actual checks and testing limits |

## Capabilities

- Read-only Original Source and editable Working Score; Compare/Edit Only retain the same composition tools in Stage 1 and Stage 2.
- Direct note/rest editing, pitch, accidentals, durations/dots, voices/staff, size, grace notes, ties/slurs, supported tuplets/beams, lyrics/verses, text and user-authored chord symbols.
- Concert Key: editable source/mode, destination, half-tone stepper, Up/Down and full-width Preview before Apply.
- Independent Alto, Soprano and Tenor scores. Readable defaults: Alto Down -3 semitones, Soprano Up +2 and Tenor Down +2; standard Up registers remain available.
- Key Change Section: select complete measures, preview a transposed copy and append it with destination signature/double barline; Undo/Redo and MusicXML saving remain available.
- Local MusicXML saving and A4 PDF preview/export, including one-page fit and multiple pages. PDF uses centered 85% lyrics and the accepted moderated rhythmic spacing; musical content and workspace rendering are unchanged.

## Data, exclusions and limits

Retain Concert and desired instrument MusicXML on your device; it is the recovery format. Reviews, Undo history and unsaved instrument variants are temporary. There is no durable score database, account service, automatic cloud storage or current cloud deployment. PDF is not an editable backup. Unchanged imported MusicXML with sufficient key context may proceed to instruments without redundant Save; changed Concert content must be retained first.

Advanced sections support one part/one staff and contiguous complete measures appended to the end. Boundary ties/slurs/tuplets must be complete. Arbitrary middle paste, partial-measure copying, general multipart expansion and nested/cross-bar tuplet authoring remain outside v1. OMR accuracy is not guaranteed, including legacy-font Vietnamese, key and voice/verse associations. Dense lyric collisions and some engraving gaps can remain; the accepted PDF maintenance is not a general layout guarantee. Other canceled PDF reflow trials are excluded.

**Direct camera capture and Web Share API are excluded from continuing scope by Product Owner decision, not pending backlog.** Import existing image files and download MusicXML/PDF instead. Public hosting requires a separate approved design.

## Verification and release provenance

The maintenance package passed build/lint, 63 frontend unit tests, three private-sample PDF export checks, package integrity/ABI and extraction checks. Decoded PDF preview pixels match the accepted spacing trial in all three samples. No musical-mutation requests or browser page errors occurred during those exports. Backend code is unchanged; full OMR/transposition suites were not repeated for this presentation-only update. Historical 1.0.0 test counts are not new 1.0.2 results.

Current source tag: `v1.0.2`; production branch: `release/1.0`. Original [v1.0.0](https://github.com/minhductrn/music-sheet-transposer/releases/tag/v1.0.0), packages and acceptance records remain unchanged. The standalone application archive was sealed before this documentation refresh; its manifest records exact source file hashes. The separate current documentation ZIP provides this refreshed English documentation without modifying the tested application archive.

Active source is `frontend-v2/` and `backend/`. Legacy `frontend/` is retired and excluded from synchronization. Personal scores, exported sample PDFs and local experiments are not release source.

## Existing-host build

The retained 1.0.1 package and installed development dependencies are required. No dependencies are installed automatically. Existing output paths are refused.

```bash
python3 -B pilot-release/build_release_1_0_2.py
# Test the exact new package and record actual results before sealing.
python3 -B pilot-release/build_release_1_0_2.py --seal
```

The builder restricts application differences from 1.0.1 to the PDF print renderer and version constant. For release history, see [1.0.0 records](docs/release-1.0/RELEASE_NOTES.md), [1.0.1 notes](docs/release-1.0.1/RELEASE_NOTES.md) and historical `pilot-release/` records. Product Owner acceptance remains distinct from passing tests.
