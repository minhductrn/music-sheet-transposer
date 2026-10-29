"""Small, explicit edits to preserved nodes. Timing events are never regenerated."""

from copy import deepcopy
from fractions import Fraction
from xml.etree import ElementTree as ET

from app.music.review.document import Document, ReviewError, local
from app.music.review.importer import import_score, rational
from app.music.review.models import EventAdd, EventPatch, HarmonyPatch, PitchInput


NOTE_ORDER = "grace cue chord pitch rest unpitched duration tie instrument footnote level voice type dot accidental time-modification stem notehead notehead-text staff beam notations lyric play listen".split()
HARMONY_ORDER = "root numeral function kind inversion bass degree frame offset footnote level staff".split()
ROOT_ORDER = "work movement-number movement-title identification defaults credit part-list part".split()
PITCH_ORDER = "step alter octave".split()


def put(doc, parent, name, text=None, order=None):
    element = doc.child(parent, name)
    if element is None:
        element = ET.Element(doc.namespace + name)
        order = order or NOTE_ORDER
        rank = order.index(name) if name in order else len(order)
        position = next((i for i, child in enumerate(parent) if local(child.tag) in order and order.index(local(child.tag)) > rank), len(parent))
        parent.insert(position, element)
    if text is not None:
        element.text = str(text)
    return element


def remove(doc, parent, name):
    for child in doc.children(parent, name):
        parent.remove(child)


def pitch_patch(doc, note, pitch: PitchInput):
    if doc.child(note, "rest") is not None or doc.child(note, "unpitched") is not None:
        raise ReviewError("Pitch edits require a pitched note. Add a note to replace a rest/unpitched event.")
    node = put(doc, note, "pitch")
    put(doc, node, "step", pitch.step, PITCH_ORDER)
    if Fraction(pitch.alter):
        put(doc, node, "alter", pitch.alter, PITCH_ORDER)
    else:
        remove(doc, node, "alter")
    put(doc, node, "octave", pitch.octave, PITCH_ORDER)
    accidental = doc.child(note, "accidental")
    if accidental is not None:
        spelling = {Fraction(-2): "flat-flat", Fraction(-1): "flat", Fraction(0): "natural", Fraction(1): "sharp", Fraction(2): "double-sharp"}.get(Fraction(pitch.alter))
        if spelling:
            accidental.text = spelling
        else:
            remove(doc, note, "accidental")  # Alter still retains the exact sounding pitch.


def size_patch(doc, note, size):
    note_type = doc.child(note, "type")
    if note_type is None and size == "cue":
        raise ReviewError("A size edit requires a note type; correct its duration first.")
    head = doc.child(note, "notehead")
    note.attrib.pop("font-size", None)
    if size == "small":
        # Valid MusicXML visual attributes; neither introduces <grace> or <cue> timing.
        if note_type is not None:
            note_type.set("size", "cue")
        put(doc, note, "notehead", head.text if head is not None else "normal").set("font-size", "small")
    elif size == "cue":
        note_type.set("size", "cue")
        if head is not None:
            head.attrib.pop("font-size", None)
    else:
        if note_type is not None:
            if doc.child(note, "cue") is not None:
                note_type.set("size", "normal")
            else:
                note_type.attrib.pop("size", None)
        if head is not None:
            head.attrib.pop("font-size", None)
        # Explicit cue semantics are retained. Size alone must not rewrite rhythmic semantics.


def group(doc, note):
    measure = doc.parent(note)
    children = list(measure)
    index = children.index(note)
    while doc.child(children[index], "chord") is not None and index > 0 and local(children[index - 1].tag) == "note":
        index -= 1
    result = [children[index]]
    index += 1
    while index < len(children) and local(children[index].tag) == "note" and doc.child(children[index], "chord") is not None:
        result.append(children[index])
        index += 1
    return result


def context(doc, note=None, measure_id=None):
    score, _ = import_score(doc)
    for part in score.parts:
        for measure in part.measures:
            if measure_id == measure.id:
                return measure, None
            for voice in measure.voices:
                for event in voice.events:
                    if note is not None and doc.refs[event.id] is note:
                        # Divisions can change inside a measure; event units/duration is authoritative.
                        measure.divisions = event.divisions
                        return measure, event
    raise ReviewError("The requested measure/event does not exist.", 404)


