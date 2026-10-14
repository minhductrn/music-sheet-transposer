# P0.2.2 — simultaneous notes and independent tie fidelity

## Evidence and scope

Inspected the dirty working tree and the complete P0.2.1 report, including its browser-failure follow-up. Existing Phase 4F/P0/P0.1/P0.2/P0.2.1 edits were retained. No applicable repository AGENTS.md was found. Neither cungdemTinMung.pdf nor saved benchmark browser MusicXML is present (including ignored files searched by filename). No connected benchmark browser was available. Thus “Mừng” and “Trời” are manual acceptance targets, not claimed reproductions or accepted results. Automated fixtures reproduce the actual insertion, XML timing, and independent relationship paths without production lyric or position special cases.

## Diagnosis: timing versus engraving

The insertion caret resolves an OSMD timestamp to a canonical rational onset; the POST uses that exact rational string. The backend projects MusicXML using Fraction arithmetic. Small display alone never introduces grace timing. Existing explicit placement with equal durations already creates same-onset chords; different durations previously rejected same-voice insertion. The selected-note simultaneous command previously copied the anchor's duration instead of retaining the requested duration. Sequential before/after commands intentionally represent different onsets and cannot stand in for simultaneous insertion.

A separate rendering defect is visible in the installed OSMD bundle at frontend/node_modules/opensheetmusicdisplay/build/opensheetmusicdisplay.min.js:
- getCueNoteAndNoteTypeXml treats type@size="cue" as IsCueNote, even without a cue element.
- VexFlowConverter.StaveNote constructs a VexFlow GraceNote when the first source note IsCueNote is true.

Our canonical small-note spelling uses type@size="cue" and notehead@font-size="small", while retaining duration and no grace/cue element. This conflation sends duration-bearing display-small notes through the renderer's grace-sized construction path. Which note leads the graphical entry can consequently affect mixed-size rendering. This explains a renderer risk independent of onset; the precise saved benchmark displacement cannot be assigned to semantics or engraving without its actual XML. Exact-onset fixture projection is verified; native graphical coordinates were not measured in a real browser.

The adapter changes only the editable viewing clone: duration-bearing notes with the application's explicit small-note spelling lose the type size flag before OSMD loading. True cue and grace XML is excluded. Native normal rhythmic engraving then handles chord/voice collisions. Uniquely mapped small SVG noteheads scale about their own engraved center, retaining the renderer's rhythmic position and existing transforms. There is no benchmark pixel translation and no attempt to conceal a timing error. Scaling is reversible on binding disposal. Canonical/export/source bytes remain unchanged. Read-only/transposed rendering retains the existing path.

## Canonical and MusicXML representation

EventAdd accepts same_onset_id: an explicit existing duration-bearing anchor in the requested measure. It conflicts with other placement modes and resolves exactly to the anchor's canonical onset. Voice/staff default to the anchor only when unspecified; size never selects a voice. The normal toolbar offers “Use selected note’s exact onset”; the advanced selected-note insertion uses the identity anchor. Existing-note ownership controls also offer “Set same onset as”, resolving an explicit selected existing event to the exact rational position before Apply.

Insertion retains requested pitch, duration, display size, accidental, voice/staff, independent lyric capability, and ties. Compatible same-voice pitched events at one onset use chord members when the requested duration does not exceed the immediately preceding member. Otherwise placement uses an isolated backup/forward cursor stream preserving the requested voice/staff and restoring the existing cursor. Different voices use the timed-stream path. No voice is invented, no duration is shortened, and no rests or missing notes are composed. Different-duration same-voice streams may receive an advisory overlap finding.

MusicXML chord durations may be shorter but cannot exceed their preceding note; see https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/chord/. Explicit chord_with_id requests now honor explicit durations with that technical guard; omitted durations retain the legacy anchor-rhythm contract. Two older fixtures now explicitly request the anchor rhythm that their assertions intended.

Duration corrections have explicit duration_scope="note" in the musical correction controls. These preserve other note durations and onsets. The existing default chord scope remains for older API clients and accepted workflow tests. A per-note chord edit that would violate duration representability fails atomically with an explicit ownership alternative. No musical unusualness gate was added. Grace/voice group-edit behavior remains the existing contract.

Stable IDs, cloned-document preservation, snapshot Undo/Redo and revision checks use the existing implementation. Original note properties, lyrics, comments, unsupported notation, directions, and layout instructions remain intact.

## Independent ties and rendering

P0.2.1 already stores separate explicit manual_ties entries keyed by source event. Each relationship has its own target, number, owned visual endpoint IDs, sound ownership and origin. No backend tie redesign was necessary: two normal/small note pairs can independently author A→B and C→D. Per-note tie/tied endpoints survive serialization; repeating a canonical pair changes neither XML nor history. Removing one pair leaves the other pair and unrelated native tie/slur markup intact. No relationship is inferred from simultaneous notes.

The prior correction overlay used identical bend depths for relationships spanning the same rhythmic positions. It now assigns separate lanes by canonical part/measure/staff/onset endpoint groups and offsets bend depth using measured SVG notehead size in local coordinates. Each curve still selects its own source. Distinct endpoints remain anchored to their own heads. Only explicit canonical relationships draw curves; native unrelated markings remain. Owned native tied elements are suppressed only in a viewing clone, as before. This is a narrow overlay adjustment, not source curve reconstruction.

