"""Require corroborated relationships and valid timing before preservation patches."""

from dataclasses import asdict, dataclass, replace
from hashlib import sha256

from app.core.config import Settings
from app.music.recognition.errors import RecognitionError
from app.music.recovery.models import RecoveryCandidate
from app.music.recovery.musicxml import XmlContext, correlate, resolved_pitch, rhythm
from app.music.recovery.omr import parse_omr, register_analysis
from app.music.review.document import Document, ReviewError
from app.music.review.importer import display_size, rational
from app.music.review.models import EventAdd
from app.music.review.patcher import add_event, group, put, size_patch


@dataclass
class RecoveryResult:
    document: Document
    report: dict


def recover(xml: bytes, omr: bytes | None, config: Settings, *, analysis_omr: bytes | None = None) -> RecoveryResult:
    doc = Document.parse(xml, config.review_max_xml_nodes)
    context = XmlContext(doc)
    before = rhythm(context)
    report = {"state": "NO_RECOVERY", "review_required": False, "candidates": [], "diagnostics": [],
              "baseline_sha256": sha256(xml).hexdigest(), "rhythm_before": before, "rhythm_after": before,
              "evidence": [], "auto_recovered": 0, "review_candidates": 0}
    if not config.audiveris_semantic_recovery_enabled:
        report["diagnostics"].append("semantic_recovery_disabled")
        return RecoveryResult(doc, report)
    evidence_sets = []
    for index, contents in enumerate((omr, analysis_omr)):
        if contents is None:
            continue
        try:
            evidence = parse_omr(contents, max_bytes=config.recognition_max_artifact_bytes,
                                 max_expanded_bytes=config.semantic_max_expanded_bytes,
                                 max_members=config.recognition_max_archive_members,
                                 max_nodes=config.semantic_max_xml_nodes)
        except RecognitionError as error:
            report["diagnostics"].extend(i.code for i in error.diagnostics)
            report.update(state="REVIEW_REQUIRED", review_required=True)
            continue
        if index == 1:
            if evidence_sets:
                evidence = register_analysis(evidence_sets[0][0], evidence)
            else:
                evidence = replace(evidence, diagnostics=evidence.diagnostics + ("omr_analysis_baseline_unavailable",))
        if any(e.sha256 == evidence.sha256 for e, _ in evidence_sets):
            report["diagnostics"].append("duplicate_omr_evidence_ignored")
            continue
        evidence_sets.append((evidence, correlate(evidence, context)))
        notes = list(evidence.notes())
        report["evidence"].append({"sha256": evidence.sha256, "version": evidence.version,
                                   "heads": len(notes), "small_heads": sum(n.visual_size == "small" for n in notes),
                                   "possible_small_heads": sum(n.visual_size == "possibly_small" for n in notes)})
        report["diagnostics"].extend(evidence.diagnostics)
    if not evidence_sets:
        report["diagnostics"].append("omr_evidence_unavailable")
    decisions = []
    for evidence, correlations in evidence_sets:
        notes = list(evidence.notes())
        for note in notes:
            if note.visual_size not in ("small", "possibly_small"):
                continue
            if len(decisions) >= config.semantic_max_candidates:
                report["diagnostics"].append("recovery_candidates_truncated")
                report["review_required"] = True
                break
            candidate = _classify(note, notes, correlations, context)
            if any(d in evidence.diagnostics for d in ("omr_unvalidated_version", "omr_analysis_source_mismatch", "omr_analysis_registration_incomplete", "omr_analysis_baseline_unavailable")):
                candidate.confidence = "AMBIGUOUS"
                candidate.diagnostics.append("unvalidated_omr_version_or_registration")
            # A small-head analysis can shrink a previously normal template incorrectly.
            # Independent baseline recognition is supporting evidence, never overwritten.
            if candidate.event_id and analysis_omr is not None and evidence.sha256 != evidence_sets[0][0].sha256:
                base, base_correlations = evidence_sets[0]
                conflict = any(n.visual_size == "normal" and candidate.event_id in base_correlations[n.provenance].event_ids
                               and base_correlations[n.provenance].confidence in ("EXACT", "HIGH")
                               for n in base.notes())
                if conflict:
                    candidate.confidence = "AMBIGUOUS"
                    candidate.diagnostics.append("baseline_analysis_size_conflict")
            decisions.append(candidate)
    patched = set()
    for candidate in decisions:
        key = (candidate.measure_id, candidate.event_id, candidate.anchor_id,
               tuple(sorted((candidate.pitch or {}).items())), candidate.operation)
        if candidate.operation is None:
            continue
        if candidate.confidence not in ("EXACT", "HIGH"):
            continue
        if key in patched:
            candidate.state = "NO_RECOVERY"
            candidate.diagnostics.append("duplicate_proposal")
            continue
        original = doc
        attempt = doc.clone()
        try:
            if candidate.operation == "PRESERVE_SMALL_DISPLAY_SIZE":
                size_patch(attempt, attempt.refs[candidate.event_id], "small")
                attempt.changed = True
            else:
                members = group(attempt, attempt.refs[candidate.anchor_id])
                if any(attempt.text(attempt.child(n, "pitch"), "step") == candidate.pitch["step"]
                       and attempt.text(attempt.child(n, "pitch"), "octave") == str(candidate.pitch["octave"])
                       and rational(attempt.text(attempt.child(n, "pitch"), "alter", "0")) == rational(candidate.pitch["alter"]) for n in members):
                    candidate.state = "NO_RECOVERY"
                    candidate.diagnostics.append("pitch_already_present_in_chord")
                    continue
                recovered_id = f"recovery-{len(patched) + 1}"
                add_event(attempt, recovered_id, EventAdd(
                    measure_id=candidate.measure_id, kind="note", pitch=candidate.pitch,
                    chord_with_id=candidate.anchor_id, display_size="small",
                ))
                x = attempt.refs[candidate.anchor_id].get("default-x")
                if x is not None:
                    attempt.refs[recovered_id].set("default-x", x)
                if candidate.evidence.alter is not None:
                    spelling = {"-2": "flat-flat", "-1": "flat", "0": "natural", "1": "sharp", "2": "double-sharp"}
                    put(attempt, attempt.refs[recovered_id], "accidental", spelling[candidate.evidence.alter])
            checked = rhythm(XmlContext(attempt))
            prior_errors = {(i["code"], i["event_id"]) for i in before[candidate.measure_id]["diagnostics"] if i["severity"] == "ERROR"}
            new_errors = {(i["code"], i["event_id"]) for i in checked[candidate.measure_id]["diagnostics"] if i["severity"] == "ERROR"}
            if (not new_errors.issubset(prior_errors) or checked[candidate.measure_id]["actual"] != before[candidate.measure_id]["actual"]
                or len(attempt.xml()) > config.recognition_max_output_bytes
                or sum(1 for _ in attempt.root.iter()) > config.review_max_xml_nodes):
                raise ReviewError("Recovery failed musical validation.")
            doc = attempt
            candidate.state = "AUTO_RECOVERED"
            candidate.diagnostics.append("timing_preserved")
            patched.add(key)
        except (ReviewError, ValueError):
            doc = original
            candidate.confidence = "AMBIGUOUS"
            candidate.diagnostics.append("patch_validation_failed")
    report["candidates"] = [asdict(c) for c in decisions]
    report["auto_recovered"] = sum(c.state == "AUTO_RECOVERED" for c in decisions)
    report["review_candidates"] = sum(c.state == "REVIEW_REQUIRED" for c in decisions)
    report["review_required"] |= report["review_candidates"] > 0
    report["state"] = "REVIEW_REQUIRED" if report["review_required"] else "AUTO_RECOVERED" if report["auto_recovered"] else "NO_RECOVERY"
    report["diagnostics"] = sorted(set(report["diagnostics"]))
    report["rhythm_after"] = rhythm(XmlContext(doc))
    return RecoveryResult(doc, report)


