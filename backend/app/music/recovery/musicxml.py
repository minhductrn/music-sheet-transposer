"""Correlate physical evidence and validate exact MusicXML timing via review projection."""

from dataclasses import dataclass
from fractions import Fraction

from app.music.recovery.models import Correlation
from app.music.recovery.omr import number
from app.music.review.document import Document
from app.music.review.importer import import_score, integer, rational


@dataclass
class XmlEvent:
    part_id: str
    measure: object
    event: object
    node: object


class XmlContext:
    def __init__(self, document: Document):
        self.document = document
        self.score, self.diagnostics = import_score(document)
        self.parts = [node.get("id") for node in document.children(document.root, "part")]
        self.events = {}
        self.measures = {}
        self.by_measure = {}
        for part in self.score.parts:
            pid = document.refs[part.id].get("id")
            for measure in part.measures:
                self.measures[measure.id] = measure
                self.by_measure.setdefault((pid, measure.number), []).append(measure)
                for voice in measure.voices:
                    for event in voice.events:
                        self.events[event.id] = XmlEvent(pid, measure, event, document.refs[event.id])


def correlate(evidence, context: XmlContext):
    result = {}
    parts = dict(zip(evidence.logical_parts, context.parts)) if len(evidence.logical_parts) == len(context.parts) else {}
    for sheet in evidence.sheets:
        for system in sheet.systems:
            for measure in system.measures:
                targets = context.by_measure.get((parts.get(measure.part), measure.id), [])
                target = targets[0] if len(targets) == 1 else None
                xml_width = number(context.document.refs[target.id].get("width")) if target else None
                factor = sheet.interline / 10 if sheet.interline else None
                geometry = bool(factor and xml_width and measure.left is not None and measure.right is not None
                                and abs(xml_width * factor - (measure.right - measure.left)) <= sheet.interline)
                for note in measure.candidates:
                    matches, strong = [], []
                    for voice in target.voices if target else []:
                        for event in voice.events:
                            if (event.pitch is None or event.pitch.step != note.step or event.pitch.octave != note.octave
                                or event.staff != note.staff_number or (note.voice is not None and event.voice != note.voice)
                                or (note.onset is not None and event.onset != note.onset)
                                or (note.alter is not None and rational(event.pitch.alter) != rational(note.alter))):
                                continue
                            node = context.document.refs[event.id]
                            x = number(node.get("default-x"))
                            matches.append(event.id)
                            if (geometry and note.bounds and x is not None
                                and abs(note.bounds[0] - (measure.left + x * factor)) <= sheet.interline * .5):
                                strong.append(event.id)
                    choices = strong or matches
                    confidence = "HIGH" if len(strong) == 1 and note.pitch_supported and note.grade is not None and note.grade >= .8 else "AMBIGUOUS" if choices else "UNMATCHED"
                    reasons = ["part_staff_measure_pitch"] if choices else ["no_compatible_exported_pitch"]
                    reasons.append("physical_position" if strong else "position_not_confirmed")
                    result[note.provenance] = Correlation(note.id, confidence, tuple(choices), target.id if target else None, tuple(reasons))
    return result


def rhythm(context: XmlContext):
    """Measure extent plus per-voice intervals; grace/chord members don't advance time.

    Voice underfill is a warning (partial voices and pickups can be intentional).
    A recovery never infers missing notes from that warning alone.
    """
    report = {}
    doc = context.document
    for mid, measure in context.measures.items():
        issues = [{"code": i.code, "severity": i.severity, "event_id": i.event_id}
                  for i in context.diagnostics if i.measure_id == mid]
        expected, actual = rational(measure.expected_duration), rational(measure.actual_duration)
        implicit = doc.refs[mid].get("implicit") == "yes"
        voices = {}
        for voice in measure.voices:
            spans = [(rational(e.onset), rational(e.onset) + rational(e.duration), e.id)
                     for e in voice.events if not e.grace and not e.chord_member
                     and rational(e.onset) is not None and rational(e.duration) is not None and rational(e.duration) > 0]
            spans.sort()
            end = Fraction(0)
            coverage = Fraction(0)
            for start, stop, eid in spans:
                if start < end:
                    issues.append({"code": "voice_overlap", "severity": "ERROR", "event_id": eid})
                coverage += max(Fraction(0), stop - max(end, start))
                end = max(end, stop)
            # A forward may explicitly occupy otherwise silent time, including a global cursor gap.
            forwards = [node for node in doc.refs[mid] if node.tag == doc.namespace + "forward"
                        and doc.text(node, "voice", voice.id) == voice.id]
            if expected is not None and coverage < expected and not implicit and not forwards:
                issues.append({"code": "voice_underfilled", "severity": "WARNING", "event_id": None})
            voices[voice.id] = {"extent": str(end), "sounding_coverage": str(coverage)}
        if expected is not None and actual is not None:
            if actual > expected:
                issues.append({"code": "measure_overfilled", "severity": "ERROR", "event_id": None})
            elif actual < expected and not implicit:
                issues.append({"code": "measure_underfilled", "severity": "WARNING", "event_id": None})
        report[mid] = {"expected": measure.expected_duration, "actual": measure.actual_duration, "voices": voices,
                       "valid": expected is not None and actual is not None and (actual == expected or implicit and actual < expected)
                                and not any(i["severity"] == "ERROR" for i in issues), "diagnostics": issues}
    return report


def resolved_pitch(note, anchor: XmlEvent, context: XmlContext):
    if not note.pitch_supported or note.step is None or note.octave is None:
        return None
    if note.alter is not None:
        return {"step": note.step, "alter": note.alter, "octave": note.octave}
    doc = context.document
    # Mixed/mid-measure key changes and octave-shift notation need a specialist review.
    seen_note = False
    for child in doc.refs[anchor.measure.id]:
        if child.tag == doc.namespace + "note":
            seen_note = True
        if seen_note and child.find(doc.namespace + "key") is not None:
            return None
    if doc.refs[anchor.measure.id].find(f'.//{doc.namespace}octave-shift') is not None:
        return None
    signatures = {k["staff"]: k for k in anchor.measure.key_signature}
    key = signatures.get(str(note.staff_number), signatures.get(None))
    fifths = integer(key["fifths"]) if key else None
    if fifths is None or abs(fifths) > 7:
        return None
    alter = "1" if fifths > 0 and note.step in "FCGDAEB"[:fifths] else "-1" if fifths < 0 and note.step in "BEADGCF"[:-fifths] else "0"
    previous = [x.event for x in context.events.values() if x.measure.id == anchor.measure.id
                and x.event.staff == note.staff_number and x.event.pitch is not None
                and x.event.pitch.step == note.step and x.event.pitch.octave == note.octave
                and rational(x.event.onset) is not None and rational(anchor.event.onset) is not None
                and rational(x.event.onset) <= rational(anchor.event.onset)]
    if previous:
        latest = max(rational(e.onset) for e in previous)
        alterations = {e.pitch.alter for e in previous if rational(e.onset) == latest}
        if len(alterations) != 1:
            return None
        alter = next(iter(alterations))
    return {"step": note.step, "alter": alter, "octave": note.octave}
