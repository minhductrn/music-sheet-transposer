# P0 browser acceptance UX fix: direct score correction

2026-10-05. Bounded frontend UX continuation from the existing working tree.
No backend, OMR/recovery, canonical-model or accepted source-system engraving
algorithm changes. No staging, commit or push.

1. **Root cause:** musical-position and property controls lived below the score.
   Renderer measure geometry was not connected to a semantic insertion command
   or a visible caret. Users therefore needed the exact-position form even when
   the missing area could be identified visually.
2. **Files changed in this task:** frontend
   `src/components/{RecognitionReview,MusicSheetViewer}.tsx`, `src/index.css`,
   `tests/{visual-review,review-selection}.test.mjs`; new
   `src/components/ScoreCorrectionToolbar.tsx`, `src/utils/scoreInsertion.ts`,
   `tests/score-correction.test.mjs`, and this report. Earlier uncommitted work
   was retained. `VisualNoteEditor`, `MusicalPositionEditor`, `ReviewScoreViewport`,
   source engraving/interaction utilities and Home's transpose routing remain
   available without changing their implementations.
3. **Toolbar architecture:** compact native SVG icons with title tooltips,
   accessible button labels, active-state indication and disabled states inside
   `.review-score`, above the Working Score viewer. Related actions form small
   groups. A sticky toolbar and bounded contextual panel keep correction controls
   alongside the score. No UI framework or permanent third pane was added.
4. **Actions:** Select, Add note, Delete, Pitch, Duration, Accidental, Normal/Small,
   Duration-bearing/Grace, Tie, Lyric, Undo, Redo and More/Advanced. Existing view
   switch and Fit/zoom controls remain. Remove tie is a contextual action.
5. **Selection:** opening a review does not implicitly select the first event.
   Existing semantic SVG-head selection and blue highlighting remain; note clicks
   synchronize normal and Advanced controls. In Add mode note clicks do not
   accidentally run selected-note commands. Selecting the Select tool leaves Add
   or Tie mode. A source-note highlight can coexist with an insertion caret.
6. **Add-note mode:** Add note enables direct score placement and compact draft
   properties. Add remains disabled until a unique visual position, representable
   duration and explicit/unambiguous voice are available. A click or draft change
   does not send a musical patch. Add sends the existing EventAdd command with
   internal measure/staff/onset values from that selected position. Normal fields
   never expose onset fractions, MusicXML or event IDs.
7. **Empty-position resolution:** each rendered measure/staff is associated with
   canonical ownership and its OSMD page. An empty measure offers exactly its
   explicit start, with a marker in its playable staff area. Populated measures
   offer rendered staff entries whose timestamps uniquely match canonical event
   onsets; an explicitly empty initial span can offer measure start. Hit lanes
   exclude clef/instruction areas, lyrics, unknown timestamps, generated
   continuations, overlapping ownership and arbitrary gaps. Pixels choose among
   those known positions; they do not generate subdivisions or infer missing
   notation from meter. Voice ambiguity requires a musical voice choice.
8. **Insertion marker:** a blue caret is appended only to the renderer SVG,
   outside canonical XML. It has an accessible label and ignores pointer events.
   It is removed on leaving Add, rejected hits, successful commands, mode/view
   changes and renderer cleanup. Responsive rerender rebuilds it from semantic
   position, rather than retaining stale pixels. No glyph or notation is created
   until Add is confirmed.
9. **Contextual properties:** pitch letter/octave, accidental, named duration,
   size and timing are compact native controls. Only the requested selected-note
   property opens; insertion groups its draft properties in a bounded panel.
   Voice choices live in a collapsed section unless ambiguous. Staff comes from
   the clicked staff, with relevant staff context shown. Secondary voice creation
   uses a generated unused label internally. Small and Grace remain independent;
   C5/Half/Small/Duration-bearing is covered by the Add callback regression.
   Existing shared-chord timing scope and backend rejection rules are retained.
10. **Tie interaction:** select source → Tie → backend-approved target highlights
    → click target uses the existing tie patch. Visible target-selection status
    and Cancel/Remove actions sit by the toolbar. No endpoint inference or manual
    IDs; existing sound/visual MusicXML endpoint behavior is untouched.
11. **Advanced fallback:** the detailed position form, VisualNoteEditor, Event
    Inspector, exact onset/voice/staff/ownership controls, metadata and technical
    information remain available under Advanced correction. They are no longer
    the normal below-score workflow. Existing source confirmations and final
    comparison/Verify controls remain in the authoritative validation panel.
12. **Fit/zoom:** SVG `getScreenCTM().inverse()` converts client coordinates through
    CSS Fit/zoom, viewBox and scrolling; OSMD's public unit-to-pixel conversion
    supplies engraving units. The adapter resolves the SVG inside the backend's
    canvas DIV and matches its actual page identity. The caret lives in that same
    SVG so the existing viewport transform moves both together; non-scaling
    stroke preserves visibility. Mode/marker changes do not request engraving.
13. **Source-system regression:** `sourceEngraving.ts`, renderer options, trusted
    grouping and the Fit/zoom viewport implementation are unchanged. Existing
    1–5 / 6–10 / 11–17 grouping, variable-system, ambiguity, measured-width and
    zoom regressions pass. A new viewer test confirms insertion/selection/mode
    updates do not cause an extra source-review render.
14. **Corrected/Transposed regression:** the same right pane still switches views;
    source remains on the left. Transposed has no corrected-identity bindings and
    mutation controls are disabled. Home's verified-master routing is unchanged;
    +2 then +3 and correction/history invalidation regressions pass.
15. **Tests:** full frontend suite passes **92 tests** via
    `node --test --test-isolation=none tests/*.test.mjs`. Thirteen new focused tests
    exercise toolbar states, commands, ambiguity, empty/canonical hits, actual
    page-wrapper integration, markers and transformations. Legacy selection tests
    now explicitly select their event instead of depending on an implicit first
    selection; their history/tie/selection assertions remain. No backend behavior
    changed, so backend suites were not rerun for this frontend-only task. The
    previous 656-test backend result is historical, not a new run.
16. **Lint/build/diff:** `npm run lint`, `npm run build`, and `git diff --check`
    pass. The existing OSMD bundle-size build warning remains. All work is
    unstaged; no reset/restore/clean/stash/stage/commit/push occurred.
17. **Remaining browser checks:** no browser executable or retained real-song
    capture was available in this workspace, so real Cùng Đem Tin Mừng acceptance
    is not claimed. Repeat Add → empty measure before Loan → visible caret →
    A4 Half Normal Duration-bearing → same canonical onset C5 Half Small
    Duration-bearing, with source-supported voice → select A4 → Tie → following
    A4 → source comparison/confirmation → Verify → transpose → view switch.
    Check actual click tolerance, multiple pages/staves, keyboard/focus, responsive
    resize and marker alignment at Fit/100%/zoom. Arbitrary unsupported pixel
    positions still fail safely and use Advanced exact placement if needed.
    Mixed-size heads in one OSMD graphical entry remain the disclosed rendering
    limitation; canonical size/timing is preserved, with no cue/grace workaround.
    No song-specific coordinates, drag-and-drop or composition behavior was added.
