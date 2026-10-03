"""Provider-independent recognition orchestration and upload safeguards."""

from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import BoundedSemaphore
from typing import Protocol
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError
from pypdf import PdfReader

from app.core.config import Settings
from app.music.recognition.errors import RecognitionError
from app.music.recognition.profiles import InputQuality, RecognitionProfile, resolve_profile
from app.music.recognition.result import ProviderOutput, RecognitionIssue, RecognitionResult
from app.music.recognition.validation import validate_musicxml


class MusicRecognitionProvider(Protocol):
    def recognize(self, source: Path, output_directory: Path) -> bytes:
        """Return uncompressed MusicXML; failures raise RecognitionError."""


_FORMATS = {
    ".pdf": ("application/pdf", None),
    ".png": ("image/png", "PNG"),
    ".jpg": ("image/jpeg", "JPEG"),
    ".jpeg": ("image/jpeg", "JPEG"),
    ".webp": ("image/webp", "WEBP"),
}


class MusicRecognitionService:
    def __init__(self, provider: MusicRecognitionProvider, config: Settings):
        self.provider = provider
        self.config = config
        # One local heavyweight process per backend worker; fail rather than queue.
        self._slot = BoundedSemaphore(1)

    def recognize(self, contents: bytes, filename: str, mime: str | None) -> bytes:
        """Compatibility interface for callers that only need MusicXML bytes."""
        return self.recognize_result(contents, filename, mime).musicxml

    def recognize_result(
        self, contents: bytes, filename: str, mime: str | None,
        profile: RecognitionProfile | None = None, input_quality: InputQuality | None = None,
    ) -> RecognitionResult:
        options = resolve_profile(self.config, profile, input_quality)
        suffix = Path(filename).suffix.lower()
        if suffix not in _FORMATS:
            raise RecognitionError("Choose a PDF, PNG, JPEG or WEBP file.", 415)
        expected_mime, image_format = _FORMATS[suffix]
        if mime and mime.split(";", 1)[0].lower() not in (expected_mime, "application/octet-stream"):
            raise RecognitionError("The file extension and MIME type disagree.", 415)
        if not contents:
            raise RecognitionError("The uploaded file is empty.")
        if len(contents) > self.config.recognition_max_upload_bytes:
            raise RecognitionError("The uploaded file exceeds the size limit.", 413)
        if not self._slot.acquire(blocking=False):
            raise RecognitionError("Recognition is busy. Try again shortly.", 503)
        try:
            with TemporaryDirectory(prefix="music-recognition-") as directory:
                workspace = Path(directory)
                source = workspace / ("input" + suffix)
                if image_format is None:
                    self._validate_pdf(contents)
                    source.write_bytes(contents)
                else:
                    source = self._prepare_image(contents, image_format, workspace)
                output = workspace / "output"
                output.mkdir()
                try:
                    recognize_result = getattr(self.provider, "recognize_result", None)
                    if recognize_result is not None:
                        result = recognize_result(source, output, options)
                    else:
                        # Existing bytes-only providers remain usable through the old contract.
                        result = ProviderOutput(self.provider.recognize(source, output), "custom")
                except RecognitionError:
                    raise
                except Exception as error:
                    raise RecognitionError("The recognition provider failed. Try again later.", 502) from error
                if not result.musicxml or len(result.musicxml) > self.config.recognition_max_output_bytes:
                    raise RecognitionError("Recognition produced empty or oversized MusicXML.", 502, (
                        RecognitionIssue("invalid_output_size", "Recognition output was empty or exceeded the size limit.", "error"),
                    ))
                diagnostics, validation_issues = validate_musicxml(
                    result.musicxml, expect_lyrics=options.lyrics,
                    max_issues=self.config.recognition_max_diagnostics,
                )
                if result.omr is not None and len(result.omr) > self.config.recognition_max_artifact_bytes:
                    raise RecognitionError("Recognition artifact exceeds the size limit.", 502)
                diagnostics["provider_metadata"] = result.metadata
                diagnostics["artifact_retained"] = result.omr is not None
                return RecognitionResult(
                    result.musicxml, result.provider, options.profile,
                    result.warnings + validation_issues, diagnostics, omr=result.omr,
                )
        except OSError as error:
            raise RecognitionError("Recognition temporary storage is unavailable.", 503) from error
        finally:
            self._slot.release()

    def _validate_pdf(self, contents: bytes) -> None:
        if not contents.startswith(b"%PDF-"):
            raise RecognitionError("The uploaded file is not a PDF.")
        try:
            reader = PdfReader(BytesIO(contents), strict=True)
            if reader.is_encrypted:
                raise RecognitionError("Encrypted PDFs are not supported.")
            count = len(reader.pages)
        except RecognitionError:
            raise
        except Exception as error:
            raise RecognitionError("The PDF is damaged or cannot be read.") from error
        if count == 0 or count > self.config.recognition_max_pages:
            raise RecognitionError(
                f"PDFs must contain 1–{self.config.recognition_max_pages} pages."
            )

    def _prepare_image(self, contents: bytes, expected_format: str, workspace: Path) -> Path:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(BytesIO(contents)) as image:
                    if image.format != expected_format:
                        raise RecognitionError("The image content does not match its extension.", 415)
                    if image.width * image.height > self.config.recognition_max_image_pixels:
                        raise RecognitionError("The image exceeds the pixel limit.", 413)
                    if getattr(image, "n_frames", 1) != 1:
                        raise RecognitionError("Animated or multi-frame images are not supported.")
                    image.verify()
                # Normalize supported image formats to PNG for provider portability.
                with Image.open(BytesIO(contents)) as image:
                    rgba = ImageOps.exif_transpose(image).convert("RGBA")
                    background = Image.new("RGBA", rgba.size, "white")
                    background.alpha_composite(rgba)
                    source = workspace / "input.png"
                    background.convert("RGB").save(source)
                    return source
        except RecognitionError:
            raise
        except (Image.DecompressionBombWarning, Image.DecompressionBombError) as error:
            raise RecognitionError("The image exceeds safe decoding limits.", 413) from error
        except (UnidentifiedImageError, OSError, ValueError) as error:
            raise RecognitionError("The image is damaged or cannot be read.") from error
