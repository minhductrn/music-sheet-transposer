"""Explicit, undoable human tie corrections; no recognition inference."""
from fractions import Fraction
from uuid import uuid4
from xml.etree import ElementTree as ET

from .document import ReviewError, local
from .importer import import_score, rational, xml_number
from .models import Diagnostic


def entries_for(score):
    return {e.id: (p, m, e) for p in score.parts for m in p.measures
            for v in m.voices for e in v.events}


def check_link(doc, source_id, target_id, *, entries=None):
    if entries is None:
        score, _ = import_score(doc)
        entries = entries_for(score)
    if source_id not in entries or target_id not in entries:
        raise ReviewError("Both tie endpoints must exist.", 404)
    part, measure, source = entries[source_id]
    other_part, _, target = entries[target_id]
    if source_id == target_id or part.id != other_part.id:
        raise ReviewError("Tie endpoints must be distinct notes in the same part.")
    for event in (source, target):
        check_link_source(doc, event.id, entries)
    return measure.id


def musical_link_issue(doc, source_id, target_id, entries):
    """Conventional tie rules are advisory, never correction eligibility."""
    part, measure, source = entries[source_id]
    _, other_measure, target = entries[target_id]
    def sounding(pitch):
        return pitch.octave * 12 + dict(C=0, D=2, E=4, F=5, G=7, A=9, B=11)[pitch.step] + Fraction(pitch.alter)
    if sounding(source.pitch) != sounding(target.pitch):
        return "tie_pitch_mismatch", "These user-selected tie endpoints have different sounding pitches. Compare with the source; no pitch was changed."
    if (source.voice, source.staff) != (target.voice, target.staff):
        return "tie_voice_staff", "These tie endpoints use different voices or staves. Compare with the source; neither endpoint was moved."
    if source.grace or target.grace or source.onset is None or target.onset is None or source.duration is None:
        return "tie_timing", "The timing of these tie endpoints cannot be checked conventionally. Compare with the source."
    end = Fraction(source.onset) + Fraction(source.duration)
    contiguous = end == Fraction(target.onset) if other_measure.id == measure.id else (
        other_measure.index == measure.index + 1 and measure.expected_duration is not None
        and end == Fraction(measure.expected_duration) and Fraction(target.onset) == 0)
    intervening = any(p.id == part.id and e.voice == source.voice and e.id not in (source_id, target_id)
                      and m.id == measure.id and e.onset is not None and Fraction(source.onset) < Fraction(e.onset) < end
                      for p, m, e in entries.values())
    if not contiguous or intervening:
        return "tie_timing", "These tie endpoints do not follow each other in conventional musical time. Compare with the source; rhythm was not changed."
    return None


def endpoint_nodes(doc, note, kind, visual=False):
    parents = doc.children(note, "notations") if visual else [note]
    return [(parent, n) for parent in parents for n in doc.children(parent, "tied" if visual else "tie") if n.get("type") == kind]


def endpoint_signature(node):
    # Attribute order and indentation are not different musical markings.
    return tuple(sorted(node.attrib.items())), (node.text or "").strip(), tuple(ET.tostring(c) for c in node)


def endpoint_safe(doc, note, kind):
    for visual in (False, True):
        nodes = endpoint_nodes(doc, note, kind, visual)
        if visual and any(n.get("number") is not None and n.get("number") not in {str(i) for i in range(1, 17)} for _, n in nodes):
            raise ReviewError("The selected tie endpoint has an invalid MusicXML number; its markings were preserved.")
        if len({endpoint_signature(n) for _, n in nodes}) > 1:
            raise ReviewError("This endpoint has distinct tie markings (numbers, repeat scopes or formatting). The single-relationship correction cannot choose among them safely; existing markings were preserved.")


def deduplicate_endpoint(doc, note, kind):
    """Only the explicitly edited endpoint; retain its first identical marking."""
    changed = False
    for visual in (False, True):
        seen = set()
        for parent, node in endpoint_nodes(doc, note, kind, visual):
            signature = endpoint_signature(node)
            if signature in seen:
                parent.remove(node)
                changed = True
            else:
                seen.add(signature)
    return changed


