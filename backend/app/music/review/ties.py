"""Explicit, undoable human tie corrections; no recognition inference."""
from fractions import Fraction
from xml.etree import ElementTree as ET

from .document import ReviewError, local
from .importer import import_score, rational, xml_number
from .models import Diagnostic


def entries_for(score):
    return {e.id: (p, m, e) for p in score.parts for m in p.measures
            for v in m.voices for e in v.events}


def check_link(doc, source_id, target_id, *, check_rhythm=False, entries=None):
    if entries is None:
        score, _ = import_score(doc)
        entries = entries_for(score)
    if source_id not in entries or target_id not in entries:
        raise ReviewError("Both tie endpoints must exist.", 404)
    part, measure, source = entries[source_id]
    other_part, other_measure, target = entries[target_id]
    if source_id == target_id or part.id != other_part.id:
        raise ReviewError("Tie endpoints must be distinct notes in the same part.")
    for event, endpoint_measure in ((source, measure), (target, other_measure)):
        if event.kind != "note" or event.grace or not event.pitch or event.duration is None or event.onset is None:
            raise ReviewError("Ties require duration-bearing pitched notes with known timing.")
        if (event.pitch.step not in tuple("ABCDEFG") or event.pitch.octave is None
                or not 0 <= event.pitch.octave <= 9 or xml_number(event.pitch.alter) is None
                or rational(event.duration) is None or not 0 < rational(event.duration) <= 1024
                or rational(event.onset) is None or rational(event.onset) < 0
                or event.staff is None or not 1 <= event.staff <= endpoint_measure.staves
                or not event.voice or any(c.isspace() for c in event.voice)):
            raise ReviewError("Tie endpoints need valid pitch, duration, onset, voice and staff.")
        if doc.child(doc.refs[event.id], "cue") is not None:
            raise ReviewError("Explicit cue notes cannot be connected by this correction operation.")
    if (source.pitch.step, Fraction(source.pitch.alter), source.pitch.octave, source.voice, source.staff) != (
            target.pitch.step, Fraction(target.pitch.alter), target.pitch.octave, target.voice, target.staff):
        raise ReviewError("Tie endpoints must have matching pitch, voice and staff.")
    end = Fraction(source.onset) + Fraction(source.duration)
    if other_measure.id == measure.id:
        contiguous = end == Fraction(target.onset)
    else:
        contiguous = (other_measure.index == measure.index + 1 and measure.expected_duration is not None
                      and end == Fraction(measure.expected_duration) and Fraction(target.onset) == 0)
    if not contiguous:
        raise ReviewError("Tie target must immediately follow the source note in musical time.")
    for p, m, e in entries.values():
        if p.id == part.id and e.voice == source.voice and e.id not in (source_id, target_id) and e.onset is not None:
            if (m.id == measure.id and Fraction(source.onset) < Fraction(e.onset) < end):
                raise ReviewError("An intervening event prevents this tie connection.")
    if check_rhythm:
        # Insertion changes time. Tie-only corrections preserve existing diagnostics.
        from app.music.recovery.musicxml import XmlContext, rhythm
        affected = {measure.id, other_measure.id}
        rhythm_issues = rhythm(XmlContext(doc))
        if any(i["severity"] == "ERROR" for mid in affected for i in rhythm_issues[mid]["diagnostics"]):
            raise ReviewError("The insertion makes the endpoint measures rhythmically invalid.")
    return measure.id


def has(doc, note, kind, visual=False):
    parent = doc.child(note, "notations") if visual else note
    return parent is not None and any(n.get("type") == kind for n in doc.children(parent, "tied" if visual else "tie"))


def mark(doc, note, kind, visual=False):
    from .patcher import put, NOTE_ORDER
    if has(doc, note, kind, visual):
        return False
    parent = put(doc, note, "notations") if visual else note
    node = ET.Element(doc.namespace + ("tied" if visual else "tie"), {"type": kind})
    # Stops precede starts for a continuation. Sound ties precede voice/type.
    if visual:
        position = next((i for i, n in enumerate(parent) if n.tag == doc.namespace + "tied" and kind == "stop"), len(parent))
    else:
        position = next((i for i, n in enumerate(parent) if n.tag == doc.namespace + "tie" and kind == "stop"
                         or local(n.tag) in NOTE_ORDER
                         and NOTE_ORDER.index(local(n.tag)) > NOTE_ORDER.index("tie")), len(parent))
    parent.insert(position, node)
    return True


def connect(doc, source_id, target_id, *, check_rhythm=True):
    check_link(doc, source_id, target_id, check_rhythm=check_rhythm)
    if any(link["target"] == target_id for link in doc.manual_ties.values()):
        raise ReviewError("This target already has a manually connected tie stop.")
    source, target = doc.refs[source_id], doc.refs[target_id]
    created_source_notations = doc.child(source, "notations") is None
    mark(doc, source, "start")
    mark(doc, source, "start", True)
    created_notations = doc.child(target, "notations") is None
    doc.manual_ties[source_id] = {"target": target_id, "created_notations": created_notations, "created_source_notations": created_source_notations, "sound": mark(doc, target, "stop"),
                                  "visual": mark(doc, target, "stop", True)}
    doc.manual_changes[target_id] = sorted(set(doc.manual_changes.get(target_id, [])) | {"tie_stop"})


