# Project State and Decisions

Recorded: 2026-10-14. Prepared under GOV-03; updated under GOV-06 limited
documentation and repository preparation authorization.
This record summarizes approved requirements and available evidence; it does not
amend the Product Constitution or grant technical or functional acceptance.

## Authority and status vocabulary

[PRODUCT_CONSTITUTION.md](PRODUCT_CONSTITUTION.md),
[ACCEPTANCE_CRITERIA.md](ACCEPTANCE_CRITERIA.md), and [AGENTS.md](AGENTS.md)
govern this record. The Product Owner approves requirements and functional
acceptance; the Technical Lead owns architecture, scope and technical review.

- IMPLEMENTED: code exists; this alone establishes neither correctness nor acceptance.
- TESTED: recorded checks passed within the stated scope and environment. Historical
  results are not fresh verification of the proposed baseline.
- TECHNICALLY VERIFIED: reserved for completion of acceptance Gates 1-3,
  including recorded Technical Lead review. No new such status is asserted here.
- PRODUCT OWNER ACCEPTED: explicit Product Owner approval, limited to its stated
  scope. It does not by itself establish completion of the other gates.
- PENDING: evidence, review, verification or acceptance remains outstanding.

These are evidence labels, not replacements for the mandatory gate/status
vocabulary. Overall baseline preparation remains IN PROGRESS. Final ACCEPTED
requires all applicable gates, not just automated checks or UI approval.

## Approved product architecture

PC-01 through PC-06 establish:

1. Stage 1: Import -> Recognition -> User Correction -> Optional Concert-Key
   Transposition -> Save Canonical Concert Score.
2. Stage 2: Generate instrument-specific written scores from the saved Stage 1
   canonical concert-pitch score only.

The user-corrected, saved Canonical Concert Score is authoritative (PC-03).
OMR is an initial reconstruction, not the source of truth. Corrections must
persist in canonical data, including notes, lyrics/associations, ties and explicit
tie direction. A display overlay alone does not satisfy persistence (PC-02/05).
Stage 2 must not rerun OMR, overwrite Stage 1, discard corrections or couple
independent instrument outputs (PC-04). Approved concert-to-written offsets:
Alto Saxophone E-flat +9, Soprano Saxophone B-flat +2, Tenor Saxophone B-flat +14
semitones. These are approved requirements, not a claim of new implementation.

## Review and Transpose

IMPLEMENTED: Review and Transpose reuse the existing shared correction editor.
Review is correction-focused. Transpose reads a saved source snapshot, displays
a read-only Original and an independent editable My Score result, and retains
Key, Instrument, Source Key confirmation, direction and Apply controls. Later
unsaved Review edits do not silently replace the selected saved source.
Saving the result must use its latest edited revision without overwriting the
source. Opening a retained result explicitly is distinct from automatic promotion.

IMPLEMENTED: UX-03C removes the redundant Advanced editing disclosure in both
modes. Select, Note, Lyrics, Tie and More remain compact. Common actions are
contextual; More retains correction measure, explicit positioning, ownership,
technical properties and the established Advanced Review route. Rendering,
independent Fit/Zoom, history, Save and editing semantics were not changed by
UX-03C. No new click-to-insert, drag or direct lyric behavior was introduced.

PRODUCT OWNER ACCEPTED, UI scope only: the GOV-02 task explicitly states that
baseline preparation follows Product Owner acceptance of UX-03C. UX-03C also
records acceptance of UX-03B except for the disclosure subsequently removed.
This conversation is the acceptance provenance; there is no separate signed
local acceptance report or recorded UX-03C Technical Lead approval available.
Do not extend this UI acceptance to recognition accuracy, backend algorithms,
all persistence cases or Stage 2. Gate 3 evidence remains PENDING/unverified.