def has(doc, note, kind, visual=False):
    return bool(endpoint_nodes(doc, note, kind, visual))


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
    # check_rhythm is retained for insertion callers; musical findings are advisory.
    check_link(doc, source_id, target_id)
    score, _ = import_score(doc)
    entries = entries_for(score)
    advisory = musical_link_issue(doc, source_id, target_id, entries)
    source, target = doc.refs[source_id], doc.refs[target_id]
    deduplicate_endpoint(doc, source, "start")
    deduplicate_endpoint(doc, target, "stop")
    part = doc.refs[entries[source_id][0].id]
    used = {"1"} | {n.get("number", "1") for n in part.iter(doc.namespace + "tied") if n.get("type") in {"start", "stop", "continue"}}
    number = next((str(n) for n in range(2, 17) if str(n) not in used), None)
    if number is None:
        raise ReviewError("All 15 explicit MusicXML tie numbers (2–16) are occupied in this part; the requested pair cannot be serialized without colliding with preserved tie markings.")
    source_sound = mark(doc, source, "start")
    target_sound = mark(doc, target, "stop")
    token = "review-tie-" + uuid4().hex + f"-s{int(source_sound)}-t{int(target_sound)}"
    link = {"target": target_id, "number": number, "source_visual_id": token + "-start", "target_visual_id": token + "-stop",
            "created_source_notations": doc.child(source, "notations") is None,
            "created_notations": doc.child(target, "notations") is None,
            "source_sound": source_sound, "sound": target_sound, "visual": True}
    from .patcher import put
    for note, kind, key in ((source, "start", "source_visual_id"), (target, "stop", "target_visual_id")):
        parent = put(doc, note, "notations")
        node = ET.Element(doc.namespace + "tied", {"type": kind, "number": number, "id": link[key]})
        position = next((i for i, n in enumerate(parent) if local(n.tag) == "tied"), len(parent)) if kind == "stop" else len(parent)
        parent.insert(position, node)
    doc.manual_ties[source_id] = link
    doc.manual_changes[target_id] = sorted(set(doc.manual_changes.get(target_id, [])) | {"tie_stop"})


def diagnostics(doc):
    score, _ = import_score(doc)
    entries = entries_for(score)
    result = []
    for source, link in doc.manual_ties.items():
        mid = entries[source][1].id if source in entries else None
        try:
            mid = check_link(doc, source, link.get("target"), entries=entries)
            if not all(any(n.get("id") == link.get(field) for _, n in endpoint_nodes(doc, doc.refs[key], kind, True)) for key, kind, field in ((source, "start", "source_visual_id"), (link.get("target"), "stop", "target_visual_id"))):
                raise ReviewError("A manually connected tie endpoint is missing its tie markup.")
            advisory = musical_link_issue(doc, source, link.get("target"), entries)
            if advisory:
                result.append(Diagnostic(*advisory, "WARNING", mid, source))
        except ReviewError as error:
            result.append(Diagnostic("invalid_manual_tie", str(error), "ERROR", mid, source))
    for key, (_, measure, _) in entries.items():
        note = doc.refs[key]
        if key not in doc.manual_ties and (has(doc, note, "start") or has(doc, note, "start", True)):
            target = current_target(doc, key, entries)
            if target is None:
                result.append(Diagnostic("tie_unresolved", "An imported tie start has no uniquely identified target. Choose its target explicitly with Tie; existing endpoints are preserved.", "WARNING", measure.id, key))
            else:
                try:
                    check_link(doc, key, target, entries=entries)
                    advisory = musical_link_issue(doc, key, target, entries)
                    if advisory:
                        result.append(Diagnostic(*advisory, "WARNING", measure.id, key))
                except ReviewError:
                    pass  # The importer already reports malformed note fields.

        sound = doc.children(note, "tie")
        visual = [n for parent in doc.children(note, "notations") for n in doc.children(parent, "tied")]
        if (any(n.get("type") not in {"start", "stop"} for n in sound)
                or any(n.get("type") not in {"start", "stop", "continue", "let-ring"}
                       or n.get("number", "1") not in {str(i) for i in range(1, 17)} for n in visual)):
            result.append(Diagnostic("invalid_tie_markup", "A tie has invalid MusicXML type or number data. Correct its representation before verifying; no markup was changed.", "ERROR", measure.id, key))
        for kind in ("start", "stop"):
            if any(len(endpoint_nodes(doc, note, kind, visual)) > 1 for visual in (False, True)):
                result.append(Diagnostic("tie_duplicate", "This note has repeated or distinct tie endpoint markings. They are preserved until you explicitly edit the relationship.", "WARNING", measure.id, key))
    return result


