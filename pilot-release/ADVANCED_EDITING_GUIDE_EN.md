# Advanced Editing v1 preview

Independent candidate based on accepted UX Next RC1. Classic and RC1 are unchanged.

1. Open a MusicXML score. For PDF/image recognition, correct and save MusicXML first.
2. Choose Key Change Section in the editing toolbar.
3. Click the first and last measures on Working Score, or adjust From/Through measure. Blue shading marks the complete selected range. V1 copies one part/one staff, including its voices.
4. Source key is filled from that passage and remains editable. Choosing a source key changes its interpretation only; no notes change until Apply.
5. Use minus/plus, each worth 0.5 tones (one semitone), or select Destination. Up/Down remains available; the counter supports up to two octaves in either direction, subject to valid note octaves.
6. Preview the copied section. The preview is not saved into Working Score. Apply appends the copy to the end with a section barline and explicit destination key; notes and chord symbols transpose together. Existing original measures remain unchanged.
7. Global Undo/Redo restores the complete append. Save/Save As downloads the edited MusicXML. Instrument editing changes only that instrument output.
8. Concert Key uses the same controls with Preview and Apply. Its Source key remains editable; its interval is explicit.

The panel floats without moving the score. Escape or Cancel closes it. Edits or range/key changes invalidate an old preview.
Boundary ties/slurs/tuplets must be contained. V1 does not infer clipped relationships, copy repeat/ending instructions, support multipart/multistaff passages, insert into the middle, or author nested/cross-bar tuplets. A passage with existing key changes preserves their relative key relationships; unsupported spellings are reported. Cross-voice slur boundaries may require correction before copying.
Preview is not Product Owner acceptance. Do not replace production with this candidate until accepted.
