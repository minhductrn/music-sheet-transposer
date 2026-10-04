from base64 import b64decode
from copy import deepcopy
from io import BytesIO
from pathlib import Path
import signal
import stat
import subprocess
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from fastapi.testclient import TestClient
from PIL import Image
import pytest

from app.api.v1.recognize import get_recognition_service
from app.api.v1.reviews import get_review_service
from app.core.config import Settings
from app.main import app
from app.music.recognition.audiveris import AudiverisProvider
from app.music.recognition.errors import RecognitionError
from app.music.recognition.profiles import resolve_profile
from app.music.recognition.result import ProviderOutput
from app.music.recognition.service import MusicRecognitionService
from app.music.recovery.musicxml import XmlContext, correlate, rhythm
from app.music.recovery.omr import parse_omr
from app.music.recovery.service import recover
from app.music.review.document import Document
from app.music.review.service import ReviewService
from app.music.review.storage import MemoryReviewStore


FIXTURES = Path(__file__).parent / "music/fixtures"
XML = (FIXTURES / "semantic_baseline.musicxml").read_bytes()
BOOK = (FIXTURES / "semantic_omr_book.xml").read_bytes()
SHEET = (FIXTURES / "semantic_omr_sheet.xml").read_bytes()


def archive(sheet=SHEET, book=BOOK, extras=()):
    data = BytesIO()
    with ZipFile(data, "w", ZIP_DEFLATED) as z:
        for name, value in [("book.xml", book), ("sheet#1/sheet#1.xml", sheet), *extras]:
            info = ZipInfo(name) if isinstance(name, str) else name
            info.compress_type = ZIP_DEFLATED
            z.writestr(info, value)
    return data.getvalue()


def modified_sheet(change):
    root = ET.fromstring(SHEET)
    change(root)
    return archive(ET.tostring(root))


def modified_xml(change):
    root = ET.fromstring(XML)
    change(root)
    return ET.tostring(root)


def png():
    data = BytesIO()
    Image.new("RGB", (40, 40), "white").save(data, "PNG")
    return data.getvalue()


def test_evidence_extraction_matches_observed_jaxb_graph_and_is_deterministic():
    evidence = parse_omr(archive())
    assert evidence == parse_omr(archive())
    assert evidence.version == "5.11.0" and evidence.logical_parts == ("1",)
    heads = {n.id: n for n in evidence.notes()}
    normal, small = heads["10"], heads["11"]
    assert (small.id, small.sheet, small.system, small.measure, small.staff, small.staff_number) == ("11", 1, "1", "1", "7", 1)
    assert small.bounds == (202, 84, 14, 12) and small.center == (209, 90)
    assert (small.staff_position, small.step, small.octave) == (-1, "C", 5)
    assert small.pitch_supported and small.visual_size == "small"
    assert small.chords == normal.chords == ("20",)
    assert small.stems == normal.stems == ("30",) and small.beams == ("40",)
    assert small.voice == "1" and small.onset == "0" and small.grade == .95
    assert "/private" not in repr(evidence)


@pytest.mark.parametrize("contents", [b"", b"not zip", archive(book=b"<broken>"), archive(book=b"<other/>"),
    archive(sheet=b"<broken>"), archive(sheet=b'<!DOCTYPE sheet [<!ENTITY x "expanded">]><sheet>&x;</sheet>'),
    archive(book=b'<!DOCTYPE book SYSTEM "file:///private"><book/>')])
def test_malformed_evidence_is_rejected_with_safe_structured_error(contents):
    with pytest.raises(RecognitionError) as caught:
        parse_omr(contents)
    assert caught.value.status_code == 422
    assert caught.value.diagnostics[0].code.startswith(("invalid_omr", "omr_"))
    assert "/private" not in str(caught.value)


@pytest.mark.parametrize("name", ["../outside", "/absolute", "sheet#1/../outside", "C:/private", "a\\b", "book.xml"])
def test_unsafe_or_duplicate_archive_members_are_rejected(name):
    if name == "book.xml":
        with pytest.warns(UserWarning, match="Duplicate name"):
            contents = archive(extras=[(name, b"data")])
    else:
        contents = archive(extras=[(name, b"data")])
    with pytest.raises(RecognitionError):
        parse_omr(contents)


