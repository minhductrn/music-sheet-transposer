"""Product workflow regressions use synthetic XML/evidence, never recognition."""
from base64 import b64decode
from copy import deepcopy
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from fastapi.testclient import TestClient
import pytest

from app.api.v1.reviews import get_review_service
from app.core.config import Settings
from app.main import app
from app.music.review.service import ReviewService
from app.music.review.storage import MemoryReviewStore

FIXTURES = Path(__file__).parent / "music/fixtures"
# Begin with a regular upper chord member; rich notation remains unrelated content.
XML = (FIXTURES / "review_mixed_size.musicxml").read_bytes().replace(
    b'<type size="cue">quarter</type>', b'<type>quarter</type>',
).replace(b'<notehead font-size="small">normal</notehead>', b'')


@pytest.fixture
def workflow():
    config = Settings()
    service = ReviewService(MemoryReviewStore(config, lambda: 1000), config, lambda: 1000)
    app.dependency_overrides[get_review_service] = lambda: service
    try:
        with TestClient(app) as client:
            yield client, service
    finally:
        app.dependency_overrides.pop(get_review_service, None)


def create(client, xml=XML, evidence=None):
    files = {"musicxml": ("score.musicxml", xml)}
    if evidence:
        files["omr"] = ("evidence.omr", evidence)
    response = client.post("/api/v1/reviews", files=files)
    assert response.status_code == 201, response.text
    return response.json()


def request(client, review, path, body=None, method="POST"):
    return client.request(method, f'/api/v1/reviews/{review["id"]}/{path}', json=body,
                          headers={"If-Match": f'"{review["revision"]}"'})


def patch(client, review, event_id="e-2", **fields):
    response = request(client, review, f"events/{event_id}", fields, "PATCH")
    assert response.status_code == 200, response.text
    return response.json()


def event(review, identifier="e-2"):
    return next(e for p in review["score"]["parts"] for m in p["measures"]
                for v in m["voices"] for e in v["events"] if e["id"] == identifier)


def xml(review):
    return b64decode(review["musicxml_base64"])


def verify(client, review):
    response = request(client, review, "verify", {"confirmed_source_comparison": True})
    assert response.status_code == 200, response.text
    return response.json()


def evidence(small=True):
    sheet = (FIXTURES / "semantic_omr_sheet.xml").read_bytes()
    if not small:
        sheet = sheet.replace(b'NOTEHEAD_BLACK_SMALL', b'NOTEHEAD_BLACK')
    data = BytesIO()
    with ZipFile(data, "w") as archive:
        archive.writestr("book.xml", (FIXTURES / "semantic_omr_book.xml").read_bytes())
        archive.writestr("sheet#1/sheet#1.xml", sheet)
    return data.getvalue()


@pytest.mark.parametrize("semitones", [0, 2, -2])
def test_mixed_size_patch_verified_handoff_and_exports(workflow, monkeypatch, semitones):
    client, _ = workflow
    original = create(client)
    corrected = patch(client, original, display_size="small")
    before, after = event(original), event(corrected)
    for field in ("pitch", "duration", "onset", "voice", "staff", "grace", "chord_id"):
        assert after[field] == before[field]
    assert after["display_size"] == "small" and not after["grace"]
    assert event(corrected, "e-1") == event(original, "e-1")
    assert corrected["validation"]["error_count"] == 0
    before_tree, after_tree = ET.fromstring(XML), ET.fromstring(xml(corrected))
    target = after_tree.findall(".//note")[1]
    target.find("type").attrib.pop("size")
    target.remove(target.find("notehead"))
    assert ET.tostring(before_tree) == ET.tostring(after_tree)
    assert after["provenance"]["manual_fields"] == ["display_size"]
    verified = verify(client, corrected)
    import app.music.musicxml.transposer as transposer
    real = transposer.transpose_musicxml_document
    inputs = []
    def capture(contents, interval):
        inputs.append(contents)
        return real(contents, interval)
    monkeypatch.setattr(transposer, "transpose_musicxml_document", capture)
    result = request(client, verified, "transpose", {"semitones": semitones})
    assert result.status_code == 200
    assert inputs == [xml(corrected)] and inputs[0] != XML
    root = ET.fromstring(result.content)
    a, c = root.findall(".//note")[:2]
    assert c.find("notehead").get("font-size") == "small"
    assert c.find("grace") is None and c.find("chord") is not None
    assert a.findtext("duration") == c.findtext("duration") == "4"
    assert [n.findtext("pitch/step") for n in (a, c)] == {0: ["A", "C"], 2: ["B", "D"], -2: ["G", "B"]}[semitones]
    assert "transposed.musicxml" in result.headers["content-disposition"]
    exported = client.get(f'/api/v1/reviews/{verified["id"]}/musicxml?verified_only=true')
    assert exported.status_code == 200 and exported.content == xml(corrected)
    assert "corrected.musicxml" in exported.headers["content-disposition"]
    assert root.findtext(".//lyric/text") == "ta"
    assert root.findtext(".//harmony/root/root-step") == "F"
    if semitones == 0:
        assert result.content == exported.content


