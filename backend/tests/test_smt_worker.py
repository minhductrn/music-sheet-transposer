import json
import sys
from types import SimpleNamespace

from PIL import Image, ImageDraw
import pytest

from smt_worker.inference import load_model, select_device
from smt_worker.preparation import (
    ArtifactStore, PreparationError, normalize_image, prepare, render_pdf,
    staff_systems, validate_boxes,
)
from smt_worker.worker import run


def staff_image():
    image = Image.new("RGB", (600, 500), "white")
    draw = ImageDraw.Draw(image)
    for top in (100, 300):
        for line in range(5):
            draw.line((40, top + line * 10, 560, top + line * 10), fill="black", width=2)
    # Pixel-sized details must survive cropping; detection does not binarize output.
    draw.ellipse((180, 115, 186, 121), fill=(80, 80, 80))
    return image


def request(source, **overrides):
    return {"source": str(source), "model_reference": "antoniorv6/smt-grandstaff",
            "model_revision": "pinned", "upstream_path": None, "device": "auto",
            "cpu_threads": 2, "dpi": 200, "staves_per_system": 1, "max_pages": 10,
            "max_pixels": 40_000_000, "max_systems": 64,
            "max_artifact_bytes": 1_000_000, "max_output_bytes": 1_000_000,
            "boxes": None, "prepare_only": False, **overrides}


@pytest.mark.parametrize(("requested", "available", "expected"), [
    ("auto", False, "cpu"), ("auto", True, "cuda"), ("cpu", True, "cpu"), ("cuda", True, "cuda"),
])
def test_device_selection_without_gpu(requested, available, expected):
    assert select_device(requested, available) == expected


@pytest.mark.parametrize(("requested", "available"), [("cuda", False), ("gpu", True)])
def test_unavailable_or_invalid_device_is_explicit(requested, available):
    with pytest.raises(ValueError):
        select_device(requested, available)


def test_image_normalization_preserves_orientation_color_and_alpha():
    image = Image.new("RGBA", (20, 10), (255, 0, 0, 0))
    image.putpixel((0, 0), (0, 0, 0, 255))
    image.getexif()[274] = 6
    normalized = normalize_image(image, 1000)
    assert normalized.size == (10, 20)
    assert normalized.mode == "RGB"
    assert normalized.getpixel((9, 0)) == (0, 0, 0)
    assert normalized.getpixel((0, 0)) == (255, 255, 255)


def test_image_pixel_limit():
    with pytest.raises(PreparationError, match="image_limit"):
        normalize_image(Image.new("RGB", (20, 20)), 399)


def test_systems_are_ordered_and_preserve_pixel_details(tmp_path):
    source = tmp_path / "input.png"
    original = staff_image()
    original.save(source)
    result = {"pages": [], "systems": [], "warnings": []}
    prepare(source, request(source), tmp_path, result)
    assert len(result["systems"]) == 2
    assert result["systems"][0]["bbox"][1] < result["systems"][1]["bbox"][1]
    first = result["systems"][0]
    with Image.open(tmp_path / first["image"]) as crop:
        assert crop.getpixel((183 - first["bbox"][0], 118 - first["bbox"][1])) == (80, 80, 80)
    assert result["pages"][0]["original_dimensions"] == [600, 500]
    assert "segmentation_requires_visual_review" in result["warnings"]


def test_staff_grouping_is_explicit():
    image = staff_image()
    assert len(staff_systems(image, 1)) == 2
    assert len(staff_systems(image, 2)) == 1
    with pytest.raises(PreparationError, match="incomplete_staff_group"):
        staff_systems(image.crop((0, 0, 600, 230)), 2)


def test_blank_image_never_fabricates_whole_page_system(tmp_path):
    source = tmp_path / "input.png"
    Image.new("RGB", (100, 100), "white").save(source)
    assert run(request(source, prepare_only=True), tmp_path) == 1
    result = json.loads((tmp_path / "result.json").read_text())
    assert result["error"] == "no_staff_systems"
    assert result["systems"] == []
    assert (tmp_path / "pages/page-0001.png").exists()


def test_manual_boxes_sort_page_then_vertical_position():
    pages = [{"page": 1, "dimensions": [600, 500]}, {"page": 2, "dimensions": [600, 500]}]
    boxes = [{"page": 2, "bbox": [0, 10, 500, 100]}, {"page": 1, "bbox": [0, 300, 500, 400]},
             {"page": 1, "bbox": [0, 100, 500, 200]}]
    assert validate_boxes(boxes, pages, 10) == [boxes[2], boxes[1], boxes[0]]


@pytest.mark.parametrize("boxes", [[], {}, [{"page": 2, "bbox": [0, 0, 10, 10]}],
    [{"page": True, "bbox": [0, 0, 10, 10]}], [{"page": 1, "bbox": [-1, 0, 10, 10]}],
    [{"page": 1, "bbox": [0, 0, 601, 10]}], [{"page": 1, "bbox": [10, 0, 10, 10]}],
    [{"page": 1, "bbox": [0.0, 0, 10, 10]}], [{"page": 1, "bbox": [0, 0, 10]}],
    [{"page": 1, "bbox": [0, 0, 10, 10], "path": "/private"}],
    [{"page": 1, "bbox": [0, 0, 10, 10]}] * 2,
])
def test_bad_boxes_are_rejected(boxes):
    with pytest.raises(PreparationError):
        validate_boxes(boxes, [{"page": 1, "dimensions": [600, 500]}], 10)