def test_symlink_corrupt_unused_member_and_archive_limits_are_rejected():
    entry = ZipInfo("unused")
    entry.create_system = 3
    entry.external_attr = (stat.S_IFLNK | 0o777) << 16
    with pytest.raises(RecognitionError):
        parse_omr(archive(extras=[(entry, b"/private")]))
    for limits in ({"max_bytes": 1}, {"max_members": 1}, {"max_expanded_bytes": 50}, {"max_nodes": 1}):
        with pytest.raises(RecognitionError):
            parse_omr(archive(), **limits)
    data = bytearray(archive(extras=[("unused", b"some bytes")]))
    with ZipFile(BytesIO(data)) as z:
        info = z.getinfo("unused")
        offset = info.header_offset + 30 + len(info.filename.encode()) + len(info.extra)
    data[offset] ^= 0xff
    with pytest.raises(RecognitionError):
        parse_omr(bytes(data))


def test_unknown_elements_and_seed_settings_are_not_note_interpretations():
    def change(root):
        ET.SubElement(root.find("scale"), "head-seed", shape="NOTEHEAD_BLACK_SMALL")
        ET.SubElement(root.find("page/system/sig/inters"), "future-inter", id="99")
        relation = ET.SubElement(root.find("page/system/sig/relations"), "relation", source="11", target="99")
        ET.SubElement(relation, "future-relation", grade="0.5")
    evidence = parse_omr(modified_sheet(change))
    assert len(list(evidence.notes())) == 2
    assert sum(n.visual_size == "small" for n in evidence.notes()) == 1
    assert any(r.kind == "future-relation" for n in evidence.notes() for r in n.relationships)


def test_correlation_requires_part_staff_measure_pitch_position_and_voice():
    evidence = parse_omr(archive())
    matches = correlate(evidence, XmlContext(Document.parse(XML)))
    heads = {n.id: n for n in evidence.notes()}
    normal, small = heads["10"], heads["11"]
    assert matches[normal.provenance].confidence == "HIGH"
    assert matches[normal.provenance].event_ids == ("e-1",)
    assert matches[small.provenance].confidence == "UNMATCHED"
    for change in (lambda r: r.find("part/measure/note/voice").__setattr__("text", "other"),
                   lambda r: r.find("part/measure/note").set("default-x", "120")):
        assert correlate(evidence, XmlContext(Document.parse(modified_xml(change))))[normal.provenance].confidence != "HIGH"


def test_ambiguous_correlation_never_adds_a_duplicate_note():
    def change(root):
        note = deepcopy(root.find("part/measure/note"))
        note.find("pitch/step").text = "C"
        note.find("pitch/octave").text = "5"
        ET.SubElement(note, "chord")
        measure = root.find("part/measure")
        measure.insert(list(measure).index(measure.find("note")) + 1, note)
        measure.insert(list(measure).index(note) + 1, deepcopy(note))
    xml = modified_xml(change)
    result = recover(xml, archive(), Settings())
    candidate = result.report["candidates"][0]
    assert candidate["correlation"]["confidence"] == "AMBIGUOUS"
    assert candidate["state"] == "REVIEW_REQUIRED"
    assert result.document.xml() == xml


def test_high_confidence_mixed_size_chord_survives_with_exact_timing_and_preservation():
    result = recover(XML, archive(), Settings())
    assert result.report["auto_recovered"] == 1
    candidate = result.report["candidates"][0]
    assert candidate["classification"] == "SIMULTANEOUS_VARIANT"
    assert candidate["operation"] == "ADD_SIMULTANEOUS_NOTE" and candidate["confidence"] == "HIGH"
    doc = result.document
    measure = doc.root.find("part/measure")
    notes = measure.findall("note")
    assert [n.findtext("pitch/step") for n in notes] == ["A", "C", None]
    small = notes[1]
    assert small.findtext("pitch/octave") == "5" and small.find("chord") is not None
    assert small.find("grace") is None and small.find("cue") is None
    assert small.findtext("duration") == notes[0].findtext("duration") == "2"
    assert small.findtext("voice") == notes[0].findtext("voice") == "1"
    assert small.findtext("staff") == "1"
    assert small.find("type").get("size") == "cue" and small.find("notehead").get("font-size") == "small"
    events = list(XmlContext(doc).events.values())
    assert events[0].event.onset == events[1].event.onset == "0"
    assert result.report["rhythm_after"]["m-1"]["valid"]
    original = ET.fromstring(XML)
    def structure(node):
        node = deepcopy(node)
        for child in node.iter():
            child.tail = None
            if child.text is not None and not child.text.strip():
                child.text = None
        return ET.tostring(node)
    for tag in ("work", "identification", "defaults", "part-list"):
        assert structure(doc.root.find(tag)) == structure(original.find(tag))
    for node in original.find("part/measure"):
        matches = [n for n in measure if structure(n) == structure(node)]
        assert matches, node.tag
    assert any(node.tag is ET.Comment for node in doc.root.iter())
    repeated = recover(doc.xml(), archive(), Settings())
    assert repeated.document.xml() == doc.xml() and repeated.report["auto_recovered"] == 0


