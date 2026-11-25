# Music Sheet Transposer 1.0.8 — User Guide

Choose Text, click a blank header location, type and press Enter. Drag a header object to reposition it. With Select active, click an object then Delete object. Equal strings remain separate objects. Undo/Redo restores edits. Save MusicXML to retain text/positions. PDF includes the visible header. Concert key changes label the score; Alto/Soprano/Tenor outputs include instrument labels. Original Source stays read-only.

Existing limits remain: local deployment only; OMR is a draft, not guaranteed correct; dense engraving collisions, multipart expansion and nested/cross-bar tuplet authoring are not newly resolved. Camera capture, Web Share API and cloud deployment are excluded. No general OMR accuracy certification is claimed.

## Working Score playback

Working Score playback adds shared Piano and Simple tone settings, live tempo adjustments, note highlighting, optional follow scrolling, and playback from a selected measure. Select area plays only selected notes. Loop repeats the selection or the specified measures. Play from beginning plays the full score.

Concert Key Preview also supports playback without allocating an editing session. Instrument Scores use the shared sound and tempo settings. Playback follows written measure order and skips grace notes. Changing tempo may retrigger a sustaining note.


## Accepted 1.0.8 correction workflow

Choose Notes and drag a duration onto Working Score. Set the insertion voice explicitly; existing notes retain their voices. Drag horizontally to move a note in musical time and use the column guide to align independent voices. Select a note for Add note before/after. Select notes and choose Groups / Beam selection to beam them.

Draft music may contain temporary conflicts. Validate is optional; Save and Save As retain your current document even if diagnostics remain. The original source stays read-only. Lyrics use the accepted lower first-row clearance; extra imported verses stay separate for explicit editing/deletion. Save MusicXML before closing or switching application versions.


## 1.0.8 note inspector and export corrections

Ctrl/Command-click toggles individual note selections. Apply Voice once to the selected group; Voice 2 defaults to Small and can be changed back to Normal. Add note before/after inherits voice, staff and size from the selected note. Notation & expressions contains Staff, Normal/Small, grace and expression tools, plus Stem Auto/Up/Down. Lyrics includes Independent/Start/Middle/End syllable connection; Independent removes automatic hyphens without deleting text or notes.

Different voices can share one rhythmic column. Temporary musical conflicts remain editable and saveable. Groups beams the selected rhythmic positions, including draft overlaps; Validate reports diagnostics only when requested.

Export PDF removes invisible engraving spacers and their dots instead of printing them. Both Auto and Standard margins, one-page fit and multiple A4 pages use the same fix.
