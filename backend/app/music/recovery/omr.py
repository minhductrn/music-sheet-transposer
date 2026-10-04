"""Read the observed Audiveris 5.11 ZIP/JAXB graph, without extracting files."""

from dataclasses import replace
from hashlib import sha256
from io import BytesIO
import math
from xml.etree import ElementTree as ET
from xml.parsers import expat
from zipfile import BadZipFile, ZipFile
import zlib

from app.music.recognition.errors import RecognitionError
from app.music.recognition.mxl import _members, _read_member
from app.music.recognition.result import RecognitionIssue
from app.music.review.importer import integer, rational
from app.music.recovery.models import (
    AudiverisEvidence, CandidateNoteEvidence, EvidenceMeasure, EvidenceSheet,
    EvidenceSystem, Relationship,
)


def invalid(code="invalid_omr"):
    return RecognitionError("Audiveris evidence is malformed, unsafe or exceeds its limits.", 422, (
        RecognitionIssue(code, "The OMR evidence could not be safely interpreted.", "error"),
    ))


def number(value):
    try:
        result = float(value) if value is not None and len(value) <= 32 else None
        return result if result is not None and math.isfinite(result) and abs(result) <= 1_000_000 else None
    except (ValueError, TypeError):
        return None


def bounds(node):
    b = node.find("bounds")
    if b is None:
        return None
    result = tuple(number(b.get(key)) for key in ("x", "y", "w", "h"))
    return result if all(v is not None for v in result) and min(result[2:]) > 0 else None


def _xml(contents, budget):
    validator = expat.ParserCreate()
    depth = 0
    def start(*_):
        nonlocal depth
        depth += 1
        budget[0] -= 1
        if budget[0] < 0 or depth > 64:
            raise invalid("omr_xml_limit")
    def end(*_):
        nonlocal depth
        depth -= 1
    def reject(*_):
        raise invalid()
    validator.StartElementHandler = start
    validator.EndElementHandler = end
    validator.StartDoctypeDeclHandler = reject
    validator.EntityDeclHandler = reject
    validator.Parse(contents, True)
    return ET.fromstring(contents)


def parse_omr(contents: bytes, *, max_bytes=20 * 1024 * 1024,
              max_expanded_bytes=64 * 1024 * 1024, max_members=128, max_nodes=200_000) -> AudiverisEvidence:
    """Validate every ZIP member, but project only book and declared sheet XML.

    Shared recognition ZIP checks reject traversal, duplicates, symlinks, encrypted
    members, unsupported compression and conflicting paths. Unknown graph types
    survive as relationship names; they are never interpreted as musical semantics.
    """
    if not contents or len(contents) > max_bytes:
        raise invalid("omr_size_limit")
    digest = sha256(contents).hexdigest()
    try:
        with ZipFile(BytesIO(contents)) as archive:
            members = _members(archive, max_expanded_bytes, max_members)
            book_info = members.get("book.xml")
            if book_info is None or book_info.is_dir():
                raise invalid()
            # CRC/local-header validation also covers binary/unknown attachments.
            for entry in members.values():
                if not entry.is_dir():
                    _read_member(archive, entry, max_expanded_bytes, retain=False)
            budget = [max_nodes]
            book = _xml(_read_member(archive, book_info, max_expanded_bytes), budget)
            if book.tag != "book":
                raise invalid()
            parts = tuple(p.get("id", "") for p in book.findall("score/logical-part"))
            if any(not p for p in parts) or len(parts) != len(set(parts)):
                raise invalid()
            sheets, issues = [], []
            stubs = book.findall("sheet")
            seen = set()
            for stub in stubs:
                n = integer(stub.get("number"))
                if n is None or n <= 0 or n in seen:
                    raise invalid()
                seen.add(n)
                name = f"sheet#{n}/sheet#{n}.xml"
                if name not in members:
                    issues.append("omr_sheet_unavailable")
                    continue
                root = _xml(_read_member(archive, members[name], max_expanded_bytes), budget)
                if root.tag != "sheet":
                    raise invalid()
                sheet = _sheet(root, stub, n, f"{digest}/{name}", issues)
                image = members.get(f"sheet#{n}/BINARY.png")
                if image is not None and not image.is_dir():
                    sheet = replace(sheet, binary_sha256=sha256(_read_member(archive, image, max_expanded_bytes)).hexdigest())
                sheets.append(sheet)
            if not sheets:
                issues.append("omr_no_sheets")
            version = book.get("software-version")
            if not version or not version.startswith("5.11."):
                issues.append("omr_unvalidated_version")
            return AudiverisEvidence(digest, version, parts, tuple(sheets), tuple(sorted(set(issues))))
    except RecognitionError as error:
        if error.diagnostics and error.diagnostics[0].code.startswith(("omr_", "invalid_omr")):
            raise
        raise invalid() from error
    except (BadZipFile, OSError, ValueError, KeyError, RuntimeError, expat.ExpatError, ET.ParseError, zlib.error) as error:
        raise invalid() from error