TESTED: UX-03C recorded 270 frontend tests passing, zero failures/skips, lint,
build and diff-check PASS. Build retained a large-bundle warning. Frontend tests
use controlled React/API harnesses; they do not establish browser behavior.
Real Firefox Save/download/reimport fidelity was not verified in that execution.
That execution limit does not negate the explicit P0.6B acceptance below.

### Product Owner confirmations in GOV-06

| Functionality | Status and scope |
| --- | --- |
| PDF/Image import and OMR Recognition | IMPLEMENTED; duration accuracy issues deferred |
| Supported corrections, Notes, Lyrics, Tie Up/Down | IMPLEMENTED |
| Tie Up/Down, Undo/Redo, MusicXML Save/Download/Reimport | PRODUCT OWNER ACCEPTED under P0.6B |
| Corrected MusicXML export | IMPLEMENTED and PRODUCT OWNER ACCEPTED within verified Stage 1 scope |
| Concert-Key Transposition | IMPLEMENTED with existing automated and UI verification evidence |
| Transposed-score MusicXML export | IMPLEMENTED |
| UX-03C simplified editing interface | PRODUCT OWNER ACCEPTED |
| Transposed-score PDF Export | NOT IMPLEMENTED |
| Stage 2 Alto/Soprano/Tenor saxophone transposition | NOT IMPLEMENTED |

GOV-06's explicit Product Owner statement is the acceptance provenance for
P0.6B and corrected export. No additional browser observations, broader
functional acceptance or Technical Lead sign-off are inferred.

## Concert-Key implementation

IMPLEMENTED: backend inspection and confirmed Concert-Key transposition APIs,
frontend client, independent result workspace and synthetic regression tests
are present in the uncommitted tree. Source major/minor selection is explicit
when absent; suggestions require confirmation. This remains optional Stage 1
Concert-Key work, not Stage 2 instrument generation.

TESTED, historical evidence: [CONCERT_KEY_TRANSPOSITION.md](CONCERT_KEY_TRANSPOSITION.md)
records 787 backend and 240 frontend tests for its checkpoint (frontend excluded
the then-private standalone fixture test).
[S2A_02_UNIFIED_WORKSPACE.md](S2A_02_UNIFIED_WORKSPACE.md) later records 788 backend
and 250 frontend tests, including edited-result API export/reimport and the full
frontend fixture suite. Subsequent UX-03C records 270 frontend tests. Different
counts describe different checkpoints, not a current backend rerun.

GOV-06 confirms existing Concert-Key automated and UI verification evidence.
PENDING: Technical Lead approval of the current mixed implementation and any
Concert-specific benchmark/functional acceptance beyond the explicit scope above.
Actual Concert-result downloaded-file reopen was not verified by the recorded
S2A/UX executions; that limitation does not negate P0.6B Stage 1 acceptance.
The approved `concert-cungdemtinmung.musicxml` benchmark was unavailable in the
S2A-02 report; `review-cungdemtimung.musicxml` is not an approved substitute.
Older report layouts/labels are historical and may differ from the current UI.
TECHNICALLY VERIFIED and broader functional acceptance are not established.

## Tie direction and persistence

IMPLEMENTED: existing tie creation, removal and explicit Up/Down controls remain.
PC-02/05/06 require preservation of selected endpoints, unrelated relationships
and explicit direction through corrections, Undo/Redo, canonical Save and
export/reimport. Optional checks must not override user-confirmed notation.

TESTED, bounded evidence: S2A-02's synthetic backend integration edits direction
and Small Note state, exports/reopens scratch files and checks relationship
identities, directions and original-source preservation. Current frontend
regressions cover command dispatch, history, current-revision exports and
source isolation. These do not certify all real scores or native downloads.

PRODUCT OWNER ACCEPTED under P0.6B: Tie Up/Down, Undo/Redo and MusicXML
Save/Download/Reimport, confirmed in GOV-06. Corrected export is accepted within
verified Stage 1 scope. PENDING/unverified beyond that scope: unusual multi-system
tie geometry, external-consumer interpretation and full benchmark fidelity.
Historical tie reports contain limitations and superseding sections; preserve
them as evidence rather than assuming every historical claim is current.