def diagnostics(doc):
    result = []
    for source, link in doc.manual_ties.items():
        try:
            mid = check_link(doc, source, link["target"])
            if not all(has(doc, doc.refs[key], kind, visual) for key, kind in ((source, "start"), (link["target"], "stop")) for visual in (False, True)):
                raise ReviewError("A manually connected tie endpoint is missing its tie markup.")
        except ReviewError as error:
            node = doc.refs.get(source)
            parent = doc.parent(node) if node is not None else None
            mid = next((key for key, value in doc.refs.items() if value is parent), None)
            result.append(Diagnostic("invalid_manual_tie", str(error), "ERROR", mid, source))
    return result


def disconnect_deleted(doc, event_id):
    for source, link in list(doc.manual_ties.items()):
        if event_id not in (source, link["target"]):
            continue
        counterpart, kind = (link["target"], "stop") if event_id == source else (source, "start")
        note = doc.refs[counterpart]
        for visual, owned in ((False, link["sound"]), (True, link["visual"])):
            if event_id == source and not owned:
                continue
            parent = doc.child(note, "notations") if visual else note
            if parent is not None:
                for node in doc.children(parent, "tied" if visual else "tie"):
                    if node.get("type") == kind:
                        parent.remove(node)
                if visual and (link.get("created_source_notations", True) if event_id != source else link["created_notations"]) and not len(parent) and not parent.attrib and not (parent.text or "").strip():
                    note.remove(parent)
        doc.manual_changes[counterpart] = sorted(set(doc.manual_changes.get(counterpart, [])) | {"tie_" + kind})
        del doc.manual_ties[source]


def targets(doc, source_id, entries):
    """Same compatibility policy for discovery and mutations, without changing rhythm."""
    if source_id not in entries:
        return []
    part, measure, source = entries[source_id]
    if source.kind != "note" or source.grace or source.duration is None or source.onset is None:
        return []
    result = []
    for target_id, (p, m, target) in entries.items():
        if p.id != part.id or m.index not in (measure.index, measure.index + 1) or target.voice != source.voice:
            continue
        if any(key != source_id and link["target"] == target_id for key, link in doc.manual_ties.items()):
            continue
        try:
            check_link(doc, source_id, target_id, entries=entries)
        except ReviewError:
            continue
        result.append(target_id)
    return result


def current_target(doc, source_id, entries):
    link = doc.manual_ties.get(source_id)
    if link:
        return link["target"]
    source = doc.refs[source_id]
    if not (has(doc, source, "start") or has(doc, source, "start", True)):
        return None
    candidates = [key for key in targets(doc, source_id, entries)
                  if has(doc, doc.refs[key], "stop") or has(doc, doc.refs[key], "stop", True)]
    return candidates[0] if len(candidates) == 1 else None


def tie_info(doc, score):
    entries = entries_for(score)
    current = {key: current_target(doc, key, entries) for key in entries}
    incoming = {}
    for source, target in current.items():
        if target is not None:
            incoming.setdefault(target, set()).add(source)
    return {key: {"tie_target_id": current[key],
                  "tie_target_ids": [target for target in targets(doc, key, entries)
                                     if not incoming.get(target, set()) - {key}]} for key in entries}



def remove_endpoint(doc, note, kind, remove_empty=True):
    for visual in (False, True):
        parent = doc.child(note, "notations") if visual else note
        if parent is None:
            continue
        for node in doc.children(parent, "tied" if visual else "tie"):
            if node.get("type") == kind:
                parent.remove(node)
        if visual and remove_empty and not len(parent) and not parent.attrib and not (parent.text or "").strip():
            note.remove(parent)


def set_target(doc, source_id, target_id):
    """Add/change/remove one outgoing relationship inside the caller's cloned edit."""
    source = doc.get(source_id, "note")
    score, _ = import_score(doc)
    entries = entries_for(score)
    old_target = current_target(doc, source_id, entries)
    if old_target is None and (has(doc, source, "start") or has(doc, source, "start", True)):
        raise ReviewError("The existing tie target cannot be resolved unambiguously; repair it in a notation editor.")
    if target_id is not None:
        check_link(doc, source_id, target_id, entries=entries)
        # A preexisting incoming relationship cannot be stolen from another source.
        if any(key != source_id and current_target(doc, key, entries) == target_id for key in entries):
            raise ReviewError("The target already has an incoming tie from another note.")
    if target_id == old_target:
        raise ReviewError("Choose a different tie target or remove the existing tie.")
    endpoints = [(source, "start")]
    if old_target is not None:
        endpoints.append((doc.refs[old_target], "stop"))
    if target_id is not None:
        endpoints.append((doc.refs[target_id], "stop"))
    for note, kind in endpoints:
        if (sum(n.get("type") == kind for n in doc.children(note, "tie")) > 1
                or sum(n.get("type") == kind for n in note.findall(f"{doc.namespace}notations/{doc.namespace}tied")) > 1):
            raise ReviewError("Duplicate tie endpoints require repair in a notation editor.")
    if old_target is not None:
        link = doc.manual_ties.pop(source_id, {})
        remove_endpoint(doc, source, "start", link.get("created_source_notations", True))
        remove_endpoint(doc, doc.refs[old_target], "stop", link.get("created_notations", True))
        doc.manual_changes[old_target] = sorted(set(doc.manual_changes.get(old_target, [])) | {"tie_stop"})
    if target_id is not None:
        connect(doc, source_id, target_id, check_rhythm=False)
    doc.manual_changes[source_id] = sorted(set(doc.manual_changes.get(source_id, [])) | {"tie_start"})
    doc.changed = True
