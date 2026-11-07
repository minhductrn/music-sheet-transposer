# Music Sheet Transposer 1.0.4 — Architecture

Header Text uses stable object IDs. App-owned header credits are excluded only from disposable native rendering XML to avoid duplicate drawing; canonical MusicXML retains them. User header positions use credit-words page coordinates, normalized within the application header region; generated labels/positions use miscellaneous fields. Atomic revision-checked text patches participate in Undo/Redo. Musical identity checks are unchanged. External applications can lay out these objects differently.

Existing limits remain: local deployment only; OMR is a draft, not guaranteed correct; dense engraving collisions, multipart expansion and nested/cross-bar tuplet authoring are not newly resolved. Camera capture, Web Share API and cloud deployment are excluded. No general OMR accuracy certification is claimed.
