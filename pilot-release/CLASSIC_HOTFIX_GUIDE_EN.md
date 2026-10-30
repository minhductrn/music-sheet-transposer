# Classic Task 06.1 — Home and Add Chord hotfix

This independent package preserves the accepted Classic backend and vertical editor layout. Home displays the title and import area without editing controls. Loaded Stage 1 and Stage 2 show Add Chord without the decorative G. No UX Next layout or accidental-engine change is included.

Save all open scores as MusicXML before stopping the old server. Stop the old terminal with Ctrl+C, then run:

`python3 -B /home/dtran/music-sheet-transposer-releases/music-sheet-transposer-classic-task06.1/start.py --port 5181`

Open http://localhost:5181 and reload once to load the new frontend. The previous Classic package is retained unchanged for rollback:

`python3 -B /home/dtran/music-sheet-transposer-releases/music-sheet-transposer-classic-task06/start.py --port 5181`

Only one server may use port 5181. A separate test server uses port 5182. Save files explicitly; unsaved sessions are not transferred between servers. Existing Python/Audiveris/OCR prerequisites and musical limitations remain unchanged. No cloud deployment is included. Functional acceptance of this hotfix remains with the Product Owner.
