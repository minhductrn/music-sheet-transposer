# Music Sheet Transposer 1.0.2

## Accepted maintenance scope - 2026-11-01

The Product Owner selected the rhythmic spacing comparison as the best current result and approved using it until a future update. This update retains PDF lyrics centered at 85% of their original font size and sets OSMD SoftmaxFactorVexFlow to 3 rather than 15 in the PDF-only print renderer. It moderates duration-driven horizontal spacing differences between notes and rests. This is not a promise of general professional engraving or collision-free lyrics.

No source notes, rests, pitches, durations, key signatures or musical relationships are edited. Workspace engraving is unchanged. Existing input text errors and dense lyric collisions can remain. Other PDF reflow experiments remain canceled; this release includes only the specifically accepted print spacing setting.

## Start and rollback

```bash
python3 -B /home/dtran/music-sheet-transposer-releases/music-sheet-transposer-1.0.2/start.py --check
python3 -B /home/dtran/music-sheet-transposer-releases/music-sheet-transposer-1.0.2/start.py --port 5250
```

Save MusicXML before stopping the old instance. If port 5250 is occupied, use another free port. This update does not stop existing sessions. Version 1.0.2 appears in the header. Sealed 1.0.0 and 1.0.1 packages remain unchanged for rollback. See USER_GUIDE.md and OPERATIONS.md for current instructions; original prerequisites remain applicable.

Source checkpoint and archive are published through the v1.0.2 GitHub release. The current documentation ZIP is distributed separately so the already-tested sealed application archive remains unchanged. See ACCEPTANCE.json and VERIFICATION.json for scope and actual checks.
