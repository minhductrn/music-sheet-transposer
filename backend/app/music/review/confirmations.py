"""Scoped source comparison sidecars. Technical diagnostics are never waivable; music review is advisory."""
from hashlib import sha256
from xml.etree import ElementTree as ET

from .document import ReviewError

from .music_check import MUSIC_CODES, category

SOURCE_CODES = MUSIC_CODES


def identity(issue):
    return sha256(f'{issue.code}|{issue.measure_id}|{issue.event_id}'.encode()).hexdigest()


def fingerprint(doc, measure_id):
    measure = doc.get(measure_id, "measure")
    part = doc.parent(measure)
    # Include inherited structural context; unrelated earlier notes do not revoke it.
    context = []
    for previous in doc.children(part, "measure"):
        if previous is measure:
            break
        context.extend(ET.tostring(a) for a in doc.children(previous, "attributes"))
    return sha256(b"\0".join(context + [ET.tostring(measure)])).hexdigest()


def diagnostics(doc, issues):
    result = []
    for issue in issues:
        allowed = issue.code in SOURCE_CODES and issue.measure_id is not None
        key = identity(issue)
        decision = doc.source_confirmations.get(key)
        current = bool(allowed and decision and not decision.get("invalidated_revision") and decision["fingerprint"] == fingerprint(doc, issue.measure_id))
        result.append({**vars(issue), "id": key, "can_confirm_source": allowed,
                       "source_confirmed": current,
                       "category": category(issue),
                       "blocking": category(issue) == "TECHNICAL_ERROR",
                       "source_confirmation": {**decision, "status": "CURRENT" if current else "STALE"} if decision else None})
    return result


def confirm(doc, issues, request, revision):
    issue = next((i for i in issues if identity(i) == request.diagnostic_id), None)
    if issue is None:
        raise ReviewError("The diagnostic no longer exists. Reload the review.", 409)
    if issue.code not in SOURCE_CODES or issue.measure_id is None:
        raise ReviewError("Technical representation failures cannot be source-confirmed.")
    doc.source_confirmations[request.diagnostic_id] = {
        "code": issue.code, "measure_id": issue.measure_id, "event_id": issue.event_id,
        "fingerprint": fingerprint(doc, issue.measure_id), "note": request.note.strip(), "revision": revision,
    }