def duration_patch(doc, note, duration: str, divisions, grace=False):
    value, scale = rational(duration), rational(divisions)
    if value is None or value <= 0 or value > 1024 or scale is None or scale <= 0:
        raise ReviewError("Duration must be positive quarter beats with valid divisions (maximum 1024 beats).")
    units = value * scale
    if units.denominator != 1:
        raise ReviewError("That duration cannot be represented with this measure's divisions.")
    visual = value
    modification = doc.child(note, "time-modification")
    if modification is not None:
        normal_type=doc.child(modification, "normal-type")
        if normal_type is not None and doc.text(modification,"normal-type") not in {"whole","half","quarter","eighth","16th","32nd","64th"}:
            raise ReviewError("This tuplet normal-type requires an unsupported notation value.")
        actual, normal = rational(doc.text(modification, "actual-notes")), rational(doc.text(modification, "normal-notes"))
        if not actual or not normal or actual <= 0 or normal <= 0:
            raise ReviewError("Correct this note's invalid tuplet in a notation editor before changing duration.")
        visual *= actual / normal
    lengths = [("maxima", 32), ("long", 16), ("breve", 8), ("whole", 4), ("half", 2), ("quarter", 1)]
    lengths.extend((name, Fraction(4, 2 ** n)) for n, name in enumerate(
        ["eighth", "16th", "32nd", "64th", "128th", "256th", "512th", "1024th"], start=3,
    ))
    for note_type, base in lengths:
        for dots in range(4):
            if visual == base * (2 - Fraction(1, 2 ** dots)):
                if grace:
                    remove(doc, note, "duration")
                else:
                    put(doc, note, "duration", int(units))
                put(doc, note, "type", note_type)
                old_dots = doc.children(note, "dot")
                for old in old_dots[dots:]:
                    note.remove(old)
                for _ in range(max(0, dots - len(old_dots))):
                    dot = ET.Element(doc.namespace + "dot")
                    type_node = doc.child(note, "type")
                    note.insert(list(note).index(type_node) + 1, dot)
                return
    raise ReviewError("That duration has no supported note type/dot spelling. Existing tuplet ratios are retained.")


