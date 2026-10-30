# Classic Task 06.1 hotfix verification

Date: October 30, 2026.
Status: TECHNICALLY VERIFIED; Product Owner acceptance pending.

Scope: Home title/import area without editor chrome; plain Add Chord label without decorative G in Stage 1 and Stage 2. Loaded Classic vertical toolbars remain unchanged. No UX Next layout, backend accidental command or advanced feature is included.

The source baseline was reconstructed from commit 47286f9 plus exactly five accepted Task 06 PDF files. All application hashes matched the accepted Classic manifest before applying the three-file Home/label overlay. The packaging builder rejects any backend or other application-source difference outside that overlay.

Verification: ESLint, 56 frontend unit tests, TypeScript and production build passed. Five packaged browser tests passed: Home at desktop/narrow widths, Demo tool restoration, MusicXML import restoring tools, visible import errors, and Add Chord labels in Stage 1/Edit Only/Stage 2 with vertical toolbar retained. Package integrity/Python ABI passed. The complete OMR/PDF/transposition regression suite was not rerun because those sources are hash-identical to Classic. Existing bundle-size warnings remain.

PC-02/06/07/08 and acceptance gates 1–3 apply. Test PASS is not Product Owner acceptance. Gate 4 remains pending.

New package: /home/dtran/music-sheet-transposer-releases/music-sheet-transposer-classic-task06.1
Archive SHA-256: f0c10fedd26ce7ddf93cb4802f1f5a1cf1fef0b909bf858b4590533be7f2951c
Test URL: http://localhost:5182/
Production switch: save all work, stop the existing port 5181 server, then launch the new package on port 5181 using CLASSIC_HOTFIX_GUIDE_EN.md.
The running port 5181 server, original Classic archive, UX Next and private score files were not modified.
