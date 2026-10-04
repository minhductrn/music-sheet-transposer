"""Provider evidence and explicit decisions, separate from musical truth."""

from dataclasses import dataclass, field
from typing import Literal


Confidence = Literal["EXACT", "HIGH", "AMBIGUOUS", "UNMATCHED"]


@dataclass(frozen=True)
class Relationship:
    source: str
    target: str
    kind: str
    grade: float | None = None


@dataclass(frozen=True)
class CandidateNoteEvidence:
    id: str
    sheet: int
    system: str
    part: str | None
    measure: str | None
    staff: str | None
    staff_number: int | None
    bounds: tuple[float, float, float, float] | None
    center: tuple[float, float] | None
    staff_position: int | None
    step: str | None
    octave: int | None
    alter: str | None
    pitch_supported: bool
    shape: str
    visual_size: str
    chords: tuple[str, ...]
    chord_kind: str | None
    stems: tuple[str, ...]
    beams: tuple[str, ...]
    voice: str | None
    onset: str | None  # Exact quarter beats, converted from OMR whole-note rationals.
    grade: float | None
    relationships: tuple[Relationship, ...]
    provenance: str  # Archive hash/member/ID; never book.xml's private source path.


@dataclass(frozen=True)
class EvidenceMeasure:
    id: str
    part: str | None
    left: float | None
    right: float | None
    candidates: tuple[CandidateNoteEvidence, ...]
    physical_part: str | None = None
    staffs: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvidenceSystem:
    id: str
    measures: tuple[EvidenceMeasure, ...]


@dataclass(frozen=True)
class EvidenceSheet:
    number: int
    width: int | None
    height: int | None
    interline: float | None
    systems: tuple[EvidenceSystem, ...]
    binary_sha256: str | None = None


@dataclass(frozen=True)
class AudiverisEvidence:
    sha256: str
    version: str | None
    logical_parts: tuple[str, ...]
    sheets: tuple[EvidenceSheet, ...]
    diagnostics: tuple[str, ...]

    def notes(self):
        return (note for sheet in self.sheets for system in sheet.systems
                for measure in system.measures for note in measure.candidates)


@dataclass(frozen=True)
class Correlation:
    evidence_id: str
    confidence: Confidence
    event_ids: tuple[str, ...]
    measure_id: str | None
    reasons: tuple[str, ...]


@dataclass
class RecoveryCandidate:
    id: str
    operation: str | None
    classification: Literal["GRACE", "CUE", "SIMULTANEOUS_VARIANT", "UNCERTAIN"]
    confidence: Confidence
    state: Literal["AUTO_RECOVERED", "REVIEW_REQUIRED", "NO_RECOVERY"]
    measure_id: str | None
    event_id: str | None
    anchor_id: str | None
    pitch: dict | None
    evidence: CandidateNoteEvidence
    correlation: Correlation
    diagnostics: list[str] = field(default_factory=list)
