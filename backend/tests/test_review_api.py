from base64 import b64decode
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree as ET

from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfWriter
import pytest

from app.api.v1.reviews import get_review_service
from app.core.config import Settings
from app.main import app
from app.music.review.document import ReviewError
from app.music.review.service import ReviewService
from app.music.review.storage import MemoryReviewStore


XML = (Path(__file__).parent / "music/fixtures/review_mixed_size.musicxml").read_bytes()


def image():
    data = BytesIO()
    Image.new("RGB", (20, 30), "white").save(data, "PNG")
    return data.getvalue()


@pytest.fixture
def setup_review():
    now = [1000.0]
    config = Settings(review_lifetime_seconds=60)
    store = MemoryReviewStore(config, lambda: now[0])
    service = ReviewService(store, config, lambda: now[0])
    app.dependency_overrides[get_review_service] = lambda: service
    try:
        with TestClient(app) as client:
            yield client, service, now
    finally:
        app.dependency_overrides.pop(get_review_service, None)


def create(client, xml=XML, source=None):
    files = {"musicxml": ("draft.musicxml", xml, "application/vnd.recordare.musicxml+xml")}
    if source:
        files["source"] = source
    return client.post("/api/v1/reviews", files=files)


def change(client, review, path, body=None, method="POST"):
    return client.request(method, f'/api/v1/reviews/{review["id"]}/{path}', json=body,
                          headers={"If-Match": f'"{review["revision"]}"'})


def test_create_retrieve_retained_source_and_exact_original(setup_review):
    client, service, _ = setup_review
    contents = image()
    response = create(client, source=("original.png", contents, "image/png"))
    assert response.status_code == 201
    review = response.json()
    assert review["state"] == "DRAFT" and review["revision"] == 1
    assert len(review["id"]) >= 24 and "/" not in review["id"]
    assert review["source"] == {"media_type": "image/png", "pages": 1}
    assert review["validation"]["can_verify"] and review["validation"]["error_count"] == 0
    assert not review["can_undo"] and not review["can_redo"]
    assert b64decode(review["musicxml_base64"]) == XML
    assert response.headers["etag"] == '"1"' and response.headers["cache-control"] == "no-store"
    assert client.get(f'/api/v1/reviews/{review["id"]}').json() == review
    src = client.get(f'/api/v1/reviews/{review["id"]}/source')
    assert src.content == contents and src.headers["content-type"] == "image/png"
    assert src.headers["x-content-type-options"] == "nosniff"
    assert service.store.get(review["id"]).document.original == XML
    assert client.get(f'/api/v1/reviews/{review["id"]}/musicxml?original=true').content == XML


def test_pdf_retention_reports_pages_without_omr(setup_review):
    client, _, _ = setup_review
    data = BytesIO()
    writer = PdfWriter()
    for _ in range(2):
        writer.add_blank_page(100, 100)
    writer.write(data)
    review = create(client, source=("original.pdf", data.getvalue(), "application/pdf")).json()
    assert review["source"]["pages"] == 2
    assert client.get(f'/api/v1/reviews/{review["id"]}/source').content == data.getvalue()


def test_event_patch_is_atomic_and_preserves_original(setup_review):
    client, service, _ = setup_review
    review = create(client).json()
    failed = change(client, review, "events/e-1", {"pitch": {"step": "G", "octave": 4}, "duration": "1/3"}, "PATCH")
    assert failed.status_code == 422
    assert service.get(review["id"]) == review
    result = change(client, review, "events/e-2", {"pitch": {"step": "B", "alter": "-1", "octave": 4}}, "PATCH")
    assert result.status_code == 200
    updated = result.json()
    assert updated["state"] == "REVIEW_REQUIRED" and updated["revision"] == 2 and updated["can_undo"]
    root = ET.fromstring(b64decode(updated["musicxml_base64"]))
    c = root.findall(".//note")[1]
    assert c.findtext("pitch/step") == "B" and c.findtext("pitch/alter") == "-1"
    assert c.find("chord") is not None and c.findtext("duration") == "4"
    assert client.get(f'/api/v1/reviews/{review["id"]}/musicxml?original=true').content == XML