def test_pitch_only_patch_preserves_unrelated_note_xml(workflow):
    client, _ = workflow
    original = create(client)
    corrected = patch(client, original, event_id="e-1", pitch={"step": "B", "alter": "-1", "octave": 4})
    before, after = ET.fromstring(XML), ET.fromstring(xml(corrected))
    node = after.find(".//note/pitch")
    node.clear()
    node.extend(deepcopy(list(before.find(".//note/pitch"))))
    assert ET.tostring(before) == ET.tostring(after)
    assert event(corrected, "e-1")["pitch"] == {"step": "B", "alter": "-1", "octave": 4}


@pytest.mark.parametrize("fields", [
    {"pitch": {"step": "H", "octave": 4}}, {"pitch": {"step": "C", "octave": 10}},
    {"pitch": {"step": "C", "alter": "NaN", "octave": 4}},
    {"duration": "0"}, {"duration": "1/0"}, {"duration": "1/3"}, {"display_size": "tiny"},
])
def test_invalid_patch_rejected_without_state_change(workflow, fields):
    client, service = workflow
    review = create(client)
    response = request(client, review, "events/e-2", fields, "PATCH")
    assert response.status_code == 422
    assert service.get(review["id"]) == review


def test_multiple_undo_restores_xml_and_manual_provenance(workflow):
    client, _ = workflow
    original = create(client)
    first = patch(client, original, display_size="small")
    second = patch(client, first, pitch={"step": "D", "octave": 5})
    undone = request(client, second, "undo").json()
    assert xml(undone) == xml(first) and event(undone) == event(first)
    twice = request(client, undone, "undo").json()
    assert xml(twice) == XML and event(twice) == event(original)
    redone = request(client, twice, "redo").json()
    assert xml(redone) == xml(first) and event(redone) == event(first)


def test_omr_ambiguity_allows_explicit_confirmation_and_export(workflow):
    client, service = workflow
    baseline = (FIXTURES / "semantic_baseline.musicxml").read_bytes()
    review = create(client, baseline, evidence(False))
    assert review["semantic_recovery"]["review_required"]
    assert "review_issues" not in review
    assert review["validation"]["can_verify"]
    assert review["state"] != "VERIFIED"
    assert request(client, review, "verify", {"confirmed_source_comparison": False}).status_code == 422
    assert client.get(f'/api/v1/reviews/{review["id"]}/musicxml?verified_only=true').status_code == 409
    verified = verify(client, review)
    exported = client.get(f'/api/v1/reviews/{verified["id"]}/musicxml?verified_only=true')
    assert exported.status_code == 200 and exported.content == baseline
    assert client.get(f'/api/v1/reviews/{verified["id"]}').json()["semantic_recovery"] == review["semantic_recovery"]
    imported = create(client, exported.content)
    assert xml(imported) == baseline and imported["state"] != "VERIFIED"
    candidate = review["semantic_recovery"]["candidates"][0]
    changed = patch(client, verified, event_id=candidate["event_id"] or candidate["anchor_id"], display_size="small")
    assert changed["state"] != "VERIFIED"
    assert request(client, changed, "transpose", {"semitones": 2}).status_code == 409
    reverted = request(client, changed, "undo").json()
    assert xml(reverted) == baseline and reverted["state"] != "VERIFIED"
    assert verify(client, reverted)["state"] == "VERIFIED"


def test_auto_recovery_history_retains_evidence_without_issue_gate(workflow):
    client, _ = workflow
    review = create(client, (FIXTURES / "semantic_baseline.musicxml").read_bytes(), evidence())
    recovered = event(review, "recovery-1")
    assert recovered["provenance"]["origin"] == "semantic_recovery"
    assert recovered["provenance"]["evidence_ids"]
    pitched = patch(client, review, event_id="recovery-1", pitch={"step": "D", "octave": 5})
    assert event(pitched, "recovery-1")["provenance"]["evidence_ids"] == recovered["provenance"]["evidence_ids"]
    undone_edit = request(client, pitched, "undo").json()
    assert xml(undone_edit) == xml(review)
    undone_recovery = request(client, undone_edit, "undo").json()
    assert xml(undone_recovery) == (FIXTURES / "semantic_baseline.musicxml").read_bytes()
    assert undone_recovery["validation"]["can_verify"]
    assert undone_recovery["semantic_recovery"] == review["semantic_recovery"]


