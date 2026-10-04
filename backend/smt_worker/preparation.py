"""Deterministic rendering and conservative five-line staff system proposals."""

from io import BytesIO
import math
from pathlib import Path
from statistics import median

from PIL import Image, ImageOps


class PreparationError(ValueError):
    pass


class ArtifactStore:
    def __init__(self, root: Path, limit: int):
        self.root, self.limit, self.used = root, limit, 0

    def image(self, name: str, image: Image.Image) -> None:
        stream = BytesIO()
        image.save(stream, format="PNG")
        contents = stream.getvalue()
        if self.used + len(contents) > self.limit:
            raise PreparationError("artifact_limit")
        target = self.root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(contents)
        self.used += len(contents)


def normalize_image(image: Image.Image, max_pixels: int) -> Image.Image:
    if image.width * image.height > max_pixels or getattr(image, "n_frames", 1) != 1:
        raise PreparationError("image_limit")
    oriented = ImageOps.exif_transpose(image).convert("RGBA")
    background = Image.new("RGBA", oriented.size, "white")
    background.alpha_composite(oriented)
    return background.convert("RGB")


def render_pdf(source: Path, dpi: int, max_pages: int, max_pixels: int):
    # PDFium lives only in the worker environment, never in backend/.venv.
    import pypdfium2 as pdfium

    document = pdfium.PdfDocument(source)
    try:
        if not 0 < len(document) <= max_pages:
            raise PreparationError("page_limit")
        for index in range(len(document)):
            page = document[index]
            try:
                points = page.get_size()
                scale = dpi / 72
                if math.ceil(points[0] * scale) * math.ceil(points[1] * scale) > max_pixels:
                    raise PreparationError("image_limit")
                bitmap = page.render(scale=scale, rotation=0)
                try:
                    image = normalize_image(bitmap.to_pil(), max_pixels)
                finally:
                    bitmap.close()
                yield image, {"source_dimensions_points": list(points), "dpi": dpi}
            finally:
                page.close()
    finally:
        document.close()


def staff_systems(image: Image.Image, staves_per_system: int) -> list[list[int]]:
    """Propose horizontal systems; skewed, broken or short staves can be missed.

    Binary pixels are used for detection only. Crops retain original RGB pixels.
    The explicit staff grouping is a benchmark assumption, not inferred truth.
    """
    width, height = image.size
    ink = image.convert("L").point(lambda value: 255 if value < 180 else 0)
    rows = [y for y in range(height)
            if ink.crop((0, y, width, y + 1)).histogram()[255] >= width * 0.45]
    centers = []
    run = []
    for row in rows:
        if run and row > run[-1] + 1:
            centers.append(sum(run) / len(run))
            run = []
        run.append(row)
    if run:
        centers.append(sum(run) / len(run))
    staves = []
    index = 0
    while index + 4 < len(centers):
        lines = centers[index:index + 5]
        gaps = [b - a for a, b in zip(lines, lines[1:])]
        spacing = median(gaps)
        if spacing >= 2 and all(abs(gap - spacing) <= spacing * 0.25 for gap in gaps):
            staves.append((lines[0], lines[-1], spacing))
            index += 5
        else:
            index += 1
    # Reject incomplete groups rather than guessing their staff assignment.
    if len(staves) % staves_per_system:
        raise PreparationError("incomplete_staff_group")
    groups = [staves[i:i + staves_per_system]
              for i in range(0, len(staves), staves_per_system)]
    boxes = []
    for index, group in enumerate(groups):
        spacing = median(staff[2] for staff in group)
        top = max(0, int(group[0][0] - spacing * 5))
        bottom = min(height, math.ceil(group[-1][1] + spacing * 6))
        if index:
            top = max(top, math.ceil((groups[index - 1][-1][1] + group[0][0]) / 2))
        if index + 1 < len(groups):
            bottom = min(bottom, int((group[-1][1] + groups[index + 1][0][0]) / 2))
        bounds = ink.crop((0, top, width, bottom)).getbbox()
        if bounds is not None:
            boxes.append([max(0, int(bounds[0] - spacing * 2)), top,
                          min(width, math.ceil(bounds[2] + spacing * 2)), bottom])
    return boxes


def validate_boxes(boxes: list, pages: list[dict], max_systems: int) -> list[dict]:
    if not isinstance(boxes, list) or not 0 < len(boxes) <= max_systems:
        raise PreparationError("invalid_system_boxes")
    sizes = {page["page"]: page["dimensions"] for page in pages}
    checked = []
    for item in boxes:
        if not isinstance(item, dict) or set(item) != {"page", "bbox"}:
            raise PreparationError("invalid_system_boxes")
        page, box = item["page"], item["bbox"]
        if type(page) is not int or page not in sizes or not isinstance(box, list) or len(box) != 4:
            raise PreparationError("invalid_system_boxes")
        if any(type(value) is not int for value in box):
            raise PreparationError("invalid_system_boxes")
        width, height = sizes[page]
        if not (0 <= box[0] < box[2] <= width and 0 <= box[1] < box[3] <= height):
            raise PreparationError("invalid_system_boxes")
        if item in checked:
            raise PreparationError("duplicate_system_box")
        checked.append(item)
    return sorted(checked, key=lambda item: (item["page"], item["bbox"][1], item["bbox"][0]))


def prepare(source: Path, request: dict, output: Path, result: dict) -> None:
    store = ArtifactStore(output, request["max_artifact_bytes"])
    if source.suffix.lower() == ".pdf":
        images = render_pdf(source, request["dpi"], request["max_pages"], request["max_pixels"])
    else:
        with Image.open(source) as original:
            metadata = {"original_dimensions": list(original.size),
                        "exif_orientation": original.getexif().get(274, 1), "dpi": None}
            normalized = normalize_image(original, request["max_pixels"])
        images = iter([(normalized, metadata)])
    proposals = []
    for page_number, (image, metadata) in enumerate(images, 1):
        try:
            name = f"pages/page-{page_number:04d}.png"
            store.image(name, image)
            result["pages"].append({"page": page_number, "image": name,
                                    "dimensions": list(image.size), **metadata})
            if request["boxes"] is None:
                try:
                    boxes = staff_systems(image, request["staves_per_system"])
                except PreparationError as error:
                    result["warnings"].append(str(error))
                    boxes = []
                proposals.extend({"page": page_number, "bbox": box} for box in boxes)
        finally:
            image.close()
    boxes = request["boxes"] if request["boxes"] is not None else proposals
    if not boxes:
        raise PreparationError("no_staff_systems")
    ordered = validate_boxes(boxes, result["pages"], request["max_systems"])
    for index, item in enumerate(ordered, 1):
        page_name = result["pages"][item["page"] - 1]["image"]
        with Image.open(output / page_name) as page:
            crop = page.crop(item["bbox"])
            try:
                name = f"systems/system-{index:04d}.png"
                store.image(name, crop)
            finally:
                crop.close()
        result["systems"].append({"index": index, **item, "image": name,
                                  "segmentation": "manual" if request["boxes"] is not None else "heuristic",
                                  "success": False, "raw_tokens": [], "raw_transcription": "",
                                  "duration_seconds": 0.0})
    result["warnings"].append("segmentation_requires_visual_review")