@pytest.mark.parametrize("problem", ["low_grade", "geometry_only", "wrong_pitch_position", "separate_stem", "no_part_map", "unknown_version"])
def test_uncertain_evidence_keeps_exact_xml_and_requires_review(problem):
    root = ET.fromstring(SHEET)
    head = root.find('.//head[@id="11"]')
    book = ET.fromstring(BOOK)
    if problem == "low_grade":
        head.set("ctx-grade", "0.3")
    elif problem == "geometry_only":
        head.set("shape", "NOTEHEAD_BLACK")
    elif problem == "wrong_pitch_position":
        head.set("pitch", "4")
    elif problem == "separate_stem":
        root.find('.//relation[@source="11"][@target="30"]').set("target", "other")
    elif problem == "no_part_map":
        book.find("sheet/page/system").remove(book.find("sheet/page/system/part"))
    else:
        book.set("software-version", "6.0.0")
    result = recover(XML, archive(ET.tostring(root), ET.tostring(book)), Settings())
    assert result.document.xml() == XML
    assert result.report["review_required"] and result.report["auto_recovered"] == 0


@pytest.mark.parametrize("kind", ["grace", "cue"])
def test_explicit_grace_and_cue_are_distinct_from_small_rhythmic_notes(kind):
    def change(root):
        chord = root.find('.//head-chord[@id="20"]')
        if kind == "grace":
            chord.tag = "grace-chord"
    xml = XML
    if kind == "cue":
        xml = modified_xml(lambda root: ET.SubElement(root.find("part/measure/note"), "cue"))
        # Cue semantics apply to the matched small head, not an unrelated normal anchor.
        xml = xml.replace(b"<step>A</step><octave>4</octave>", b"<step>C</step><octave>5</octave>")
    result = recover(xml, modified_sheet(change), Settings())
    assert result.document.xml() == xml
    assert result.report["candidates"][0]["classification"] == kind.upper()
    assert result.report["review_required"]


def test_inherited_key_and_written_pitch_justify_flat_without_hard_coded_pitch():
    def change_sheet(root):
        root.find('.//head[@id="11"]').set("pitch", "0")
        root.find('.//head[@id="11"]/bounds').set("y", "94")
        root.find("page/system/stack").set("id", "2")
        root.find("page/system/part/measure").set("id", "2")
    def change_xml(root):
        root.find("part/measure/attributes/key/fifths").text = "-1"
        measure = deepcopy(root.find("part/measure"))
        measure.set("number", "2")
        measure.find("attributes").remove(measure.find("attributes/key"))
        root.find("part").append(measure)
    result = recover(modified_xml(change_xml), modified_sheet(change_sheet), Settings())
    candidate = result.report["candidates"][0]
    assert candidate["pitch"] == {"step": "B", "octave": 4, "alter": "-1"}
    assert candidate["state"] == "AUTO_RECOVERED"
    recovered = result.document.root.findall("part/measure")[1].findall("note")[1]
    assert recovered.findtext("pitch/alter") == "-1"


def test_existing_small_member_only_changes_display_and_preserves_notation():
    def change(root):
        measure = root.find("part/measure")
        note = ET.fromstring('<note default-x="51"><chord/><pitch><step>C</step><octave>5</octave></pitch><duration>2</duration><voice>1</voice><type>quarter</type><notations><articulations><staccato/></articulations></notations></note>')
        measure.insert(list(measure).index(measure.find("note")) + 1, note)
    xml = modified_xml(change)
    result = recover(xml, archive(), Settings())
    assert result.report["candidates"][0]["operation"] == "PRESERVE_SMALL_DISPLAY_SIZE"
    assert result.report["auto_recovered"] == 1
    notes = result.document.root.findall("part/measure/note")
    assert len(notes) == 3
    assert notes[1].find("notehead").get("font-size") == "small"
    assert notes[1].find("notations/articulations/staccato") is not None
    assert notes[1].find("grace") is None and notes[1].findtext("duration") == "2"