def remove_owned(doc, source_id, link):
    """Remove precisely the nodes introduced by this explicit relationship."""
    for key, kind, visual_id, sound_owned in (
            (source_id, "start", link.get("source_visual_id"), link.get("source_sound", True)),
            (link.get("target"), "stop", link.get("target_visual_id"), link.get("sound", False))):
        note = doc.refs.get(key)
        if note is None:
            continue
        for parent, node in endpoint_nodes(doc, note, kind, True):
            if visual_id and node.get("id") == visual_id:
                parent.remove(node)
        if sound_owned and kind == "stop":
            others = [(other_source, other) for other_source, other in doc.manual_ties.items()
                      if other_source != source_id and other.get("target") == key]
            if others:
                other_source, other = others[0]
                other["sound"] = True
                # Transfer shared sound-node ownership, including its export identity.
                for endpoint, field, endpoint_kind in ((other_source, "source_visual_id", "start"), (key, "target_visual_id", "stop")):
                    previous_id = other.get(field, "")
                    replacement_id = previous_id.replace("-t0-", "-t1-")
                    for _, marker in endpoint_nodes(doc, doc.refs[endpoint], endpoint_kind, True):
                        if marker.get("id") == previous_id:
                            marker.set("id", replacement_id)
                    other[field] = replacement_id
                sound_owned = False
        if sound_owned:
            for parent, node in endpoint_nodes(doc, note, kind):
                if node.attrib == {"type": kind}:
                    parent.remove(node)
                    break
        for parent in doc.children(note, "notations"):
            if not len(parent) and not parent.attrib and not (parent.text or "").strip():
                note.remove(parent)
        doc.manual_changes[key] = sorted(set(doc.manual_changes.get(key, [])) | {"tie_" + kind})


def disconnect_deleted(doc, event_id):
    for source, link in list(doc.manual_ties.items()):
        if event_id in (source, link.get("target")):
            remove_owned(doc, source, link)
            del doc.manual_ties[source]


def targets(doc, source_id, entries):
    result = []
    for target_id in entries:
        try:
            check_link(doc, source_id, target_id, entries=entries)
        except ReviewError:
            continue
        result.append(target_id)
    return result


def current_target(doc, source_id, entries):
    link = doc.manual_ties.get(source_id)
    if link:
        return link.get("target")
    source = doc.refs[source_id]
    if not (has(doc, source, "start") or has(doc, source, "start", True)):
        return None
    try:
        endpoint_safe(doc, source, "start")
    except ReviewError:
        return None
    # Imported numbering can identify an explicit pair without conventional theory.
    part = entries[source_id][0]
    visual_starts = endpoint_nodes(doc, source, "start", True)
    numbers = {n.get("number") for _, n in visual_starts}
    if len(numbers) == 1 and None not in numbers:
        number = next(iter(numbers))
        starts = {key for key, (p, _, _) in entries.items() if p.id == part.id and any(n.get("number") == number for _, n in endpoint_nodes(doc, doc.refs[key], "start", True))}
        stops = {key for key, (p, _, _) in entries.items() if p.id == part.id and any(n.get("number") == number for _, n in endpoint_nodes(doc, doc.refs[key], "stop", True))}
        if starts == {source_id} and len(stops) == 1 and source_id not in stops:
            return next(iter(stops))
    # Legacy unnumbered relationships resolve only a unique conventional match.
    candidates = []
    for key in entries:
        try:
            check_link(doc, source_id, key, entries=entries)
            if musical_link_issue(doc, source_id, key, entries) is not None:
                continue
            if not (has(doc, doc.refs[key], "stop") or has(doc, doc.refs[key], "stop", True)):
                continue
            target_numbers = {n.get("number") for _, n in endpoint_nodes(doc, doc.refs[key], "stop", True)}
            if numbers and target_numbers and numbers != target_numbers:
                continue
            candidates.append(key)
        except ReviewError:
            continue
    return candidates[0] if len(candidates) == 1 else None


