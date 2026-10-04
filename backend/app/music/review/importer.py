"""Read ordered XML events into a lossless review projection and diagnostics."""

from fractions import Fraction
import re

from app.music.review.document import Document, local
from app.music.review.models import Diagnostic, EditableScore, Event, Measure, Part, Pitch, Voice


def rational(value) -> Fraction | None:
    try:
        if value is None or len(str(value)) > 32 or not re.fullmatch(r"[+-]?\d+(?:\.\d+|/\d+)?", str(value)):
            return None
        return Fraction(value)
    except (ValueError, ZeroDivisionError):
        return None


def integer(value) -> int | None:
    return int(value) if value is not None and len(str(value)) <= 16 and re.fullmatch(r"[+-]?\d+", str(value)) else None


def xml_number(value) -> Fraction | None:
    return rational(value) if value is not None and re.fullmatch(r"[+-]?\d+(?:\.\d+)?", str(value)) else None


def display_size(doc: Document, note) -> str:
    head = doc.child(note, "notehead")
    if (head is not None and head.get("font-size") in ("small", "x-small", "xx-small")) or note.get("font-size") in ("small", "x-small", "xx-small"):
        return "small"
    note_type = doc.child(note, "type")
    if note_type is not None and note_type.get("size") == "normal":
        return "normal"
    return "cue" if doc.child(note, "cue") is not None or (note_type is not None and note_type.get("size") == "cue") else "normal"


def inherit_staff_values(previous, updates):
    values = {value["staff"]: value for value in previous}
    for update in updates:
        if update["staff"] is None:
            values.clear()  # An unnumbered signature applies to all staves.
        values[update["staff"]] = update
    return list(values.values())


