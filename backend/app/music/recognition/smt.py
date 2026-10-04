"""SMT is EXPERIMENTAL / BENCHMARK ONLY; heavy dependencies stay outside FastAPI."""

import json
import os
from pathlib import Path
import re
import signal
import subprocess
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from PIL import Image
from io import BytesIO

from app.core.config import Settings
from app.music.recognition.errors import RecognitionError
from app.music.recognition.profiles import ProfileOptions
from app.music.recognition.result import ProviderOutput, RecognitionIssue
from app.music.recognition.symbolic import parse_symbolic


_Positive = Annotated[int, Field(strict=True, gt=0)]
_Coordinate = Annotated[int, Field(strict=True, ge=0)]
_Code = Annotated[str, Field(pattern=r"^[a-z_]+$", max_length=100)]


class _Record(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class _Page(_Record):
    page: _Positive
    image: str
    dimensions: Annotated[list[_Positive], Field(min_length=2, max_length=2)]
    dpi: int | None
    original_dimensions: Annotated[list[_Positive], Field(min_length=2, max_length=2)] | None = None
    source_dimensions_points: Annotated[list[float], Field(min_length=2, max_length=2)] | None = None
    exif_orientation: int | None = None


class _System(_Record):
    index: _Positive
    page: _Positive
    bbox: Annotated[list[_Coordinate], Field(min_length=4, max_length=4)]
    image: str
    segmentation: Literal["manual", "heuristic"]
    success: bool
    raw_tokens: Annotated[list[str], Field(max_length=20_000)]
    raw_transcription: str
    duration_seconds: Annotated[float, Field(ge=0)]
    inference_dimensions: Annotated[list[_Positive], Field(min_length=2, max_length=2)] | None = None
    resize_scale: Annotated[float, Field(gt=0, le=1)] | None = None
    at_token_limit: bool | None = None
    error: _Code | None = None


class _WorkerResult(_Record):
    version: Literal[1]
    success: bool
    model_reference: str
    model_revision: str
    device: Literal["cpu", "cuda"] | None
    pages: list[_Page]
    systems: list[_System]
    warnings: Annotated[list[_Code], Field(max_length=128)]
    error: _Code | None


class SMTProvider:
    def __init__(self, config: Settings, *, boxes: list[dict] | None = None, prepare_only: bool = False):
        self.config, self.boxes, self.prepare_only = config, boxes, prepare_only

    def recognize_result(self, source: Path, output_directory: Path, options: ProfileOptions) -> ProviderOutput:
        config = self.config
        # Gate inference and prepare-only jobs before any worker setup or launch.
        if not config.smt_enabled:
            raise RecognitionError("SMT is disabled (EXPERIMENTAL / BENCHMARK ONLY). "
                                   "Set SMT_ENABLED=true explicitly for development or benchmarks.", 503, (
                RecognitionIssue("smt_disabled", "SMT_ENABLED defaults to false; provider selection does not enable SMT.", "error"),
            ))
        if config.smt_worker_python is None or (config.smt_upstream_path is None and not self.prepare_only):
            raise RecognitionError("SMT is not configured. Follow backend/SMT.md to install the isolated worker.", 503, (
                RecognitionIssue("smt_unconfigured", "An isolated worker interpreter and official source checkout are required.", "error"),
            ))
        request = {
            "source": str(source.resolve()),
            "upstream_path": str(config.smt_upstream_path.resolve()) if config.smt_upstream_path else None,
            "model_reference": config.smt_model_reference, "model_revision": config.smt_model_revision,
            "device": config.smt_device, "dpi": config.smt_pdf_dpi,
            "cpu_threads": config.smt_cpu_threads, "staves_per_system": config.smt_staves_per_system,
            "max_pages": config.recognition_max_pages, "max_pixels": config.recognition_max_image_pixels,
            "max_systems": config.smt_max_systems, "max_artifact_bytes": config.recognition_max_artifact_bytes,
            "max_output_bytes": config.recognition_max_output_bytes,
            "boxes": self.boxes, "prepare_only": self.prepare_only,
        }
        request_path = output_directory / "request.json"
        request_path.write_text(json.dumps(request, allow_nan=False), encoding="utf-8")
        worker = Path(__file__).resolve().parents[3] / "smt_worker/worker.py"
        command = [str(config.smt_worker_python), "-I", str(worker), str(request_path)]
        environment = {key: value for key, value in os.environ.items() if key not in {"PYTHONPATH", "PYTHONHOME"}}
        environment.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", TOKENIZERS_PARALLELISM="false")
        failure = None
        try:
            process = subprocess.Popen(
                command, cwd=output_directory, env=environment, stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True,
            )
        except OSError as error:
            raise RecognitionError("The isolated SMT worker could not be started.", 503) from error
        try:
            code = process.wait(timeout=config.smt_timeout_seconds)
            if code != 0:
                failure = "worker_failed"
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
            failure = "worker_timeout"
        native = self._read_result(output_directory, failure)
        issues = [RecognitionIssue(code, code.replace("_", " ").capitalize() + ".")
                  for code in native["warnings"]]
        if native["error"]:
            issues.append(RecognitionIssue(native["error"], "SMT did not complete all requested inference.", "error"))
        native["parsing_summary"] = self._parse_systems(native["systems"])
        if native["success"] and native["parsing_summary"]["coverage"] < 1:
            issues.append(RecognitionIssue("partial_symbolic_parse", "Some symbolic tokens are unsupported; inspect raw output."))
        if any(system.get("at_token_limit") for system in native["systems"]):
            issues.append(RecognitionIssue("token_limit_reached", "A system reached the checkpoint token limit; output may be incomplete."))
        artifacts = self._artifacts(output_directory)
        for record in native["pages"] + native["systems"]:
            name = record["image"]
            try:
                with Image.open(BytesIO(artifacts[name])) as image:
                    dimensions = record.get("dimensions")
                    if dimensions is None:
                        x1, y1, x2, y2 = record["bbox"]
                        dimensions = [x2 - x1, y2 - y1]
                    if image.format != "PNG" or list(image.size) != dimensions:
                        raise ValueError("invalid image")
                    image.verify()
            except (KeyError, OSError, ValueError) as error:
                raise RecognitionError("SMT debug images failed validation.", 502) from error
        return ProviderOutput(
            None, "SMT", warnings=tuple(issues), symbolic=native,
            metadata={"model_reference": config.smt_model_reference, "model_revision": config.smt_model_revision,
                      "device": native["device"], "cpu_threads": config.smt_cpu_threads,
                      "pdf_dpi": config.smt_pdf_dpi, "staves_per_system": config.smt_staves_per_system,
                      "musicxml_conversion": False, "ocr": False},
            debug_artifacts=artifacts,
        )

    def _read_result(self, output: Path, failure: str | None) -> dict:
        path = output / "result.json"
        if not path.exists():
            code = failure or "invalid_worker_output"
            raise RecognitionError("SMT produced no readable benchmark result.", 504 if code == "worker_timeout" else 502, (
                RecognitionIssue(code, "No partial result was available.", "error"),
            ))
        try:
            if path.is_symlink() or not path.is_file() or path.stat().st_size > self.config.recognition_max_output_bytes:
                raise ValueError("unsafe result")
            document = _WorkerResult.model_validate_json(path.read_bytes())
            if document.model_reference != self.config.smt_model_reference or document.model_revision != self.config.smt_model_revision:
                raise ValueError("model mismatch")
            if len(document.pages) > self.config.recognition_max_pages or len(document.systems) > self.config.smt_max_systems:
                raise ValueError("too many records")
            for number, page in enumerate(document.pages, 1):
                if page.page != number or page.image != f"pages/page-{number:04d}.png":
                    raise ValueError("invalid page")
                if page.dimensions[0] * page.dimensions[1] > self.config.recognition_max_image_pixels:
                    raise ValueError("oversized page")
            previous = None
            for number, system in enumerate(document.systems, 1):
                if not 1 <= system.page <= len(document.pages) or system.index != number:
                    raise ValueError("invalid system")
                width, height = document.pages[system.page - 1].dimensions
                x1, y1, x2, y2 = system.bbox
                if not (x1 < x2 <= width and y1 < y2 <= height):
                    raise ValueError("invalid box")
                order = (system.page, y1, x1)
                if previous is not None and order < previous:
                    raise ValueError("unordered systems")
                previous = order
                if system.image != f"systems/system-{number:04d}.png" or system.raw_transcription != "".join(system.raw_tokens):
                    raise ValueError("invalid transcription")
                if system.success and not system.raw_tokens:
                    raise ValueError("empty prediction")
            if document.success and (not document.systems or not all(s.success for s in document.systems) or document.error):
                raise ValueError("inconsistent success")
            native = document.model_dump(exclude_none=True)
            # Keep nullable fields stable for callers even on setup failures.
            native.update(device=document.device, error=document.error)
        except (OSError, ValueError, ValidationError) as error:
            raise RecognitionError("SMT returned malformed or unsafe benchmark output.", 502, (
                RecognitionIssue("invalid_worker_output", "The isolated worker result failed validation.", "error"),
            )) from error
        if failure:
            native.update(success=False, error="worker_timeout" if failure == "worker_timeout" else native["error"] or failure)
        return native

    @staticmethod
    def _parse_systems(systems: list[dict]) -> dict:
        totals = {key: 0 for key in ("notes", "rests", "grace_notes", "chord_groups", "simultaneous_events", "barline_rows")}
        parsed_cells = total_cells = 0
        for system in systems:
            # Raw output survives regardless of parsing coverage or inference status.
            parsed = parse_symbolic(system["raw_transcription"])
            system["parsed"] = parsed
            for key in totals:
                totals[key] += parsed["metrics"][key]
            parsed_cells += parsed["parsing"]["parsed_cells"]
            total_cells += parsed["parsing"]["total_cells"]
        return {"metrics": totals, "parsed_cells": parsed_cells, "total_cells": total_cells,
                "coverage": parsed_cells / total_cells if total_cells else 0.0,
                "scope": "Partial per-system token counts. System-edge barlines can repeat; no accuracy score."}

    def _artifacts(self, output: Path) -> dict[str, bytes]:
        artifacts = {}
        used = 0
        for folder in ("pages", "systems"):
            directory = output / folder
            if directory.is_symlink():
                raise RecognitionError("SMT returned unsafe debug artifacts.", 502)
            if not directory.exists():
                continue
            files = sorted(directory.iterdir())
            if len(files) > max(self.config.recognition_max_pages, self.config.smt_max_systems):
                raise RecognitionError("SMT returned too many debug artifacts.", 502)
            for path in files:
                if path.is_symlink() or not path.is_file() or not re.fullmatch(r"(?:page|system)-\d{4}\.png", path.name):
                    raise RecognitionError("SMT returned unsafe debug artifacts.", 502)
                used += path.stat().st_size
                if used > self.config.recognition_max_artifact_bytes:
                    raise RecognitionError("SMT debug artifacts exceed the size limit.", 502)
                artifacts[f"{folder}/{path.name}"] = path.read_bytes()
        return artifacts
