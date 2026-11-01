# Music Sheet Transposer 1.0.0 — Release Notes

Release date: October 31, 2026. Status: Product Owner-designated local production release. Accepted feature baseline: Advanced Editing v1 preview.5, commit `e8a6b24`. Tag: `v1.0.0`.

## Included

This release consolidates accepted UX Next layout, PDF/image recognition and manual correction, MusicXML import/save/reimport, Concert transposition, independent Alto/Soprano/Tenor written scores, A4 PDF export, direct composition tools and Advanced Editing v1. It includes unobscured section actions and full-width Concert Preview. Version labels, startup defaults, documentation and receipts are updated to 1.0.0; musical behavior is preserved.

## Handoff and verification

Package: `music-sheet-transposer-1.0.0.tar.gz`. Local URL: http://localhost:5250. No source checkout or development server is needed to run it. Existing packages remain available for rollback. Users retain MusicXML locally; there is no durable backend database or cloud deployment.

The accepted baseline passed 124 browser regression checks, 14 final focused checks, 63 frontend unit checks, a 32-test backend transposition suite and a 91-test relationship suite (eight section tests overlap). The final 1.0.0 package passed all 133 browser checks, 63 unit checks, lint/build, saved Concert and three-instrument recovery after server restart, and one fresh local Audiveris PDF recognition run. Results are recorded in VERIFICATION.json. PDF regression uses retained recognition replay and does not certify general OMR accuracy. Acceptance.json records explicit feature acceptance and production designation; tests alone do not confer acceptance.

## Known limits

- OMR can misread keys, accidentals, rhythms, voices, verses, lyrics and marks. Compare and correct; old-font OCR is not guaranteed.
- Review state, history and instrument caches are temporary. Retain MusicXML before closing.
- Advanced sections support one part/one staff, complete contiguous measures and append-to-end. Repeat/ending copying, arbitrary middle paste, multipart expansion and new nested/cross-bar tuplets are excluded.
- Boundary relationships must be complete. Unsupported custom/microtonal spellings and out-of-range pitches can be reported instead of normalized.
- General Stage 2 multipart and Add measure across multiple parts/staves remain limited.
- Fit-in-one-page PDF can make long scores small; multiple A4 pages remain available.
- Existing Ubuntu/Python ABI, Audiveris/Java and OCR prerequisites remain. This is not a universal Windows installer, cloud release or OMR accuracy certification.

Future notation, cloud and UX changes should start from this production checkpoint in a separate development version.