def test_debug_storage_is_bounded(tmp_path):
    with pytest.raises(PreparationError, match="artifact_limit"):
        ArtifactStore(tmp_path, 1).image("pages/page-0001.png", staff_image())
    assert not (tmp_path / "pages").exists()


def test_pdf_rendering_uses_dpi_and_closes_resources(monkeypatch, tmp_path):
    calls = []
    class Bitmap:
        def to_pil(self):
            return Image.new("RGB", (200, 400), "white")
        def close(self):
            calls.append("bitmap_closed")
    class Page:
        def close(self):
            calls.append("page_closed")
        def get_size(self):
            return (72.0, 144.0)
        def render(self, **kwargs):
            calls.append(kwargs)
            return Bitmap()
    class Document:
        def close(self):
            calls.append("document_closed")
        def __len__(self):
            return 2
        def __getitem__(self, index):
            return Page()
    monkeypatch.setitem(sys.modules, "pypdfium2", SimpleNamespace(PdfDocument=lambda source: Document()))
    pages = list(render_pdf(tmp_path / "input.pdf", 200, 10, 100_000))
    assert len(pages) == 2
    assert pages[0][0].size == (200, 400)
    assert pages[0][1] == {"source_dimensions_points": [72.0, 144.0], "dpi": 200}
    assert calls.count({"scale": 200 / 72, "rotation": 0}) == 2
    assert calls.count("bitmap_closed") == 2
    assert calls.count("page_closed") == 2
    assert calls.count("document_closed") == 1
    with pytest.raises(PreparationError, match="page_limit"):
        list(render_pdf(tmp_path / "input.pdf", 200, 1, 100_000))
    with pytest.raises(PreparationError, match="image_limit"):
        list(render_pdf(tmp_path / "input.pdf", 600, 10, 100))


def test_prepare_only_never_loads_weights(tmp_path):
    source = tmp_path / "input.png"
    staff_image().save(source)
    def unexpected_loader(_):
        raise AssertionError("Model download/load attempted")
    assert run(request(source, prepare_only=True), tmp_path, loader=unexpected_loader) == 0
    result = json.loads((tmp_path / "result.json").read_text())
    assert result["success"] is False
    assert "inference_not_run" in result["warnings"]
    assert len(result["systems"]) == 2


def test_model_failure_keeps_preprocessing_evidence(tmp_path):
    source = tmp_path / "input.png"
    staff_image().save(source)
    def broken_loader(_):
        raise RuntimeError("/private/cache/model")
    assert run(request(source), tmp_path, loader=broken_loader) == 1
    text = (tmp_path / "result.json").read_text()
    assert "/private" not in text
    result = json.loads(text)
    assert result["error"] == "model_load_failed"
    assert len(result["systems"]) == 2


def test_partial_inference_retains_first_raw_result(tmp_path):
    source = tmp_path / "input.png"
    staff_image().save(source)
    count = 0
    def prediction(*_):
        nonlocal count
        count += 1
        if count == 2:
            raise RuntimeError("bad second system")
        return ["**ekern_1.0", "<b>", "4a", "<s>", "4cc"], {"inference_dimensions": [500, 150]}
    assert run(request(source), tmp_path, loader=lambda _: (object(), "cpu"), predictor=prediction) == 1
    result = json.loads((tmp_path / "result.json").read_text())
    assert result["systems"][0]["raw_transcription"] == "**ekern_1.0<b>4a<s>4cc"
    assert result["systems"][0]["success"] is True
    assert result["systems"][1]["error"] == "inference_failed"
    assert result["device"] == "cpu"


@pytest.mark.parametrize("mismatch", [False, True])
def test_official_loader_is_offline_and_rejects_incomplete_weights(monkeypatch, tmp_path, mismatch):
    (tmp_path / "smt_model").mkdir()
    (tmp_path / "smt_model/modeling_smt.py").touch()
    recorded = {}
    class Model:
        @classmethod
        def from_pretrained(cls, reference, **kwargs):
            recorded.update(reference=reference, **kwargs)
            return cls(), {"missing_keys": ["decoder"] if mismatch else []}
        def eval(self):
            return self
        def to(self, device):
            recorded["device"] = device
            return self
    monkeypatch.setattr(sys, "path", sys.path.copy())
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False),
                         set_num_threads=lambda _: None, manual_seed=lambda _: None))
    monkeypatch.setitem(sys.modules, "smt_model", SimpleNamespace(SMTModelForCausalLM=Model))
    config = request(tmp_path / "source.png", upstream_path=str(tmp_path))
    if mismatch:
        with pytest.raises(ValueError, match="checkpoint_mismatch"):
            load_model(config)
    else:
        _, device = load_model(config)
        assert device == "cpu"
    assert recorded["local_files_only"] is True
    assert recorded["use_safetensors"] is True
    assert recorded["revision"] == "pinned"