def _sheet(root, stub, sheet_number, provenance, issues):
    scale = root.find("scale/interline")
    interline = number(scale.get("main")) if scale is not None else None
    nominal = root.find("scale/black-head")
    nominal_width = number(nominal.get("mean-width")) if nominal is not None else None
    page_stubs = {p.get("id"): p for p in stub.findall("page")}
    systems = []
    for page in root.findall("page"):
        page_stub = page_stubs.get(page.get("id"))
        mappings = page_stub.findall("system") if page_stub is not None else []
        for index, system in enumerate(page.findall("system")):
            sid = system.get("id", "")
            entries = system.findall("sig/inters/*")
            inters = {e.get("id"): e for e in entries if e.get("id")}
            if len(inters) != sum(bool(e.get("id")) for e in entries):
                raise invalid()
            relations = tuple(Relationship(r.get("source", ""), r.get("target", ""), c.tag, number(c.get("grade")))
                              for r in system.findall("sig/relations/relation") for c in r)
            dangling = {r for r in relations if r.source not in inters or r.target not in inters}
            if dangling:
                issues.append("omr_dangling_relation")
            links = {}
            for r in relations:
                links.setdefault(r.source, []).append(r)
                links.setdefault(r.target, []).append(r)
            stacks = {s.get("id"): s for s in system.findall("stack")}
            stub_parts = mappings[index].findall("part") if index < len(mappings) else []
            measures = []
            assigned = set()
            for pi, part in enumerate(system.findall("part")):
                logical = stub_parts[pi].get("logical-id") if pi < len(stub_parts) else None
                if logical is None:
                    # Physical IDs are retained, but missing logical mapping blocks automatic correlation.
                    issues.append("omr_part_mapping_unavailable")
                staff_nodes = {s.get("id"): (si + 1, s) for si, s in enumerate(part.findall("staff"))}
                for measure in part.findall("measure"):
                    mid = measure.get("id", "")
                    stack = stacks.get(mid)
                    left = number(stack.get("left")) if stack is not None else None
                    right = number(stack.get("right")) if stack is not None else None
                    chord_ids = set((measure.findtext("head-chords", "") + " " + measure.findtext("small-chords", "")).split())
                    voices = {}
                    slots = {s.get("id"): rational(s.get("time-offset")) for s in stack.findall("slot")} if stack is not None else {}
                    for voice in measure.findall("voice"):
                        for entry in voice.findall("slots/entry"):
                            value = entry.find("value")
                            if value is not None and value.get("status") == "BEGIN":
                                onset = slots.get(entry.findtext("key"))
                                voices[value.get("chord")] = (voice.get("id"), str(onset * 4) if onset is not None else None)
                    notes = []
                    for head in entries:
                        if head.tag != "head" or head.get("staff") not in staff_nodes:
                            continue
                        hid = head.get("id")
                        if not hid:
                            continue
                        box = bounds(head)
                        related = links.get(hid, [])
                        chords = tuple(sorted({r.source for r in related if r.kind == "containment"
                                               and r.target == hid and r.source in inters
                                               and inters[r.source].tag in ("head-chord", "small-chord", "grace-chord")}))
                        contained = bool(set(chords) & chord_ids)
                        geometrical = box and left is not None and right is not None and left <= box[0] + box[2] / 2 < right
                        if not contained and (chords or not geometrical):
                            continue
                        if hid in assigned:
                            issues.append("omr_duplicate_measure_assignment")
                            continue
                        assigned.add(hid)
                        chord_links = [r for cid in chords for r in links.get(cid, [])]
                        stems = tuple(sorted({r.target for r in related if r.kind == "head-stem" and r.source == hid}
                                             | {r.target for r in chord_links if r.kind == "chord-stem"}))
                        beams = tuple(sorted({r.source for stem in stems for r in links.get(stem, [])
                                              if r.kind == "beam-stem" and r.target == stem}))
                        staff_number, staff = staff_nodes[head.get("staff")]
                        position = integer(head.get("pitch"))
                        clefs = [e for e in entries if e.tag == "clef" and e.get("staff") == head.get("staff")
                                 and bounds(e) and box and bounds(e)[0] <= box[0]]
                        clef = max(clefs, key=lambda e: bounds(e)[0], default=None)
                        step, octave, supported = _pitch(position, clef, staff, box)
                        if any(r in dangling for r in related + chord_links):
                            supported = False
                        alterations = {inters[r.source].get("shape") for r in related
                                       if r.kind == "alter-head" and r.target == hid and r.source in inters}
                        alters = {"FLAT": "-1", "SHARP": "1", "NATURAL": "0", "DOUBLE_FLAT": "-2", "DOUBLE_SHARP": "2"}
                        alter = alters.get(next(iter(alterations))) if len(alterations) == 1 else None
                        if alterations and alter is None:
                            supported = False
                        shape = head.get("shape", "")
                        size = "small" if shape.endswith("_SMALL") else "normal"
                        if size == "normal" and shape == "NOTEHEAD_BLACK" and box and nominal_width and box[2] < nominal_width * .88:
                            size = "possibly_small"  # Geometry alone never authorizes a display change.
                        rhythm = [voices[c] for c in chords if c in voices]
                        voice, onset = rhythm[0] if len(rhythm) == 1 else (None, None)
                        notes.append(CandidateNoteEvidence(
                            hid, sheet_number, sid, logical, mid, head.get("staff"), staff_number,
                            box, (box[0] + box[2] / 2, box[1] + box[3] / 2) if box else None,
                            position, step, octave, alter, supported, shape, size, chords,
                            inters[chords[0]].tag if len(chords) == 1 else None, stems, beams, voice, onset,
                            number(head.get("ctx-grade", head.get("grade"))),
                            tuple(dict.fromkeys(related + chord_links)), f"{provenance}#{hid}",
                        ))
                    measures.append(EvidenceMeasure(mid, logical, left, right, tuple(sorted(notes, key=lambda n: (n.center or (0, 0), n.id))),
                                                    part.get("id"), tuple(staff_nodes)))
            systems.append(EvidenceSystem(sid, tuple(measures)))
    picture = root.find("picture")
    return EvidenceSheet(sheet_number, integer(picture.get("width")) if picture is not None else None,
                         integer(picture.get("height")) if picture is not None else None, interline, tuple(systems))


