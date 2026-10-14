# P0 Scanner Correction Editor continuation

2026-10-05. Continued from the interrupted working tree without resetting,
restoring, cleaning, stashing, staging, committing or pushing. Browser acceptance
is pending; canonical/XML and component regressions are passing.

1. **Recovered state:** master was already ahead of origin by one commit, with
   19 modified tracked files and 23 untracked files. Initial `git diff --check`
   passed. Earlier Phase 4F/4F.1 changes include visual selection, lyrics, source
   evidence/structure, workspace containment and the accepted source-system
   engraving adapter. There is no separate interrupted-task commit or snapshot;
   exact authorship within a shared file cannot be proved. Feature-specific
   fields and the two P0 components reasonably identify the partial P0 work.
2. **Previously present P0 work:** explicit-onset insertion and cursor bracketing;
   positioned-event and source-confirmation sidecars; independent visual
   size/timing controls; written-accidental patching; scoped confirmation API and
   Verify policy. These were partial, not accepted as complete. Position insertion
   had an unconnected component; confirmation lacked normal UI; measure moves
   and the right-pane switch were absent. Baseline frontend build/lint passed;
   an overfill wording assertion failed. Restricted backend tests stalled before
   application execution in Starlette TestClient; outside-sandbox tests work.
3. **Continuation:** connected normal position insertion and source confirmation;
   added bounded explicit measure/voice/staff ownership; connected same-pane
   transposition; corrected positioned-note deletion/chord promotion; made
   source-confirmation invalidation persist until explicit confirmation or Undo;
   rejected technically malformed placement contexts; added regression coverage.
4. **Files edited in this continuation:**
   `app/api/v1/reviews.py`, `app/music/review/{models,patcher,service,confirmations}.py`,
   `tests/test_p0_scanner_editor.py`; frontend
   `src/components/{RecognitionReview,VisualNoteEditor}.tsx`, `src/pages/Home.tsx`,
   `src/utils/visualReview.ts`, `tests/{review-lifecycle,visual-review}.test.mjs`;
   this report. Paths for backend code are relative to backend. Existing
   `MusicalPositionEditor.tsx`, Document/model/API/type work, renderer files and
   all other prior changes are retained.
5. **Canonical model:** preserved XML remains the only musical authority.
   Explicit onset insertion is projected back to measure/voice/staff/onset.
   `EventMove` specifies the same ownership fields. Sidecars travel through
   bounded snapshots without writing review IDs/decisions into MusicXML.
6. **XML patches:** position insertion brackets an explicit stream with exact
   backup/forward movements, or joins one unique compatible chord. Other event
   onsets stay unchanged. Positioned duration/grace edits compensate advancement;
   deletion preserves cursor time and transfers positioning to a promoted chord
   leader. Ownership moves retain the original note/lyrics/opaque attributes and
   adjust duration units for destination divisions; technical/context-dependent
   cases fail atomically. No meter padding, inferred notation or automatic spill.
7. **API:** retained `EventAdd.onset`, `written_accidental`, and revision-checked
   `POST /{id}/diagnostics/confirm-source`. Added revision-checked
   `POST /{id}/events/{event_id}/ownership` with measure_id/onset/voice/staff.
   Existing property/tie/Verify/export/transpose APIs remain in use.
8. **Visual editor:** Visual Review offers a musical measure selector and Add at
   musical position, including empty measures, with named durations, pitch,
   accidental, independent size/timing and explicit voice/staff. Note controls
   expose properties and a destination measure/position/voice/staff command.
   Users choose musical labels; identifiers are internal transport values.
9. **Insertion:** position choices are measure start, existing onsets or explicit
   quarter-note units. No meter-derived completion or pixel-derived onset.
   Missing voice/staff, unrepresentable fractions, competing occupancy, broken
   chords, unknown/negative timelines and mid-measure context changes fail safely.
   Matching same-voice/onset/duration notes form a chord; independent timing uses
   an explicitly chosen secondary voice. Overflow stays in the chosen measure.
10. **Normal/Small versus Grace:** Small writes visual type/notehead attributes
    while retaining ordinary duration. It never creates `<grace>` or `<cue>`.
    Timing is an independent control. Shared-chord duration/grace changes have
    their existing documented group scope; staff/size are per note.
11. **Ownership:** simple duration-bearing pitched notes can move to an explicit
    position/staff/voice in the same part, including separating a chord member.
    Existing notes keep their onsets. Cross-part moves, grace/cue moves, ties,
    opaque notations, beams, instruments and tuplets are rejected by this bounded
    command rather than guessed. Secondary voice assignment is supported; this
    is not a full independent-part/score-structure editor.
