# UX Next preview.13 — Local WSL candidate

This independent UI candidate is pending Product Owner acceptance. Classic remains immutable and can run independently.

## Launch

```sh
python3 -B /home/dtran/music-sheet-transposer-releases/music-sheet-transposer-ux-next-preview13/start.py --check
python3 -B /home/dtran/music-sheet-transposer-releases/music-sheet-transposer-ux-next-preview13/start.py --port 5233
```

Open http://localhost:5233. Keep the terminal open. If a port is occupied, choose an unused port; do not stop a user's unsaved session. Existing Ubuntu/Python ABI, Audiveris and OCR-language prerequisites are unchanged. No dependencies are installed by the launcher.

Classic launch: `python3 -B /home/dtran/music-sheet-transposer-releases/music-sheet-transposer-classic-task06/start.py --port 5181`. Open http://localhost:5181.

## Layout

The horizontal Score tools bar replaces the vertical rail. All existing tools remain: Select, area selection, Notes/Rest durations, all five accidentals, Dots including missing-dot correction and double dot, Tie, Slur, all Groups/beam/tuplet options, Lyrics, Text, Add Chord, Add measure, More and Delete. Editing the selected note retains Normal/Small, voice/staff, pitch/octave, grace, expression, verse and lyric commands.

Concert Key keeps source key, mode, confirmation, new key, Up/Down, Keep Original and Apply. Correct Key Signature opens a compact visual selector for the existing explicit measure-key correction; it does not transpose notes. Save retains source-key choice and tentative opening-chord suggestion when the initial declaration is missing. This UI does not automatically repair an incorrectly recognized signature.

Compare shows Source and Working Score; Edit Only keeps the same tools and hides Source. Stage 2 retains independent Alto/Soprano/Tenor documents and Up/Down. Register and session details are expandable. Header actions, Save As, Validate, Undo/Redo, original key prompts and PDF preview remain available. PDF is the accepted Task 06 export implementation.

## Data and boundaries

Classic and UX Next run separate backend processes with separate in-memory review stores; there is no shared mutable review-session database. Save desired MusicXML files explicitly. Use separately named files for preview tests: either app can overwrite a local file only when you explicitly save to that path. Nothing migrates automatically. Close/refresh/restart does not promise recovery of unsaved work.

No cloud deployment, new engine or dependency is included. Explicit accidental editing now carries its notation effect within a measure and across resolved tie chains; see the scoped acceptance record. OMR accuracy and existing multipart/notation limitations are unchanged. Read the accepted Classic guide for the existing musical workflows. Technical test PASS is not Product Owner acceptance.

## Home layout revision — 2026-10-30

Before a score is opened, Home shows only the application title and import area. Score actions, editing tools, Stage 1 status and the simulated-workspace subtitle are hidden. Import profile, file selection and Demo remain available. Relevant import error feedback remains visible. All editing controls return after opening a real score or Demo; existing save/discard prompts are unchanged.

## Accepted accidental controls

Home and accidental/tie controls have scoped Product Owner acceptance. The overall UX redesign remains a candidate. Select a note, then choose an accidental or Remove accidental. The notation command affects subsequent matching notes in the same measure and preserves resolved tie chains. Undo/Redo restores the complete command. Ambiguous or mismatched ties are reported; the editor does not infer new connections.