def patch_event(doc: Document, identifier: str, patch: EventPatch):
    if "tie_direction" in patch.model_fields_set:
        if patch.model_fields_set != {"tie_direction"} or patch.tie_direction is None:
            raise ReviewError("Tie direction requires a direction-only correction (up or down).")
        from .ties import set_direction
        return set_direction(doc, identifier, patch.tie_direction)
    values = patch.model_dump(exclude_unset=True)
    tie_edit = "tie_to_event_id" in values
    values.pop("tie_to_event_id", None)
    values.pop("preserve_onsets", None)
    values.pop("duration_scope", None)
    if (not values and not tie_edit) or any(value is None for key, value in values.items() if key != "written_accidental"):
        raise ReviewError("Provide at least one non-null event correction.")
    note = doc.get(identifier, "note")
    measure, event = context(doc, note)
    members = group(doc, note)
    if patch.staff is not None and patch.staff > measure.staves:
        raise ReviewError("Staff exceeds the part's declared staff count.")
    if patch.pitch:
        pitch_patch(doc, note, patch.pitch)
    if "written_accidental" in patch.model_fields_set:
        if patch.written_accidental is None:
            remove(doc, note, "accidental")
        else:
            accidental_patch(doc, note, patch.written_accidental)
    if patch.staff is not None:
        put(doc, note, "staff", patch.staff)
    if patch.voice is not None:
        for member in members:
            put(doc, member, "voice", patch.voice)
    leader = members[0]
    preserve_position = patch.preserve_onsets or any(doc.refs.get(key) is leader for key in doc.positioned_events)
    old_advance = (Fraction(0) if event.grace else rational(doc.text(leader, "duration")) / rational(event.divisions)) if preserve_position else None
    grace = patch.grace if patch.grace is not None else event.grace
    if patch.grace is not None:
        for member in members:
            if grace:
                if doc.child(member, "cue") is not None:
                    raise ReviewError("Cue and grace semantics cannot coexist. Edit cue semantics in a notation editor.")
                put(doc, member, "grace")
                remove(doc, member, "duration")
            else:
                remove(doc, member, "grace")
        if not grace and event.grace and patch.duration is None:
            raise ReviewError("Converting grace to a regular note requires an explicit duration.")
    if patch.grace_slash is not None:
        if not grace:
            raise ReviewError("A grace slash requires a grace note.")
        for member in members:
            doc.child(member, "grace").set("slash", "yes" if patch.grace_slash else "no")
    if patch.duration is not None:
        if patch.duration_scope == "note" and not grace and len(members) > 1:
            requested = rational(patch.duration)
            if requested is None:
                raise ReviewError("Duration requires an exact rational value.")
            index = members.index(note)
            # MusicXML bounds each member by its immediate predecessor.
            # A note-scoped edit can invalidate either neighboring adjacency.
            if index > 0 and requested > rational(doc.text(members[index - 1], "duration")) / rational(event.divisions):
                raise ReviewError("The chord member cannot exceed its preceding note; use explicit ownership to separate it.")
            if index + 1 < len(members) and requested < rational(doc.text(members[index + 1], "duration")) / rational(event.divisions):
                raise ReviewError("The chord note cannot become shorter than its following member; use explicit ownership to separate it.")
        for member in ([note] if patch.duration_scope == "note" else members):
            duration_patch(doc, member, patch.duration, measure.divisions, grace)
    if (patch.duration is not None or patch.grace is not None) and preserve_position:
        new_advance = Fraction(0) if grace else rational(doc.text(leader, "duration")) / rational(event.divisions)
        delta = old_advance - new_advance
        if delta:
            compensation = ET.Element(doc.namespace + ("forward" if delta > 0 else "backup"))
            ET.SubElement(compensation, doc.namespace + "duration").text = str(int(abs(delta) * rational(event.divisions)))
            parent = doc.parent(leader)
            parent.insert(list(parent).index(members[-1]) + 1, compensation)
    if patch.display_size:
        size_patch(doc, note, patch.display_size)
    if tie_edit:
        from .ties import set_target
        changed = set_target(doc, identifier, patch.tie_to_event_id)
        if changed is False and patch.model_fields_set == {"tie_to_event_id"}:
            return False
    doc.changed = True


