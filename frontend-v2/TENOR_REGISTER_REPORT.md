# Tenor Saxophone B♭ readable written register

Date: 2026-10-25. Status: **ACCEPTED**. Product Owner approved “đồng ý, nên viết giống Soprano Saxophone” after the specific proposal to retain standard Tenor Up +14 and change Tenor Down to +2. The Product Owner subsequently stated “xác nhận nghiệm thu và đề nghi commit, push kết quả”; final acceptance and publication authorization are recorded below.

## Musical contract

This is the written part for the B♭ tenor saxophone in treble clef, not a tenor singer's concert-pitch part. Standard written-to-sounding metadata remains diatonic -1, chromatic -2, octave-change -1 (total -14 semitones); instrument name remains Tenor Saxophone and MIDI program remains 67.

| Instrument/mode | Written notes relative to saved Concert | Sounding register relative to Concert |
| --- | --- | --- |
| Soprano Up, unchanged | +2 | same |
| Tenor Up, standard, unchanged | +14 | same |
| Tenor Down, corrected | +2 | one octave lower |
| Alto Down, unchanged | -3 | one octave lower |
| Soprano Down, unchanged | -10 | one octave lower |

Tenor Down is therefore identical in written pitch spelling, octave and key signature to Soprano Up, while remaining a true Tenor instrument part. Concert C4 becomes written D4 for the readable Tenor option and D5 for standard Tenor Up. This is an explicit octave arrangement, not a way to keep the exact original sounding octave while writing the same pitches as Soprano.

The previous generic Down rule used offset modulo 12 minus 12: Tenor +14 became -10, a two-octave jump from Up. Down now subtracts exactly one octave from each standard offset: Tenor +14 becomes +2. Alto/Soprano outputs are unchanged. No new direction mode, automatic range adjustment, clef change, melody rewrite, or source mutation was added.

## Bounded implementation

- backend/app/music/musicxml/instruments.py: one-octave Down selection; identity and transpose metadata unchanged.
- frontend-v2/src/real/RealWorkspace.tsx: accurate signed interval labels and explicit Tenor Down explanation/option label. Existing Up/Down selection and variant caches are reused.
- backend/tests/test_task02_integration.py: explicit expected Down offsets plus written-equality/sounding-identity, HTTP endpoint and private-sample preservation checks.
- frontend-v2/tests/e2e/tenor-register.spec.ts: Soprano Up versus Tenor Down, automatic Up/Down refresh, octave difference, exported metadata and unchanged Concert export.

Prior Home implementation and upper-left placement remain included. There are no changes to the Product Constitution: PC-04's standard Tenor +14 remains available in Up. The separately approved lower-register choice is corrected.

## Standalone delivery

A separate local package is supplied at evidence/tenor/music-sheet-transposer-pilot-tenor-v0.3.tar.gz, with the extracted runnable folder and adjacent SHA256 file. Archive SHA256: a382a30deeeae8f8f20507ce0d04406e53fe5a0b19abeae5e716c75ebc06d53b.

It preserves the existing pilot runtime and Home layout, overlays only the new frontend build and the single backend instrument module, and records explicit uncommitted source overlay hashes in manifest.json. The old Task 03/Home archives and running user sessions are untouched. No Git add/commit/push was performed during implementation; publication is now authorized separately below.

Run the extracted package with `python3 -B /path/to/music-sheet-transposer-pilot-tenor-v0.3/start.py --port 5183`, then open http://localhost:5183. From saved Concert input, select Tenor Saxophone B♭ and Direction → Down · like Soprano notation (+2). Up remains the standard +14 choice. Already exported old Tenor files are not migrated or edited; generate the new written part from the saved Concert source. Do not transpose an already-written instrument file again.

## Verification

- 496 relevant backend tests PASS, including the three new cases and approved private-sample checks; two existing dependency deprecation warnings remain.
- Root typecheck, lint, 44 unit tests and build PASS; existing large-bundle warning remains.
- Direct private sample comparison: 63 note pitches, Concert MIDI 60–74; Tenor Up 74–88; Tenor Down and Soprano Up both 62–76, with exactly 12 semitones between Tenor modes. The original private file retained its checksum. MIDI values here describe stored written pitches, not actual Tenor sounding pitches.
- Final standalone package regression: **54 Firefox tests PASS, zero failures/skips**, in 3.2 minutes. This includes the new private-sample Tenor notation/metadata case, all Home cases, and the prior MusicXML/PDF/editing workflows. The final screenshot was reviewed: Tenor Down notes occupy the same written register as Soprano Up. Tested source hashes remained unchanged.

Technical Lead source review checks PC-03/04/05: saved Concert remains authoritative and unchanged; same written notes do not erase Tenor's physical transposition metadata; IDs, lyrics, ties/slurs, voices, rhythm and harmony are preserved. PC-06: the user explicitly selects the lower arrangement, with its sounding-octave effect stated in the UI. PC-07: old Alto/Soprano/standard Tenor tests and existing editor/Home workflows remain in regression. PC-08: final Product Owner acceptance remains separate.

## Reference distinction

[Texas A&M — Transposing Instruments](https://odp.library.tamu.edu/stepstomusictheory/chapter/transposing-instruments/) distinguishes Tenor's sounding major ninth below its treble-clef written pitch. [MusicXML 4.0 transpose](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/transpose/) and [octave-change](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/octave-change/) specify the written-to-sounding direction of the stored transposition metadata.

## Final protection and acceptance

All pre-existing local changes outside the explicitly modified instrument module/test and real workspace remain byte-identical. The old Home r2 archive is unchanged. Final package per-file hashes match, Git index is empty, and HEAD remains 474af9b. No dependencies were installed and no legacy frontend, original private score or existing exported file was modified. Gates 1–4 are complete following the Product Owner acceptance on 2026-10-25. Evidence: evidence/tenor/backend.log, checks.json, production-regression.json, production-browser.log, sample-comparison.json, tested-source-hashes.json and tenor-readable-down.png.

## Product Owner acceptance and publication authorization

On 2026-10-25 (America/New_York), after the verified v0.3 handoff, the Product Owner stated “xác nhận nghiệm thu và đề nghi commit, push kết quả”. The delivered Tenor correction is ACCEPTED and commit/push is authorized. The consolidated source checkpoint includes the previously accepted Home behavior, its upper-left placement in the current delivery, Tenor Down +2 with standard Up +14 retained, their tests and acceptance reports. Only these bounded source/test/documentation files are published; bundles, screenshots, private inputs and unrelated local work remain excluded. Source and delivered runtime archives are unchanged by this acceptance/publication documentation update. Earlier notes about empty index and HEAD 474af9b describe the verification-time state before this publication.
