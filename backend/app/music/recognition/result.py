"""Bounded recognition results, without client-visible server paths."""

from base64 import b64encode
from dataclasses import asdict, dataclass, field
from hashlib import sha256
from typing import Literal

from app.music.recognition.profiles import RecognitionProfile


@dataclass(frozen=True)
class RecognitionIssue:
    code: str
    message: str
    severity: Literal["info", "warning", "error"] = "warning"
    part_id: str | None = None
    measure: str | None = None
    details: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderOutput:
    musicxml: bytes | None
    provider: str
    omr: bytes | None = None
    warnings: tuple[RecognitionIssue, ...] = ()
    metadata: dict = field(default_factory=dict)
    symbolic: dict | None = None
    debug_artifacts: dict[str, bytes] = field(default_factory=dict)
    evidence_omr: bytes | None = None


@dataclass(frozen=True)
class RecognitionResult:
    musicxml: bytes
    provider: str
    profile: RecognitionProfile
    warnings: tuple[RecognitionIssue, ...]
    diagnostics: dict
    # Structural checks cannot establish OMR accuracy against the source image.
    review_required: bool = True
    omr: bytes | None = None
    # Local benchmark only; omitted from HTTP payloads.
    debug_artifacts: dict[str, bytes] = field(default_factory=dict)
    evidence_omr: bytes | None = None
    baseline_musicxml: bytes | None = None

    def metadata(self) -> dict:
        return {
            "provider": self.provider, "profile": self.profile.value,
            "review_required": self.review_required,
            "warnings": [asdict(issue) for issue in self.warnings],
            "diagnostics": self.diagnostics,
        }

    def response_payload(self) -> dict:
        artifact = None
        if self.omr is not None:
            artifact = {
                "filename": "recognized.omr", "media_type": "application/octet-stream",
                "size_bytes": len(self.omr), "sha256": sha256(self.omr).hexdigest(),
                "data_base64": b64encode(self.omr).decode("ascii"),
            }
        return {
            **self.metadata(),
            "musicxml_base64": b64encode(self.musicxml).decode("ascii"),
            "baseline_musicxml_base64": b64encode(self.baseline_musicxml).decode("ascii") if self.baseline_musicxml is not None else None,
            "omr_artifact": artifact,
            "semantic_evidence_artifact": {
                "filename": "semantic-evidence.omr", "media_type": "application/octet-stream",
                "size_bytes": len(self.evidence_omr), "sha256": sha256(self.evidence_omr).hexdigest(),
                "data_base64": b64encode(self.evidence_omr).decode("ascii"),
            } if self.evidence_omr is not None else None,
        }


@dataclass(frozen=True)
class SymbolicRecognitionResult:
    """Native symbolic evidence; deliberately has no fabricated MusicXML."""

    provider: str
    profile: RecognitionProfile
    symbolic: dict
    warnings: tuple[RecognitionIssue, ...]
    diagnostics: dict
    debug_artifacts: dict[str, bytes] = field(default_factory=dict)
