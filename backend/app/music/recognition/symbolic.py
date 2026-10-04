"""Small, deliberately partial parser for SMT's eKern/Humdrum evidence.

This is an analytical view, not a notation converter. Absolute kern accidentals
are never inferred from key signatures. Unsupported syntax remains in the raw
transcription and makes uncertain timing explicit.
"""

from copy import deepcopy
from fractions import Fraction
import re


_NOTE = re.compile(r"^([\[\]{}()&]*)(\d+(?:%\d+)?)?(\.*)([a-g]+|[A-G]+|r+)(#{1,4}|-{1,4}|n)?(.*)$")
_ANNOTATIONS = set("LJKk/\\~^'\"`;:()[]_{}&qQyYxtTmMwWS$ROIPpuv<>")


def transcription_text(raw: str) -> str:
    return raw.replace("<bos>", "").replace("<eos>", "").replace(
        "<b>", "\n").replace("<t>", "\t").replace("<s>", " ")


def _duration(reciprocal: str | None, dots: str) -> Fraction | None:
    if reciprocal is None or len(reciprocal) > 12 or len(dots) > 8:
        return None
    if set(reciprocal) == {"0"}:
        if len(reciprocal) > 4:
            return None
        value = Fraction(2 ** (len(reciprocal) + 2))
    else:
        values = reciprocal.split("%")
        denominator = int(values[0])
        numerator = int(values[1]) if len(values) == 2 else 1
        if denominator == 0 or numerator == 0:
            return None
        value = Fraction(4 * numerator, denominator)
    return value * (2 - Fraction(1, 2 ** len(dots)))


def _note(token: str) -> tuple[dict | None, bool]:
    match = _NOTE.fullmatch(token)
    if match is None:
        return None, False
    prefix, reciprocal, dots, pitch, accidental, suffix = match.groups()
    if len(set(pitch)) != 1 or (pitch[0] == "r" and accidental):
        return None, False
    duration = _duration(reciprocal, dots)
    grace = "q" in suffix
    if grace:
        duration = Fraction(0)
    is_rest = pitch[0] == "r"
    event = {
        "token": token, "kind": "rest" if is_rest else "note",
        "duration_quarters": str(duration) if duration is not None else None,
        "grace": grace, "groupetto": "Q" in suffix,
        "annotations": prefix + suffix,
    }
    if not is_rest:
        event["pitch"] = {
            "step": pitch[0].upper(),
            "octave": 3 + len(pitch) if pitch.islower() else 4 - len(pitch),
            "alter": (accidental or "").count("#") - (accidental or "").count("-"),
        }
    complete = duration is not None and set(suffix) <= _ANNOTATIONS and not event["groupetto"]
    return event, complete


