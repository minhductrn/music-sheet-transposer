# Task 05 — Stabilize & Release

Date: 2026-10-29. Status: **ACCEPTED**. Gates 1–3 are technically verified and the Product Owner explicitly completed Gate 4 on 2026-10-29. The application source remains separately accepted. Product Owner authorization covers preparation, packaging, integrated verification and English documentation. The Product Owner has now authorized closing Task 05 and its GitHub checkpoint.

## Frozen application baseline

Accepted source: `945821c55cb7760a7200329ebbea7ed79055ffd2` on `master`. This source checkpoint is already on GitHub. Preserve its application behavior and all earlier archives. Package application sources from that commit, rather than copying the dirty working tree. Add only reviewed Task 05 packaging/documentation files to the release overlay and record their hashes separately. Do not include legacy changes, personal inputs, generated evidence, repository metadata or unsaved user data. Reuse the validated local runtime only after checking its hashes and ABI.

Initial candidate: `music-sheet-transposer-1.0.0-rc1`. Final candidate: `music-sheet-transposer-1.0.0-rc2`; it has identical application/runtime hashes and finalized English guide wording. See the verification report for measured status. Record source commit, package version, source acceptance, release acceptance PENDING, ABI, runtime dependencies, OMR prerequisites and file hashes in the manifest. Do not reuse the historical hardcoded checkpoint in build_task04.py. Source acceptance must not imply acceptance of a new release package.

## Work and acceptance evidence

1. Scope audit: verify the commit and protected-file hashes; identify the exact application tree and documentation overlay. Preserve unrelated changes and every existing package.
2. Build: create a new immutable standalone archive and checksum. Refuse existing targets. Verify archive extraction, package hashes and Python ABI. Runtime execution must not import application code from the source checkout or require Node/Codex.
3. Integrated release test: use an isolated extracted bundle, separate browser context and an unused local port. Never use sessions with unsaved user edits. Exercise MusicXML import and PDF recognition, correct the working document, save/reopen it, transpose Concert, generate Alto/Soprano/Tenor, edit independently and export MusicXML/PDF. Confirm original bytes and other outputs remain unchanged.
4. Persistence test: save Concert and instrument documents, close the owned browser/server, restart the same package and reopen saved files. Compare semantic contents (notes, duration, voice, staff, lyrics, chord symbols, ties/slurs and supported properties). Temporary sessions/history are not recovery artifacts.
5. PDF test: inspect A4 dimensions, one-page fit and multi-page output, full content coverage and a rendered page. Confirm export changes no musical data.
6. Editor regression: cover Compare/Edit Only in both stages, per-note Small in a chord, Undo/Redo, supported tuplets, verse entry, chord/text editing, dismissible notices and explicit composer-header conversion.
7. OMR evidence: use an explicitly identified local sample and installed engine once; record result, warnings, profile and source hash. Separately replay a known OMR result for deterministic editor checks. A mock is not evidence of engine accuracy. Do not invent missing notes or claim universal recognition accuracy. No autonomous retries or new model installation.
8. Documentation: ship USER_GUIDE_EN.md, launch instructions, limitations and recovery guidance consistent with the actual package. Historical documents remain clearly labeled; do not silently rewrite unrelated historical records.
9. Technical Lead review: review final artifact and evidence under PC-01 through PC-08 and the repository acceptance gates. Present remaining failures/skips and a concrete package for Product Owner acceptance.
10. Release checkpoint: only after Product Owner acceptance and authorization, commit/push the Task 05 release checkpoint. Do not publish private inputs or runtime archives to GitHub by default.

## Environment evidence and current progress

- The accepted commit was read using local Git through the existing folder connection: `945821c55cb7760a7200329ebbea7ed79055ffd2`.
- Direct folder access works. `wsl.exe -d Ubuntu --exec /usr/bin/ls -la /home/dtran/music-sheet-transposer` failed with `Wsl/Service/E_UNEXPECTED` and `Catastrophic failure`.
- Governance, the existing builder/launcher and Task 04 guide were read. The old Task 03 restart test predates current PDF dialogs and Stage 2 toolbar semantics and must not be reused unchanged as release proof.
- At initial preflight, only English scope and guide drafts existed. Packaging and verification are now complete as documented below; that early state is retained here as historical context.
- The Product Owner confirmed all work was saved and explicitly permitted WSL restart. `wsl.exe --shutdown` succeeded; Ubuntu command execution recovered. Previously running local servers were stopped by that authorized restart.

