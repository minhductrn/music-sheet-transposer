"""Atomic review operations, history and explicit human verification."""

from base64 import b64encode
from dataclasses import asdict, replace
from copy import deepcopy
from fractions import Fraction
import secrets
from xml.etree import ElementTree as ET

from app.core.config import Settings
from app.music.review.document import Document, ReviewError
from app.music.review.models import Diagnostic, EventAdd, EventPatch, HarmonyAdd, HarmonyPatch, LyricAdd, LyricMove, ScoreTextAdd, TextPatch
from app.music.review.patcher import (
    add_event, delete_event, delete_preserving_timing, group, patch_event, patch_harmony, patch_lyric, patch_title, put,
)
from app.music.review.source import prepare_source
from app.music.review.storage import ReviewSession, ReviewStore


class ReviewService:
    def __init__(self, store: ReviewStore, config: Settings, clock):
        self.store, self.config, self.clock = store, config, clock

    def create(self, xml: bytes, source: bytes | None = None, source_mime: str | None = None,
               omr: bytes | None = None, analysis_omr: bytes | None = None):
        if not xml or len(xml) > self.config.recognition_max_output_bytes:
            raise ReviewError("Review MusicXML is empty or exceeds the size limit.", 413)
        document = Document.parse(xml, self.config.review_max_xml_nodes)
        baseline = document
        recovery_report = None
        if omr is not None or analysis_omr is not None:
            if len(omr or b"") + len(analysis_omr or b"") > self.config.recognition_max_artifact_bytes:
                raise ReviewError("Review evidence exceeds the combined artifact size limit.", 413)
            from app.music.recovery.service import recover
            recovery = recover(xml, omr, self.config, analysis_omr=analysis_omr)
            document, recovery_report = recovery.document, recovery.report
        if recovery_report:
            node_ids = {node: key for key, node in document.refs.items()}
            for candidate in recovery_report["candidates"]:
                if candidate["state"] == "AUTO_RECOVERED":
                    if candidate["event_id"]:
                        document.candidate_events[candidate["id"]] = candidate["event_id"]
                    elif candidate["anchor_id"] in document.refs and candidate["pitch"]:
                        pitch = candidate["pitch"]
                        matches = [node_ids[node] for node in group(document, document.refs[candidate["anchor_id"]])
                                   if document.child(node, "pitch") is not None
                                   and document.text(document.child(node, "pitch"), "step") == pitch["step"]
                                   and document.text(document.child(node, "pitch"), "octave") == str(pitch["octave"])
                                   and document.text(document.child(node, "pitch"), "alter", "0") == pitch["alter"]]
                        if len(matches) == 1:
                            document.candidate_events[candidate["id"]] = matches[0]
        # Evidence retention is independent of recovery enablement and never mutates notes.
        source_evidence = []
        from app.music.recovery.omr import parse_omr
        from app.music.recognition.errors import RecognitionError
        for contents in (omr, analysis_omr):
            if contents is None:
                continue
            try:
                observed = parse_omr(contents, max_bytes=self.config.recognition_max_artifact_bytes,
                                     max_expanded_bytes=self.config.semantic_max_expanded_bytes,
                                     max_members=self.config.recognition_max_archive_members,
                                     max_nodes=self.config.semantic_max_xml_nodes)
                if not any(e['sha256'] == observed.sha256 for e in source_evidence):
                    source_evidence.append(asdict(observed))
            except RecognitionError:
                # Existing recovery reports parse failures; no fabricated evidence.
                pass
        retained = prepare_source(source, source_mime or "", self.config) if source is not None else None
        session = ReviewSession(secrets.token_urlsafe(24), document, retained,
                                self.clock() + self.config.review_lifetime_seconds,
                                state="REVIEW_REQUIRED" if recovery_report and (recovery_report["review_required"] or recovery_report["auto_recovered"]) else "DRAFT",
                                undo=self._history([baseline]) if recovery_report and recovery_report["auto_recovered"] else [],
                                semantic_recovery=recovery_report, source_evidence=source_evidence)
        with self.store.lock:
            score, _ = self._projection(session)
            if any(m.conflict_state == "CONFLICT" for p in score.parts for m in p.measures):
                session.state = "REVIEW_REQUIRED"
            self.store.put(session)
            return self.payload(session)

    def payload(self, session):
        score, issues = self._projection(session)
        from .confirmations import diagnostics
        diagnosed = diagnostics(session.document, issues)
        errors = sum(i["blocking"] for i in diagnosed)
        evidence_candidates = (session.semantic_recovery or {}).get("candidates", [])
        from .structure import source_layout
        source_layout(score, session.source_evidence)
        projected = asdict(score)
        from .omr_marks import marks
        projected["omr_marks"] = [{**mark,"id":f"{session.revision}|{mark['id']}"} for mark in marks(session.document)]
        from .ties import tie_info
        relationships = tie_info(session.document, score)
        for part in projected["parts"]:
            for measure in part["measures"]:
                for voice in measure["voices"]:
                    for event in voice["events"]:
                        event.update(relationships[event["id"]])
                        # Discover standard picker values with the existing patcher;
                        # tuplets/chord members can further restrict representability.
                        from .patcher import duration_patch
                        members = group(session.document, session.document.refs[event["id"]])
                        options = []
                        if not event["grace"]:
                            for value in ("1/4", "1/2", "1", "3/2", "2", "3", "4"):
                                try:
                                    for member in members:
                                        duration_patch(session.document, deepcopy(member), value, event["divisions"])
                                except ReviewError:
                                    continue
                                options.append(value)
                        event["duration_options"] = options
                        # Palette keys are WRITTEN durations; values are effective
                        # command durations, checked by the existing spelling guard.
                        palette = {}
                        node = session.document.refs[event["id"]]
                        modification = session.document.child(node, "time-modification")
                        from .importer import rational
                        ratio = Fraction(1)
                        if modification is not None:
                            actual = rational(session.document.text(modification, "actual-notes"))
                            normal = rational(session.document.text(modification, "normal-notes"))
                            ratio = normal / actual if actual and normal and actual > 0 and normal > 0 else None
                        if not event["grace"] and ratio is not None:
                            for base in (4, 2, 1, Fraction(1, 2), Fraction(1, 4), Fraction(1, 8), Fraction(1, 16)):
                                for factor in (1, Fraction(3, 2), Fraction(7, 4)):
                                    written = Fraction(base) * factor
                                    effective = written * ratio
                                    try:
                                        duration_patch(session.document, deepcopy(node), str(effective), str(Fraction(event["divisions"]) * (effective * Fraction(event["divisions"])).denominator))
                                    except ReviewError:
                                        continue
                                    palette[str(written)] = str(effective)
                        event["palette_duration_options"] = palette
                        event["provenance"] = {
                            "origin": "semantic_recovery" if event["id"].startswith("recovery-") else
                                      "manual_addition" if event["id"].startswith("new-") else
                                      "audiveris_baseline" if session.semantic_recovery else "musicxml_import",
                            "manual_fields": session.document.manual_changes.get(event["id"], []),
                            "layer": "USER_CORRECTION" if session.document.manual_changes.get(event["id"]) or event["id"].startswith("new-") else "RECOGNITION_INTERPRETATION",
                            "evidence_ids": [i["id"] for i in evidence_candidates if event["id"] in (session.document.candidate_events.get(i["id"], i.get("event_id")), i.get("anchor_id"))],
                        }
        from .slurs import pairs as slur_pairs
        return {"id": session.id, "revision": session.revision, "state": session.state,
                "expires_at": session.expires_at, "score": projected,
                "validation": {"can_verify": not errors, "error_count": errors,
                               "warning_count": sum(i.severity == "WARNING" for i in issues),
                               "diagnostics": diagnosed[:500], "truncated": len(issues) > 500},
                "can_undo": bool(session.undo), "can_redo": bool(session.redo),
                "source_confirmations": [{**decision, "diagnostic_id": key,
                    "status": "CURRENT" if any(i["id"] == key and i["source_confirmed"] for i in diagnosed) else "STALE"}
                    for key, decision in session.document.source_confirmations.items()],
                "source_evidence": session.source_evidence,
                "semantic_recovery": session.semantic_recovery,
                "source": {"media_type": session.source.media_type, "pages": session.source.pages} if session.source else None,
                "slurs": slur_pairs(session.document),
                "musicxml_base64": b64encode(session.document.xml()).decode("ascii")}

    def _projection(self, session):
        from app.music.recovery.musicxml import XmlContext, rhythm
        context = XmlContext(session.document)
        score, issues = context.score, list(context.diagnostics)
        for mid, validation in rhythm(context).items():
            for issue in validation["diagnostics"]:
                if issue["code"] in ("voice_overlap", "voice_underfilled", "measure_overfilled"):
                    issues.append(Diagnostic(issue["code"], issue["code"].replace("_", " ").capitalize() + "; compare with the source.",
                                             issue["severity"], mid, issue["event_id"]))
        from .ties import diagnostics as tie_diagnostics
        issues.extend(tie_diagnostics(session.document))
        from .music_check import classify
        issues = classify(issues)
        for part in score.parts:
            for measure in part.measures:
                severities = {i.severity for i in issues if i.measure_id == measure.id}
                measure.validation_state = "ERROR" if "ERROR" in severities else "WARNING" if "WARNING" in severities else "VALID"
                if "ERROR" in severities:
                    measure.conflict_state = "CONFLICT"
                    if measure.rhythm_status == "VALID":
                        measure.rhythm_status = "STRUCTURALLY_AMBIGUOUS"
        return score, issues

    def confirm_source(self, identifier, revision, request):
        with self.store.lock:
            session = self._session(identifier, revision)
            _, issues = self._projection(session)
            from .confirmations import confirm
            return self.edit(identifier, revision, lambda doc, _: confirm(doc, issues, request, revision + 1))

    def get(self, identifier):
        with self.store.lock:
            return self.payload(self.store.get(identifier))

    def keepalive(self, identifier):
        """Renew an existing open editor; never resurrect expired data or change history."""
        with self.store.lock:
            session = self.store.get(identifier)
            renewed = replace(session, expires_at=self.clock() + self.config.review_lifetime_seconds)
            self.store.put(renewed)
            return {"id": renewed.id, "expires_at": renewed.expires_at}

    def _session(self, identifier, revision):
        session = self.store.get(identifier)
        if revision != session.revision:
            raise ReviewError("This review changed in another request. Reload it before applying corrections.", 409)
        return session

    def _history(self, documents):
        result = list(documents[-self.config.review_history_limit:])
        while result and sum(d.weight() for d in result) > self.config.review_history_max_bytes:
            result.pop(0)
        return result

    def edit(self, identifier, revision, operation):
        with self.store.lock:
            session = self._session(identifier, revision)
            candidate = session.document.clone()
            sequence = session.sequence + 1
            if operation(candidate, f"new-{sequence}") is False:
                return self.payload(session)
            if len(candidate.xml()) > self.config.recognition_max_output_bytes or sum(1 for _ in candidate.root.iter()) > self.config.review_max_xml_nodes:
                raise ReviewError("The correction exceeds the score size limit.", 413)
            from .confirmations import fingerprint
            for key, decision in candidate.source_confirmations.items():
                if key in session.document.source_confirmations and decision == session.document.source_confirmations[key]:
                    if decision["fingerprint"] != fingerprint(candidate, decision["measure_id"]):
                        decision["invalidated_revision"] = revision + 1
            updated = replace(session, document=candidate, state="REVIEW_REQUIRED", revision=session.revision + 1,
                              sequence=sequence, undo=self._history(session.undo + [session.document]), redo=[])
            # Validate/encode before commit. Musical errors remain editable and undoable.
            payload = self.payload(updated)
            self.store.put(updated)  # Commit only after the edit, projection and quotas succeed.
            return payload

    def document_correction(self, identifier, revision, contents):
        """Keep source/history/sidecars for explicit beam, meter and key edits.

        Existing identity-bearing elements must retain order and count. Appending
        empty measures is allowed; note insertion/deletion uses event commands.
        """
        if not contents or len(contents) > self.config.recognition_max_output_bytes:
            raise ReviewError("Correction exceeds the MusicXML size limit.", 413)
        parsed = Document.parse(contents, self.config.review_max_xml_nodes)
        from .document import local
        def operation(doc, sequence):
            old_nodes = list(doc.root.iter())
            new_nodes = list(parsed.root.iter())
            mapping = {}
            for tag in ("part", "measure", "note", "lyric", "harmony", "credit-words", "work-title", "movement-title", "creator", "words"):
                old = [n for n in old_nodes if local(n.tag) == tag]
                new = [n for n in new_nodes if local(n.tag) == tag]
                if len(new) != len(old) and not (tag == "measure" and len(new) > len(old)):
                    raise ReviewError("Use the event or text tools to add/remove score objects; document correction preserves their identities.")
                mapping.update(zip(old, new))
            # Notes must keep their original measure membership. No silent ID reassignment.
            for node in [n for n in old_nodes if local(n.tag) == "note"]:
                if mapping.get(doc.parent(node)) is not parsed.parent(mapping[node]):
                    raise ReviewError("Document correction cannot move notes between measures.")
            refs = {key: mapping[node] for key, node in doc.refs.items() if node in mapping}
            assigned = set(refs.values())
            for i, node in enumerate(n for n in new_nodes if local(n.tag) == "measure" and n not in assigned):
                refs[f"{sequence}-measure-{i}"] = node
            doc.root, doc.refs = parsed.root, refs
            doc.changed = True
            for decision in doc.source_confirmations.values():
                decision["invalidated_revision"] = revision + 1
        return self.edit(identifier, revision, operation)

    def event_patch(self, identifier, revision, event_id, patch: EventPatch):
        def operation(doc, _):
            if patch.duration is not None:
                from .patcher import context
                from .triplets import refine_divisions
                measure, event = context(doc, doc.get(event_id, "note"))
                from .importer import rational
                requested = rational(patch.duration)
                if event.divisions and requested is not None and 0 < requested <= 1024:
                    scale = Fraction(event.divisions)
                    factor = (requested * scale).denominator
                    if factor > 1:
                        refine_divisions(doc, doc.get(event.measure_id, "measure"), scale, factor)
            members = group(doc, doc.get(event_id, "note"))
            if patch_event(doc, event_id, patch) is False:
                return False
            shared = patch.model_fields_set.intersection({"duration", "voice", "grace"})
            if patch.model_fields_set.intersection({"duration", "grace"}):
                measure = doc.parent(doc.get(event_id, "note"))
                mid = next(key for key, node in doc.refs.items() if node is measure)
                doc.manual_changes[mid] = sorted(set(doc.manual_changes.get(mid, [])) | {"events"})
            for key, node in doc.refs.items():
                if node in members and shared:
                    doc.manual_changes[key] = sorted(set(doc.manual_changes.get(key, [])) | shared)
            doc.manual_changes[event_id] = sorted(set(doc.manual_changes.get(event_id, [])) | (patch.model_fields_set - {"preserve_onsets"}))
        return self.edit(identifier, revision, operation)

    def event_move(self, identifier, revision, event_id, request):
        def operation(doc, _):
            from .patcher import move_event
            move_event(doc, event_id, request)
            doc.manual_changes[event_id] = sorted(set(doc.manual_changes.get(event_id, [])) | {"ownership", "voice", "staff", "onset"})
        return self.edit(identifier, revision, operation)

    def replacement_options(self, identifier, revision, event_id):
        from .triplet_replacement import replacement_options
        with self.store.lock:
            session = self._session(identifier, revision)
            return replacement_options(session.document, revision, event_id)

    def replacement_preview(self, identifier, revision, event_id, request):
        from .triplet_replacement import preview_replacement
        with self.store.lock:
            session = self._session(identifier, revision)
            return preview_replacement(session.document, revision, event_id, request)

    def triplet_replace(self, identifier, revision, event_id, request):
        from .triplet_replacement import replace_single
        return self.edit(identifier, revision, lambda doc, new_id: replace_single(doc, new_id, event_id, request))

    def triplet_preview(self, identifier, revision, request):
        from .triplets import preview_selection
        with self.store.lock:
            session = self._session(identifier, revision)
            return preview_selection(session.document, revision, request.event_ids)

    def tuplet_work(self, identifier, revision, request):
        from .tuplet_work import edit_tuplet
        return self.edit(identifier, revision, lambda doc, new_id: edit_tuplet(doc, new_id, request))

    def triplet_edit(self, identifier, revision, request):
        from .triplets import triplet
        return self.edit(identifier, revision, lambda doc, new_id: triplet(doc, new_id, request))

    def notation_edit(self, identifier, revision, event_id, request):
        def operation(doc, _):
            note = doc.get(event_id, "note")
            allowed = {"articulation": {"staccato", "tenuto", "accent", "strong-accent", "staccatissimo", "breath-mark"},
                       "fermata": {"normal", "angled", "square"},
                       "dynamic": {"ppp", "pp", "p", "mp", "mf", "f", "ff", "fff", "sfz"}}
            if request.value not in allowed[request.field]:
                raise ReviewError("Choose a supported notation value.")
            if request.field == "dynamic":
                measure = doc.parent(note)
                from .patcher import context
                _, event = context(doc, note)
                # Only directions at this exact stream position and owner are eligible.
                for sibling in reversed(list(measure)[:list(measure).index(note)]):
                    from .document import local
                    if local(sibling.tag) in ("note", "backup", "forward"):
                        break
                    if local(sibling.tag) != "direction" or doc.child(sibling, "offset") is not None:
                        continue
                    if doc.text(sibling, "voice", event.voice) != event.voice or doc.text(sibling, "staff", str(event.staff)) != str(event.staff):
                        continue
                    for kind in doc.children(sibling, "direction-type"):
                        for dynamic in doc.children(kind, "dynamics"):
                            for marking in list(dynamic):
                                if not request.remove or local(marking.tag) == request.value:
                                    dynamic.remove(marking)
                            if not len(dynamic):
                                kind.remove(dynamic)
                        if not len(kind):
                            sibling.remove(kind)
                    if not doc.children(sibling, "direction-type"):
                        measure.remove(sibling)
                if not request.remove:
                    direction = ET.Element(doc.namespace + "direction")
                    kind = ET.SubElement(direction, doc.namespace + "direction-type")
                    dynamic = ET.SubElement(kind, doc.namespace + "dynamics")
                    ET.SubElement(dynamic, doc.namespace + request.value)
                    ET.SubElement(direction, doc.namespace + "voice").text = event.voice
                    ET.SubElement(direction, doc.namespace + "staff").text = str(event.staff)
                    measure.insert(list(measure).index(note), direction)
            else:
                notations = doc.child(note, "notations")
                if notations is None:
                    notations = put(doc, note, "notations")
                if request.field == "fermata":
                    for existing in doc.children(notations, "fermata"):
                        notations.remove(existing)
                    if not request.remove:
                        ET.SubElement(notations, doc.namespace + "fermata").text = request.value
                else:
                    articulations = doc.child(notations, "articulations")
                    if articulations is None:
                        articulations = ET.SubElement(notations, doc.namespace + "articulations")
                    for existing in doc.children(articulations, request.value):
                        articulations.remove(existing)
                    if not request.remove:
                        ET.SubElement(articulations, doc.namespace + request.value)
            doc.manual_changes[event_id] = sorted(set(doc.manual_changes.get(event_id, [])) | {request.field})
            doc.changed = True
        return self.edit(identifier, revision, operation)

    def event_add(self, identifier, revision, request: EventAdd):
        def operation(doc, new_id):
            from .patcher import position_context
            from .triplets import refine_divisions
            info, _, scale = position_context(doc, request.measure_id)
            from .importer import rational
            duration = rational(request.duration)
            factor = (duration * scale).denominator if duration is not None and 0 < duration <= 1024 else 1
            if factor > 1:
                refine_divisions(doc, doc.get(request.measure_id, "measure"), scale, factor)
            add_event(doc, new_id, request)
            doc.manual_changes[new_id] = ["addition", "tie_start"] if request.tie_to_event_id else ["addition"]
            doc.manual_changes[request.measure_id] = ["events"]
        return self.edit(identifier, revision, operation)

    def events_delete(self, identifier, revision, event_ids):
        def operation(doc, _):
            ids=set(event_ids)
            if len(ids)!=len(event_ids):
                raise ReviewError("Select each note only once.")
            nodes={doc.get(key,"note"):key for key in ids}
            # Remove chord followers before their advancing head, in one history entry.
            ordered=[nodes[node] for node in doc.root.iter() if node in nodes]
            from .slurs import disconnect_deleted
            for key in reversed(ordered):
                parent=doc.parent(doc.get(key,"note"))
                mid=next(k for k,v in doc.refs.items() if v is parent)
                disconnect_deleted(doc,key)
                delete_preserving_timing(doc,key)
                doc.manual_changes[key]=["deletion"]
                doc.manual_changes[mid]=["events"]
        return self.edit(identifier,revision,operation)

    def event_delete(self, identifier, revision, event_id, preserve_timing=False):
        def operation(doc, _):
            note = doc.get(event_id, "note")
            parent = doc.parent(note)
            mid = next(key for key, value in doc.refs.items() if value is parent)
            from .slurs import disconnect_deleted
            disconnect_deleted(doc, event_id)
            if preserve_timing:
                delete_preserving_timing(doc, event_id)
            else:
                delete_event(doc, event_id)
            doc.manual_changes[event_id] = ["deletion"]
            doc.manual_changes[mid] = ["events"]
        return self.edit(identifier, revision, operation)

    def slur_edit(self, identifier, revision, request):
        from .slurs import apply
        return self.edit(identifier, revision, lambda doc, _: apply(doc, request))

    def lyric_move(self, identifier, revision, lyric_id, request: LyricMove):
        def operation(doc, _):
            from .importer import import_score
            from .lyrics import auxiliary_lyric_owner
            lyric = doc.get(lyric_id, "lyric")
            source = doc.get(request.source_event_id, "note")
            destination = doc.get(request.destination_event_id, "note")
            if doc.parent(lyric) is not source or lyric.get("number", "1") != request.number:
                raise ReviewError("The lyric owner or verse changed. Select it again.", 409)
            if destination is source:
                return False
            score, _ = import_score(doc)
            events = [e for p in score.parts for m in p.measures for v in m.voices for e in v.events]
            targets = [e for e in events if e.id == request.destination_event_id]
            if len(targets) != 1 or targets[0].kind != "note" or targets[0].pitch is None:
                raise ReviewError("Choose a pitched destination note.")
            if auxiliary_lyric_owner(score, targets[0]) is not None:
                raise ReviewError("Select the normal-note lyric owner instead of its auxiliary note.")
            if any(l.get("number", "1") == request.number for l in doc.children(destination, "lyric")):
                raise ReviewError("The destination already contains this verse; nothing was overwritten.", 409)
            source.remove(lyric)
            index = next((i for i, child in enumerate(destination)
                          if child.tag in (doc.namespace + "play", doc.namespace + "listen")), len(destination))
            destination.insert(index, lyric)  # Move the complete subtree, retaining its sidecar identity.
            for event_id in (request.source_event_id, request.destination_event_id):
                doc.manual_changes[event_id] = sorted(set(doc.manual_changes.get(event_id, [])) | {"lyrics"})
            doc.changed = True
        return self.edit(identifier, revision, operation)

    def lyric_patch(self, identifier, revision, lyric_id, request: TextPatch):
        def operation(doc, _):
            lyric = doc.get(lyric_id, "lyric")
            note = doc.parent(lyric)
            event_id = next(key for key, node in doc.refs.items() if node is note)
            patch_lyric(doc, lyric_id, request.text, request.segment_index)
            doc.manual_changes[event_id] = sorted(set(doc.manual_changes.get(event_id, [])) | {"lyrics"})
        return self.edit(identifier, revision, operation)

    def lyric_delete(self, identifier, revision, lyric_id):
        def operation(doc, _):
            lyric = doc.get(lyric_id, "lyric")
            note = doc.parent(lyric)
            event_id = next(key for key, node in doc.refs.items() if node is note)
            note.remove(lyric)
            del doc.refs[lyric_id]
            doc.manual_changes[event_id] = sorted(set(doc.manual_changes.get(event_id, [])) | {"lyrics"})
            doc.changed = True
        return self.edit(identifier, revision, operation)

    def text_to_lyrics(self, identifier, revision, text_id, request):
        def operation(doc, new_id):
            source = doc.get(text_id, "words")
            seen = set()
            for index, mapping in enumerate(request.mappings):
                note = doc.get(mapping.event_id, "note")
                if doc.child(note, "pitch") is None:
                    raise ReviewError("Lyrics must be assigned to an explicitly selected pitched note.")
                owner = (mapping.event_id, mapping.number)
                if owner in seen or any(l.get("number", "1") == mapping.number for l in doc.children(note, "lyric")):
                    raise ReviewError("This note/verse already has lyrics; edit or move that lyric explicitly.")
                seen.add(owner)
                lyric = ET.Element(doc.namespace + "lyric", {"number": mapping.number})
                put(doc, lyric, "text", mapping.text)
                index_in_note = next((i for i, c in enumerate(note) if c.tag in (doc.namespace + "play", doc.namespace + "listen")), len(note))
                note.insert(index_in_note, lyric)
                doc.refs[f"{new_id}-lyric-{index}"] = lyric
                doc.manual_changes[mapping.event_id] = sorted(set(doc.manual_changes.get(mapping.event_id, [])) | {"lyrics"})
            if request.remove_source:
                from .score_text import delete_text
                delete_text(doc, text_id)
            doc.changed = True
        return self.edit(identifier, revision, operation)

    def lyric_add(self, identifier, revision, event_id, request: LyricAdd):
        def operation(doc, new_id):
            note = doc.get(event_id, "note")
            if any(l.get("number", "1") == request.number for l in doc.children(note, "lyric")):
                raise ReviewError("This verse already exists on the event; edit its lyric instead.")
            lyric = ET.Element(doc.namespace + "lyric", {"number": request.number})
            put(doc, lyric, "text", request.text)
            # Keep MusicXML's note child order, including any trailing play/listen.
            index = next((i for i, child in enumerate(note) if child.tag in (doc.namespace + "play", doc.namespace + "listen")), len(note))
            note.insert(index, lyric)
            doc.refs[new_id] = lyric
            doc.manual_changes[event_id] = sorted(set(doc.manual_changes.get(event_id, [])) | {"lyrics"})
            doc.changed = True
        return self.edit(identifier, revision, operation)

    def mark_delete(self, identifier, revision, mark_id):
        from .omr_marks import delete_mark
        prefix, separator, mark = mark_id.partition("|")
        if not separator or prefix != str(revision):
            raise ReviewError("The selected mark belongs to an older revision. Select it again.",409)
        return self.edit(identifier, revision, lambda doc, _: delete_mark(doc, mark))

    def harmony_delete(self, identifier, revision, harmony_id):
        def operation(doc, _):
            node=doc.get(harmony_id,"harmony")
            doc.parent(node).remove(node)
            del doc.refs[harmony_id]
            doc.changed=True
        return self.edit(identifier, revision, operation)

    def harmony_position(self, doc, node, measure, before_event_id, onset):
        if onset is not None:
            if before_event_id:
                raise ReviewError("Choose a note anchor or a beat position, not both.")
            from .patcher import context
            from .importer import rational
            from .triplets import refine_divisions
            beat=rational(onset)
            info,_=context(doc,measure_id=next(k for k,v in doc.refs.items() if v is measure))
            scale=rational(info.divisions)
            if beat is None or beat<0 or beat>1024 or scale is None or scale<=0:
                raise ReviewError("Choose a nonnegative beat position and a measure with known divisions.")
            scale=refine_divisions(doc,measure,scale,(beat*scale).denominator)
            for offset in doc.children(node,"offset"):node.remove(offset)
            offset=ET.SubElement(node,doc.namespace+"offset");offset.text=str(int(beat*scale))
            # Before the first timed item: offset is measured from the bar start.
            position=next((i for i,c in enumerate(measure) if c.tag not in (doc.namespace+"attributes",doc.namespace+"print")),len(measure))
        else:
            anchor=doc.get(before_event_id,"note") if before_event_id else None
            if anchor is not None and doc.parent(anchor) is not measure:
                raise ReviewError("Choose a note in the destination measure.")
            for offset in doc.children(node,"offset"):node.remove(offset)
            position=list(measure).index(group(doc,anchor)[0]) if anchor is not None else next((i for i,c in enumerate(measure) if c.tag==doc.namespace+"barline" and c.get("location","right")=="right"),len(measure))
        measure.insert(position,node)

    def harmony_move(self, identifier, revision, harmony_id, request):
        def operation(doc, _):
            node=doc.get(harmony_id,"harmony")
            measure=doc.get(request.measure_id,"measure")
            doc.parent(node).remove(node)
            self.harmony_position(doc,node,measure,request.before_event_id,request.onset)
            doc.changed=True
        return self.edit(identifier, revision, operation)

    def harmony_patch(self, identifier, revision, harmony_id, request: HarmonyPatch):
        return self.edit(identifier, revision, lambda doc, _: patch_harmony(doc, harmony_id, request))

    def harmony_add(self, identifier, revision, request: HarmonyAdd):
        def operation(doc, new_id):
            measure = doc.get(request.measure_id, "measure")
            harmony = ET.Element(doc.namespace + "harmony")
            self.harmony_position(doc,harmony,measure,request.before_event_id,request.onset)
            doc.refs[new_id] = harmony
            patch_harmony(doc, new_id, HarmonyPatch(root_step=request.root_step, root_alter=request.root_alter,
                                                    kind=request.kind or "major", text=request.text or ""))
        return self.edit(identifier, revision, operation)

    def score_text_patch(self, identifier, revision, text_id, request: TextPatch):
        from .score_text import patch_text
        if request.segment_index:
            raise ReviewError('Choose an independent text element; lyric segments use the lyric editor.')
        if request.header_role:
            from .score_text import move_text_to_header
            return self.edit(identifier, revision, lambda doc, _: move_text_to_header(doc, text_id, request.text, request.header_role))
        return self.edit(identifier, revision, lambda doc, _: patch_text(doc, text_id, request.text))

    def score_text_add(self, identifier, revision, request: ScoreTextAdd):
        from .score_text import add_text
        return self.edit(identifier, revision, lambda doc, new_id: add_text(doc, new_id, request))

    def score_text_delete(self, identifier, revision, text_id):
        from .score_text import delete_text
        return self.edit(identifier, revision, lambda doc, _: delete_text(doc, text_id))

    def title_patch(self, identifier, revision, request: TextPatch):
        def operation(doc, new_id):
            patch_title(doc, request.text)
            title = doc.child(doc.root, 'movement-title')
            if title is not None and not any(node is title for node in doc.refs.values()):
                doc.refs[new_id] = title
        return self.edit(identifier, revision, operation)

    def credit_patch(self, identifier, revision, credit_id, request: TextPatch):
        def operation(doc, _):
            doc.get(credit_id, "credit-words").text = request.text
            doc.changed = True
        return self.edit(identifier, revision, operation)

    def music_check(self, identifier, revision):
        """Explicit assistance; no state/revision/history/verification mutation."""
        with self.store.lock:
            session = self._session(identifier, revision)
            _, issues = self._projection(session)
            from .confirmations import diagnostics
            result = diagnostics(session.document, issues)
            return {"revision": session.revision, "diagnostics": result[:500],
                    "warning_count": sum(i["category"] == "MUSIC_WARNING" for i in result),
                    "technical_error_count": sum(i["blocking"] for i in result),
                    "truncated": len(result) > 500}

    def validate(self, identifier, revision):
        with self.store.lock:
            session = self._session(identifier, revision)
            updated = replace(session, state="REVIEW_REQUIRED" if session.state == "DRAFT" else session.state,
                              revision=session.revision + 1)
            self.store.put(updated)
            return self.payload(updated)

    def verify(self, identifier, revision):
        with self.store.lock:
            session = self._session(identifier, revision)
            _, issues = self._projection(session)
            from .confirmations import diagnostics
            if any(issue["blocking"] for issue in diagnostics(session.document, issues)):
                raise ReviewError("Correct technical representation errors before marking this review VERIFIED. Optional music warnings do not block source confirmation.", 409)
            updated = replace(session, state="VERIFIED", revision=session.revision + 1)
            self.store.put(updated)
            return self.payload(updated)

    def history(self, identifier, revision, direction):
        with self.store.lock:
            session = self._session(identifier, revision)
            source = session.undo if direction == "undo" else session.redo
            destination = session.redo if direction == "undo" else session.undo
            if not source:
                raise ReviewError(f"There is no correction to {direction}.", 409)
            destination = self._history(destination + [session.document])
            updated = replace(session, document=source[-1], state="REVIEW_REQUIRED", revision=session.revision + 1,
                              undo=source[:-1] if direction == "undo" else destination,
                              redo=destination if direction == "undo" else source[:-1])
            self.store.put(updated)
            return self.payload(updated)

    def musicxml(self, identifier, verified_only=False, original=False):
        with self.store.lock:
            session = self.store.get(identifier)
            if verified_only and (session.state != "VERIFIED" or original):
                raise ReviewError("Only the verified corrected document can be used for reviewed transposition.", 409)
            return session.document.original if original else session.document.xml()

    def transpose(self, identifier, revision, semitones):
        from app.music.musicxml.transposer import MusicXMLTranspositionError, transpose_musicxml_document
        # One revision check + verified snapshot + stable transposer call under the existing lock.
        with self.store.lock:
            self._session(identifier, revision)
            contents = self.musicxml(identifier, verified_only=True)
            try:
                return transpose_musicxml_document(contents, semitones)
            except MusicXMLTranspositionError as error:
                raise ReviewError(str(error)) from error

    def source(self, identifier):
        with self.store.lock:
            source = self.store.get(identifier).source
            if source is None:
                raise ReviewError("This review has no retained original source.", 404)
            return source

    def delete(self, identifier):
        with self.store.lock:
            self.store.delete(identifier)