def add_event(doc: Document, identifier: str, request: EventAdd):
    measure = doc.get(request.measure_id, "measure")
    if request.same_onset_id:
        if any((request.onset is not None, request.after_event_id, request.before_event_id, request.chord_with_id)):
            raise ReviewError("Choose one exact-onset anchor or another placement mode.")
        anchor = doc.get(request.same_onset_id, "note")
        if doc.parent(anchor) is not measure:
            raise ReviewError("The onset anchor must belong to the requested measure.")
        _, event = context(doc, anchor)
        if event.onset is None or event.grace:
            raise ReviewError("The onset anchor requires known duration-bearing timing.")
        return add_at_position(doc, identifier, request.model_copy(update={
            "same_onset_id": None, "onset": event.onset,
            "voice": request.voice or event.voice, "staff": request.staff or event.staff}))
    if request.kind == "note" and request.pitch is None:
        raise ReviewError("A new pitched note requires pitch fields.")
    if request.kind == "rest" and (request.pitch is not None or request.grace or request.chord_with_id):
        raise ReviewError("A rest cannot have pitch, grace or chord membership.")
    if sum(bool(value) for value in (request.after_event_id, request.before_event_id, request.chord_with_id)) > 1:
        raise ReviewError("Choose a sequential anchor or a simultaneous anchor.")
    if request.onset is not None:
        return add_at_position(doc, identifier, request)
    anchor_id = request.chord_with_id or request.after_event_id or request.before_event_id
    anchor = doc.get(anchor_id, "note") if anchor_id else None
    if anchor is not None and doc.parent(anchor) is not measure:
        raise ReviewError("The anchor must belong to the requested measure.")
    info, event = context(doc, anchor, request.measure_id if anchor is None else None)
    note = ET.Element(doc.namespace + "note")
    voice, staff = request.voice or (event.voice if event else "1"), request.staff or (event.staff if event else 1)
    if staff is None or staff > info.staves:
        raise ReviewError("Staff exceeds the part's declared staff count.")
    if request.kind == "rest":
        put(doc, note, "rest")
    else:
        pitch_patch(doc, note, request.pitch)
    inherit_position = bool(request.chord_with_id and "duration" not in request.model_fields_set)
    if request.chord_with_id:
        if event.kind != "note" or event.grace or request.grace:
            raise ReviewError("Simultaneous additions currently require duration-bearing pitched notes.")
        if request.voice is not None and request.voice != event.voice:
            raise ReviewError("A chord member must share its anchor's voice.")
        rhythm_anchor = group(doc, anchor)[0] if inherit_position else anchor
        if inherit_position:
            _, rhythm = context(doc, rhythm_anchor)
            if rhythm.kind != "note" or rhythm.grace or rhythm.onset is None or rational(rhythm.duration) is None or rational(rhythm.duration) <= 0 or rhythm.voice != event.voice:
                raise ReviewError("The selected rhythmic position has unresolved timing or ownership. Technical Lead review is required.")
        for tag in ("duration", "type", "dot", "time-modification", "stem"):
            for child in doc.children(rhythm_anchor, tag):
                note.append(deepcopy(child))
        # Legacy chord requests without an explicit duration retain the anchor rhythm.
        if "duration" in request.model_fields_set:
            preceding = group(doc, anchor)[-1]
            duration_patch(doc, note, request.duration, info.divisions)
            if rational(request.duration) > rational(doc.text(preceding, "duration")) / rational(info.divisions):
                raise ReviewError("A chord member cannot exceed the preceding duration; use exact-onset placement.")
        put(doc, note, "chord")
        # Type size copied from the anchor is replaced with the explicitly requested display size.
    else:
        if request.grace:
            grace_node = put(doc, note, "grace")
            if request.grace_slash is not None:
                grace_node.set("slash", "yes" if request.grace_slash else "no")
        elif request.grace_slash is not None:
            raise ReviewError("A grace slash requires a grace note.")
        duration_patch(doc, note, request.duration, info.divisions, request.grace)
    if request.written_accidental is not None:
        accidental_patch(doc, note, request.written_accidental)
    put(doc, note, "voice", voice)
    put(doc, note, "staff", staff)
    size_patch(doc, note, request.display_size)
    if anchor is not None:
        members = group(doc, anchor)
        position = list(measure).index(members[0]) if request.before_event_id else list(measure).index(members[-1]) + 1
        if inherit_position:
            last_duration = rational(doc.text(members[-1], "duration"))
            if last_duration is None:
                raise ReviewError("The selected chord has unresolved member timing. Technical Lead review is required.")
            # Preserve established append order for shared-duration chords. A
            # shorter last member cannot precede a longer new member in the
            # current importer; place the inherited full rhythm after its leader.
            if last_duration < rational(doc.text(members[0], "duration")):
                position = list(measure).index(members[0]) + 1
    else:
        position = next((i for i, element in enumerate(measure) if local(element.tag) == "barline" and element.get("location", "right") == "right"), len(measure))
    measure.insert(position, note)
    doc.refs[identifier] = note
    if request.tie_to_event_id:
        from .ties import connect
        connect(doc, identifier, request.tie_to_event_id)
    doc.changed = True


def delete_preserving_timing(doc: Document, identifier: str):
    """Remove one pitch/event while preserving the existing XML cursor advance."""
    note = doc.get(identifier, "note")
    measure = doc.parent(note)
    score, issues = import_score(doc)
    mid = next(key for key, node in doc.refs.items() if node is measure)
    timing_errors = {"invalid_divisions", "invalid_timing", "negative_onset", "invalid_duration",
                     "broken_chord", "invalid_voice", "invalid_staff", "grace_duration"}
    if any(i.measure_id == mid and i.code in timing_errors for i in issues):
        raise ReviewError("Cannot preserve timing: invalid MusicXML timing or event ownership.")
    events = [e for p in score.parts for m in p.measures if m.id == mid for v in m.voices for e in v.events]
    if any(e.onset is None or (not e.grace and (e.duration is None or e.divisions is None)) for e in events):
        raise ReviewError("Cannot preserve timing: event timing is unresolved.")
    members = group(doc, note)
    if members[0] is note and len(members) > 1 and doc.child(note, "grace") is None:
        if rational(doc.text(note, "duration")) != rational(doc.text(members[1], "duration")):
            raise ReviewError("Cannot preserve timing without changing a surviving chord note's duration.")
    event = next(e for e in events if e.id == identifier)
    index = list(measure).index(note)
    # Existing deletion already compensates positioned standalone events. Reuse
    # that path, adding the same protection explicitly for imported events.
    if len(members) == 1 and not event.grace:
        doc.positioned_events.add(identifier)
    delete_event(doc, identifier)
    if len(members) == 1 and not event.grace:
        forward = list(measure)[index]
        ET.SubElement(forward, doc.namespace + "voice").text = event.voice
        ET.SubElement(forward, doc.namespace + "staff").text = str(event.staff)
    after, _ = import_score(doc)
    surviving = {e.id: e for p in after.parts for m in p.measures if m.id == mid for v in m.voices for e in v.events}
    for old in events:
        if old.id == identifier:
            continue
        new = surviving.get(old.id)
        if new is None or (new.onset, new.duration, new.voice, new.staff, new.grace) != (old.onset, old.duration, old.voice, old.staff, old.grace):
            raise ReviewError("Cannot preserve surviving event timing. No changes applied.")