def test_add_delete_preserves_stable_ids_and_live_preview(setup_review):
    client, _, _ = setup_review
    review = create(client).json()
    updated = change(client, review, "events", {"measure_id": "m-1", "chord_with_id": "e-1", "pitch": {"step": "E", "octave": 5}, "display_size": "small"}).json()
    es = updated["score"]["parts"][0]["measures"][0]["voices"][0]["events"]
    new = next(e for e in es if e["id"].startswith("new-"))
    assert (new["onset"], new["duration"], new["display_size"], new["grace"]) == ("0", "1", "small", False)
    assert [e["id"] for e in es[:2]] == ["e-1", "e-2"]
    deleted = change(client, updated, f'events/{new["id"]}', method="DELETE").json()
    assert [e["id"] for e in deleted["score"]["parts"][0]["measures"][0]["voices"][0]["events"]] == ["e-1", "e-2", "e-3"]


@pytest.mark.parametrize("path,body,method", [
    ("events/e-1", {"pitch": {"step": "G", "octave": 4}}, "PATCH"),
    ("events", {"measure_id": "m-2", "kind": "rest", "duration": "1"}, "POST"),
    ("events/e-2", None, "DELETE"),
    ("lyrics/l-1", {"text": "tạ"}, "PATCH"),
    ("harmonies/h-1", {"root_step": "G", "kind": "minor", "text": "Gm"}, "PATCH"),
    ("metadata/title", {"text": "Corrected title"}, "PATCH"),
    ("credits/c-1", {"text": "Corrected printed title"}, "PATCH"),
    ("events/e-6/lyrics", {"text": "mừng", "number": "1"}, "POST"),
    ("harmonies", {"measure_id": "m-2", "before_event_id": "e-6", "root_step": "B", "root_alter": "-1", "kind": "major", "text": "Bb"}, "POST"),
])
def test_undo_redo_restores_correction_and_stable_ids_for_every_operation(setup_review, path, body, method):
    client, _, _ = setup_review
    review = create(client).json()
    response = change(client, review, path, body, method)
    assert response.status_code == 200, response.text
    edited = response.json()
    undo = change(client, edited, "undo").json()
    assert b64decode(undo["musicxml_base64"]) == XML
    assert undo["score"] == review["score"] and undo["can_redo"]
    redo = change(client, undo, "redo").json()
    assert redo["score"] == edited["score"]
    assert b64decode(redo["musicxml_base64"]) == b64decode(edited["musicxml_base64"])
    assert redo["state"] == "REVIEW_REQUIRED"


def test_validation_never_auto_verifies_and_requires_human_confirmation(setup_review):
    client, _, _ = setup_review
    review = create(client).json()
    validated = change(client, review, "validate").json()
    assert validated["state"] == "REVIEW_REQUIRED" and validated["validation"]["can_verify"]
    assert change(client, validated, "verify", {}).status_code == 422
    assert change(client, validated, "verify", {"confirmed_source_comparison": False}).status_code == 422
    verified = change(client, validated, "verify", {"confirmed_source_comparison": True}).json()
    assert verified["state"] == "VERIFIED"
    edited = change(client, verified, "lyrics/l-1", {"text": "tạ"}, "PATCH").json()
    assert edited["state"] == "REVIEW_REQUIRED"
    undo = change(client, edited, "undo").json()
    assert undo["state"] == "REVIEW_REQUIRED"  # Undo must never restore an old verification.


def test_errors_block_verification_but_warnings_allow_it_and_stay_visible(setup_review):
    client, _, _ = setup_review
    invalid = XML.replace(b"<octave>5</octave>", b"<octave>22</octave>")
    review = create(client, invalid).json()
    assert review["validation"]["error_count"] > 0
    assert change(client, review, "verify", {"confirmed_source_comparison": True}).status_code == 409
    corrected = change(client, review, "events/e-2", {"pitch": {"step": "C", "octave": 5}, "duration": "2"}, "PATCH").json()
    assert corrected["validation"]["error_count"] == 0 and corrected["validation"]["warning_count"] > 0
    verified = change(client, corrected, "verify", {"confirmed_source_comparison": True}).json()
    assert verified["state"] == "VERIFIED" and verified["validation"]["warning_count"] > 0


