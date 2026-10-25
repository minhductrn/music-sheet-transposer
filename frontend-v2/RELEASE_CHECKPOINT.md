# Accepted UX v2 checkpoint — 2026-10-25

Product Owner disposition: ACCEPTED. The owner confirmed “đáp ứng yêu cầu và nghiệm thu” and explicitly authorized preparation, commit, and push to GitHub.

## Scope

Task 01 synthetic React/TypeScript workspace and Task 02 real MusicXML editing: read-only source comparison, note/lyric/text editing, ties/slurs, tuplets and beams, explicit accidentals, Concert Key, saved canonical concert input, independent Alto/Soprano/Tenor outputs with Up/Down, instrument editing, MusicXML/PDF exports, and independent pane Fit/zoom.

Required existing backend editor modules and their focused tests are included so this checkpoint is coherent. Legacy frontend work and unrelated local documents remain outside this commit. Private music, screenshots, generated PDFs, runtime directories, and full local evidence reports are excluded.

## Verification before packaging

- 493 relevant backend tests passed, including the opt-in private sample integration checks.
- 44 frontend unit tests, type checking, lint, and production build passed.
- Full Firefox regression: 49 passed before the final short-tail tie geometry refinement; four relevant browser cases passed again after that refinement.
- Independent source review passed. All 31 frozen UX baseline checksums and the original private MusicXML sample remained unchanged.

Packaging verification on the staged candidate: 493 backend tests, 44 frontend unit tests and all 49 Firefox cases passed; type checking, lint and build passed. Existing installed dependencies were reused in an isolated temporary checkout, with separate browser-test ports. The final update after testing only records these results in this document. Build reports the existing large-bundle warning; backend reports two dependency deprecation warnings. Tests are technical evidence; acceptance came from the Product Owner.

## Limits

This is an accepted local pilot, not a production deployment. Firefox uses download plus explicit retention confirmation where a native file picker is unavailable. The private sample and full verification artifacts remain local. Unknown/ambiguous tie mappings retain renderer fallback. Browser setup contains a host-specific executable path. No OMR, LLM calls, autonomous agents, or production hosting are included.
