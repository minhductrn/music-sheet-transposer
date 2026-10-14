# S2A-01 — Concert Key Transposition

Status: IN PROGRESS — implementation and automated evidence prepared for Technical
Lead review; Firefox Product Owner acceptance remains pending.

Use **Concert Key Transposition** below the existing editor. Select a saved
Concert MusicXML file, or choose **Use saved Working Score** after Save and, for
downloads, explicit acknowledgement. This operation reads the saved blob, never
unsaved editor state. Later edits do not change a selected saved snapshot.

First inspect the detected signature and select/confirm the Source Key. An explicit
MusicXML major/minor declaration supplies an editable suggestion, never automatic
confirmation. With missing mode, both compatible major/minor candidates are shown
and neither is selected. For one flat, these are F Major and D Minor. The user
selects F Major for the Product Owner-identified benchmark, then explicitly checks
**I confirm the Source Key**. Choosing D Minor instead enables minor-key targets.
A different signature is rejected with a clear compatibility message. Changing
the selected source key or loading another file clears confirmation and the prior
result. No harmonic analysis or OMR is performed.

Select a target key in the confirmed source major/minor mode and Up/Down within one octave.
Enharmonic unisons change spelling without changing sounding register. Concert
Transpose previews an independent result using the existing MusicSheetViewer.
The original file is never opened for writing. **Save As Concert MusicXML** asks
for a different filename and requests a browser download, including Firefox.
Download destination/completion remain browser-controlled; acknowledge retaining
the file before **Open saved Concert result for editing** becomes available.
Opening replaces the temporary editing session, so save or explicitly close an
unsaved Working Score first. Opening does not rerun OMR or implicitly confirm
subsequent edits. The downloaded file can also be opened with the existing Open
MusicXML action after a backend restart.

## Transformation and supported inputs

`POST /api/v1/concert-key` inspects an uploaded saved MusicXML blob.
`POST /api/v1/transpose/concert-key` accepts that blob, `target_fifths` (-7…7),
and `direction` (`up`/`down`), plus required `source_fifths`, `source_mode`
(`major`/`minor`), and `source_confirmed=true`. The backend validates the confirmed
signature against the supplied XML; missing/false confirmation or an incompatible
key returns HTTP 422. The source needs one traditional signature across pitched
parts/staves. An absent mode is allowed; an unsupported modal declaration is not.
Detection returns `fifths`, declared `mode` or null, both `candidates`, and an
explicit-mode `suggested` key or null. No musical conclusion is inferred from OMR,
lyrics, a final chord, or a final note. Missing keys, key changes/conflicting
signatures, instrument transposition, mixed pitched/percussion instruments in one part, microtones,
scordatura, custom chord-root display text, rootless harmony, explicit ornament
accidentals, custom accidental display overrides, custom key-signature octave
placement, and intervals requiring accidentals beyond double sharp/flat produce
an actionable limitation rather than a guessed result. Existing semitone and
Stage 1 correction operations remain unchanged.

A chromatic interval and a diatonic interval are derived from the chosen tonic
spellings. Each note, chord root, and chord bass uses both components; chromatic
alterations are retained relative to the shifted letter. XML is edited in a DOM,
not reconstructed from a reduced score model. Only pitches, key/cancel values,
and existing printed note accidentals change. The explicitly confirmed mode is
stored in result key declarations, adding missing mode elements only to the
independent result. Confirming an unchanged signature changes no note/chord data.
Rests/unpitched notes and identified
percussion parts are untouched. Comments, node order, tie IDs/numbers/endpoints,
Up/Down attributes, lyrics, size, rhythms, voices, staves, chord membership, slurs,
and articulations remain. Nonzero output serialization can change whitespace,
quoting, and encoding declarations; unchanged target keys with already matching
mode declarations return the original bytes. Otherwise the explicitly confirmed
mode is serialized in the independent result. Existing Stage 1 technical diagnostics are checked before and after;
music/OMR warnings remain advisory.

The spelling approach follows MusicXML's separate diatonic step and chromatic
alteration representation: [W3C MusicXML tutorial](https://www.w3.org/2021/06/musicxml40/tutorial/midi-compatible-part/).

## Verification

Controlled synthetic tests are in `backend/tests/music/test_concert_key.py`,
`backend/tests/test_concert_key_api.py`, and
`frontend/tests/concert-transpose.test.mjs`; no private benchmark XML is used.
The backend round-trip writes a source and independent output in pytest's
scratch directory, reopens through the correction API, verifies and exports the
same output bytes, checks both owned ties/directions and Small Note/lyrics/chord
membership, and confirms the reopened result remains editable.

Run backend tests with the existing environment:

```
cd backend
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q tests
```

Frontend regression selection follows the accepted Stage 1 checkpoint exclusion
of the historical untracked private-fixture test:

```
cd frontend
mapfile -t frontend_tests < <(rg --files tests -g '*.test.mjs' | rg -v '^tests/standalone-ties.test.mjs$' | sort)
node --test --test-isolation=none --test-reporter=tap "${frontend_tests[@]}"
npm run lint
npm run build
```

S2A-01A final automated results using the commands above: backend **787 passed**
(including 44 concert-key cases), frontend **240 passed** (including 12 concert
workflow cases). Lint, production build, and `git diff --check` passed.
The build retains the existing large-chunk
warning; backend tests report existing Starlette test-client deprecations.
Unrelated preexisting modified/untracked files, including the private MusicXML
and Stage 1 editor implementation, were checked against their preflight SHA-256
hashes and remained unchanged. Only the eight concert-key source/API/test/document
files identified in the implementation report changed for S2A-01A.

Firefox acceptance: select a saved score without mode, check that F Major/D Minor
are offered for one flat, choose and confirm F Major, then try Up and Down. Also
confirm an explicit suggestion and try correcting its mode. Inspect
notes/chord symbols/lyrics/small notes and independent tie directions, Save As a
new filename, acknowledge the download, reopen and edit the result. Reopen the
actual downloaded file separately to verify disk persistence. Check that unsaved
editor changes cannot be used implicitly and that the source file is unchanged.

PC-02/03/04/05/06/07 are protected by using saved user-corrected source data,
explicit key/direction choices, independent output, unchanged corrections, and
regression checks. Gate 3 Technical Lead review and Gate 4 Product Owner
acceptance remain required. No instrument-specific Stage 2 operation is added.