def test_explicit_accidental_is_retained_on_recovered_pitch_and_display():
    def change(root):
        inters = root.find("page/system/sig/inters")
        ET.SubElement(inters, "alter", id="42", shape="SHARP", grade="0.95")
        relation = ET.SubElement(root.find("page/system/sig/relations"), "relation", source="42", target="11")
        ET.SubElement(relation, "alter-head", grade="0.95")
    result = recover(XML, modified_sheet(change), Settings())
    note = result.document.root.findall("part/measure/note")[1]
    assert note.findtext("pitch/alter") == "1" and note.findtext("accidental") == "sharp"
    assert result.report["auto_recovered"] == 1


@pytest.mark.parametrize("problem,code", [("under", "measure_underfilled"), ("over", "measure_overfilled"),
    ("invalid", "invalid_duration"), ("chord", "broken_chord"), ("overlap", "voice_overlap")])
def test_rhythm_mismatches_block_missing_note_recovery(problem, code):
    def change(root):
        measure = root.find("part/measure")
        if problem in ("under", "over", "invalid"):
            measure.findall("note")[1].find("duration").text = {"under": "1", "over": "4", "invalid": "-1"}[problem]
        elif problem == "chord":
            ET.SubElement(measure.find("note"), "chord")
        else:
            backup = ET.Element("backup")
            ET.SubElement(backup, "duration").text = "2"
            measure.insert(list(measure).index(measure.find("note")) + 1, backup)
    result = recover(modified_xml(change), archive(), Settings())
    assert code in {d["code"] for d in result.report["rhythm_before"]["m-1"]["diagnostics"]}
    assert result.report["auto_recovered"] == 0 and result.report["review_required"]


def test_backup_forward_rests_chords_and_independent_voices_keep_order_and_extent():
    def change(root):
        measure = root.find("part/measure")
        backup = ET.SubElement(measure, "backup")
        ET.SubElement(backup, "duration").text = "4"
        forward = ET.SubElement(measure, "forward")
        ET.SubElement(forward, "duration").text = "2"
        ET.SubElement(forward, "voice").text = "2"
        rest = deepcopy(measure.findall("note")[1])
        rest.find("voice").text = "2"
        measure.append(rest)
    xml = modified_xml(change)
    result = recover(xml, archive(), Settings())
    nodes = result.document.root.find("part/measure")
    assert [e.tag for e in nodes][-3:] == ["backup", "forward", "note"]
    assert result.report["rhythm_after"]["m-1"]["actual"] == "2"
    assert result.report["rhythm_after"]["m-1"]["valid"]


def test_recognition_and_review_surface_evidence_without_replacing_the_transposer():
    config = Settings()
    class Provider:
        def recognize_result(self, *_):
            return ProviderOutput(XML, "Audiveris", archive())
    recognition = MusicRecognitionService(Provider(), config)
    review = ReviewService(MemoryReviewStore(config, lambda: 1000), config, lambda: 1000)
    app.dependency_overrides[get_recognition_service] = lambda: recognition
    app.dependency_overrides[get_review_service] = lambda: review
    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/recognize", files={"file": ("source.png", png(), "image/png")}, data={"response_format": "json"})
            assert response.status_code == 200
            payload = response.json()
            assert payload["diagnostics"]["semantic_recovery"]["auto_recovered"] == 1
            corrected = b64decode(payload["musicxml_base64"])
            assert b64decode(payload["baseline_musicxml_base64"]) == XML
            response = client.post("/api/v1/reviews", files={"musicxml": ("baseline.musicxml", XML), "omr": ("evidence.omr", archive())})
            session = response.json()
            assert response.status_code == 201 and session["state"] == "REVIEW_REQUIRED"
            assert session["semantic_recovery"]["auto_recovered"] == 1
            assert review.store.get(session["id"]).document.original == XML
            assert b64decode(session["musicxml_base64"]) == corrected
            assert session["can_undo"]
            undone = review.history(session["id"], session["revision"], "undo")
            assert b64decode(undone["musicxml_base64"]) == XML
            assert "/private" not in response.text
            transposed = client.post("/api/v1/transpose/musicxml", files={"file": ("corrected.musicxml", corrected)}, data={"semitones": "0"})
            assert transposed.status_code == 200 and transposed.content == corrected
    finally:
        app.dependency_overrides.pop(get_recognition_service, None)
        app.dependency_overrides.pop(get_review_service, None)


