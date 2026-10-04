"""Validate and retain the original source without running OMR again."""

from io import BytesIO
import warnings

from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader

from app.core.config import Settings
from app.music.review.document import ReviewError
from app.music.review.storage import Source


def prepare_source(contents: bytes, mime: str, config: Settings) -> Source:
    if not contents or len(contents) > config.recognition_max_upload_bytes:
        raise ReviewError("The source is empty or exceeds the upload size limit.", 413)
    if mime in ("", "application/octet-stream"):
        # Browsers sometimes omit the source MIME; decode the detected format below.
        mime = ("application/pdf" if contents.startswith(b"%PDF-") else
                "image/png" if contents.startswith(b"\x89PNG\r\n\x1a\n") else
                "image/jpeg" if contents.startswith(b"\xff\xd8") else
                "image/webp" if contents.startswith(b"RIFF") and contents[8:12] == b"WEBP" else "")
    try:
        if mime == "application/pdf":
            if not contents.startswith(b"%PDF-"):
                raise ReviewError("The source is not a PDF.")
            reader = PdfReader(BytesIO(contents), strict=True)
            if reader.is_encrypted or not 1 <= len(reader.pages) <= config.recognition_max_pages:
                raise ReviewError("The PDF is encrypted or exceeds the page limit.")
            return Source(contents, mime, len(reader.pages))
        formats = {"image/png": "PNG", "image/jpeg": "JPEG", "image/webp": "WEBP"}
        if mime not in formats:
            raise ReviewError("Review sources must be PDF, PNG, JPEG or WEBP.", 415)
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(contents)) as image:
                if image.format != formats[mime] or getattr(image, "n_frames", 1) != 1:
                    raise ReviewError("The source format is inconsistent or animated.")
                if image.width * image.height > config.recognition_max_image_pixels:
                    raise ReviewError("The source exceeds the image pixel limit.", 413)
                image.verify()
        return Source(contents, mime, 1)
    except ReviewError:
        raise
    except (Image.DecompressionBombWarning, Image.DecompressionBombError):
        raise ReviewError("The source exceeds safe image decoding limits.", 413) from None
    except (UnidentifiedImageError, OSError, ValueError):
        raise ReviewError("The source is damaged or cannot be read.") from None
    except Exception:
        raise ReviewError("The original source is damaged or cannot be read.") from None