def direction_endpoints(doc, source_id, entries):
    """Resolve existing visual endpoints without authoring a relationship."""
    target_id = current_target(doc, source_id, entries)
    if target_id is None:
        raise ReviewError("Tie direction requires a uniquely resolved existing relationship.")
    check_link(doc, source_id, target_id, entries=entries)
    link = doc.manual_ties.get(source_id)
    endpoints = []
    for key, kind, field in ((source_id, "start", "source_visual_id"), (target_id, "stop", "target_visual_id")):
        nodes = [n for _, n in endpoint_nodes(doc, doc.refs[key], kind, True)]
        if link:
            nodes = [n for n in nodes if n.get("id") == link.get(field) and n.get("number") == link.get("number")]
            owners = [n for n in doc.root.iter(doc.namespace + "tied") if n.get("id") == link.get(field)]
            if len(owners) != 1:
                raise ReviewError("Tie direction cannot resolve duplicated visual endpoint identities.")
        if len(nodes) != 1:
            raise ReviewError("Tie direction requires one matching visual endpoint at each note.")
        endpoints.append(nodes[0])
    if endpoints[0].get("number") != endpoints[1].get("number"):
        raise ReviewError("Tie direction requires matching visual endpoint numbers.")
    return endpoints


def explicit_direction(endpoints):
    directions = []
    for node in endpoints:
        direction = {"over": "up", "under": "down"}.get(node.get("orientation"))
        if direction is None:
            direction = {"above": "up", "below": "down"}.get(node.get("placement"))
        directions.append(direction)
    return directions[0] if directions[0] == directions[1] else None


def set_direction(doc, source_id, direction):
    score, _ = import_score(doc)
    endpoints = direction_endpoints(doc, source_id, entries_for(score))
    orientation = {"up": "over", "down": "under"}[direction]
    if all(n.get("orientation") == orientation for n in endpoints):
        return False
    for node in endpoints:
        node.set("orientation", orientation)
    doc.changed = True
    return True


def tie_info(doc, score):
    entries = entries_for(score)
    current = {key: current_target(doc, key, entries) for key in entries}
    result = {}
    for key in entries:
        error = None
        try:
            check_link_source(doc, key, entries)
        except ReviewError as issue:
            error = str(issue)
        link = doc.manual_ties.get(key)
        direction, direction_editable = None, False
        try:
            direction = explicit_direction(direction_endpoints(doc, key, entries))
            direction_editable = True
        except ReviewError:
            pass
        result[key] = {"tie_target_id": current[key], "tie_correction_error": error, "tie_source_editable": error is None,
                       "tie_direction": direction, "tie_direction_editable": direction_editable,
                       "tie_target_ids": [] if error else targets(doc, key, entries),
                       "tie_relationship": {"source_event_id": key, "target_event_id": link["target"], "origin": link.get("origin", "USER_CORRECTION"), "source_visual_id": link["source_visual_id"], "target_visual_id": link["target_visual_id"]} if link and link.get("target") in entries and link.get("source_visual_id") else None}
    return result


def check_link_source(doc, source_id, entries):
    # Validate a single endpoint without creating a dummy/self relationship.
    _, measure, event = entries[source_id]
    if event.kind != "note" or not event.pitch:
        raise ReviewError("Select a pitched note to start a tie.")
    note = doc.get(source_id, "note")
    if len(doc.children(note, "pitch")) != 1 or doc.child(note, "rest") is not None or doc.child(note, "unpitched") is not None:
        raise ReviewError("A tie endpoint needs exactly one pitched MusicXML note; its current note-kind markup is ambiguous.")
    if event.cue:
        raise ReviewError("Explicit cue notes cannot carry sound ties in MusicXML.")
    if (event.pitch.step not in tuple("ABCDEFG") or event.pitch.octave is None or not 0 <= event.pitch.octave <= 9
            or xml_number(event.pitch.alter) is None or not event.voice or len(event.voice) > 32 or any(c.isspace() for c in event.voice)
            or event.staff is None or not 1 <= event.staff <= measure.staves
            or (not event.grace and (rational(event.duration) is None or not 0 < rational(event.duration) <= 1024))
            or (event.onset is not None and (rational(event.onset) is None or rational(event.onset) < 0))
            or (event.grace and doc.child(note, "duration") is not None)):
        raise ReviewError("The tie source has malformed pitch, duration, voice or staff data; correct those fields first.")


