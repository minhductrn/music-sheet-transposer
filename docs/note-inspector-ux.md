# Shared note inspector preview — 2026-11-23

Status: implementation verified with targeted checks; Product Owner acceptance pending. Production 1.0.7, its sealed package and GitHub release were not changed or republished.

## User requirements

The previous dense panel made Voice assignment hard to find. The Product Owner requested a clearer layout, identical across every editing stage, and clarified a preference for typing 1 or 2 into a Voice field rather than relying on quick-choice buttons. Voice 1 represents Main and Voice 2 represents Harmony in this workflow; lyric Verse is a separate concept.

## Implementation

RealWorkspace renders one shared inspector for the Concert workspace and the recursive Alto/Soprano/Tenor editors. It is also retained after an applied Concert key change. The shared NoteVoiceControl is always at the top, with a directly editable Voice field, Apply button, current applied voice badge and the explanation `1 = Main · 2 = Harmony`. Enter submits, Apply submits, and Tab/blur retains the previous application behavior. A local pending guard avoids duplicate requests from overlapping submit/blur events. Other voice IDs remain supported by the same input.

Pitch, octave, duration and accidentals form the basic group. Add-before/after remains visible. Lyrics/Verse and notation/expression tools are placed in separate expandable groups; existing commands and semantics are retained. Delete remains at the sticky bottom. The header and close button stay accessible while scrolling. Positioning keeps the inspector below the common toolbar and within the viewport. CSS is scoped to prevent Stage 2 section styles changing the inspector's spacing.

Assignment reuses the accepted assignSelectedVoice path: a single selected chord note is separated through explicit ownership; a standalone note uses the existing event patch. Pitch, duration, onset and unrelated voices are not changed. No backend or musical validation policy was changed.

## Verification

- Typecheck, lint and build passed. Existing bundle-size warning remains.
- A 28-test browser run of the first layout passed after correcting toolbar overlap; later typed-input coverage replaced the quick buttons at the Product Owner's request.
- With typed input, the broader 29-case run passed 27 cases. The two remaining cases exposed loss of blur application when focus reached Apply and a test that selected a note before Concert transposition finished. Blur behavior was restored; the Concert test now waits for completion before editing.
- Final focused verification: 7 passed in 28.5 seconds, covering typed Voice updates in Concert/Alto/Soprano/Tenor, small-screen bounds, editing after applied Concert transposition, and splitting only the selected G4 from a chord with Tab and Undo.
- Other checks in the broader run covered byte-exact unconditional Save, temporary voice conflicts, lyrics, drag/drop, sequential insertion, beaming, timing movement and voice alignment. A complete legacy browser suite was not run.
- Visual screenshots of the actual preview were reviewed. No private score file was committed.

Relevant principles: PC-02, PC-05, PC-06, PC-07 and PC-09. Product Owner approval is separate from these test results. Preview: http://localhost:5327/.


## Layout acceptance and adjacent-note defaults

The Product Owner located the expandable controls and approved the shared inspector layout in conversation on 2026-11-23. Normal/Small, expressions and lyric commands remain available in their existing groups.

The subsequent Add note before/after request requires new notes to inherit the selected note's Voice and display size. The shared SequentialNoteEditor now initializes Size from the selected event and includes display_size in the add request. Existing selected pitch, alteration, octave and Staff defaults remain intact. Each opening of Before/After resets Voice, Size and pitch fields to the selected note, so canceled edits cannot leak into a later insertion. The user may explicitly override Voice or Size before insertion. Existing duration picker defaults are unchanged by this update; note relationships, lyrics or expression associations are not copied implicitly.

Verification: typecheck, lint and build passed. Fourteen targeted browser checks passed in 44.8 seconds, including before/after × Normal/Small with Voice 2, preserved selected pitch/Staff, Undo, MusicXML reimport, explicit overrides and reset after cancel. The shared Concert/Alto/Soprano/Tenor inspector checks also set a selected note to Small in Voice 2, add after it, and confirm the new note remains Small in Voice 2. Editing after Concert key application and small-screen bounds also passed. No backend or validation policy changed. Production 1.0.7 and GitHub remain untouched; the inheritance update is available in the preview pending Product Owner acceptance.