def test_review_ambiguity_invalid_evidence_and_quota_are_visible():
    config = Settings()
    service = ReviewService(MemoryReviewStore(config, lambda: 1000), config, lambda: 1000)
    weak = modified_sheet(lambda root: root.find('.//head[@id="11"]').set("ctx-grade", "0.3"))
    payload = service.create(XML, omr=weak)
    assert payload["state"] == "REVIEW_REQUIRED" and payload["semantic_recovery"]["review_candidates"] == 1
    assert b64decode(payload["musicxml_base64"]) == XML
    invalid = service.create(XML, omr=b"bad zip")
    assert "invalid_omr" in invalid["semantic_recovery"]["diagnostics"]
    assert invalid["state"] == "REVIEW_REQUIRED"
    store = MemoryReviewStore(Settings(review_max_total_bytes=1), lambda: 1000)
    from app.music.review.document import ReviewError
    with pytest.raises(ReviewError, match="memory budget"):
        ReviewService(store, config, lambda: 1000).create(XML, omr=weak)


def test_semantic_review_validation_blocks_overlapping_voice_verification():
    def change(root):
        measure = root.find("part/measure")
        backup = ET.Element("backup")
        ET.SubElement(backup, "duration").text = "2"
        measure.insert(list(measure).index(measure.find("note")) + 1, backup)
    config = Settings()
    service = ReviewService(MemoryReviewStore(config, lambda: 1000), config, lambda: 1000)
    payload = service.create(modified_xml(change), omr=archive())
    assert not payload["validation"]["can_verify"]
    assert "voice_overlap" in {d["code"] for d in payload["validation"]["diagnostics"]}
    from app.music.review.document import ReviewError
    with pytest.raises(ReviewError, match="validation errors"):
        service.verify(payload["id"], payload["revision"])


def test_duplicate_evidence_does_not_repeat_candidates():
    result = recover(XML, archive(), Settings(), analysis_omr=archive())
    assert result.report["auto_recovered"] == 1 and len(result.report["candidates"]) == 1
    assert "duplicate_omr_evidence_ignored" in result.report["diagnostics"]


def test_disabled_semantic_recovery_does_not_change_xml():
    result = recover(XML, archive(), Settings(audiveris_semantic_recovery_enabled=False))
    assert result.document.xml() == XML
    assert result.report["diagnostics"] == ["semantic_recovery_disabled"]


@pytest.mark.parametrize("baseline", [None, b"invalid archive"])
def test_analysis_without_valid_baseline_cannot_patch_even_with_complete_metadata(baseline):
    result = recover(XML, baseline, Settings(), analysis_omr=archive())
    assert result.document.xml() == XML
    assert result.report["auto_recovered"] == 0 and result.report["review_required"]
    assert "omr_analysis_baseline_unavailable" in result.report["diagnostics"]
    assert result.report["candidates"][0]["confidence"] == "AMBIGUOUS"


@pytest.mark.parametrize("mismatch", [None, "pixels", "geometry", "staff"])
def test_links_analysis_requires_identical_source_and_unique_geometry_registration(mismatch):
    root = ET.fromstring(SHEET)
    root.find('.//head[@id="11"]').set("shape", "NOTEHEAD_BLACK")
    root.find("scale/black-head").set("mean-width", "14")
    baseline = archive(ET.tostring(root), extras=[("sheet#1/BINARY.png", b"same-source-pixels")])
    book = ET.fromstring(BOOK)
    book.find("score").remove(book.find("score/logical-part"))
    book.find("sheet/page/system/part").attrib.pop("logical-id")
    analysis = ET.fromstring(SHEET)
    for measure in analysis.findall("page/system/part/measure"):
        measure.remove(measure.find("voice"))
    analysis.find("page/system/stack").remove(analysis.find("page/system/stack/slot"))
    if mismatch == "geometry":
        analysis.find("page/system/stack").set("left", "101")
    elif mismatch == "staff":
        analysis.find("page/system/part/staff").set("id", "other")
    pixels = b"other-score" if mismatch == "pixels" else b"same-source-pixels"
    second = archive(ET.tostring(analysis), ET.tostring(book), [("sheet#1/BINARY.png", pixels)])
    result = recover(XML, baseline, Settings(), analysis_omr=second)
    assert result.report["auto_recovered"] == int(mismatch is None)
    if mismatch is None:
        assert "omr_analysis_registered_by_source_and_geometry" in result.report["diagnostics"]
    else:
        assert result.document.xml() == XML
        assert "omr_analysis_registration_incomplete" in result.report["diagnostics"]