def remove_endpoint(doc, note, kind, remove_empty=True):
    for visual in (False, True):
        parents = doc.children(note, "notations") if visual else [note]
        for parent in parents:
            for owner, node in endpoint_nodes(doc, note, kind, visual):
                if owner is parent:
                    parent.remove(node)
            if visual and remove_empty and not len(parent) and not parent.attrib and not (parent.text or "").strip():
                note.remove(parent)


def set_target(doc, source_id, target_id):
    """An explicit choice authors a relationship; raw fragments never prove it."""
    source = doc.get(source_id, "note")
    score, _ = import_score(doc)
    entries = entries_for(score)
    link = doc.manual_ties.get(source_id)
    if link and link.get("target") not in entries:
        raise ReviewError("The existing tie target no longer exists. Reload the score; no relationship was changed.", 409)
    if target_id is not None:
        check_link(doc, source_id, target_id, entries=entries)
    if link and link.get("target") == target_id and link.get("source_visual_id"):
        complete = all(any(n.get("id") == link.get(field) and n.get("number") == link.get("number") for _, n in endpoint_nodes(doc, doc.refs[key], kind, True))
                       for key, kind, field in ((source_id, "start", "source_visual_id"), (target_id, "stop", "target_visual_id")))
        changed = any([deduplicate_endpoint(doc, doc.refs[key], kind) for key, kind in ((source_id, "start"), (target_id, "stop"))])
        if complete and not changed:
            return False
        if complete:
            doc.changed = True
            return True
    if link:
        remove_owned(doc, source_id, link)
        del doc.manual_ties[source_id]
    elif target_id is None:
        # Legacy imported removal is allowed only for a uniquely resolved pair.
        old_target = current_target(doc, source_id, entries)
        if old_target is None:
            raise ReviewError("Choose an explicit target with Tie before removing unresolved imported fragments.")
        endpoint_safe(doc, source, "start")
        endpoint_safe(doc, doc.refs[old_target], "stop")
        remove_endpoint(doc, source, "start")
        remove_endpoint(doc, doc.refs[old_target], "stop")
    if target_id is not None:
        connect(doc, source_id, target_id, check_rhythm=False)
    doc.manual_changes[source_id] = sorted(set(doc.manual_changes.get(source_id, [])) | {"tie_start"})
    doc.changed = True
    return True


def restore_explicit_relationships(doc):
    """Recover our paired XML identities; never promote arbitrary scanner fragments."""
    import re
    notes = {key: note for key, note in doc.refs.items() if local(note.tag) == "note"}
    for source, note in notes.items():
        starts = endpoint_nodes(doc, note, "start", True)
        identifiers = {n.get("id", "") for _, n in starts}
        links = []
        for identifier in identifiers:
            match = re.fullmatch(r"review-tie-[0-9a-f]{32}-s([01])-t([01])-start", identifier)
            if not match:
                continue
            stop_id = identifier[:-6] + "-stop"
            destinations = [key for key, target in notes.items() if any(n.get("id") == stop_id for _, n in endpoint_nodes(doc, target, "stop", True))]
            owners = [key for key, candidate in notes.items() if any(n.get("id") == identifier for _, n in endpoint_nodes(doc, candidate, "start", True))]
            if len(destinations) != 1 or owners != [source] or destinations[0] == source:
                continue
            target = destinations[0]
            start_numbers = {n.get("number") for _, n in starts if n.get("id") == identifier}
            stop_numbers = {n.get("number") for _, n in endpoint_nodes(doc, notes[target], "stop", True) if n.get("id") == stop_id}
            if (start_numbers == stop_numbers and len(start_numbers) == 1
                    and next(iter(start_numbers)) in {str(i) for i in range(2, 17)}
                    and doc.parent(doc.parent(note)) is doc.parent(doc.parent(notes[target]))):
                links.append({"target": destinations[0], "source_visual_id": identifier, "target_visual_id": stop_id,
                              "source_sound": match[1] == "1", "sound": match[2] == "1", "visual": True, "number": next(iter(start_numbers)), "origin": "EXPORTED_CORRECTION"})
        if len(links) == 1:
            doc.manual_ties[source] = links[0]
