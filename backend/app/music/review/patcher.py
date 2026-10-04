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
    if note_type is None and size != "normal":
        raise ReviewError("A size edit requires a note type; correct its duration first.")
    head = doc.child(note, "notehead")
    note.attrib.pop("font-size", None)
    if size == "small":
        # Valid MusicXML visual attributes; neither introduces <grace> or <cue> timing.
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
        if doc.child(modification, "normal-type") is not None:
            raise ReviewError("Duration edits to tuplets with an explicit normal-type require a notation editor.")
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
    values = patch.model_dump(exclude_unset=True)
    if not values or any(value is None for value in values.values()):
        raise ReviewError("Provide at least one non-null event correction.")
    note = doc.get(identifier, "note")
    measure, event = context(doc, note)
    members = group(doc, note)
    if patch.staff is not None and patch.staff > measure.staves:
        raise ReviewError("Staff exceeds the part's declared staff count.")
    if patch.pitch:
        pitch_patch(doc, note, patch.pitch)
    if patch.staff is not None:
        put(doc, note, "staff", patch.staff)
    if patch.voice is not None:
        for member in members:
            put(doc, member, "voice", patch.voice)
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
    if patch.duration is not None:
        for member in members:
            duration_patch(doc, member, patch.duration, measure.divisions, grace)
    if patch.display_size:
        size_patch(doc, note, patch.display_size)
    doc.changed = True


def add_event(doc: Document, identifier: str, request: EventAdd):
    measure = doc.get(request.measure_id, "measure")
    if request.kind == "note" and request.pitch is None:
        raise ReviewError("A new pitched note requires pitch fields.")
    if request.kind == "rest" and (request.pitch is not None or request.grace or request.chord_with_id):
        raise ReviewError("A rest cannot have pitch, grace or chord membership.")
    if sum(bool(value) for value in (request.after_event_id, request.before_event_id, request.chord_with_id)) > 1:
        raise ReviewError("Choose a sequential anchor or a simultaneous anchor.")
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
    if request.chord_with_id:
        if event.kind != "note" or event.grace or request.grace:
            raise ReviewError("Simultaneous additions currently require duration-bearing pitched notes.")
        if request.voice is not None and request.voice != event.voice:
            raise ReviewError("A chord member must share its anchor's voice.")
        for tag in ("duration", "type", "dot", "time-modification", "stem"):
            for child in doc.children(anchor, tag):
                note.append(deepcopy(child))
        put(doc, note, "chord")
        # Type size copied from the anchor is replaced with the explicitly requested display size.
    else:
        if request.grace:
            put(doc, note, "grace")
        duration_patch(doc, note, request.duration, info.divisions, request.grace)
    put(doc, note, "voice", voice)
    put(doc, note, "staff", staff)
    size_patch(doc, note, request.display_size)
    if anchor is not None:
        members = group(doc, anchor)
        position = list(measure).index(members[0]) if request.before_event_id else list(measure).index(members[-1]) + 1
    else:
        position = next((i for i, element in enumerate(measure) if local(element.tag) == "barline" and element.get("location", "right") == "right"), len(measure))
    measure.insert(position, note)
    doc.refs[identifier] = note
    doc.changed = True


def delete_event(doc: Document, identifier: str):
    note = doc.get(identifier, "note")
    members = group(doc, note)
    if members[0] is note and len(members) > 1:
        promoted = members[1]
        remove(doc, promoted, "chord")
        # The surviving chord retains its original advancing duration.
        duration = doc.child(note, "duration")
        if duration is not None:
            put(doc, promoted, "duration", duration.text)
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
