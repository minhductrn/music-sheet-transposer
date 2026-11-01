# Music Sheet Transposer 1.0

**Version 1.0.0 is the Product Owner-designated local production release.** It promotes accepted UX Next Advanced Editing checkpoint `e8a6b24`, including the full-width Concert Key Preview. The production UI, frontend package and release manifest use version `1.0.0`.

Import PDF/images through local OMR or open MusicXML directly, correct Working Score, save editable MusicXML, change Concert key, generate independent saxophone scores, and export MusicXML/PDF. Users decide musical content; OMR is a draft requiring correction.

## Start production

From Ubuntu WSL:

```bash
python3 -B /home/dtran/music-sheet-transposer-releases/music-sheet-transposer-1.0.0/start.py --check
python3 -B /home/dtran/music-sheet-transposer-releases/music-sheet-transposer-1.0.0/start.py --port 5250
```

Open **http://localhost:5250**. Keep the terminal open. Use Ctrl+C to stop after saving MusicXML. The package runs without a development server or source checkout. It requires the existing Ubuntu Linux/Python ABI, local Audiveris/Java and Vietnamese/English OCR models; it is not a universal Windows installer. The launcher installs nothing.

Download the application archive, documentation bundle and checksums from the [GitHub 1.0.0 release](https://github.com/minhductrn/music-sheet-transposer/releases/tag/v1.0.0).

## Documentation

| Document | Purpose |
| --- | --- |
| [User guide](docs/release-1.0/USER_GUIDE.md) | Import, edit, save/recover, transpose and export |
| [Product and UX design](docs/release-1.0/DESIGN.md) | Workflows, interactions, scope and acceptance |
| [Architecture](docs/release-1.0/ARCHITECTURE.md) | Components, contracts, data and runtime |
| [Operations](docs/release-1.0/OPERATIONS.md) | Startup, prerequisites, backup and rollback |
| [Release notes](docs/release-1.0/RELEASE_NOTES.md) | Accepted scope, verification and limits |
| [Acceptance](docs/release-1.0/ACCEPTANCE.json) | Product Owner production designation |
| [Verification](docs/release-1.0/VERIFICATION.json) | Final package validation |

## Capabilities

- Read-only Original Source and editable Working Score; Compare/Edit Only retain the same composition tools in Stage 1 and Stage 2.
- Direct note/rest editing, pitch, accidentals, duration/dots, voices/staff, size, grace notes, ties/slurs, supported tuplets/beams, lyrics/verses, text and chord symbols.
- Concert Key: editable source/mode, destination, half-tone stepper, Up/Down and full-width Preview before Apply.
- Independent Alto, Soprano and Tenor scores. Readable defaults: Alto Down −3 semitones, Soprano Up +2 and Tenor Down +2; standard Up registers remain available.
- Key Change Section: select complete measures, preview a transposed copy and append it with a signature/double barline; Undo/Redo and save remain available.
- Local MusicXML saving and A4 PDF preview/export, including fit-in-one-page and multi-page layouts.

## Data and limitations

Retain MusicXML on your device; it is the recovery format. Review sessions and unsaved instrument variants are temporary. There is no durable score database, account service, automatic cloud storage or cloud deployment in release 1.0. PDF is a rendered output, not an editable backup.

Advanced sections support one part/one staff and contiguous complete measures appended to the end. Boundary ties/slurs/tuplets must be complete. Multipart expansion, arbitrary middle paste and nested/cross-bar tuplet authoring are outside v1. OMR accuracy is not guaranteed, including legacy-font Vietnamese, keys and voice/verse associations. See release notes for limits.

## Source and releases

Active application source: `frontend-v2/` and `backend/`. Legacy `frontend/` is retired and excluded from synchronization. Official tag: `v1.0.0`; release branch: `release/1.0`. The default GitHub branch is promoted by normal fast-forward after final checks; no history is rewritten.

Build in the existing development environment:

```bash
python3 -B pilot-release/build_release_1_0.py --output /home/dtran/music-sheet-transposer-releases/music-sheet-transposer-1.0.0
```

The builder requires the retained accepted preview.5 package as its runtime baseline. It verifies that application source differs only in the version constant, refuses to overwrite output directories and installs no dependencies. Release archives and checksums live outside the repository.

Classic Task06.1, UX Next RC1 and Advanced previews remain intact for rollback. Version 1.0.0 is the production version going forward. Historical records under `pilot-release/` describe earlier checkpoints.
