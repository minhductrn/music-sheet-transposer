# Music Sheet Transposer 1.0.5

**The Music Sheet Transposer web application is complete and Product Owner accepted. Release 1.0.5 is the local production version.** Hosting is a separate lift-and-shift assessment.

Import PDF/images through local OMR or open MusicXML directly, correct Working Score, save editable MusicXML, change Concert key, generate independent saxophone scores, and export MusicXML/PDF. Users decide musical content; OMR is a draft requiring correction.

## Download and start

Release 1.0.5 is Product Owner accepted for official local use. Package and publication evidence are recorded under docs/release-1.0.5. Extract into a new directory and retain all older packages.

From Ubuntu WSL:

```bash
python3 -B /home/dtran/music-sheet-transposer-releases/music-sheet-transposer-1.0.5/start.py --check
python3 -B /home/dtran/music-sheet-transposer-releases/music-sheet-transposer-1.0.5/start.py --port 5250
```

Open **http://localhost:5250**. Keep the terminal open. Save MusicXML before Ctrl+C. Use another free `--port` if occupied. Updating the app does not require a WSL-wide shutdown or Docker. The header identifies version 1.0.5.

The package needs the recorded Ubuntu/Python ABI and existing Audiveris, Java and Vietnamese/English OCR models. Node, source checkout and a development server are unnecessary at runtime. The launcher installs nothing. This is not a universal Windows installer or a cloud-hosted service.

## Current English documentation

| Document | Purpose |
| --- | --- |
| [Project specification](PROJECT_SPEC.md) | Consolidated accepted scope, exclusions and future limits |
| [User guide](docs/release-1.0.5/USER_GUIDE.md) | Import, edit, save/recover, transpose and export |
| [Product and UX design](docs/release-1.0.5/DESIGN.md) | Workflows, interactions and accepted PDF defaults |
| [Architecture](docs/release-1.0.5/ARCHITECTURE.md) | Components, contracts, data and runtime |
| [Operations](docs/release-1.0.5/OPERATIONS.md) | Prerequisites, startup, backup, updates and rollback |
| [Release notes](docs/release-1.0.5/RELEASE_NOTES.md) | Maintenance scope and known limitations |
| [Acceptance](docs/release-1.0.5/ACCEPTANCE.json) | Product Owner decision |
| [Verification](docs/release-1.0.5/VERIFICATION.json) | Actual checks and testing limits |

## Release 1.0.5 changes

- Select duplicate score text by measure and remove unmatched octave shifts from the score object menu.

### Prior maintenance

- Edit, delete or move imported lyricist text to the header.
- Delete unwanted rests while preserving the timing of other notes. Insertion markers appear above the staff with transparent fill.
- Load tie candidates more efficiently on larger scores.

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

See [verification](docs/release-1.0.5/VERIFICATION.json) for checks actually run and [acceptance](docs/release-1.0.5/ACCEPTANCE.json) for the Product Owner decision. Older records remain historical evidence. Active source is frontend-v2 and backend. Personal scores and local exports are excluded from Git.

## Existing-host build

The retained 1.0.4 package and installed development dependencies are required. No dependencies are installed automatically. Existing output paths are refused.

```bash
python3 -B pilot-release/build_release_1_0_5.py
# Test the exact new package and record actual results before sealing.
python3 -B pilot-release/build_release_1_0_5.py --seal
```

The builder restricts application differences from 1.0.2 to the accepted Text object implementation allowlist; it refuses existing outputs and installs no dependencies. For release history, see [1.0.0 records](docs/release-1.0/RELEASE_NOTES.md), [1.0.1 notes](docs/release-1.0.1/RELEASE_NOTES.md) and historical `pilot-release/` records. Product Owner acceptance remains distinct from passing tests.

## Accepted 1.0.5 Text objects

Choose Text, click a blank header location, type and press Enter. Drag a header object to reposition it. With Select active, click an object then Delete object. Equal strings remain separate objects. Undo/Redo restores edits. Save MusicXML to retain text/positions. PDF includes the visible header. Concert key changes label the score; Alto/Soprano/Tenor outputs include instrument labels. Original Source stays read-only.