def _classify(note, notes, correlations, context):
    correlation = correlations[note.provenance]
    matched = context.events.get(correlation.event_ids[0]) if len(correlation.event_ids) == 1 else None
    candidate = RecoveryCandidate(note.provenance, None, "UNCERTAIN", "AMBIGUOUS", "REVIEW_REQUIRED",
                                  correlation.measure_id, matched.event.id if matched else None, None, None, note, correlation)
    explicit_grace = note.chord_kind == "grace-chord" or any(r.kind == "chord-grace" for r in note.relationships)
    if explicit_grace or matched and matched.event.grace:
        candidate.classification = "GRACE"
        candidate.diagnostics.append("explicit_grace_evidence")
        return candidate
    if matched and context.document.child(matched.node, "cue") is not None:
        candidate.classification = "CUE"
        candidate.diagnostics.append("explicit_cue_semantics")
        return candidate
    peers = []
    for peer in notes:
        if (peer.provenance == note.provenance or peer.sheet != note.sheet or peer.system != note.system
            or peer.part != note.part or peer.measure != note.measure or peer.staff != note.staff
            or not note.center or not peer.center or not note.bounds or not peer.bounds
            or len(note.chords) != 1 or len(peer.chords) != 1 or note.chords != peer.chords
            or len(note.stems) != 1 or note.stems != peer.stems
            or abs(note.center[0] - peer.center[0]) > max(note.bounds[2], peer.bounds[2]) * .5):
            continue
        link = correlations[peer.provenance]
        if link.confidence not in ("EXACT", "HIGH") or len(link.event_ids) != 1:
            continue
        anchor = context.events[link.event_ids[0]]
        if anchor.event.grace or anchor.event.kind != "note" or context.document.child(anchor.node, "cue") is not None:
            continue
        peers.append(anchor)
    # All corroborated peers must belong to the same exported rhythmic chord.
    groups = {(p.event.chord_id or p.event.id, p.event.onset, p.event.duration, p.event.voice, p.event.staff) for p in peers}
    if len(groups) != 1:
        candidate.diagnostics.append("no_unique_shared_stem_rhythmic_anchor")
        return candidate
    anchor = peers[0]
    candidate.anchor_id, candidate.measure_id = anchor.event.id, anchor.measure.id
    candidate.classification = "SIMULTANEOUS_VARIANT"
    candidate.pitch = resolved_pitch(note, anchor, context)
    candidate.operation = "PRESERVE_SMALL_DISPLAY_SIZE" if matched else "ADD_SIMULTANEOUS_NOTE"
    candidate.diagnostics.extend(("shared_chord_and_stem", "aligned_heads", "duration_bearing_anchor"))
    strong = (note.visual_size == "small" and note.grade is not None and note.grade >= .8
              and candidate.pitch is not None and (note.voice is None or note.voice == anchor.event.voice)
              and (note.onset is None or note.onset == anchor.event.onset))
    if matched:
        strong &= (correlation.confidence in ("EXACT", "HIGH") and matched.event.onset == anchor.event.onset
                   and matched.event.duration == anchor.event.duration and matched.event.voice == anchor.event.voice
                   and matched.event.staff == anchor.event.staff)
        if display_size(context.document, matched.node) == "small" and strong:
            candidate.state, candidate.operation, candidate.confidence = "NO_RECOVERY", None, "HIGH"
            candidate.diagnostics.append("small_display_already_preserved")
            return candidate
    else:
        strong &= correlation.confidence == "UNMATCHED" and not correlation.event_ids
        # Complex markings on a missing head need review; don't invent ties/slurs/ornaments.
        strong &= not any(r.kind in ("slur-head", "mirror") for r in note.relationships)
        strong &= rhythm(context)[anchor.measure.id]["valid"]
    if any(i.severity == "ERROR" and i.measure_id == anchor.measure.id for i in context.diagnostics):
        strong = False
    candidate.confidence = "HIGH" if strong else "AMBIGUOUS"
    if not strong:
        candidate.diagnostics.append("insufficient_size_pitch_or_rhythm_evidence")
    return candidate
