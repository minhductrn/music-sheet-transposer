# Task 04 User Guide: PDF Recognition and Score Completion

The Product Owner accepted the documented Task 04 scope on October 27, 2026. The earlier accepted Tenor v0.3 archive remains unchanged. This guide is maintained in English; its historical `_VI` filename is retained for existing links and packaging compatibility.

## Start and stop

Extract the accepted bundle into a new directory. In Ubuntu WSL, run:

```bash
python3 -B /path/to/extracted-bundle/start.py --check
python3 -B /path/to/extracted-bundle/start.py --port 5180
```

Open http://localhost:5180. Replace the example path with the actual extracted directory. Use another port if occupied, keep the terminal open, and press Ctrl+C to stop. Save MusicXML before closing.

System Python must match the ABI in the bundle manifest. OMR additionally requires local Java, Audiveris and OCR language models. The verified host uses `/opt/audiveris/bin/Audiveris` and `~/.config/AudiverisLtd/audiveris/tessdata` with Vietnamese/English data. Override these locations with `AUDIVERIS_EXECUTABLE` and `AUDIVERIS_TESSDATA_PATH`. The bundle does not contain or automatically install/download these external tools or models. MusicXML editing does not require Audiveris.

## Import and compare

Choose a suitable recognition profile, such as Vocal song or Choir/SATB, and import PDF/PNG/JPEG. Recognition runs once per explicit attempt. Failures remain visible; demo music is never substituted for a failed result.

Original Source is read-only on the left. Working Score on the right is the editable draft. PDF.js displays the original locally with independent Fit, zoom and vertical scrolling. Navigation between the source and notation is manual; no automatic note-to-image alignment is claimed.

Compare and Edit Only use the same editing tools. Edit Only hides the original and expands Working Score without reloading the document or removing editing capabilities. The same supported tools are available for Concert and instrument scores.

## Edit notes, rhythm and measures

Click a notehead to open contextual tools or drag it to change pitch. Keep existing accidentals unless explicitly changed; new notes follow the working key signature. Notes and Rest provide whole through 64th durations. Small changes display size only; Grace before and Slashed grace before create supported grace notes.

Dots groups augmentation-dot tools. Dot and Double dot apply to a single note or its chord. For an explicitly identified missing dot on a quarter note, Missing dot +½ changes it to a dotted quarter and moves the following eighth-note group to the 1½-beat position in that measure. Pitch and accidentals remain unchanged. The ordinary Dot action retains existing event positions; choose the dedicated missing-dot action when that timing correction is intended.

Choose Notes or Rest, click a staff position, and select the relevant voice and duration to insert content. An eighth rest is half a beat when the quarter note is the beat unit. Explicit-position tools are available for specifying measure, beat, voice and staff when OMR placement is unclear. Incomplete measures are not silently filled with notes or rests.

Use Select area, or Shift-drag, to enclose noteheads in a rectangle. Selected notes are highlighted. Delete removes the group while preserving timing positions outside the selection; one Undo restores the operation. Groups offers the supported beams and tuplets, including mixed 3:2 and equal-duration ratios 3:2, 2:3, 5:4, 6:4, 7:4 and 9:8. Each pitch remains independently editable. Ambiguous or nested membership is not guessed.

Measure correction changes supported beginning-of-measure properties: meter, key signature without pitch transposition, clef for the chosen staff, staff count, pickup intent and right barline. Mid-measure context changes are preserved rather than edited by that control. Add measure appends a measure when the current single-part/single-staff structure is supported.

A key change later in the piece must not be applied backward to its beginning. Missing initial key information does not authorize automatic pitch or accidental changes.

## Lyrics, voices and text

Click a lyric to edit Unicode text, or select a note and use Edit lyrics/Add Verse to add missing lyrics. Select the intended verse for each line. Voice belongs to a note; verse identifies a lyric line. Move lyric transfers text only to an explicitly selected note and verse. Segmented lyrics remain separately editable; legacy-font encoding is not guessed.

The lyric input follows the edited location on the score, including navigation between notes. Working Score remains the primary editing surface; floating tools should not push the score below additional forms.

Click supported OCR text or marks to select them and use their contextual edit/delete action or Delete. This includes supported dynamics, pedal marks and other incorrectly recognized objects. Undo restores deletions. The system must not invent expressions absent from the source. Secondary OCR-object controls are available for ambiguous or difficult selections; they are recovery tools rather than the normal workflow.

Repair text recognized as lyrics supports explicit recovery from OCR misclassification: select the text, correct its Unicode content, choose a verse, prepare syllable mapping and assign each syllable to a chosen note. No destination is assigned automatically. Removing the original text is explicit, and the conversion is one Undo operation.