def test_semantic_projection_limit_keeps_valid_recognition_baseline():
    class Provider:
        def recognize_result(self, *_):
            return ProviderOutput(XML, "Audiveris", archive())
    result = MusicRecognitionService(Provider(), Settings(review_max_xml_nodes=1)).recognize_result(png(), "score.png", "image/png")
    assert result.musicxml == XML
    assert result.diagnostics["semantic_recovery"]["diagnostics"] == ["semantic_projection_unavailable"]


def test_benchmark_records_baseline_and_corrected_artifacts_independently(monkeypatch, tmp_path):
    from app.music.recovery.benchmark import run
    class Provider:
        def __init__(self, *_):
            pass
        def recognize_result(self, *_):
            return ProviderOutput(XML, "Audiveris", archive())
    monkeypatch.setattr("app.music.recovery.benchmark.AudiverisProvider", Provider)
    source = tmp_path / "input.png"
    source.write_bytes(png())
    report, artifacts = run(source, Settings())
    assert report["A_baseline"]["pitched_notes"] == 1
    assert report["F_corrected"]["pitched_notes"] == 2
    assert len(report["D_auto_recovered"]) == 1
    assert artifacts["baseline.musicxml"] == XML
    assert artifacts["corrected.musicxml"] != XML


@pytest.mark.parametrize("analysis", [False, True])
def test_adapter_keeps_production_switches_off_and_analysis_bounded_separate(monkeypatch, tmp_path, analysis):
    config = Settings(audiveris_semantic_analysis_enabled=analysis)
    provider = AudiverisProvider(config)
    monkeypatch.setattr(provider, "_check_languages", lambda *_: tmp_path)
    commands = []
    class Process:
        def __init__(self, command, **kwargs):
            commands.append(command)
            output = Path(command[command.index("-output") + 1])
            (output / "input.omr").write_bytes(archive())
            if "-transcribe" in command:
                (output / "input.musicxml").write_bytes(XML)
            assert kwargs["start_new_session"] and "shell" not in kwargs
            assert kwargs["env"]["TESSDATA_PREFIX"] == str(tmp_path)
        def wait(self, timeout=None):
            assert timeout == 120
            return 0
    monkeypatch.setattr(subprocess, "Popen", Process)
    result = MusicRecognitionService(provider, config).recognize_result(png(), "score.png", "image/png")
    assert len(commands) == 1 + analysis
    for switch in ("smallHeads", "smallBeams"):
        assert f"org.audiveris.omr.sheet.ProcessingSwitches.{switch}=false" in commands[0]
        if analysis:
            assert f"org.audiveris.omr.sheet.ProcessingSwitches.{switch}=true" in commands[1]
    if analysis:
        assert commands[1][commands[1].index("-step") + 1] == "LINKS"
        assert "-export" not in commands[1] and "-transcribe" not in commands[1]
        assert result.evidence_omr == archive()


def test_optional_analysis_timeout_kills_group_and_keeps_baseline(monkeypatch, tmp_path):
    config = Settings(audiveris_semantic_analysis_enabled=True)
    provider = AudiverisProvider(config)
    source = tmp_path / "input.pdf"
    source.write_bytes(b"pdf")
    directory = tmp_path / "output"
    directory.mkdir()
    monkeypatch.setattr(provider, "_check_languages", lambda *_: tmp_path)
    killed = []
    class Process:
        pid = 123
        def __init__(self, command, **kwargs):
            self.analysis = "-step" in command
            output = Path(command[command.index("-output") + 1])
            if not self.analysis:
                (output / "input.omr").write_bytes(archive())
                (output / "input.musicxml").write_bytes(XML)
        def wait(self, timeout=None):
            if self.analysis and timeout:
                raise subprocess.TimeoutExpired("analysis", timeout)
            return 0
    monkeypatch.setattr(subprocess, "Popen", Process)
    monkeypatch.setattr("os.killpg", lambda pid, sig: killed.append((pid, sig)))
    result = provider.recognize_result(source, directory, resolve_profile(config))
    assert result.musicxml == XML and result.evidence_omr is None
    assert killed == [(123, signal.SIGKILL)]
    assert "semantic_analysis_unavailable" in {issue.code for issue in result.warnings}