def _pitch(position, clef, staff, box):
    centers = {"TREBLE": 34, "BASS": 22, "ALTO": 28, "TENOR": 26,
               "TREBLE_8VA": 41, "TREBLE_8VB": 27, "BASS_8VA": 29, "BASS_8VB": 15}
    base = centers.get(clef.get("kind")) if clef is not None else None
    if base is None or position is None or abs(position) > 40:
        return None, None, False
    index = base - position
    step, octave = "CDEFGAB"[index % 7], index // 7
    lines = staff.findall("lines/line")
    supported = False
    if len(lines) == 5 and box:
        x, y = box[0] + box[2] / 2, box[1] + box[3] / 2
        ordinates = []
        for line in lines:
            points = [(number(p.get("x")), number(p.get("y"))) for p in line.findall("point")]
            if len(points) < 2 or any(v is None for p in points for v in p):
                break
            a, b = points[0], points[-1]
            ordinates.append(a[1] + (b[1] - a[1]) * (x - a[0]) / (b[0] - a[0]) if b[0] != a[0] else a[1])
        if len(ordinates) == 5:
            spacing = (ordinates[-1] - ordinates[0]) / 4
            supported = spacing > 0 and abs((y - ordinates[2]) * 2 / spacing - position) <= .5 and 0 <= octave <= 9
    return step, octave, supported


def register_analysis(baseline, analysis):
    """LINKS books lack logical parts/voices. Register to the untouched PAGE book.

    Require identical per-sheet binary pixels, dimensions and scale, then unique
    system/physical-part/staff/measure geometry. IDs are not matched across runs.
    No voice, rhythm, head shape or pitch is borrowed from the baseline graph.
    """
    base_sheets = {s.number: s for s in baseline.sheets}
    sheets = []
    complete = True
    diagnostics = list(analysis.diagnostics)
    for sheet in analysis.sheets:
        base = base_sheets.get(sheet.number)
        identical = (base is not None and base.binary_sha256 is not None and base.binary_sha256 == sheet.binary_sha256
                     and (base.width, base.height, base.interline) == (sheet.width, sheet.height, sheet.interline))
        if not identical:
            complete = False
            diagnostics.append("omr_analysis_source_mismatch")
            sheets.append(sheet)
            continue
        systems = []
        base_systems = {s.id: s for s in base.systems}
        for system in sheet.systems:
            original = base_systems.get(system.id)
            measures = []
            for measure in system.measures:
                matches = [m for m in original.measures if m.part is not None
                           and m.physical_part == measure.physical_part and m.staffs == measure.staffs
                           and m.left is not None and m.right is not None
                           and m.left == measure.left and m.right == measure.right] if original else []
                if len(matches) != 1:
                    complete = False
                    measures.append(measure)
                    continue
                target = matches[0]
                notes = tuple(replace(n, part=target.part, measure=target.id) for n in measure.candidates)
                measures.append(replace(measure, part=target.part, id=target.id, candidates=notes))
            systems.append(replace(system, measures=tuple(measures)))
        sheets.append(replace(sheet, systems=tuple(systems)))
    if not complete:
        diagnostics.append("omr_analysis_registration_incomplete")
    else:
        diagnostics = [d for d in diagnostics if d != "omr_part_mapping_unavailable"]
        diagnostics.append("omr_analysis_registered_by_source_and_geometry")
    if "omr_unvalidated_version" in baseline.diagnostics:
        diagnostics.append("omr_analysis_registration_incomplete")
    return replace(analysis, logical_parts=baseline.logical_parts, sheets=tuple(sheets), diagnostics=tuple(sorted(set(diagnostics))))