def delete_event(doc: Document, identifier: str):
    note = doc.get(identifier, "note")
    from .ties import disconnect_deleted
    disconnect_deleted(doc, identifier)
    members = group(doc, note)
    if members[0] is note and len(members) > 1:
        promoted = members[1]
        remove(doc, promoted, "chord")
        # The surviving chord retains its original advancing duration.
        duration = doc.child(note, "duration")
        if duration is not None:
            put(doc, promoted, "duration", duration.text)
    if identifier in doc.positioned_events and members[0] is note:
        if len(members) > 1:
            doc.positioned_events.add(next(key for key, node in doc.refs.items() if node is members[1]))
        elif doc.child(note, "grace") is None:
            parent = doc.parent(note)
            compensation = ET.Element(doc.namespace + "forward")
            ET.SubElement(compensation, doc.namespace + "duration").text = doc.text(note, "duration")
            parent.insert(list(parent).index(note), compensation)
    doc.positioned_events.discard(identifier)
    doc.parent(note).remove(note)
    removed = set(note.iter())
    doc.refs = {key: node for key, node in doc.refs.items() if node not in removed}
    doc.changed = True


def patch_lyric(doc, identifier, text, segment_index=0):
    lyric = doc.get(identifier, "lyric")
    segments = doc.children(lyric, "text")
    if not segments:
        if segment_index:
            raise ReviewError("The lyric segment does not exist.", 404)
        put(doc, lyric, "text", text, ["syllabic", "text", "elision", "extend", "end-line", "end-paragraph", "footnote", "level"])
    elif segment_index >= len(segments):
        raise ReviewError("The lyric segment does not exist.", 404)
    else:
        segments[segment_index].text = text
    doc.changed = True


def patch_harmony(doc: Document, identifier: str, patch: HarmonyPatch):
    values = patch.model_dump(exclude_unset=True)
    if not values or any(v is None for v in values.values()):
        raise ReviewError("Provide a non-null harmony correction.")
    harmony = doc.get(identifier, "harmony")
    if patch.root_step is not None or patch.root_alter is not None:
        if doc.child(harmony, "numeral") is not None or doc.child(harmony, "function") is not None:
            raise ReviewError("Roman-numeral/function harmonies need a notation editor; root edits would change their semantics.")
        root = put(doc, harmony, "root", order=HARMONY_ORDER)
        if patch.root_step:
            put(doc, root, "root-step", patch.root_step, ["root-step", "root-alter"])
        if patch.root_alter is not None:
            put(doc, root, "root-alter", patch.root_alter, ["root-step", "root-alter"])
    if patch.kind is not None:
        put(doc, harmony, "kind", patch.kind, HARMONY_ORDER)
    if patch.text is not None:
        put(doc, harmony, "kind", order=HARMONY_ORDER).set("text", patch.text)
    doc.changed = True


def patch_title(doc: Document, text: str):
    put(doc, doc.root, "movement-title", text, ROOT_ORDER)
    work = doc.child(doc.root, "work")
    if work is not None and doc.child(work, "work-title") is not None:
        put(doc, work, "work-title", text, ["work-number", "work-title", "opus"])
    doc.changed = True


