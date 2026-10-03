"""Inspect provider XML without rebuilding it or guessing missing music."""

from fractions import Fraction
import re
from xml.parsers import expat
from xml.etree import ElementTree as ET

from app.music.recognition.errors import RecognitionError
from app.music.recognition.result import RecognitionIssue


def _invalid(message: str) -> RecognitionError:
    return RecognitionError(message, 502, (
        RecognitionIssue("invalid_musicxml", message, "error"),
    ))


def _number(value: str | None) -> Fraction:
    value = value.strip() if value is not None else None
    if value is None or len(value) > 32 or not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", value):
        raise ValueError("Expected a nonnegative MusicXML decimal")
    return Fraction(value)


def validate_musicxml(
    contents: bytes, *, expect_lyrics: bool, max_issues: int = 100,
) -> tuple[dict, tuple[RecognitionIssue, ...]]:
    try:
        parser = expat.ParserCreate()

        def reject_entity(*args):
            raise _invalid("Recognition produced MusicXML with unsafe entity declarations.")

        parser.EntityDeclHandler = reject_entity
        parser.Parse(contents, True)  # External MusicXML DTDs are not fetched.
        root = ET.fromstring(contents)
    except (ET.ParseError, expat.ExpatError, ValueError) as error:
        raise _invalid("Recognition produced invalid MusicXML.") from error
    namespace = root.tag[:root.tag.index("}") + 1] if root.tag.startswith("{") else ""
    if root.tag != namespace + "score-partwise":
        raise _invalid("Recognition must produce score-partwise MusicXML.")

    def children(element, name):
        return element.findall(namespace + name)

    def child(element, name):
        return element.find(namespace + name)

    def text(element, name):
        value = element.findtext(namespace + name)
        return value.strip() if value is not None else None

    parts = children(root, "part")
    if not parts:
        raise _invalid("Recognition produced MusicXML without parts.")
    issues: list[RecognitionIssue] = []
    issue_count = 0
    counts = {
        "parts": len(parts), "measures": 0, "notes": 0, "pitched_notes": 0,
        "rest_notes": 0, "unpitched_notes": 0, "grace_notes": 0,
        "cue_notes": 0, "chord_notes": 0, "lyrics": 0,
    }
    voices: set[str] = set()

    def issue(code, message, part, measure, details=None):
        nonlocal issue_count
        issue_count += 1
        if len(issues) < max_issues:
            issues.append(RecognitionIssue(
                code, message, part_id=part.get("id", "")[:128],
                measure=measure.get("number", "")[:128], details=details or {},
            ))

    for part in parts:
        measures = children(part, "measure")
        if not measures:
            raise _invalid("Recognition produced a part without measures.")
        divisions = None
        expected = None
        counts["measures"] += len(measures)
        for measure_index, measure in enumerate(measures):
            position = Fraction(0)
            extent = Fraction(0)
            previous_onset = None
            previous_voice = None
            timing_known = True
            note_count = 0
            for event in measure:
                tag = event.tag.removeprefix(namespace)
                if tag == "attributes":
                    if child(event, "divisions") is not None:
                        try:
                            divisions = _number(text(event, "divisions"))
                            if divisions <= 0:
                                raise ValueError
                        except ValueError:
                            divisions = None
                            issue("invalid_divisions", "Measure timing has invalid divisions.", part, measure)
                    times = children(event, "time")
                    if times:
                        durations = []
                        for time in times:
                            try:
                                if child(time, "senza-misura") is not None:
                                    raise ValueError
                                beats = children(time, "beats")
                                beat_types = children(time, "beat-type")
                                if not beats or len(beats) != len(beat_types):
                                    raise ValueError
                                duration = Fraction(0)
                                for beat, beat_type in zip(beats, beat_types):
                                    values = (beat.text or "").split("+")
                                    if any(not re.fullmatch(r"\d{1,4}", value) for value in values):
                                        raise ValueError
                                    denominator = _number(beat_type.text)
                                    if denominator <= 0:
                                        raise ValueError
                                    duration += sum(map(int, values)) * 4 / denominator
                                durations.append(duration)
                            except ValueError:
                                durations.append(None)
                        expected = durations[0] if len(set(durations)) == 1 else None
                        if position:
                            timing_known = False  # Mid-measure meter changes need richer analysis.
                elif tag in ("backup", "forward"):
                    previous_onset = None
                    try:
                        if divisions is None:
                            raise ValueError
                        duration = _number(text(event, "duration")) / divisions
                        if duration <= 0:
                            raise ValueError
                        position += duration if tag == "forward" else -duration
                        extent = max(extent, position)
                        if position < 0:
                            issue("negative_measure_position", "Backup moves before the measure start.", part, measure)
                            timing_known = False
                    except ValueError:
                        timing_known = False
                        issue("unknown_timing", "A timing event could not be evaluated.", part, measure)
                elif tag == "note":
                    counts["notes"] += 1
                    note_count += 1
                    pitch = child(event, "pitch")
                    rest = child(event, "rest")
                    unpitched = child(event, "unpitched")
                    if sum(value is not None for value in (pitch, rest, unpitched)) != 1:
                        raise _invalid("Recognition produced a note without one valid pitch, rest or unpitched representation.")
                    if pitch is not None:
                        if text(pitch, "step") not in tuple("ABCDEFG"):
                            raise _invalid("Recognition produced an invalid pitch step.")
                        octave = text(pitch, "octave")
                        if octave is None or not re.fullmatch(r"[0-9]", octave):
                            raise _invalid("Recognition produced an invalid pitch octave.")
                        alter = text(pitch, "alter")
                        if alter is not None and (len(alter) > 32 or not re.fullmatch(r"[+-]?\d+(?:\.\d+)?", alter)):
                            raise _invalid("Recognition produced an invalid pitch alteration.")
                    counts["pitched_notes"] += pitch is not None
                    counts["rest_notes"] += rest is not None
                    counts["unpitched_notes"] += unpitched is not None
                    grace = child(event, "grace") is not None
                    chord = child(event, "chord") is not None
                    counts["grace_notes"] += grace
                    counts["cue_notes"] += child(event, "cue") is not None
                    counts["chord_notes"] += chord
                    counts["lyrics"] += sum(
                        bool((text(lyric, "text") or "").strip())
                        for lyric in children(event, "lyric")
                    )
                    voice = text(event, "voice") or "1"
                    voices.add(voice[:128])
                    if chord and (previous_onset is None or previous_voice != voice):
                        issue("orphan_chord", "A chord note has no preceding note in the same voice.", part, measure)
                        timing_known = False
                    onset = previous_onset if chord and previous_onset is not None else position
                    previous_onset, previous_voice = onset, voice
                    if grace:
                        continue  # Grace notation does not consume the ordinary rhythmic timeline.
                    try:
                        if divisions is None:
                            raise ValueError
                        duration = _number(text(event, "duration")) / divisions
                        if duration <= 0:
                            raise ValueError
                        extent = max(extent, onset + duration)
                        if not chord:
                            position += duration
                    except ValueError:
                        timing_known = False
                        issue("unknown_note_duration", "A note's rhythmic duration could not be evaluated.", part, measure)
            if not note_count:
                issue("empty_measure", "A measure contains no notes or rests; compare it with the source.", part, measure)
            elif timing_known and expected is not None and extent != expected:
                if not (measure.get("implicit") == "yes" and extent < expected):
                    issue(
                        "measure_duration_mismatch",
                        "Measure duration differs from its time signature; check for omitted notes or a pickup.",
                        part, measure,
                        {"expected_quarter_beats": str(expected), "actual_quarter_beats": str(extent),
                         "first_measure": measure_index == 0},
                    )
    if not counts["notes"]:
        raise _invalid("Recognition produced no musical notes. Try a clearer scan.")
    if expect_lyrics and not counts["lyrics"]:
        issue_count += 1
        if len(issues) < max_issues:
            issues.append(RecognitionIssue("missing_lyrics", "Lyrics were expected, but no lyric text was exported."))
    if issue_count > max_issues:
        issues[-1] = RecognitionIssue(
            "diagnostics_truncated", "Additional recognition issues were omitted from this response.",
            details={"total_issues": issue_count},
        )
    return {"counts": counts, "voices": sorted(voices), "issue_count": issue_count,
            "validation_scope": "structural_and_timing_checks; not_full_schema_or_source_accuracy"}, tuple(issues)