@pytest.mark.parametrize("semitones,expected", [(0, ["A", "C"]), (2, ["B", "D"]), (-2, ["G", "B"])])
def test_verified_corrected_xml_handoff_to_unchanged_transposer(setup_review, semitones, expected):
    client, _, _ = setup_review
    review = create(client).json()
    assert client.get(f'/api/v1/reviews/{review["id"]}/musicxml?verified_only=true').status_code == 409
    corrected = change(client, review, "lyrics/l-1", {"text": "tạ"}, "PATCH").json()
    verified = change(client, corrected, "verify", {"confirmed_source_comparison": True}).json()
    xml = client.get(f'/api/v1/reviews/{review["id"]}/musicxml?verified_only=true').content
    response = client.post("/api/v1/transpose/musicxml", files={"file": ("verified.musicxml", xml)}, data={"semitones": str(semitones)})
    assert response.status_code == 200
    root = ET.fromstring(response.content)
    a, c = root.findall(".//note")[:2]
    assert [n.findtext("pitch/step") for n in (a, c)] == expected
    assert a.findtext("duration") == c.findtext("duration") == "4" and c.find("chord") is not None
    assert c.find("notehead").get("font-size") == "small" and c.find("grace") is None
    assert root.findtext(".//lyric/text") == "tạ"
    assert root.find(".//direction/direction-type/dynamics/p") is not None
    if semitones == 0:
        assert response.content == xml
    assert verified["state"] == "VERIFIED"


def test_stale_revision_and_missing_if_match_cannot_overwrite_corrections(setup_review):
    client, _, _ = setup_review
    review = create(client).json()
    updated = change(client, review, "lyrics/l-1", {"text": "tạ"}, "PATCH").json()
    assert change(client, review, "events/e-1", {"duration": "2"}, "PATCH").status_code == 409
    url = f'/api/v1/reviews/{review["id"]}/events/e-1'
    assert client.patch(url, json={"duration": "2"}).status_code == 428
    assert client.patch(url, json={"duration": "2"}, headers={"If-Match": "bogus"}).status_code == 422
    assert client.get(f'/api/v1/reviews/{review["id"]}').json() == updated


def test_cleanup_expiry_and_explicit_delete_release_original_source_and_history(setup_review):
    client, service, now = setup_review
    review = create(client, source=("source.png", image(), "image/png")).json()
    updated = change(client, review, "lyrics/l-1", {"text": "tạ"}, "PATCH").json()
    assert service.store.get(review["id"]).source is not None and updated["can_undo"]
    now[0] = 1060
    assert service.store.cleanup() == 1
    assert client.get(f'/api/v1/reviews/{review["id"]}').status_code == 404
    assert client.get(f'/api/v1/reviews/{review["id"]}/source').status_code == 404
    new = create(client).json()
    assert client.delete(f'/api/v1/reviews/{new["id"]}').status_code == 204
    assert client.get(f'/api/v1/reviews/{new["id"]}').status_code == 404
    assert service.store.cleanup() == 0


@pytest.mark.parametrize("path", ["", "/musicxml", "/source"])
def test_unknown_review_id_does_not_expose_paths(setup_review, path):
    client, _, _ = setup_review
    response = client.get(f"/api/v1/reviews/unknown{path}")
    assert response.status_code == 404 and "/tmp" not in response.text


@pytest.mark.parametrize("body", [{"pitch": {"step": "H", "octave": 4}}, {"pitch": {"step": "C", "octave": -1}}, {"staff": True}, {"voice": ""}, {"display_size": "tiny"}, {"unexpected": True}])
def test_input_schema_rejects_invalid_corrections(setup_review, body):
    client, _, _ = setup_review
    review = create(client).json()
    assert change(client, review, "events/e-1", body, "PATCH").status_code == 422


def test_control_characters_cannot_make_corrected_xml_malformed(setup_review):
    client, _, _ = setup_review
    review = create(client).json()
    assert change(client, review, "lyrics/l-1", {"text": "bad\u0000text"}, "PATCH").status_code == 422


@pytest.mark.parametrize("source", [("source.svg", b"<svg/>", "image/svg+xml"), ("bad.png", b"not png", "image/png"), ("bad.pdf", b"%PDF-invalid", "application/pdf")])
def test_invalid_sources_do_not_allocate_session(setup_review, source):
    client, service, _ = setup_review
    assert create(client, source=source).status_code in (415, 422)
    assert not service.store._sessions