def accidental_patch(doc, note, spelling):
    pitch = doc.child(note, "pitch")
    values = {"flat-flat": -2, "flat": -1, "natural": 0, "sharp": 1, "double-sharp": 2}
    if pitch is None or rational(doc.text(pitch, "alter", "0")) != values[spelling]:
        raise ReviewError("Written accidental must match the explicitly selected pitch alteration.")
    put(doc, note, "accidental", spelling)


def position_context(doc, measure_id):
    """Resolve a constant-divisions XML cursor; never derive position from meter."""
    info, _ = context(doc, measure_id=measure_id)
    _, issues = import_score(doc)
    if any(issue.severity == "ERROR" and issue.measure_id == measure_id for issue in issues):
        raise ReviewError("Explicit placement cannot resolve a measure with technical representation errors. Correct those errors first.")
    measure = doc.get(measure_id, "measure")
    scale = rational(info.divisions)
    if scale is None or scale <= 0:
        raise ReviewError("Explicit insertion requires known positive divisions.")
    cursor = Fraction(0)
    seen_timing = False
    for child in measure:
        tag = local(child.tag)
        if tag == "attributes":
            if seen_timing:
                raise ReviewError("Insertion around mid-measure context changes is ambiguous; use a notation editor.")
        elif tag in ("note", "backup", "forward"):
            seen_timing = True
            if tag == "note" and (doc.child(child, "grace") is not None or doc.child(child, "chord") is not None):
                continue
            units = rational(doc.text(child, "duration"))
            if units is None or units <= 0:
                raise ReviewError("Insertion cannot resolve an invalid existing timeline.")
            cursor += units / scale * (-1 if tag == "backup" else 1)
            if cursor < 0:
                raise ReviewError("Insertion cannot resolve a negative existing timeline.")
    return info, cursor, scale


def add_at_position(doc, identifier, request):
    """Append an isolated, explicit stream or join one unique compatible chord.

    Existing notes, backup/forward, directions and their onsets stay intact.
    No capacity-based placement, spill into another measure, or generated rests.
    """
    if any((request.after_event_id, request.before_event_id, request.chord_with_id)):
        raise ReviewError("Choose an explicit onset or an anchor, not both.")
    onset = rational(request.onset)
    if onset is None or not 0 <= onset <= 1024 or request.voice is None or request.staff is None:
        raise ReviewError("Explicit insertion requires a nonnegative onset, explicit voice and staff.")
    info, cursor, scale = position_context(doc, request.measure_id)
    if request.staff > info.staves:
        raise ReviewError("Staff exceeds the part's declared staff count.")
    if any(e.onset is None or (not e.grace and e.duration is None) for v in info.voices for e in v.events):
        raise ReviewError("Insertion cannot resolve ambiguous event timing.")
    duration = rational(request.duration)
    if duration is None or not 0 < duration <= 1024:
        raise ReviewError("Duration must be positive quarter beats (maximum 1024).")
    gaps = [g for g in info.insertion_gaps if g['voice'] == request.voice and g['staff'] == request.staff
            and rational(g['onset']) <= onset < rational(g['onset']) + rational(g['duration'])]
    if not request.grace and gaps and all(onset + duration > rational(g['onset']) + rational(g['duration']) for g in gaps):
        raise ReviewError("The note exceeds the available insertion interval.")
    existing = [e for v in info.voices for e in v.events if e.voice == request.voice and not e.grace]
    overlaps = [e for e in existing if not request.grace and onset < rational(e.onset) + rational(e.duration)
                and rational(e.onset) < onset + duration]
    if overlaps:
        leaders = {e.chord_id or e.id for e in overlaps}
        if (request.kind != "note" or len(leaders) != 1 or
            any(e.kind != "note" or rational(e.onset) != onset for e in overlaps)):
            raise ReviewError("This voice already occupies that position. Choose its exact chord rhythm or an explicit secondary voice.")
        leader = next(iter(leaders))
        members = group(doc, doc.get(leader, "note"))
        preceding_duration = rational(doc.text(members[-1], "duration")) / scale
        if duration <= preceding_duration:
            add_event(doc, identifier, request.model_copy(update={"onset": None, "chord_with_id": leader}))
            return
        # Longer independent notes use an isolated cursor stream, retaining the chosen voice.
    # Use existing note construction with no anchor, then bracket its duration.
    add_event(doc, identifier, request.model_copy(update={"onset": None, "tie_to_event_id": None}))
    measure = doc.get(request.measure_id, "measure")
    note = doc.refs[identifier]
    index = list(measure).index(note)
    advance = Fraction(0) if request.grace else duration
    def shift(delta, position):
        if not delta:
            return
        units = abs(delta) * scale
        if units.denominator != 1:
            raise ReviewError("That position cannot be represented with this measure's divisions.")
        node = ET.Element(doc.namespace + ("forward" if delta > 0 else "backup"))
        ET.SubElement(node, doc.namespace + "duration").text = str(int(units))
        measure.insert(position, node)
    shift(cursor - onset - advance, index + 1)
    shift(onset - cursor, index)
    # Projection is the postcondition, not graphical placement.
    doc.positioned_events.add(identifier)
    _, added = context(doc, note)
    if added.onset != str(onset) or added.voice != request.voice or added.staff != request.staff:
        raise ReviewError("Insertion could not preserve the requested musical position.")
    if request.tie_to_event_id:
        from .ties import connect
        connect(doc, identifier, request.tie_to_event_id)