## Files affected in this milestone

Application: backend/app/music/review/models.py, backend/app/music/review/patcher.py; frontend/src/components/MusicSheetViewer.tsx, RecognitionReview.tsx, ScoreCorrectionToolbar.tsx, VisualNoteEditor.tsx; frontend/src/utils/visualReview.ts, scoreRenderer.ts, scoreInteraction.ts, scoreTies.ts.

Tests: new backend/tests/test_p022_simultaneous.py; backend/tests/test_review_tied_insertion.py, test_review_overfill_diagnosis.py; frontend/tests/score-correction.test.mjs, score-renderer.test.mjs, score-ties.test.mjs, visual-review.test.mjs. This report is new. These files include earlier uncommitted work; the list identifies this milestone's additions, not exclusive ownership of their full git diff.

## Validation

- Focused backend simultaneous/drag/tie suites: 41 passed (including seven P0.2.2 cases).
- Full final backend suite: 718 passed, two existing TestClient deprecation warnings. Command: PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/pytest -q, from backend. The established TestClient sandbox stall required approved unsandboxed test execution; plugin autoload remains disabled for the previously documented unrelated plugin.
- Frontend: node --test tests/*.test.mjs, from frontend: all 11 test files passed.
- npm run lint: passed.
- npm run build: passed, existing large-bundle warning.
- git diff --check and untracked implementation/test/report whitespace checks: passed.

Coverage includes exact anchored normal/small insertion; distinct pitches and durations; chords and timed voices; stable IDs; two independent ties; replay without duplication; relationship-scoped removal; XML/history restoration; comments, lyrics, accidentals and original properties; read-only optional Check. Existing suites cover source grouping, three-system layout algorithm, Fit/zoom, unsupported XML, P0.2 drag, P0.2.1 ties and correction lifecycle. These are automated regression results, not browser acceptance.

## Known limitations

Mixed independent durations, same-pitch unisons, shared stems and unsupported OSMD engraving can still differ from the PDF. Ambiguously mapped/shared unison heads are intentionally not resized, selected, dragged or assigned guessed overlay endpoints. Scaling adjusts a small head, not an entire independent stem/beam/accidental engraving. Legacy group-duration API behavior remains available; the visual correction controls explicitly request per-note changes. Existing ownership movement requires removal/resolution of relationships before moving tied notes. Parallel correction lanes reduce overlap but do not solve all crossings or reconstruct source-specific bezier shapes, above/below placement or curvature. Source visual properties and unsupported XML remain authoritative in export; overlays do not rewrite them. True cue/grace and read-only transposed engraving use the existing renderer behavior.

## Exact manual browser acceptance steps

1. Open a review for cungdemTinMung.pdf. Keep Source PDF visible beside Working score. Confirm the accepted three source systems at Fit, 100%, zoom in/out and pane resizing before editing.
2. At “Mừng”, select the regular source-corresponding note. Inspect its canonical onset, duration, voice and staff in Advanced. Record the downloaded working XML before correction; do not infer a voice from display size.
3. Select Add note, then “Use selected note’s exact onset”. Explicitly choose the missing pitch, duration, Normal/Small, accidental and voice. Choose Duration-bearing unless the PDF and user choice explicitly indicate grace. Press Add once.
4. Inspect both notes: exact rational onsets must match, pitches/durations/sizes must match the choices, original lyric/accidental/voice/staff must survive. Download XML and inspect chord membership or backup/forward timing. Compare vertical grouping against the PDF; minor collision displacement is acceptable, a separate rhythmic column is not.
5. If correcting an existing displaced untied note, open its explicit ownership controls, choose “Set same onset as” the intended anchor, confirm destination voice/staff and Apply. If tied, remove its explicit relationship first, apply the move, then author the relationship again. Do not change duration or pitch merely to achieve closeness.
6. Select the intended regular source note → Tie → click its exact regular target. Separately select the small source note → Tie → click its exact small target, only if the PDF/user supports that second tie. Check two independently selectable curves and four owned tied endpoints with distinct relationship numbers in downloaded XML. No extra curve should appear for an unlinked simultaneous note.
7. Repeat the same pair: no duplicate curve, revision or history operation. Select one correction curve → Remove tie: only that pair disappears. Undo restores it; Redo removes it. Undo/Redo insertion and per-note duration changes too; identities and both timelines must remain stable.
8. Run Optional Check score and compare downloads/revision/history before and after: all must be unchanged. Advisory musical findings must not prohibit an explicit faithful correction.
9. Repeat steps 2–8 around “Trời”, independently selecting its actual notes. No shared score-specific positions or lyric logic should be assumed.
10. Recheck Fit, 100%, zoom, scroll and pane resize with both tie pairs present. Confirm three systems, correct head/curve attachment, selectable endpoints, and P0.2 vertical pitch dragging. Switch to Transposed and back to Corrected; verify read-only controls and preserved corrections. Record screenshots, actual XML and browser/version for acceptance.

No browser acceptance is claimed. No files were staged, committed or pushed. No reset, restore, clean, stash or discard operation was performed. Existing work remains uncommitted. Stop after implementation, validation and this report.