def parse_symbolic(raw: str) -> dict:
    text = transcription_text(raw)
    events, clefs, keys, meters, barlines, unsupported = [], [], [], [], [], []
    states = []
    serial = 0
    clock = Fraction(0)
    measure_start = Fraction(0)
    measure_label = None
    timeline = True
    total = parsed = chord_groups = simultaneous = 0

    def issue(row: int, cell: str, reason: str):
        unsupported.append({"row": row, "token": cell, "reason": reason})

    def state():
        nonlocal serial
        serial += 1
        return {"id": str(serial), "remaining": Fraction(0), "staff": None, "meter": None}

    for row, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.startswith("!!"):
            continue
        cells = line.split("\t")
        total += len(cells)
        if not states:
            states = [state() for _ in cells]
            if not all(cell in {"**kern", "**ekern_1.0"} for cell in cells):
                timeline = False
                issue(row, line, "missing_spine_declaration")
        if len(cells) != len(states):
            timeline = False
            issue(row, line, "spine_count_mismatch")
            # Keep inspecting tokens; positional/timing claims stop here.
            while len(states) < len(cells):
                states.append(state())
        if all(cell.startswith("=") for cell in cells):
            labels = {re.sub(r"[^0-9].*$", "", cell.lstrip("=")) for cell in cells}
            measure_label = next(iter(labels)) if len(labels) == 1 else None
            barlines.append({"row": row, "tokens": cells, "label": measure_label})
            measure_start = clock
            parsed += len(cells)
            continue
        if any(cell in {"*^", "*v", "*x", "*+", "*-"} for cell in cells):
            if len(cells) != len(states) or any(cell not in {"*", "*^", "*v", "*-"} for cell in cells):
                timeline = False
                issue(row, line, "unsupported_spine_operation")
                continue
            updated = []
            index = 0
            valid = True
            while index < len(cells):
                cell, current = cells[index], states[index]
                if cell == "*v":
                    end = index + 1
                    while end < len(cells) and cells[end] == "*v":
                        end += 1
                    if end - index < 2 or len({s["remaining"] for s in states[index:end]}) != 1:
                        valid = False
                    updated.append(current)
                    index = end
                    continue
                if cell == "*^":
                    other = deepcopy(current)
                    other["id"] = state()["id"]
                    updated.extend([current, other])
                elif cell != "*-":
                    updated.append(current)
                index += 1
            states = updated
            if valid:
                parsed += len(cells)
            else:
                timeline = False
                issue(row, line, "ambiguous_spine_join")
            continue
        row_events = []
        data_row = False
        for column, cell in enumerate(cells):
            current = states[column]
            if cell in {"*", "**kern", "**ekern_1.0"} or cell.startswith("!"):
                parsed += 1
                continue
            record = {"row": row, "spine": current["id"], "value": cell}
            if cell.startswith("*clef"):
                clefs.append(record)
                parsed += 1
                continue
            if re.fullmatch(r"\*k\[(?:[a-g](?:#+|-+))*\]", cell):
                keys.append(record)
                parsed += 1
                continue
            meter = re.fullmatch(r"\*M([1-9]\d*)/([1-9]\d*)", cell)
            if meter and all(len(value) <= 6 for value in meter.groups()):
                current["meter"] = [int(value) for value in meter.groups()]
                meters.append(record)
                parsed += 1
                continue
            if re.fullmatch(r"\*staff\d+", cell):
                current["staff"] = cell.removeprefix("*staff")
                parsed += 1
                continue
            if cell.startswith("*"):
                issue(row, cell, "unsupported_interpretation")
                continue
            data_row = True
            if cell == ".":
                parsed += 1
                if timeline and current["remaining"] <= 0:
                    timeline = False
                    issue(row, cell, "null_without_active_event")
                continue
            members = []
            complete = True
            for token in cell.split():
                event, supported = _note(token)
                complete = complete and supported
                if event is not None:
                    members.append(event)
            durations = {event["duration_quarters"] for event in members}
            if not members or len(durations) != 1 or None in durations or any(e["groupetto"] for e in members):
                complete = False
                timeline = False
                issue(row, cell, "unsupported_or_ambiguous_duration")
            if not complete:
                issue(row, cell, "partial_or_unsupported_token")
            else:
                parsed += 1
            duration = Fraction(next(iter(durations))) if len(durations) == 1 and None not in durations else None
            if timeline and duration and current["remaining"] > 0:
                timeline = False
                issue(row, cell, "overlapping_spine_events")
            if duration is not None and duration > 0:
                current["remaining"] = duration
            notes = sum(event["kind"] == "note" for event in members)
            if notes > 1:
                chord_groups += 1
            for event in members:
                event.update({"row": row, "spine": current["id"], "staff": current["staff"],
                              "measure_label": measure_label,
                              "onset_quarters": str(clock) if timeline else None,
                              "measure_offset_quarters": str(clock - measure_start) if timeline else None,
                              "chord_group": f"{row}:{column}" if notes > 1 else None})
                event["beat"] = (str(1 + (clock - measure_start) * current["meter"][1] / 4)
                                 if timeline and current["meter"] else None)
                row_events.append(event)
        if any(event["grace"] for event in row_events) and any(not event["grace"] for event in row_events):
            timeline = False
            issue(row, line, "mixed_grace_and_metric_record")
        # If a row invalidated the clock, do not retain earlier onsets on that row.
        if not timeline:
            for event in row_events:
                event.update(onset_quarters=None, measure_offset_quarters=None, beat=None)
        timed_notes = [event for event in row_events if event["kind"] == "note" and not event["grace"]]
        if len(timed_notes) > 1 and timeline:
            simultaneous += 1
        events.extend(row_events)
        if data_row and row_events and not any(event["grace"] for event in row_events) and timeline:
            active = [s["remaining"] for s in states if s["remaining"] > 0]
            if active:
                increment = min(active)
                clock += increment
                for current in states:
                    current["remaining"] = max(Fraction(0), current["remaining"] - increment)
    return {
        "format": "partial-ekern", "text": text, "events": events,
        "clefs": clefs, "keys": keys, "time_signatures": meters, "barlines": barlines,
        "metrics": {
            "notes": sum(event["kind"] == "note" for event in events),
            "rests": sum(event["kind"] == "rest" for event in events),
            "grace_notes": sum(event["kind"] == "note" and event["grace"] for event in events),
            "chord_groups": chord_groups, "simultaneous_events": simultaneous,
            "barline_rows": len(barlines),
            "encoded_measure_labels": sorted({b["label"] for b in barlines if b["label"]}),
        },
        "parsing": {"total_cells": total, "parsed_cells": parsed,
                    "coverage": parsed / total if total else 0.0,
                    "unsupported_tokens": unsupported, "timeline_reliable": timeline,
                    "scope": "Encoded tokens per system; coverage is not recognition accuracy."},
    }