## Chord symbols, ties and slurs

Choose Add Chord, click the desired note or staff position, and type the chord symbol, for example Bm, G or E7. Press Enter to save or Esc to cancel. Click an existing chord to edit or delete it. If several canonical chords share a location, select the intended object. Harmony and placement are user decisions; no chord is inferred from melody.

Use the supported tie/slur tools to connect suitable notes and edit or delete the resulting relationship. Direction is an explicit user choice. Existing links must remain attached through supported zoom, Fit, save and transposition operations. Unsupported or ambiguous imported notation is not silently reconstructed.

## Validate

Validate displays recognition and rhythm warnings in the notification area. Warnings may identify measures when the engine supplies locations. They do not automatically repair or override the score. Check the source for omitted notes, pickup measures, incorrect meter and missing accidentals. A draft warning is not proof that the printed source itself is wrong.

## Save, reopen and declare the original key

Compare the corrected score with each original page, including voices and verses. Confirm the comparison checkbox before saving an OMR draft. Further edits or history changes invalidate that confirmation. Save/Save As writes MusicXML. If the browser downloads the file, retain it and confirm only after verifying its actual name and location.

If the initial key is missing, Save asks for the mode and tonic. An optional recommendation is based on the recognized opening chord and is not a definitive key analysis. Accept the suggestion only if appropriate, or choose the correct original key yourself. Declaring the key does not transpose note pitches. The saved MusicXML carries the declaration for reopening and instrument generation.

Reopen the retained MusicXML to continue. Review sessions and Undo/Redo history are temporary; they are not restored after shutdown. MusicXML is the editable record; PDF is print output.

## Concert key and register

Open Concert Key, confirm the current source key and mode, select the target key and Up/Down, then Apply. Notes, chord symbols and supported key changes transpose together. Save the result before using an edited Concert score for Instrument Scores.

For the same source and target key, Down lowers every supported pitched note by one octave while preserving key spelling and harmony. Up with the same key retains pitch. The panel explains this behavior before applying. Use Undo to reverse the operation. Close the panel with × or Esc without applying a change.

If the requested spelling makes a section exceed seven sharps/flats, choose a supported target or explicitly accept the offered enharmonic alternative. The application does not switch spelling automatically.

## Instrument scores

An unchanged imported MusicXML document with an explicit initial key can proceed directly to Instrument Scores without an unnecessary save. The interface identifies it as unchanged imported input. Edited Concert scores and corrected PDF/image drafts must be saved before instrument generation; OMR is not rerun.

Readable defaults relative to Concert are Alto E♭ Down −3 semitones, Soprano B♭ Up +2, and Tenor B♭ Down +2. Tenor uses Soprano-like written notation under the accepted register choice; when played on Tenor it sounds one octave below Concert. Alto Down likewise changes the sounding register relative to standard written output. These choices do not modify Concert.

The application remembers the selected Up/Down option separately for each instrument during the session. Changing direction updates the selected instrument output. Each instrument/direction retains its independent edits; save each required version before leaving. Stage 2 input remains single-part and is not automatically merged from a multipart choir score.

Reopened instrument MusicXML is an independent written-score document. Do not transpose it as an instrument again unless intended; open the Concert source to generate a new variant.

## Export PDF

Export PDF prints the current Working Score, for either Concert or instrument notation. Output uses portrait A4, 12 mm margins, compact system/verse/note spacing and page numbers. Longer scores paginate between complete systems. Not every score is forced onto one sheet. PDF rendering does not change editor zoom or MusicXML.

## Return Home

With unsaved changes, Home offers saving the affected score, Continue editing, or Discard changes and go Home. Discard explicitly drops unsaved Concert and instrument work and returns to import. Saved files remain unchanged. Continue editing or Escape keeps the work open. Wait for active save/edit operations to finish before leaving.

## Limits

- OMR may misread or omit notes, voices, lyrics, symbols and legacy-font text. User correction remains necessary.
- Encrypted PDFs are unsupported; poor scans may fail. Current recognition limits are 20 MB, 10 pages and a 120-second timeout. There are no autonomous retries or AI agents.
- Multiple score outputs are not silently selected or merged.
- This is not complete MuseScore/Symphony Pro parity. Nested tuplets, every ornament and arbitrary engraving are not universally supported.
- Stage 2 remains single-part; Add measure retains its single-part/single-staff restriction.
- Personal inputs, recognition evidence and runtime archives are not distributed in Git.

See the repository's Task 04 report for actual verification results, exclusions and Product Owner acceptance. Earlier development-port/version notes do not override the current accepted behavior described here.