def test_session_quota_expiry_and_history_bounds(setup_review):
    _, service, now = setup_review
    service.config.review_max_sessions = 1
    service.config.review_history_limit = 2
    review = service.create(XML)
    with pytest.raises(ReviewError) as exc:
        service.create(XML)
    assert exc.value.status_code == 503
    from app.music.review.models import TextPatch
    for index in range(4):
        review = service.lyric_patch(review["id"], review["revision"], "l-1", TextPatch(text=str(index)))
    assert len(service.store.get(review["id"]).undo) == 2
    now[0] = 1061
    assert service.create(XML)["state"] == "DRAFT"


def test_memory_budget_failure_leaves_existing_state_intact(setup_review):
    _, service, _ = setup_review
    review = service.create(XML)
    service.config.review_max_total_bytes = service.store.get(review["id"]).weight() + 1
    from app.music.review.models import TextPatch
    with pytest.raises(ReviewError) as exc:
        service.lyric_patch(review["id"], 1, "l-1", TextPatch(text="long replacement"))
    assert exc.value.status_code == 503
    assert service.get(review["id"]) == review


def test_edit_after_undo_discards_redo_without_reusing_added_id(setup_review):
    client, _, _ = setup_review
    review = create(client).json()
    request = {"measure_id": "m-2", "kind": "rest", "duration": "1"}
    first = change(client, review, "events", request).json()
    undone = change(client, first, "undo").json()
    second = change(client, undone, "events", request).json()
    assert not second["can_redo"]
    first_id = first["score"]["parts"][0]["measures"][1]["voices"][0]["events"][-1]["id"]
    second_id = second["score"]["parts"][0]["measures"][1]["voices"][0]["events"][-1]["id"]
    assert first_id != second_id


@pytest.mark.parametrize("path,body,method", [
    ("events/missing", {"duration": "1"}, "PATCH"),
    ("events/missing", None, "DELETE"),
    ("lyrics/missing", {"text": "word"}, "PATCH"),
    ("harmonies/missing", {"text": "C"}, "PATCH"),
    ("events", {"measure_id": "missing", "kind": "rest", "duration": "1"}, "POST"),
])
def test_invalid_score_object_ids_fail_without_changing_session(setup_review, path, body, method):
    client, _, _ = setup_review
    review = create(client).json()
    assert change(client, review, path, body, method).status_code == 404
    assert client.get(f'/api/v1/reviews/{review["id"]}').json() == review


def test_history_byte_limit_and_empty_undo_redo_are_bounded(setup_review):
    client, service, _ = setup_review
    service.config.review_history_max_bytes = 1
    review = create(client).json()
    assert change(client, review, "undo").status_code == 409
    assert change(client, review, "redo").status_code == 409
    updated = change(client, review, "lyrics/l-1", {"text": "tạ"}, "PATCH").json()
    assert not updated["can_undo"] and not updated["can_redo"]


def test_upload_limits_are_enforced_without_allocating_session(setup_review):
    client, service, _ = setup_review
    service.config.recognition_max_output_bytes = 50
    assert create(client).status_code == 413
    assert not service.store._sessions
    service.config.recognition_max_output_bytes = 20_000
    service.config.recognition_max_upload_bytes = 2
    assert create(client, source=("source.png", image(), "image/png")).status_code == 413
    assert not service.store._sessions


def test_concurrent_edits_to_same_revision_have_exactly_one_winner(setup_review):
    from concurrent.futures import ThreadPoolExecutor
    from app.music.review.models import TextPatch
    _, service, _ = setup_review
    review = service.create(XML)
    def edit(text):
        try:
            return service.lyric_patch(review["id"], 1, "l-1", TextPatch(text=text))
        except ReviewError as error:
            return error.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(edit, ["first", "second"]))
    assert sum(isinstance(result, dict) for result in results) == 1
    assert 409 in results
    assert service.get(review["id"])["revision"] == 2


def test_added_harmony_anchors_to_chord_onset_and_preserves_barline_order(setup_review):
    client, _, _ = setup_review
    review = create(client).json()
    updated = change(client, review, "harmonies", {"measure_id": "m-1", "before_event_id": "e-2", "root_step": "C", "kind": "major"}).json()
    assert updated["score"]["harmonies"][-1]["onset"] == "0"
    root = ET.fromstring(b64decode(updated["musicxml_base64"]))
    measure = root.find("./part/measure")
    assert list(measure)[-1].tag == "barline"


def test_source_mime_fallback_uses_validated_content_not_a_filename(setup_review):
    client, _, _ = setup_review
    review = create(client, source=("original.data", image(), "application/octet-stream")).json()
    assert review["source"]["media_type"] == "image/png"
