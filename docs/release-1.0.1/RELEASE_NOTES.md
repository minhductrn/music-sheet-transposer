# Music Sheet Transposer 1.0.1

## Accepted maintenance scope - 2026-11-01

The Product Owner accepted PDF lyric centering at 85% of the original lyric font size and authorized updating Release 1.0. This is a maintenance update based on the sealed 1.0.0 package, not a continuation of canceled PDF reflow experiments.

Only PDF lyric placement/font size changes: center each lyric on its associated notehead and use 85% of its original font size. Note/rest geometry, musical data, system spacing, page-layout options, other font sizes and existing editing/transposition behavior are retained. Some dense lyric collisions and source text errors can remain; this is not a general engraving correction.

PROJECT_SPEC.md now reflects accepted Release 1.0 scope. Direct camera capture and Web Share API are excluded from continuing scope, rather than pending backlog.

## Start and rollback

```bash
python3 -B /home/dtran/music-sheet-transposer-releases/music-sheet-transposer-1.0.1/start.py --check
python3 -B /home/dtran/music-sheet-transposer-releases/music-sheet-transposer-1.0.1/start.py --port 5250
```

Save MusicXML before stopping the old instance. If port 5250 is occupied, use a free port such as 5251; this update does not stop existing sessions. Version 1.0.1 is shown in the header. The unchanged 1.0.0 package remains available for rollback. Original prerequisites, storage limits and user guide remain applicable; see ../release-1.0/OPERATIONS.md and USER_GUIDE.md.

No GitHub publication is implied by local packaging. Existing v1.0.0 artifacts and acceptance records remain historical and unchanged.
