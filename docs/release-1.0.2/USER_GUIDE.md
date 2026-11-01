# Music Sheet Transposer 1.0.2 — User Guide

## 1. Start and import

In Ubuntu WSL:

```bash
python3 -B /home/dtran/music-sheet-transposer-releases/music-sheet-transposer-1.0.2/start.py --port 5250
```

Open http://localhost:5250 and keep the terminal running. Home shows import controls. Choose File opens MusicXML or a supported PDF/image. Select a recognition profile before PDF/image import; Vocal song is intended for Vietnamese lyrics. MusicXML opens directly without OMR. Try Demo Score is simulated, not a real imported score.

PDF recognition produces a draft. Compare key/time signatures, notes, durations, voices, verses, lyrics and symbols with the original. If recognition fails, explicit manual reconstruction can create an empty working score; no recognized content is invented.

## 2. Compare and edit

Original Source is read-only. Working Score is editable. Compare shows both panes; Edit Only shows Working Score with the same tools. Fit fits pane width; scroll vertically for more systems. Minus/plus changes zoom independently.

Use Select to choose a notehead, including a chosen chord member. Overlapping targets can show a voice choice. Drag vertically to change pitch or use context controls for duration, pitch/octave, voice/staff, Normal/Small, grace and supported expressions. Small affects only the selected note. Undo/Redo handles complete commands.

Choose Notes or Rest, select duration, then click an insertion position. Use explicit position tools for a missing event without a direct target. Add measure appends a measure. Select area and drag a rectangle to select several notes, then Delete or Groups. Editing is not restricted to what OMR recognized.

A single augmentation dot adds half the base duration; a double dot adds three quarters. These are not staccato marks. Correct missing quarter-note dot handles the approved missing-half-beat case. Validate shows rhythm warnings without automatically composing missing notes.

## 3. Accidentals, ties, slurs and groups

Choose accidentals explicitly. They carry within the applicable measure scope. Remove accidental returns to preceding active accidental/key context and can change the selected pitch accordingly. Resolved tied chains adjust consistently; incomplete/mismatched ties require correction.

Choose a source note, select Tie or Slur, then select a valid later destination. Ties require matching pitch; slurs can join different pitches. Select a curve to set Up/Down, move direction or remove it. Undo restores it.

Groups offers supported ratios, duration division, application to compatible written selections, appearance/removal and separate beams. Choose a ratio and read its duration relationship. Generated notes remain individually editable. Nested/cross-bar tuplets are not authored in v1; invalid selections are reported rather than guessed.

## 4. Lyrics, text and chords

Choose Lyrics and click a note or syllable. Type, Enter saves, Escape cancels and Tab moves to the next note. Use the Verse tabs or Add Verse for another verse; verse is distinct from musical voice. Correct missing syllables and note associations directly. Unicode Vietnamese is supported; old-font OCR may require replacement.

Choose Text and click a text object to edit. Select an unwanted OCR object such as a false dynamic or pedal mark and use Delete object. The source stays unchanged. Shared playback information may be retained while deleting a visible mark. When targets overlap, use the supported object selection tools; browser text highlighting alone is not necessarily score selection.

Choose Add Chord, click the intended position and type the chord. Click an existing chord to edit/delete. Harmony is your choice. A missing chord can be added at an empty rhythmic position; an existing chord anchor is not required.

## 5. Save and confirm source key

Save/Save As retains MusicXML on your device. Complete the browser file action and retain the file. Use distinct Concert/instrument names, for example `song-concert-Am.musicxml` and `song-alto.musicxml`.

If the original key is unavailable, saving lets you choose Major/Minor and source key or accept an optional recommendation. You decide. Declaring source context is different from transposing notes. If OMR gave a wrong signature, Correct Key Signature changes the selected measure's signature without transposing notes; inspect note accidentals separately. Confirmed key context persists on MusicXML reimport.

PDF drafts need comparison confirmation for the current revision before canonical saving. If edits invalidate it, compare and confirm again. Your confirmation does not assert that OMR was correct.

## 6. Concert Key

Open Concert Key, check Source key/Mode and confirm. Use minus/plus in 0.5-tone steps, Destination or Up/Down. A minor down half a tone can be G-sharp minor or equivalent A-flat minor; choose a supported spelling for the whole piece. Same-key Down lowers one octave and keeps the key.

Preview is full-width beneath the buttons and read-only; scroll inside for more systems. Nothing changes until Apply concert key. Keep Original/Close cancels. Apply changes notes and supported chord symbols. Save changed Concert MusicXML before generating new instruments.

## 7. Instrument scores

Choose Instrument Scores, an instrument and direction. Unchanged imported Concert MusicXML with sufficient key context can proceed without redundant Save. Changed Concert input must be saved first.

Defaults: Alto Down writes Concert −3 semitones; Soprano Up and Tenor Down write Concert +2. Tenor remains a B-flat tenor saxophone part, sounding an octave lower than the same written Soprano notation. Standard Up registers remain available.

Left pane is read-only Concert input; right pane is the active instrument Working Score. Supported tools remain available, including Edit Only. Instrument/direction variants keep independent temporary edits. Save each desired output separately. Instrument edits never overwrite Concert input.

## 8. Key Change Section

1. Use MusicXML; correct and save PDF drafts as MusicXML first.
2. Choose Key Change Section. Click first/last measures or adjust From/Through; blue shading marks complete measures.
3. Choose Source key/Mode and interval/Destination. Each step is 0.5 tones.
4. Preview the copy. If range/key changes during loading, preview again.
5. Apply section appends the copy with destination key/double barline. Notes and chord symbols transpose together. Old measures remain unchanged.
6. Undo/Redo handles the append; save the resulting MusicXML.

V1 supports one part/one staff, including its voices. Extend selection to contain complete ties/slurs/tuplets. Repeat/ending copying and arbitrary middle paste are unsupported. This works in Concert/instrument Working Score and Compare/Edit Only.

## 9. Export

MusicXML is the editable recovery/interchange file. Save before Export saved MusicXML. Export PDF opens layout preview for the current working score. Choose fit-in-one-A4-page or multiple pages and margin options. Review pages, then Export. Cancel/Close creates no download. Long scores forced onto one page can become small; use multiple pages when readability matters.

PDF lyrics are centered under their notes at 85% of the original size. Print spacing moderates large duration-driven gaps between notes/rests. These are fixed accepted export defaults; workspace zoom and font sizes are unaffected. Some dense lyrics or incorrect source text may remain. Do not treat PDF presentation as a change to note duration or pitch.

Direct camera capture and browser Web Share are outside this release. Import an existing image file and download MusicXML/PDF to your device.

## 10. Home, stopping and recovery

Home allows a new import. With unsaved variants choose save, Continue editing or explicit discard. Discard loses unsaved changes; refresh is not Save.

Before closing browser, terminal or WSL, retain desired MusicXML files. Reopen them in a fresh session to recover saved content without OMR. Unsaved changes, selection, history and variant caches are temporary. Keep the original PDF separately for future comparison. PDF output is not an editable backup.

## 11. Updating from an earlier release

Save desired Concert/instrument MusicXML files, stop the old terminal with Ctrl+C, then run the 1.0.2 command above. If another app uses port 5250, choose a free port. Check the header says 1.0.2. Reimport retained MusicXML; unsaved history and review IDs do not transfer. Keep the original source and older packages. A WSL-wide shutdown is unnecessary for an application update.