## Stage 2 instruments

Approved architecture/offsets are recorded above and are not reopened.
Stage 2 Alto/Soprano/Tenor saxophone transposition is NOT IMPLEMENTED, as
explicitly confirmed in GOV-06. Instrument choices in the current Concert
workspace are unavailable/disabled except Concert.
Do not treat Concert-Key Apply or disabled instrument options as implemented
Stage 2 functionality.

## Known OMR duration-recognition defect

PENDING: duration-recognition/source-fidelity debugging resumes after the UI
phase and baseline review. The known reported duration defect is not resolved
or accepted by the UX work.
[Half-note diagnostic](backend/PHASE4F1_SOURCE_FIDELITY_HALF_NOTE_DIAGNOSTIC.md)
establishes a specific source A4 half note at the lyric location identified in
that report, and adjacent small upper C5 half note, absent from the
persisted recognized graph before MusicXML export. The following eighth-note
chord survives. The internal recognition step responsible is unknown.
This is evidence of an upstream omission for that captured case, not proof of
the cause of every reported duration discrepancy.
[Small-note RCA](backend/P0_3_SMALL_NOTE_REGRESSION_RCA.md) also separates upstream
recognition from downstream display classification. Do not infer duration or
invent missing content from meter, visual size or test counts (PC-01/06).
No recognition investigation or fix is authorized by GOV-06. Required regression
verification is not a new recognition-accuracy investigation.

## Local user artifact policy

PO decision in GOV-05, reaffirmed in GOV-06: all user-imported PDFs/images and
resulting MusicXML/PDF files from Recognition, Correction, Save, Export or
Transposition remain local and must not be committed to GitHub. Users are
responsible for copyright compliance when sharing files; copyright enforcement
is outside application scope. This policy does not change application Save/Export.

Preserve without editing, deletion, relocation or replacement:

- `review-cungdemtimung.musicxml` and dependent
  `frontend/tests/standalone-ties.test.mjs`: untracked; exclude from checkpoint.
- `backend/tests/music/fixtures/p05_benchmark_raw.musicxml` and dependent
  `backend/tests/test_p05_small_note_preservation.py`: already tracked, unchanged.

The native P05 recognition export conflicts with a GitHub-bound snapshot.
Omitting it from staging or adding ignore rules does not remove an inherited
tracked file. Removing only its fixture breaks its dependent test. GOV-06
authorizes neither index/history changes nor test changes. Stop resolution at
this documented blocker; leave both tracked files intact. Earlier-history and
publication disposition remain outside this task.

## Baseline preparation and next decision

GOV-02 found 48 preexisting changed/untracked files: 21 tracked modifications,
27 untracked, nothing staged. HEAD was `2942913` (accepted Stage 1 editor
checkpoint). [BASELINE_MANIFEST.md](BASELINE_MANIFEST.md) enumerates those files
and these two new governance records separately. Mixed frontend changes,
Concert-Key backend/API scope, fixture provenance, historical report status and
README claims require review before an exact staging plan is authorized.

GOV-04 recorded 788 backend and 270 frontend tests, lint, build and diff-check
PASS. The sandboxed backend attempt timed out in the test-client portal; the
same suite passed outside the sandbox. Those tests included local artifacts
and do not verify a future artifact-free candidate tree.

PC-07 requires regression protection; PC-08 reserves review/acceptance authority.
GOV-06 updates only the two baseline documents and outdated README status and
reran all required checks without weakening tests: 788 backend and 270 frontend
tests PASS, lint/build/diff-check PASS. Exact commands and warnings are recorded
in BASELINE_MANIFEST.md's GOV-06 verification section. Historical reports remain
unchanged. NO-GO for staging/commit pending the tracked-artifact decision,
Technical Lead scope review and explicit Product Owner authorization.
