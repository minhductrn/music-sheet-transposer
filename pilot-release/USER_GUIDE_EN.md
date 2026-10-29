# Music Sheet Transposer — Standalone User Guide

Task 05 accepted standalone guide, 2026-10-29. Application baseline: accepted source commit 945821c. The Product Owner accepted artifact 1.0.0-rc2; see TASK_05_ACCEPTANCE.json for the exact archive hash. The immutable downloaded package retains its build-time status text. Consult the Task 05 release report for the measured verification results. Replace example paths with the actual installed package directory.

## Start and stop

Extract the supplied verified archive into a new directory in Ubuntu WSL. Keep its contents together. Use the actual extracted directory in place of the example:

```bash
python3 -B /absolute/path/to/extracted-package/start.py --check
python3 -B /absolute/path/to/extracted-package/start.py --port 5180
```

Open http://localhost:5180. Keep the terminal open; Ctrl+C stops the server. Choose a different unused port when needed. Do not stop another application that contains unsaved edits. Save all desired MusicXML documents before shutdown, refresh, WSL restart or changing packages.

The package needs the Ubuntu Linux/Python ABI recorded in its manifest. It is not a native Windows installer. Built assets and bundled Python libraries remove the need for Node or Codex during ordinary use. PDF recognition additionally needs installed Java, Audiveris and OCR language data. The current OMR-enabled launcher validates Audiveris and both OCR language models before starting, even for a MusicXML-only session. The package does not install or download these automatically. Environment overrides are AUDIVERIS_EXECUTABLE and AUDIVERIS_TESSDATA_PATH. Follow the final release prerequisites if OMR startup reports a missing tool.

## Import and correct

Open MusicXML directly, or import PDF/PNG/JPEG and choose the applicable recognition profile. OMR output is a draft and may contain incorrect or missing notes, key signatures, voices, lyrics or marks. Compare it with the original; correct the draft yourself. The application must not invent missing musical content.

Original Source is read-only. Edit Working Score directly. Compare shows both; Edit Only hides the source and keeps the same editor. Fit fits the pane width; use vertical scroll. Source and Working Score have independent zoom and scroll. No automatic PDF-note alignment is claimed.

Click a notehead for pitch, octave, accidental, duration, voice/staff and supported notation tools. Drag a notehead to change pitch. Small affects only that selected notehead, even within a chord; it does not change pitch, duration or voice. Normal restores its normal size. Grace and cue timing are different from display size.

Choose Notes or Rest and an explicit staff position to insert. Existing accidentals are retained unless changed; new notes use the current key signature. Dot/Double dot change supported written durations. Missing dot +half on an undotted quarter restores the explicitly intended dotted-quarter/eighth placement. Add measure retains its single-part/single-staff limitation.

Select area or Shift-drag encloses noteheads for group operations. Delete removes the selected objects. Undo/Redo restores supported edits. Select the intended voice/note when notes overlap.

## Tuplets

Groups exposes 3:2, 2:3, 4:3, 5:4, 6:4, 7:4, 8:6 and 9:8. Ratio a:b means a written units occupy the duration of b corresponding normal units.

- Divide duration splits the selected ordinary note/rest/chord span while keeping its total duration.
- Apply to selection changes the selected written durations by b/a; its total span may change.
- Select a complete existing group before changing/removing its ratio. Removing the ratio restores written durations and can change its span.
- Every resulting pitch remains separately editable. Bracket, placement and number display are selectable.
- Fixed mixed 3:2 and Beam buttons are separate tools. Nested/cross-measure tuplets and unsupported written-unit combinations remain unavailable. Overlaps or incomplete membership are reported, not silently repaired.

## Lyrics, text and chords

Click a lyric or select a note and choose Edit lyrics/Add Verse. Choose Verse 1, 2, 3 or another intended verse; voice is the musical part, not the lyric verse. Unicode content is retained. Enter saves, Esc cancels and Tab moves to the next supported note. Check note associations against the source. Recovery mapping for text misrecognized as lyrics requires explicit syllable/note/verse assignments.

Choose Add Chord, click a note/staff position, type a chord (for example Bm or E7), then Enter. Click an existing chord to edit/delete it. The user decides harmony. Select supported text or marks and use their direct edit/delete controls. Select a measure-attached author text and choose Move to composer header to make it page-level composer metadata; this is explicit and can be undone. Its scale follows the page, not a measure anchor. Notifications can be closed with the cross button.

## Save and reopen

Save/Save As writes MusicXML, the editable document. Prefer Save As to protect the original. Retain the actual downloaded file, check its name/location (including browser-added suffixes), then confirm retention. A browser confirmation is not proof that a file was retained.

For OMR drafts, compare every relevant source page, including voices/verses, and confirm the comparison before saving. Further edits invalidate that confirmation. A missing initial key declaration prompts an explicit original-key choice; an optional chord-based suggestion is not definitive analysis. Declaring the original key does not transpose notes.

Reopen the saved MusicXML to continue. Unsaved sessions, variants and Undo/Redo history are temporary and are not restored after shutdown. Recovery means reopening the last MusicXML file actually saved; later unsaved edits cannot be promised recoverable. Keep separate backups of important versions. If a session expires, preserve any saved files and reopen one rather than repeatedly editing a stale session.

Home offers saving, continued editing or explicitly discarding unsaved work. Discard does not delete saved files. Save each Concert and instrument document that you want to retain.

## Concert and instrument scores

Concert Key changes supported notes, chord symbols and local key changes together after explicit source-key confirmation. Same-key Down lowers an octave; same-key Up keeps pitch. Save an edited Concert before generating instrument outputs. An unchanged imported MusicXML with explicit initial key may proceed directly.

Instrument scores are independent of the Concert and one another. Readable defaults: Alto Down is concert minus 3 semitones; Soprano Up and Tenor Down are concert plus 2. Standard written-register alternatives remain available. Tenor Down reads like Soprano but sounds an octave below Concert when played on a B-flat Tenor. Changing direction changes the chosen instrument output; retain each variant you need.

Stage 2 global Save/Save As, Validate, Undo/Redo and saved XML export target the active instrument editor. Supported composition tools also remain available in its Compare/Edit Only views. Reopening an instrument MusicXML treats it as an independent written document; do not transpose it again accidentally.

## PDF output

Export PDF opens a layout choice. Fit in 1 A4 page is the default and uniformly scales the whole score; long scores may become small. Multiple A4 pages keeps system-aware pagination. Paper margins remain 12 mm; content-aware four-margin adjustment is not implemented. Cancel produces no file. PDF is print output, not the editable master, and exporting does not correct OCR errors.

## Known boundaries

Local pilot, not a production/cloud deployment. No full MuseScore/Symphony Pro parity is claimed. Stage 2 generation remains single-part; measure append remains single-part/single-staff. Nested/cross-measure tuplets, arbitrary passage copy/paste/transposition and automatic margins belong to later work. Perfect OMR accuracy, automatic OCR-font recovery and unsaved-session recovery are not promised. No AI agents, LLM API calls or Docker are required by this workflow.