## Limits retained in this stabilization task

No new notation features, automatic margin engine, nested/cross-measure tuplets, multi-part expansion, advanced clipboard/selection transposition, broad UX redesign, AI agents, LLM calls, Docker or cloud deployment. Existing warnings do not authorize silently changing music. Existing accepted readable instrument registers are retained; this task does not rewrite instrument requirements.

## Subsequent roadmap requested by the Product Owner

After Task 05 acceptance, prepare bounded designs and verification plans in this order:

1. Content-aware PDF top/bottom/left/right margins, with safe print limits and explicit one-page versus multi-page behavior.
2. Extended notation/structure: nested or cross-measure tuplets, multi-part instrument handling and multi-part/staff measure operations. Each needs persistence and relation-preservation evidence.
3. Wider OMR assessment on a varied corpus, reporting specific recognition errors and correction workflows rather than a blanket accuracy claim.
4. Professional UX review and refinement, retaining direct on-score interactions and full editor availability across stages/views.
5. Advanced creative composition on MusicXML: select any supported passage, copy it, paste at an explicit measure/beat/voice/staff, and transpose only a chosen passage by semitones or a target key. PDF inputs first require recognition, user correction and a successfully saved MusicXML document. The original is read-only; users own the arrangement.

Before advanced-composition implementation, resolve insert versus overwrite behavior, partial-measure selection, cross-boundary ties/slurs, lyric/chord copying, local key boundaries and destination conflicts. Preserve notes outside the chosen range; preview the affected range; support one Undo operation and save/reopen. No automatic reharmonization or inferred musical changes. Musical rhythm warnings remain advisory and belong in explicit validation, rather than preventing creative editing. Technical representation failures must be explained without silently overwriting music. These are recorded requirements, not implemented features or completed milestones.

## Final verification and handoff — 2026-10-29

### Candidate and reproducibility

- Version: **1.0.0-rc2**. Application source commit: **945821c55cb7760a7200329ebbea7ed79055ffd2**.
- The builder uses Git archive from that exact accepted commit, not application code from the dirty checkout. Its Task 05 guide/builder overlay hashes are recorded separately.
- Final archive: `frontend-v2/evidence/task05/music-sheet-transposer-1.0.0-rc2.tar.gz`, with adjacent `.sha256` file.
- Installed independent directory: `/home/dtran/music-sheet-transposer-releases/music-sheet-transposer-1.0.0-rc2`.
- The final archive contains 866 hashed package files. Ninety-nine application-source inputs were verified against the accepted Git archive; backend bytes also match it directly. No .git, node_modules, private evidence or legacy frontend directory is shipped.
- RC1 is retained. RC2 changes documentation/version metadata only; backend, web and runtime file hashes are identical to RC1, which received the initial real-OMR test. RC2 received its own restart checks and full final browser run.
- All 619 protected preexisting file hashes remain unchanged; no application-source diff from the accepted commit was introduced.

### Executed checks

- Production build and TypeScript: PASS from the frozen accepted tree. ESLint and TypeScript also passed for the adjusted host verification tests.
- Final packaged browser run: **106 passed, 0 failed, 0 skipped**. Private fixture cases were explicitly enabled on this host. Results are local in `frontend-v2/evidence/task05/final-browser-results.json`.
- Final restart integration: PASS. Concert key change, Alto/Soprano/Tenor generation and independent edits preserve the source. After stopping and restarting the owned server, all four saved MusicXML documents reopen byte-identically. Temporary review sessions are correctly absent after restart.
- One real Audiveris PDF recognition attempt: HTTP 200, 85.8 seconds, 131 mapped events, 9 warnings. The draft accepted a user-directed correction, exported/reopened it and preserved original PDF bytes. This checks the pipeline, not recognition perfection or a complete user score comparison. There was no automatic recognition retry.
- A4 PDF one-page and multi-page tests: PASS. Complete unique lyric coverage and A4 dimensions were checked; rendered one-page and final multi-page outputs were inspected. PDF export remains a print operation without mutating XML.
- Package guards: PASS for integrity/ABI, existing-output refusal, occupied-port refusal, a deliberately invalid test package and the archive checksum.
- The accepted-source baseline already recorded 1,147 backend tests passed (3 skipped) and 56 frontend unit tests passed. Those are baseline results, not newly rerun Task 05 backend/unit counts. Task 05 changes packaging, documentation and test maintenance, not application behavior.