def import_score(doc: Document) -> tuple[EditableScore, list[Diagnostic]]:
    ids = {node: identifier for identifier, node in doc.refs.items()}
    issues: list[Diagnostic] = []
    measure_severities: dict[str, set[str]] = {}
    lyrics, harmonies, parts = [], [], []

    def issue(code, message, severity="ERROR", measure_id=None, event_id=None):
        issues.append(Diagnostic(code, message, severity, measure_id, event_id))
        if measure_id:
            measure_severities.setdefault(measure_id, set()).add(severity)

    part_names = {p.get("id"): doc.text(p, "part-name", "")
                  for p in doc.root.findall(f"{doc.namespace}part-list/{doc.namespace}score-part")}
    seen_parts = set()
    for part in doc.children(doc.root, "part"):
        part_xml_id = part.get("id", "")
        if not part_xml_id or part_xml_id in seen_parts:
            issue("invalid_part", "Parts need distinct nonempty MusicXML IDs.")
        seen_parts.add(part_xml_id)
        divisions, time, keys, staves = None, [], [], 1
        measures = []
        for index, measure in enumerate(doc.children(part, "measure")):
            mid = ids[measure]
            position, extent, previous = Fraction(0), Fraction(0), None
            timing_known = True
            voices = {}
            expected = None

            def meter_duration():
                durations = []
                signatures = {signature["staff"]: signature for signature in time}
                for staff in range(1, staves + 1):
                    signature = signatures.get(str(staff), signatures.get(None))
                    if signature is None:
                        return None
                    total = Fraction(0)
                    for pair in signature["pairs"]:
                        beats, beat_type = pair["beats"], integer(pair["beat_type"])
                        if not beats or not re.fullmatch(r"\d{1,4}(?:\+\d{1,4})*", beats) or not beat_type or beat_type <= 0:
                            return None
                        total += sum(map(int, beats.split("+"))) * Fraction(4, beat_type)
                    if not signature["pairs"]:
                        return None
                    durations.append(total)
                return durations[0] if durations and len(set(durations)) == 1 else None

            for element in measure:
                tag = local(element.tag)
                if tag == "attributes":
                    if doc.child(element, "divisions") is not None:
                        divisions = xml_number(doc.text(element, "divisions"))
                        if divisions is None or divisions <= 0:
                            issue("invalid_divisions", "Divisions must be positive.", measure_id=mid)
                            divisions = None
                    if doc.child(element, "staves") is not None:
                        declared = integer(doc.text(element, "staves"))
                        if declared is None or not 1 <= declared <= 128:
                            issue("invalid_staves", "Staff count must be between 1 and 128.", measure_id=mid)
                        else:
                            staves = declared
                    if doc.children(element, "time"):
                        time = inherit_staff_values(time, [{"staff": t.get("number"), "pairs": [
                            {"beats": b.text or "", "beat_type": bt.text or ""}
                            for b, bt in zip(doc.children(t, "beats"), doc.children(t, "beat-type"))
                        ]} for t in doc.children(element, "time")])
                        for t in doc.children(element, "time"):
                            if doc.child(t, "senza-misura") is None and (not doc.children(t, "beats") or len(doc.children(t, "beats")) != len(doc.children(t, "beat-type"))):
                                issue("invalid_meter", "A time signature needs matching beats and beat-type fields.", measure_id=mid)
                        if position:
                            issue("complex_meter", "Mid-measure meter changes require manual timing review.", "WARNING", mid)
                            timing_known = False
                    if doc.children(element, "key"):
                        keys = inherit_staff_values(keys, [{"staff": k.get("number"), "fifths": doc.text(k, "fifths"), "mode": doc.text(k, "mode")}
                                for k in doc.children(element, "key")])
                elif tag in ("backup", "forward"):
                    previous = None
                    duration = xml_number(doc.text(element, "duration"))
                    if divisions is None or duration is None or duration <= 0:
                        timing_known = False
                        issue("invalid_timing", "Backup/forward needs positive duration and divisions.", measure_id=mid)
                    elif position is not None:
                        position += duration / divisions * (1 if tag == "forward" else -1)
                        extent = max(extent, position)
                        if position < 0:
                            issue("negative_onset", "Backup moves before the measure start.", measure_id=mid)
                elif tag == "harmony":
                    offset = xml_number(doc.text(element, "offset", "0"))
                    onset = position + offset / divisions if position is not None and offset is not None and divisions else position
                    root = doc.child(element, "root")
                    kind = doc.child(element, "kind")
                    if root is not None and (doc.text(root, "root-step") not in tuple("ABCDEFG") or xml_number(doc.text(root, "root-alter", "0")) is None):
                        issue("invalid_harmony", "Harmony has invalid root pitch fields.", measure_id=mid)
                    if kind is None or not (kind.text or "").strip():
                        issue("invalid_harmony", "Harmony needs a chord kind.", measure_id=mid)
                    harmonies.append({"id": ids[element], "measure_id": mid, "onset": str(onset) if onset is not None else None,
                                      "root_step": doc.text(root, "root-step") if root is not None else None,
                                      "root_alter": doc.text(root, "root-alter", "0") if root is not None else None,
                                      "kind": kind.text if kind is not None else None,
                                      "text": kind.get("text", "") if kind is not None else ""})
                elif tag == "note":
                    eid = ids[element]
                    pitch_node = doc.child(element, "pitch")
                    rest, unpitched = doc.child(element, "rest"), doc.child(element, "unpitched")
                    kind = "note" if pitch_node is not None else "rest" if rest is not None else "unpitched"
                    if sum(n is not None for n in (pitch_node, rest, unpitched)) != 1:
                        issue("missing_note_kind", "An event needs exactly one pitch, rest or unpitched element.", measure_id=mid, event_id=eid)
                    pitch = None
                    if pitch_node is not None:
                        pitch = Pitch(doc.text(pitch_node, "step"), doc.text(pitch_node, "alter", "0"), integer(doc.text(pitch_node, "octave")))
                        if pitch.step not in tuple("ABCDEFG") or pitch.octave is None or not 0 <= pitch.octave <= 9 or xml_number(pitch.alter) is None:
                            issue("invalid_pitch", "Pitch needs an A–G step, decimal alter and octave 0–9.", measure_id=mid, event_id=eid)
                    voice = doc.text(element, "voice", "1")
                    staff = integer(doc.text(element, "staff", "1"))
                    if not voice or len(voice) > 32 or re.search(r"\s", voice):
                        issue("invalid_voice", "Voice must be a nonempty label without whitespace.", measure_id=mid, event_id=eid)
                    if staff is None or not 1 <= staff <= staves:
                        issue("invalid_staff", "Staff refers outside the part's declared staff count.", measure_id=mid, event_id=eid)
                    grace, chord = doc.child(element, "grace") is not None, doc.child(element, "chord") is not None
                    raw_duration = doc.text(element, "duration")
                    units = xml_number(raw_duration)
                    duration = units / divisions if units is not None and divisions else None
                    if not grace and (duration is None or duration <= 0 or duration > 1024):
                        issue("invalid_duration", "A duration-bearing event needs positive duration and divisions.", measure_id=mid, event_id=eid)
                        timing_known = False
                    if grace and raw_duration is not None:
                        issue("grace_duration", "Grace notes must not carry an ordinary duration.", measure_id=mid, event_id=eid)
                    onset = previous.onset if chord and previous else str(position) if position is not None else None
                    event = Event(eid, kind, pitch, onset, str(duration) if duration is not None else None,
                                  raw_duration, str(divisions) if divisions else None, voice, staff, None, chord, grace, display_size(doc, element),
                                  list(dict.fromkeys(t.get("type", "") for t in (
                                      doc.children(element, "tie") + element.findall(f"{doc.namespace}notations/{doc.namespace}tied")
                                  ))), [])
                    if chord:
                        if previous is None or previous.voice != voice or previous.grace != grace or previous.kind != "note" or kind != "note":
                            issue("broken_chord", "Chord members require a preceding pitched note in the same voice and grace group.", measure_id=mid, event_id=eid)
                        else:
                            previous.chord_id = previous.chord_id or previous.id
                            event.chord_id = previous.chord_id
                            if not grace and duration is not None and previous.duration is not None and duration > Fraction(previous.duration):
                                issue("chord_duration", "A chord member cannot be longer than its leading note.", measure_id=mid, event_id=eid)
                    for lyric in doc.children(element, "lyric"):
                        lid = ids[lyric]
                        segments = [t.text or "" for t in doc.children(lyric, "text")]
                        lyrics.append({"id": lid, "event_id": eid, "number": lyric.get("number", "1"),
                                       "text": " ".join(segments), "segments": segments,
                                       "syllabic": doc.text(lyric, "syllabic")})
                        event.lyric_ids.append(lid)
                    voices.setdefault(voice, Voice(voice)).events.append(event)
                    if not grace:
                        if duration is not None and onset is not None:
                            extent = max(extent, Fraction(onset) + duration)
                        if not chord:
                            position = position + duration if position is not None and duration is not None else None
                    previous = event
            expected = meter_duration()
            if time and expected is None:
                issue("unknown_meter", "The meter needs manual review; timing could not be fully checked.", "WARNING", mid)
            events = [event for voice in voices.values() for event in voice.events]
            if not events:
                issue("empty_measure", "This measure contains no notes or rests; compare it with the source.", "WARNING", mid)
            elif timing_known and expected is not None and extent != expected and not (measure.get("implicit") == "yes" and extent < expected):
                issue("measure_duration_mismatch", f"Measure contains {extent} quarter beats; its meter expects {expected}. Compare with the source.", "WARNING", mid)
            measures.append(Measure(mid, measure.get("number", ""), index, str(divisions) if divisions else None,
                                    time, keys, staves, str(expected) if expected is not None else None,
                                    str(extent) if timing_known else None, "VALID", list(voices.values())))
        if not measures:
            issue("missing_measures", "A part contains no measures.")
        parts.append(Part(ids[part], part_names.get(part_xml_id, part_xml_id), measures))
    if not any(v.events for p in parts for m in p.measures for v in m.voices):
        issue("empty_score", "The score contains no musical events.")
    for p in parts:
        for m in p.measures:
            severities = measure_severities.get(m.id, set())
            m.validation_state = "ERROR" if "ERROR" in severities else "WARNING" if "WARNING" in severities else "VALID"
    metadata = {"title": doc.text(doc.root, "movement-title", "") or doc.root.findtext(f"{doc.namespace}work/{doc.namespace}work-title", ""),
                "credits": [{"id": ids[c], "text": c.text or ""} for c in doc.root.iter() if local(c.tag) == "credit-words"],
                "musicxml_version": doc.root.get("version", "")}
    issues.append(Diagnostic("source_comparison", "Structural checks do not establish recognition accuracy. Compare every correction with the source.", "INFO"))
    return EditableScore(metadata, parts, lyrics, harmonies), issues
