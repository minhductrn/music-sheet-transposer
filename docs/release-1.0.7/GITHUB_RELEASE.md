# Music Sheet Transposer 1.0.7 — Release notes

Product Owner accepted on 2026-11-22 for official local production use.

- Add notes by dragging from the common Notes palette, or explicitly before/after a selected note.
- Move notes in time with a visible alignment guide; retain the chosen voice and independent rhythms. Same-voice simultaneous notes can form chords.
- Draft correction is not rejected solely for occupancy, meter mismatches, negative imported cursor positions or inconsistent imported notation. Validate is optional; Save/Save As retain the current document without musical verification, key declaration or comparison-attestation gates.
- Improve selected-note beaming and independent voice engraving without rewriting saved musical content.
- Top-align lyric rows with the accepted lower first-row clearance below notation. Preserve words, original verse identities and note associations; extra verses remain available for explicit user deletion.
- Preserve original source, unrelated notes and Undo/Redo. Keep production 1.0.6 unchanged for rollback.

OMR accuracy is not guaranteed. Unresolvable timing/unsupported command shapes and actual file/network failures still report errors. This release is not universal malformed-MusicXML authoring, unrestricted multipart/nested-tuplet composition, or a cloud deployment. Existing runtime prerequisites and exclusions remain.


## Start

Extract the archive into a new directory. From Ubuntu WSL, run `python3 -B /home/dtran/music-sheet-transposer-releases/music-sheet-transposer-1.0.7/start.py --check`, then use `--port 5250` (or another free port). Windows users can run `Start-Production.ps1` from the extracted package. Existing Ubuntu/Python ABI, Audiveris/Java and vie/eng models are required; the launcher installs nothing. Save MusicXML before closing an older session.

The exact package passed 23 browser regressions and launcher integrity/ABI checks. The archive SHA-256 is supplied as a separate asset. Older releases are preserved.