def move_event(doc, identifier, request):
    """Explicit ownership correction preserving both timelines and opaque note data.

    Relationship-bearing or context-dependent notation fails atomically rather
    than guessing endpoint, instrument or tuplet ownership in another measure.
    """
    note = doc.get(identifier, "note")
    source = doc.parent(note)
    source_id = next(key for key, node in doc.refs.items() if node is source)
    source_info, event = context(doc, note)
    destination = doc.get(request.measure_id, "measure")
    if doc.parent(source) is not doc.parent(destination):
        raise ReviewError("Ownership correction is bounded to measures in the same part; use voice assignment for a secondary voice.")
    if event.kind != "note" or event.grace or event.cue or event.onset is None or event.duration is None:
        raise ReviewError("Ownership correction requires a duration-bearing pitched note with known timing.")
    if (doc.children(note, "tie") or doc.child(note, "notations") is not None
            or any(doc.child(note, tag) is not None for tag in ("beam", "time-modification", "instrument"))):
        raise ReviewError("Remove ties or resolve context-dependent relationships before changing ownership.")
    position_context(doc, source_id)
    position_context(doc, request.measure_id)
    members = group(doc, note)
    leader = members[0] is note
    index = list(source).index(note)
    source.remove(note)
    if leader and len(members) > 1:
        remove(doc, members[1], "chord")
        if identifier in doc.positioned_events:
            doc.positioned_events.add(next(key for key, node in doc.refs.items() if node is members[1]))
    elif leader:
        compensation = ET.Element(doc.namespace + "forward")
        ET.SubElement(compensation, doc.namespace + "duration").text = doc.text(note, "duration")
        source.insert(index, compensation)
    remove(doc, note, "chord")
    # Reuse the explicit position planner and its collision/divisions guards.
    pitch = PitchInput(step=event.pitch.step, alter=event.pitch.alter, octave=event.pitch.octave)
    add_at_position(doc, identifier, EventAdd(measure_id=request.measure_id, onset=request.onset,
                    voice=request.voice, staff=request.staff, kind="note", pitch=pitch,
                    duration=event.duration, display_size=event.display_size))
    generated = doc.refs[identifier]
    target_info, placed = context(doc, generated)
    duration_patch(doc, note, event.duration, target_info.divisions)
    put(doc, note, "voice", request.voice)
    put(doc, note, "staff", request.staff)
    if doc.child(generated, "chord") is not None:
        put(doc, note, "chord")
    parent = doc.parent(generated)
    index = list(parent).index(generated)
    parent.remove(generated)
    parent.insert(index, note)
    doc.refs[identifier] = note
    doc.positioned_events.discard(identifier)
    if doc.child(note, "chord") is None:
        doc.positioned_events.add(identifier)
    doc.manual_changes[source_id] = sorted(set(doc.manual_changes.get(source_id, [])) | {"events"})
    doc.manual_changes[request.measure_id] = sorted(set(doc.manual_changes.get(request.measure_id, [])) | {"events"})
    doc.changed = True
