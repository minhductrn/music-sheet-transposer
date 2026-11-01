# Working Score text objects - 1.0.3-preview.2

Status: historical preview record; the Product Owner accepted these changes on 2026-11-01 for Release 1.0.3. Production 1.0.2 and its release Pull Request remain unchanged. The preview source is on feature/working-score-text and is not an accepted release commit.

## Direct object interactions

Choose Text, click the page header or a note/rest, type and press Enter (or blur) to save. Header text is a MusicXML credit object; note/rest text is a direction object. Click an existing object with Text active to edit it. With Select active, click the object and use Delete object. Undo/Redo restores/reapplies these edits. Escape or Cancel dismisses an unsaved draft without deleting its anchor note. Compare/Edit Only and both Concert/instrument workspaces share these actions. Empty staff clicks use a nearby existing measure event; Header text can be dragged within the page header.

Header objects have stable IDs and explicit SVG bindings, so their selection does not rely on guessing OCR strings. Header objects occupy existing whitespace above the first staff. Adding objects does not expand the page or add header rows. Positions are normalized within this region and persist in MusicXML; generated-label positions use application metadata. Standard subtitle-sized text replaces the tiny zoom-multiplied label. Default generated labels sit compactly above the title. Users control manual placement. Lyric PDF size remains the accepted 85%.

## Key and instrument text objects

Applying Concert Key stores the destination label in the MusicXML miscellaneous field mst-output-heading. Instrument generation stores the Alto/Soprano/Tenor Saxophone name. Original titles, composer, notes and part identity are retained. The existing text projection exposes this field as the stable output-heading object; patch/delete uses existing text commands. Users can edit or delete these labels just like header Text objects. Reimport restores supported text. A subsequent explicit transposition/generation creates its current label again.

Metadata travels in the same Concert correction transaction, so Undo/Redo restores the key change and label together. Musical object-identity checks are unchanged. Header addition extends only the text API role list; it does not permit arbitrary note insertion through document correction.

## Verification and limits

Build/lint and 63 frontend unit tests passed. All 19 score-text backend cases passed, including header/output-label edit, delete, Undo and MusicXML reimport with unchanged notes/lyrics. Ten browser cases passed, including header dragging, stable staff geometry, position persistence, Undo/Redo and reimport: direct Text in Compare/Edit Only; Concert label persistence/Undo/Redo/PDF/reimport; editable/deletable labels and direct Text on all three instruments; header Text creation/edit/deletion in Compare/Edit Only/Stage 2 with a title-overlap check. The Standard-margin header PDF check was repeated after adding coverage; its extracted PDF text contains both header and original title. Real-score PDF and synthetic Standard-margin header previews were visually inspected and the reported title overlap was absent.

These bounded checks do not certify all OMR layouts, arbitrary object dragging or every overlapping musical target. Existing unrelated equal-string ambiguity remains for legacy native score text. The test harness uses physical mouse coordinates for noteheads crossed by staff lines, matching the SVG hit-testing path. PC-02/03/05/06/07 apply; final acceptance belongs to the Product Owner under PC-08.

## Preview handoff

Use http://localhost:5305 for this updated preview. Keep 1.0.2 production at port 5250 unchanged. The older previews at 5303 and 5304 were not stopped to avoid disrupting unsaved user edits; save MusicXML there before opening it in the updated preview. The accepted implementation is promoted separately under docs/release-1.0.3; preview URLs are not production launch instructions.

## Header object placement

Header labels use the existing header whitespace with compact spacing above the title. Adding text does not add a row or move the staff. Users can drag header text within the header, edit or delete it, and undo or redo these actions. Header positions persist in MusicXML and PDF output. Production 1.0.2 remains unchanged.
