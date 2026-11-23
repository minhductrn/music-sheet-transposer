# Music Sheet Transposer 1.0.7 — Operations

Run from Ubuntu WSL:

```bash
python3 -B /home/dtran/music-sheet-transposer-releases/music-sheet-transposer-1.0.7/start.py --check
python3 -B /home/dtran/music-sheet-transposer-releases/music-sheet-transposer-1.0.7/start.py --port 5250
```

Open http://localhost:5250. If occupied, use a different free port; the launcher never stops an existing application. Save MusicXML before closing any current session. Unsaved review state is temporary and is not transferred between running versions. Keep the terminal open. The header must show 1.0.7.

From Windows, run the package's Start-Production.ps1 (Start-Pilot.ps1 is retained for compatibility) with the same arguments. The release requires its recorded Ubuntu/Python ABI, existing Audiveris/Java and vie/eng models. It installs nothing. Node and the source checkout are not runtime prerequisites. Keep the sealed 1.0.6 package unchanged for rollback.