12. **Ties:** normal select-source → Tie → highlighted compatible target and
    Remove tie reuse the existing explicit endpoint engine. Both `<tie>` and
    `<notations><tied>` survive; matching pitch alone creates nothing. Invalid
    endpoints remain technical blockers. Existing conservative adjacency and
    expected-meter cross-barline limits remain; unusual-boundary tie editing is
    not expanded by this milestone.
13. **Source-confirmed Verify:** only the narrow measure-overfill, voice-underfill
    and measure-duration-mismatch allowlist is eligible. A user supplies an
    explicit handling note for the displayed measure. Diagnostic identity,
    affected measure/context fingerprint and revision are retained separately
    from notation. Relevant edits mark decisions stale; ordinary edit-back cannot
    reactivate them. Undo can restore the exact decision/content snapshot but
    never restores VERIFIED. Technical failures and unresolved candidate issues
    still block. Verify retains fresh final source-comparison confirmation.
14. **Right pane:** one score viewer switches Corrected/Transposed; original source
    remains on the left. Transposed is read-only, without corrected-pitch identity
    bindings/cursor/editor. Corrected layout is passed only for source grouping.
    The extra reviewed-result viewer below the workspace is removed. Direct
    non-review MusicXML preview retains its prior route.
15. **Verified-master safety:** Home sends every offset with the current verified
    review revision. Backend transposes a locked corrected-master snapshot and
    never replaces it. Literal +2 then +3 regressions assert master → +3, not
    compounded output. Corrections/Undo/Redo clear verification and derived result.
16. **OSMD:** canonical Small/duration fidelity and XML round trip pass. Mixed-size
    heads sharing a graphical entry remain an explicitly disclosed renderer
    limitation. No glyph-only transform, chord reorder, invented voice, cue/grace
    workaround or renderer migration was introduced. Accepted source grouping
    and Fit/zoom algorithms are unchanged; regression groups remain 1–5/6–10/11–17.
17. **Generalized real acceptance:** synthetic A4 Half Normal plus C5 Half Small
    Duration-bearing at the same explicit position, in source-selected voices,
    followed by an A→A tie, Verify, +2/+3 transposition and XML reimport passes.
    Separate tests cover same-voice chord insertion and ownership separation,
    faithful overfill confirmation/export and technical-error rejection. No
    song-specific logic or fresh recognition was used. Real Cùng Đem Tin Mừng
    browser/source comparison is not claimed passed by these tests.
18. **Backend:** final full suite: 656 passed, two existing dependency warnings.
    Command: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests -q`
    from backend, outside the sandbox. Restricted runs were interrupted after a
    stack trace confirmed TestClient portal startup blocking. Autoload was
    disabled to avoid an unrelated installed ROS plugin import failure.
19. **Frontend:** final regressions: 79 passed using
    `node --test --test-isolation=none tests/*.test.mjs`. Component callbacks,
    API lifecycle, source-confirmation form, empty-measure insertion, ownership,
    tie editing, same-pane switching and accepted renderer/zoom contracts pass.
20. **Lint/build:** `npm run lint` and `npm run build` pass. Existing large OSMD
    bundle warning remains. No browser rendering/focus/download proof is inferred
    from semantic/SVG doubles.
21. **Whitespace:** final `git diff --check` passes. All changes remain unstaged.
22. **Remaining bounded acceptance gaps:** real-browser empty-measure selection,
    mixed-size visual identity/tie attachment, source comparison, ownership,
    Corrected/Transposed switching, downloads and trusted source grouping under
    resize/zoom must be checked. Direct empty-space click insertion is not claimed;
    normal musical selectors provide explicit safe placement. Broader cross-part,
    relationship-bearing moves and unusual-boundary ties remain support limits,
    not silently accepted operations.
23. **Recommendation:** browser-accept the bounded P0 workflow before checkpointing.
    Use source evidence to choose chord versus secondary voice, inspect exported
    size/duration/tie XML, confirm faithful diagnostics only after comparison,
    verify and transpose +2 then +3, switch back and edit to prove invalidation.
    Recheck 1–5/6–10/11–17 grouping without changing its adapter. Next separately
    scoped work can address supported unusual tie boundaries, relationship-aware
    ownership or mixed-size rendering; no generalized glyph reconstruction,
    drag-and-drop or composition work was begun.
