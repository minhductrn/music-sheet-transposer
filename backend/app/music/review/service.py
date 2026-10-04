"""Atomic review operations, history and explicit human verification."""

from base64 import b64encode
from dataclasses import asdict, replace
from copy import deepcopy
import secrets
from xml.etree import ElementTree as ET

from app.core.config import Settings
from app.music.review.document import Document, ReviewError
from app.music.review.models import Diagnostic, EventAdd, EventPatch, HarmonyAdd, HarmonyPatch, LyricAdd, TextPatch
from app.music.review.patcher import (
    add_event, delete_event, group, patch_event, patch_harmony, patch_lyric, patch_title, put,
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
                    document.issue_handlings[candidate["id"]] = {
                        "status": "AUTO_RECOVERED", "note": "Corroborated recovery at import.", "revision": 1,
                    }
        retained = prepare_source(source, source_mime or "", self.config) if source is not None else None
        session = ReviewSession(secrets.token_urlsafe(24), document, retained,
                                self.clock() + self.config.review_lifetime_seconds,
                                state="REVIEW_REQUIRED" if recovery_report and (recovery_report["review_required"] or recovery_report["auto_recovered"]) else "DRAFT",
                                undo=self._history([baseline]) if recovery_report and recovery_report["auto_recovered"] else [],
                                semantic_recovery=recovery_report)
        with self.store.lock:
            self.store.put(session)
            return self.payload(session)

    def payload(self, session):
        score, issues = self._projection(session)
        errors = sum(i.severity == "ERROR" for i in issues)
        review_issues = self.review_issues(session)
        unresolved = sum(i["status"] == "REVIEW_REQUIRED" for i in review_issues)
        projected = asdict(score)
        from .ties import tie_info
        relationships = tie_info(session.document, score)
        for part in projected["parts"]:
            for measure in part["measures"]:
                for voice in measure["voices"]:
                    for event in voice["events"]:
                        event.update(relationships[event["id"]])
                        event["provenance"] = {
                            "origin": "semantic_recovery" if event["id"].startswith("recovery-") else
                                      "manual_addition" if event["id"].startswith("new-") else
                                      "audiveris_baseline" if session.semantic_recovery else "musicxml_import",
                            "manual_fields": session.document.manual_changes.get(event["id"], []),
                            "evidence_ids": [i["id"] for i in review_issues if event["id"] in (i["event_id"], i["anchor_id"])],
                        }
        return {"id": session.id, "revision": session.revision, "state": session.state,
                "expires_at": session.expires_at, "score": projected,
                "validation": {"can_verify": not errors and not unresolved, "unresolved_issue_count": unresolved, "error_count": errors,
                               "warning_count": sum(i.severity == "WARNING" for i in issues),
                               "diagnostics": [asdict(i) for i in issues[:500]], "truncated": len(issues) > 500},
                "can_undo": bool(session.undo), "can_redo": bool(session.redo),
                "semantic_recovery": session.semantic_recovery,
                "review_issues": review_issues,
                "source": {"media_type": session.source.media_type, "pages": session.source.pages} if session.source else None,
                "musicxml_base64": b64encode(session.document.xml()).decode("ascii")}

    def _projection(self, session):
        from app.music.recovery.musicxml import XmlContext, rhythm
        context = XmlContext(session.document)
        score, issues = context.score, list(context.diagnostics)
        for mid, validation in rhythm(context).items():
            for issue in validation["diagnostics"]:
                if issue["code"] in ("voice_overlap", "voice_underfilled") or ((session.semantic_recovery is not None or "events" in session.document.manual_changes.get(mid, [])) and issue["code"] == "measure_overfilled"):
                    issues.append(Diagnostic(issue["code"], issue["code"].replace("_", " ").capitalize() + "; compare with the source.",
                                             issue["severity"], mid, issue["event_id"]))
        from .ties import diagnostics as tie_diagnostics
        issues.extend(tie_diagnostics(session.document))
        for part in score.parts:
            for measure in part.measures:
                severities = {i.severity for i in issues if i.measure_id == measure.id}
                measure.validation_state = "ERROR" if "ERROR" in severities else "WARNING" if "WARNING" in severities else "VALID"
        return score, issues

    def review_issues(self, session):
        # Evidence is immutable import provenance; handling lives in undoable sidecars.
        result = []
        for candidate in (session.semantic_recovery or {}).get("candidates", []):
            if candidate["state"] == "NO_RECOVERY":
                continue
            handling = session.document.issue_handlings.get(candidate["id"], {})
            issue = deepcopy(candidate)
            # Bind once at import, so later pitch/size edits retain evidence identity.
            if candidate["id"] in session.document.candidate_events:
                issue["event_id"] = session.document.candidate_events[candidate["id"]]
            related = [issue.get("event_id"), issue.get("anchor_id"), issue.get("measure_id")]
            evidence = candidate["evidence"]
            archive_hash = evidence["provenance"].split("/")[0]
            sheets = [sheet for archive in (session.semantic_recovery or {}).get("evidence", [])
                      if archive["sha256"] == archive_hash for sheet in archive.get("sheets", [])
                      if sheet["number"] == evidence["sheet"]]
            issue["source_location"] = {"page": evidence["sheet"], "bounds": evidence.get("bounds"),
                                        "width": sheets[0]["width"] if sheets else None,
                                        "height": sheets[0]["height"] if sheets else None}
            issue.update(status=handling.get("status", "REVIEW_REQUIRED"), handling=deepcopy(handling),
                         can_mark_corrected=any(session.document.manual_changes.get(eid) for eid in related))
            result.append(issue)
        return result

    def resolve_issue(self, identifier, revision, request):
        with self.store.lock:
            session = self._session(identifier, revision)
            issue = next((i for i in self.review_issues(session) if i["id"] == request.issue_id), None)
            if issue is None:
                raise ReviewError("The review issue does not exist.", 404)
            if issue["status"] != "REVIEW_REQUIRED":
                raise ReviewError("This issue is already handled. Reload the review.", 409)
            if request.disposition == "MANUALLY_CORRECTED" and not issue["can_mark_corrected"]:
                raise ReviewError("Apply a related correction first, or accept the notation after source comparison.", 409)
            def operation(doc, _):
                doc.issue_handlings[request.issue_id] = {
                    "status": request.disposition, "note": request.note.strip(), "revision": revision + 1,
                }
            return self.edit(identifier, revision, operation)

    def get(self, identifier):
        with self.store.lock:
            return self.payload(self.store.get(identifier))

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
            operation(candidate, f"new-{sequence}")
            if len(candidate.xml()) > self.config.recognition_max_output_bytes or sum(1 for _ in candidate.root.iter()) > self.config.review_max_xml_nodes:
                raise ReviewError("The correction exceeds the score size limit.", 413)
            changed_ids = {eid for eid in candidate.refs.keys() | session.document.refs.keys()
                           if eid not in candidate.refs or eid not in session.document.refs
                           or ET.tostring(candidate.refs[eid]) != ET.tostring(session.document.refs[eid])}
            for issue in self.review_issues(session):
                if changed_ids.intersection((issue.get("event_id"), issue.get("anchor_id"), issue.get("measure_id"))):
                    previous = candidate.issue_handlings.get(issue["id"])
                    if previous:
                        candidate.issue_handlings[issue["id"]] = {
                            **previous, "status": "REVIEW_REQUIRED", "invalidated_revision": revision + 1,
                        }
            updated = replace(session, document=candidate, state="REVIEW_REQUIRED", revision=session.revision + 1,
                              sequence=sequence, undo=self._history(session.undo + [session.document]), redo=[])
            # Validate/encode before commit. Musical errors remain editable and undoable.
            payload = self.payload(updated)
            self.store.put(updated)  # Commit only after the edit, projection and quotas succeed.
            return payload

    def event_patch(self, identifier, revision, event_id, patch: EventPatch):
        def operation(doc, _):
            members = group(doc, doc.get(event_id, "note"))
            patch_event(doc, event_id, patch)
            shared = patch.model_fields_set.intersection({"duration", "voice", "grace"})
            for key, node in doc.refs.items():
                if node in members and shared:
                    doc.manual_changes[key] = sorted(set(doc.manual_changes.get(key, [])) | shared)
            doc.manual_changes[event_id] = sorted(set(doc.manual_changes.get(event_id, [])) | patch.model_fields_set)
        return self.edit(identifier, revision, operation)

    def event_add(self, identifier, revision, request: EventAdd):
        def operation(doc, new_id):
            add_event(doc, new_id, request)
            doc.manual_changes[new_id] = ["addition", "tie_start"] if request.tie_to_event_id else ["addition"]
            doc.manual_changes[request.measure_id] = ["events"]
        return self.edit(identifier, revision, operation)

    def event_delete(self, identifier, revision, event_id):
        def operation(doc, _):
            note = doc.get(event_id, "note")
            parent = doc.parent(note)
            mid = next(key for key, value in doc.refs.items() if value is parent)
            delete_event(doc, event_id)
            doc.manual_changes[event_id] = ["deletion"]
            doc.manual_changes[mid] = ["events"]
        return self.edit(identifier, revision, operation)

    def lyric_patch(self, identifier, revision, lyric_id, request: TextPatch):
        return self.edit(identifier, revision, lambda doc, _: patch_lyric(doc, lyric_id, request.text, request.segment_index))

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
            doc.changed = True
        return self.edit(identifier, revision, operation)

    def harmony_patch(self, identifier, revision, harmony_id, request: HarmonyPatch):
        return self.edit(identifier, revision, lambda doc, _: patch_harmony(doc, harmony_id, request))

    def harmony_add(self, identifier, revision, request: HarmonyAdd):
        def operation(doc, new_id):
            measure = doc.get(request.measure_id, "measure")
            anchor = doc.get(request.before_event_id, "note") if request.before_event_id else None
            if anchor is not None and doc.parent(anchor) is not measure:
                raise ReviewError("Harmony anchor must belong to the requested measure.")
            harmony = ET.Element(doc.namespace + "harmony")
            if anchor is not None:
                position = list(measure).index(group(doc, anchor)[0])
            else:
                position = next((i for i, child in enumerate(measure) if child.tag == doc.namespace + "barline" and child.get("location", "right") == "right"), len(measure))
            measure.insert(position, harmony)
            doc.refs[new_id] = harmony
            patch_harmony(doc, new_id, HarmonyPatch(root_step=request.root_step, root_alter=request.root_alter,
                                                    kind=request.kind or "major", text=request.text or ""))
        return self.edit(identifier, revision, operation)

    def title_patch(self, identifier, revision, request: TextPatch):
        return self.edit(identifier, revision, lambda doc, _: patch_title(doc, request.text))

    def credit_patch(self, identifier, revision, credit_id, request: TextPatch):
        def operation(doc, _):
            doc.get(credit_id, "credit-words").text = request.text
            doc.changed = True
        return self.edit(identifier, revision, operation)

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
            if any(issue.severity == "ERROR" for issue in issues):
                raise ReviewError("Correct all validation errors before marking this review VERIFIED.", 409)
            if any(i["status"] == "REVIEW_REQUIRED" for i in self.review_issues(session)):
                raise ReviewError("Handle each review issue by correction or explicit source comparison before verification.", 409)
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
