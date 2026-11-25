# Release 1.0.8

Product Owner confirmed the Export PDF fix and requested production packaging and GitHub publication on 2026-11-25.

- Share the organized note inspector across Concert, Alto, Soprano and Tenor. Typed voice changes, Ctrl/Command-click selection, Voice 2 Small defaults, insertion inheritance, Normal/Small/grace/expression tools remain available.
- Keep musical draft edits and Save non-blocking. Validate is optional. Beam selected notes in musical time order, including imported append/backup order and temporary overlaps.
- Restore correct engraving columns for independently timed voices. Keep canonical MusicXML, pitch, duration, voice, lyric associations and playback unchanged.
- Keep lyric rows aligned across voices and prevent adjacent corrected lyrics from colliding. Add explicit syllable connection and Stem Auto/Up/Down controls.
- Preserve grace-note timing and authored grace slurs, chord entry at simultaneous notes, and notehead selection at reduced zoom.
- Remove transparent rest glyphs and their modifiers from PDF output. Apply the fix to all score stages, one-page/multipage layout, Auto and Standard margins.
- Support explicit recovery of checkpointed review/instrument workspaces. The optional disk review store is a local preview facility; this release does not add a durable score database or cloud hosting. Save local MusicXML backups.

The runtime, OMR dependencies and supported Linux/Python ABI are inherited from 1.0.7. Older sealed packages remain unchanged.