def test_overlap_is_advisory_without_omr_and_edit_is_undoable(workflow):
    client, _ = workflow
    review = create(client)
    # Longer voice-2 note crosses its retained forward into the following rest.
    corrected = patch(client, review, event_id="e-4", duration="4")
    assert any(i["code"] == "voice_overlap" for i in corrected["validation"]["diagnostics"]) is False
    # Switching voice 2 to voice 1 makes its inherited backup timeline overlap voice 1.
    overlap = patch(client, corrected, event_id="e-4", voice="1")
    assert any(i["code"] == "voice_overlap" for i in overlap["validation"]["diagnostics"])
    assert overlap["validation"]["can_verify"]
    assert all(not i["blocking"] for i in overlap["validation"]["diagnostics"] if i["code"] == "voice_overlap")
    undone = request(client, overlap, "undo").json()
    assert xml(undone) == xml(corrected)


def test_stale_verification_and_invalid_endpoint_inputs(workflow):
    client, service = workflow
    review = create(client)
    assert request(client, review, "transpose", {"semitones": 2}).status_code == 409
    verified = verify(client, review)
    assert request(client, review, "transpose", {"semitones": 2}).status_code == 409
    assert request(client, verified, "transpose", {"semitones": True}).status_code == 422
    changed = patch(client, verified, display_size="small")
    assert request(client, verified, "transpose", {"semitones": 2}).status_code == 409
    assert client.get(f'/api/v1/reviews/{changed["id"]}/musicxml?verified_only=true').status_code == 409
    assert request(client, changed, "events/deleted", {"display_size": "small"}, "PATCH").status_code == 404
    assert request(client, changed, "issues/resolve", {"issue_id": "unknown", "disposition": "ACCEPTED", "note": "Checked"}).status_code == 404
    assert service.get(changed["id"]) == changed
    assert client.post('/api/v1/reviews/missing/transpose', json={"semitones": 0}, headers={"If-Match": '"1"'}).status_code == 404


def test_transposition_failure_does_not_mutate_verified_review(workflow):
    client, service = workflow
    source = XML.replace(b'<fifths>-1</fifths>', b'<key-step>C</key-step><key-alter>0.5</key-alter>')
    verified = verify(client, create(client, source))
    response = request(client, verified, "transpose", {"semitones": 2})
    assert response.status_code == 422 and isinstance(response.json()["detail"], str)
    assert service.get(verified["id"]) == verified


def test_removed_issue_resolution_endpoint_is_unavailable(workflow):
    client, _ = workflow
    review = create(client)
    assert request(client, review, "issues/resolve", {"issue_id": "obsolete"}).status_code == 404


@pytest.mark.parametrize("lower,upper", [("A", "C"), ("F", "A")])
def test_two_benchmark_style_pairs_using_synthetic_score(workflow, lower, upper):
    client, _ = workflow
    tree = ET.fromstring(XML)
    first, second = tree.findall(".//note")[:2]
    first.find("pitch/step").text = lower
    second.find("pitch/step").text = upper
    second.find("pitch/octave").text = "5" if upper == "C" else "4"
    source = ET.tostring(tree)
    original = create(client, source)
    corrected = patch(client, original, display_size="small")
    for field in ("pitch", "onset", "duration", "voice", "staff", "grace", "chord_id"):
        assert event(corrected)[field] == event(original)[field]
    assert event(corrected)["display_size"] == "small"
    assert event(corrected, "e-1") == event(original, "e-1")
    assert corrected["validation"]["error_count"] == 0
    verified = verify(client, corrected)
    result = request(client, verified, "transpose", {"semitones": 0})
    assert result.status_code == 200 and result.content == xml(corrected)



def test_duration_patch_checks_chord_and_keeps_backup_forward(workflow):
    client, _ = workflow
    original = create(client)
    corrected = patch(client, original, duration="2")
    assert event(corrected)["duration"] == event(corrected, "e-1")["duration"] == "2"
    assert event(corrected)["onset"] == event(corrected, "e-1")["onset"] == "0"
    assert any(i["code"] == "measure_duration_mismatch" for i in corrected["validation"]["diagnostics"])
    before, after = ET.fromstring(XML), ET.fromstring(xml(corrected))
    for tag in ("backup", "forward", "lyric", "harmony", "notations", "direction"):
        assert [ET.tostring(n) for n in before.findall('.//' + tag)] == [ET.tostring(n) for n in after.findall('.//' + tag)]
    assert event(corrected, "e-1")["provenance"]["manual_fields"] == ["duration"]


def test_malformed_document_does_not_create_review(workflow):
    client, _ = workflow
    response = client.post('/api/v1/reviews', files={"musicxml": ("broken.musicxml", b"<broken>")})
    assert response.status_code == 422 and isinstance(response.json()["detail"], str)
