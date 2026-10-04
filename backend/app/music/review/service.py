"""Atomic review operations, history and explicit human verification."""

from base64 import b64encode
from dataclasses import asdict, replace
import secrets
from xml.etree import ElementTree as ET

from app.core.config import Settings
from app.music.review.document import Document, ReviewError
from app.music.review.importer import import_score
from app.music.review.models import EventAdd, EventPatch, HarmonyAdd, HarmonyPatch, LyricAdd, TextPatch
from app.music.review.patcher import (
    add_event, delete_event, group, patch_event, patch_harmony, patch_lyric, patch_title, put,
)
from app.music.review.source import prepare_source
from app.music.review.storage import ReviewSession, ReviewStore


class ReviewService:
    def __init__(self, store: ReviewStore, config: Settings, clock):
        self.store, self.config, self.clock = store, config, clock

    def create(self, xml: bytes, source: bytes | None = None, source_mime: str | None = None):
        if not xml or len(xml) > self.config.recognition_max_output_bytes:
            raise ReviewError("Review MusicXML is empty or exceeds the size limit.", 413)
        document = Document.parse(xml, self.config.review_max_xml_nodes)
        retained = prepare_source(source, source_mime or "", self.config) if source is not None else None
        session = ReviewSession(secrets.token_urlsafe(24), document, retained,
                                self.clock() + self.config.review_lifetime_seconds)
        with self.store.lock:
            self.store.put(session)
            return self.payload(session)

    def payload(self, session):
        score, issues = import_score(session.document)
        errors = sum(i.severity == "ERROR" for i in issues)
        return {"id": session.id, "revision": session.revision, "state": session.state,
                "expires_at": session.expires_at, "score": asdict(score),
                "validation": {"can_verify": not errors, "error_count": errors,
                               "warning_count": sum(i.severity == "WARNING" for i in issues),
                               "diagnostics": [asdict(i) for i in issues[:500]], "truncated": len(issues) > 500},
                "can_undo": bool(session.undo), "can_redo": bool(session.redo),
                "source": {"media_type": session.source.media_type, "pages": session.source.pages} if session.source else None,
                "musicxml_base64": b64encode(session.document.xml()).decode("ascii")}

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
            updated = replace(session, document=candidate, state="REVIEW_REQUIRED", revision=session.revision + 1,
                              sequence=sequence, undo=self._history(session.undo + [session.document]), redo=[])
            self.store.put(updated)  # Commit only after the edit and quotas succeed.
            return self.payload(updated)

    def event_patch(self, identifier, revision, event_id, patch: EventPatch):
        return self.edit(identifier, revision, lambda doc, _: patch_event(doc, event_id, patch))

    def event_add(self, identifier, revision, request: EventAdd):
        return self.edit(identifier, revision, lambda doc, new_id: add_event(doc, new_id, request))

    def event_delete(self, identifier, revision, event_id):
        return self.edit(identifier, revision, lambda doc, _: delete_event(doc, event_id))

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
            _, issues = import_score(session.document)
            if any(issue.severity == "ERROR" for issue in issues):
                raise ReviewError("Correct all validation errors before marking this review VERIFIED.", 409)
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

    def source(self, identifier):
        with self.store.lock:
            source = self.store.get(identifier).source
            if source is None:
                raise ReviewError("This review has no retained original source.", 404)
            return source

    def delete(self, identifier):
        with self.store.lock:
            self.store.delete(identifier)
