# Phase 4E overfill investigation

The browser reports one blocking measure-overfill error and seven warnings.
Verification must remain blocked. No validator, insertion algorithm, recognition,
recovery, transposition or frontend behavior was changed by this investigation.

## Evidence boundary

The backend health endpoint responded. After the browser review ID was supplied,
read-only probes on 2026-10-04 returned the following:

- Direct `GET http://127.0.0.1:8000/api/v1/reviews/{id}`: 404.
- Through Vite, `GET http://127.0.0.1:5173/api/v1/reviews/{id}`: the same 404.
- Direct `GET .../musicxml?original=true`: the same 404.

All returned Uvicorn JSON: `{"detail":"Review session was not found or has expired. Import the source again."}`.
The real corrected and original XML therefore remain unavailable from the running
backend. The real event ledger, baseline extent and recognition-versus-manual-placement attribution
remain unconfirmed. No restart, close, correction or validation mutation was sent.

Reviews live in process memory with a configurable fixed lifetime (default 3600
seconds). An open browser retains its last review payload even when that backend
session expires or is lost. The 404 alone cannot distinguish expiry, prior close,
reload/restart or a different backend process; no particular cause is established.

The port-5173 URL is intentional. `frontend/src/services/api.ts` uses relative
`/api/v1` paths; `frontend/vite.config.ts` proxies `/api` to `VITE_BACKEND_URL`,
defaulting to `http://127.0.0.1:8000`. The returned Uvicorn JSON establishes that
this 404 comes through the backend proxy, rather than a missing Vite route.
Changing the browser fetch to an absolute backend URL is not a fix for a missing
review session. This runtime session failure is separate from musical overfill.

Preserve browser-held work with **Download corrected XML**, which uses its retained
Blob without a backend fetch. Keep the tab open until that file is saved; reload,
close, or server-gated verified export cannot recover missing backend session data.
Inspect that saved XML next, plus the original draft/source, to finish the real
measure-ownership investigation. No automatic replacement session was created.

The previously reported A4 at onset 0 with duration 2 ends at 2. Its following A4
at onset 2 with duration 1/2 ends at 5/2. If these remain the current events,
measure extent 7/2 requires an additional event end or forward/cursor extent at
7/2. The pair alone exceeds a measure whose expected duration is 2. Neither the
extra contribution nor correct source measure ownership can be inferred from the
warning count. A tie never merges the two duration-bearing notes.

## Exact synthetic reproduction

`tests/test_review_overfill_diagnosis.py` runs the current review API without OMR.
Its baseline measure contains an A4 of duration 1/2 and a rest of duration 1,
with extent 3/2. A human insertion adds A4 duration 2 before that A4:

| Event | Onset | Duration | End | Voice/staff | Origin | Tie |
| --- | --- | --- | --- | --- | --- | --- |
| A4 | 0 | 2 | 2 | 1/1 | manual addition | start to following A4 |
| A4 | 2 | 1/2 | 5/2 | 1/1 | baseline import; manually added tie stop | stop |
| Rest | 5/2 | 1 | 7/2 | 1/1 | baseline import | none |

The rest is a synthetic stand-in, not a claim about the PDF or real review.
The validator reaches `max(0 + 2, 2 + 1/2, 5/2 + 1) = 7/2`, compared with
`2 × 4/4 = 2` expected quarter beats. In this single sequential voice the same
result is `2 + 1/2 + 1`. The general validator uses maximum extent, not a sum
of simultaneous chord notes or parallel voices. The fixture also reproduces the
reported measure-1 underfill and two voice warnings, measure-4 empty warning,
and measure-17 extent and voice warnings: exactly one error and seven warnings.

Adding the tie preserves all durations/onsets and every diagnostic. Verification
returns 409. Undo insertion restores 3/2; redo restores 7/2. Tie-only undo/redo
does not change timing. Other measures remain unchanged. Separate regressions
confirm chord insertion does not double-count duration and backup/forward nodes
remain unchanged with any resulting timing error exposed.

This proves that an ordinary, correctly scoped insertion can reproduce the
symptoms. It does not prove the real baseline contained those events or that
manual insertion was musically assigned to the correct measure.

## Sequential insertion and timing-event limits

`review/patcher.py:add_event` inserts into the requested measure's existing XML
children, before/after the anchor's chord group or before the right barline.
The anchor must belong to that measure. It never moves notes into another
measure, modifies barlines, or distributes a duration across a barline.

`review/importer.py` advances its cursor for non-grace, non-chord notes, retains
the leader onset for chord members, applies forward/backup durations, and resets
the cursor for each measure. Consequently a sequential addition can leave notes
past the meter boundary inside that same measure. It can also shift subsequent
voices in that measure: retaining a backup's original duration does not restore
a voice's old onset after an earlier addition. Preservation of timing-event XML
is intentional; automatic multivoice rebalancing is outside this editor's scope.
The regression demonstrates this effect and its blocking overfill diagnostic.

The existing rhythm validator reports `measure_overfilled` as ERROR after an
insertion and in semantic-evidence reviews. No overflow is hidden or marked valid.
Insertion/timing repair does not automatically establish musical correctness.
Unknown ownership, barline repairs and arbitrary onset/backup/forward edits can
require an external notation editor. No automatic cross-barline movement was added.

## Remaining source comparison

For an available review, read its JSON and both corrected and `?original=true`
MusicXML using its review ID. For this unavailable session, use saved browser-held
corrected XML and the original draft/source; unsaved session provenance cannot
be recovered from the backend. Inspect every note/rest/chord/grace event and backup/forward in the
affected measure, together with preceding/following measures, divisions, meter,
voices/staves, import provenance and manual fields. Replay the XML cursor and
compare baseline versus corrected event ownership. To distinguish recognition
structure from user placement, compare the original PDF barlines and the two
A notes with those XML measures; inspector labels alone cannot establish this.

A two-quarter-beat note at onset zero fills a two-quarter-beat measure. Its tied
half-beat successor would normally start at onset zero in the next measure if
those source barlines and meter are confirmed. This is a conditional musical
interpretation, not an instruction to move events without checking the source.
Do not shorten, merge or delete valid musical events merely to remove an error.

## Warning classification and checkpoint

- Measure 1 extent 3/2 and measure 17 extent 1/2 are plausible complementary
  pickup/final partial measures because their extents sum to the expected 2.
  Source confirmation is required; missing recognition events remain possible.
- The two measure-1 voice-underfill warnings describe separate voice coverage,
  not two extra duration contributions. Partial voices may be intentional.
- Measure 4 with no notes/rests requires source review for a missing rest/event,
  erroneous measure structure, or intentional empty representation. It must not
  silently be treated as a full-measure rest.

All warnings remain visible; the genuine overfill remains blocking. No generic
Phase 4E bug was demonstrated, so no production fix was made. The engine is
technically ready for a checkpoint: safe correction, visible validation, explicit
verification, corrected-byte transposition/export and undo/redo are covered.
The particular recognized score is not ready for verification until its rhythm
and measure ownership are corrected and compared with the source.

The Phase 4E engine checkpoint is accepted independently of this invalid score.
Remaining work is source-specific musical review; no claim is made that the real
measure-5 cause was established.
For a later Phase 4F planning task, consider explicit source-to-measure mapping
and validated placement/movement in a visual editor. No Phase 4F work began here.