### Initial failures and test maintenance

The first broad run had 97 passed, 2 failed and 7 skipped. A separate private-fixture run had 8 passed and 2 failed. Four tests contained stale assumptions: a Vietnamese suggestion assertion after the accepted English UI change; selecting disabled Direction before choosing an instrument; expecting a real PDF dialog in the simulated demo; and omitting the new PDF confirmation in the instrument editor. These assertions/gestures were updated without changing application code. Targeted reruns passed, followed by the clean 106-test final run above. Earlier failure evidence is retained locally.

### Technical Lead review and remaining boundaries

PC-01: real OMR remains a draft with warnings and no invented content. PC-02/PC-06: existing direct user-controlled editing is preserved; no new feature scope was inserted. PC-03/PC-05: saved canonical data and export/reopen behavior were verified. PC-04: instrument outputs remain independent and do not rerun OMR. PC-07: the final packaged regression run passed. PC-08 and acceptance Gates 1–3 are recorded here; only the Product Owner can accept this release candidate at Gate 4.

Remaining boundaries: Ubuntu/Python ABI and local OMR prerequisites; the OMR-enabled launcher currently requires its local engine/models even for a MusicXML-only session; no automatic installation; no recovery promise for unsaved edits/history; fixed 12 mm PDF margins; small print for long one-page output; existing part/staff and nested/cross-measure tuplet limits; no advanced passage clipboard/transposition yet; no production-deployment or universal OMR-accuracy claim.

### Start and recovery

The standalone candidate is running at **http://localhost:5180**. In Ubuntu WSL, restart it with:

```bash
python3 -B /home/dtran/music-sheet-transposer-releases/music-sheet-transposer-1.0.0-rc2/start.py --port 5180
```

Use `--check` instead of `--port 5180` for integrity/ABI verification. The launcher refuses an occupied port; do not launch a second instance there. Save all desired Concert and instrument MusicXML documents before closing. After restart, reopen those saved files; temporary sessions and Undo history do not survive.

English operating instructions: [USER_GUIDE_EN.md](USER_GUIDE_EN.md). The subsequent roadmap above records requested work without implementing it. No Task 05 commit, push or release tag has been created. Product Owner release acceptance is the next gate before the authorized GitHub checkpoint step.

Archive SHA-256: `65e5797a6df645dbd0a3efe1a0f347dda2c4777ad1a20922994f0f1ccfbb1058`.


## Product Owner acceptance — 2026-10-29

The Product Owner explicitly confirmed closing Task 05 after receiving the package and documentation. Status is now **ACCEPTED**, including Gate 4. This supersedes the pending release labels in the historical verification narrative above, without changing the recorded test results or extending feature scope.

The accepted artifact is exactly `music-sheet-transposer-1.0.0-rc2.tar.gz`, SHA-256 `65e5797a6df645dbd0a3efe1a0f347dda2c4777ad1a20922994f0f1ccfbb1058`. Its existing version/name and archive bytes are retained to match the downloaded and verified artifact. It has not been rebuilt or relabeled as another version. The manifest and embedded guide describe build-time pending status; [TASK_05_ACCEPTANCE.json](TASK_05_ACCEPTANCE.json) is the authoritative subsequent acceptance record for this exact hash. A future rebuilt artifact remains pending until independently accepted.

The GitHub checkpoint covers Task 05 documentation, packaging/verification tools, the acceptance record and four test-only updates needed for the already accepted UI. Application code remains frozen at `945821c`; protected files, personal samples, local archives/runtime and unrelated legacy changes are excluded. No release tag, public binary upload or production deployment is implied.

The subsequent roadmap remains recorded for later bounded design/implementation authorization. Closing Task 05 does not implement automatic PDF margins, nested/cross-measure tuplets, multi-part expansion, broad UX redesign, passage copy/paste or selected-passage transposition.
