# UX Next 1.0.0-rc1 — local candidate guide

This independent candidate consolidates the UX layout and accepted Home/accidental/tie corrections. The Product Owner accepted RC1 on October 31, 2026; see UX_NEXT_RC1_ACCEPTANCE.json. The immutable package contains its build-time guide; this repository guide records the later approval. Classic Task 06.1 remains the local production version.

## Start and stop

From Ubuntu WSL:

`python3 -B /home/dtran/music-sheet-transposer-releases/music-sheet-transposer-ux-next-1.0.0-rc1/start.py --check`

`python3 -B /home/dtran/music-sheet-transposer-releases/music-sheet-transposer-ux-next-1.0.0-rc1/start.py --port 5234`

Open http://localhost:5234/. Keep the terminal open. Existing Ubuntu/Python ABI, Audiveris and OCR model prerequisites are required; the launcher installs nothing. Do not stop another server holding unsaved work.

## Workflow

Choose MusicXML or PDF/image on Home. MusicXML opens directly; PDF/image recognition creates a draft requiring comparison and manual correction. Original Source is read-only. Compare and Edit Only provide the same Working Score tools; Edit Only hides only the source.

Select notes to correct pitch, accidentals, duration, dots, size, voices or lyrics. Add Chord is user-directed. An explicit accidental command carries within its notation scope, and resolved tie chains retain matching pitches. Ambiguous or mismatched ties are reported rather than guessed. Undo/Redo restores complete commands.

Confirm an unknown original key when saving. A recommendation is optional and the user decides. Save Concert changes to MusicXML before generating instruments; an unchanged imported MusicXML with an explicit initial key may proceed directly. Choose Alto, Soprano or Tenor and a direction. Edits affect the active instrument score independently. Save instrument outputs separately.

Use Export PDF for preview, layout choice and download. Fit in one A4 page may reduce readability for long scores; multiple pages remain available.

## Save and recovery

Save and Save As download MusicXML to your device. Retain the downloaded file, then reopen that file after restarting. Unsaved review/browser sessions are temporary and cannot be promised recoverable. Use distinct filenames for Concert and instrument versions. PDF is a rendered output, not the editable recovery format. Home offers save, continue editing or explicit discard.

## Version separation and limits

Classic is not overwritten; use its existing Task 06.1 command for production. UX Next runs on a separate port and process. This candidate includes no advanced passage copy/paste or selective transposition, no cloud deployment and no generalized OMR accuracy guarantee. Existing multipart and nested/cross-measure tuplet limitations remain.
