"""Review values use exact rational quarter beats; XML remains authoritative."""

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, model_validator


@dataclass
class Diagnostic:
    code: str
    message: str
    severity: Literal["ERROR", "WARNING", "INFO"]
    measure_id: str | None = None
    event_id: str | None = None


@dataclass
class Pitch:
    step: str | None
    alter: str
    octave: int | None


@dataclass
class Event:
    id: str
    kind: str
    pitch: Pitch | None
    onset: str | None
    duration: str | None
    duration_units: str | None
    divisions: str | None
    voice: str
    staff: int | None
    chord_id: str | None
    chord_member: bool
    grace: bool
    display_size: str
    ties: list[str]
    lyric_ids: list[str]
    key_signature: list[dict] = field(default_factory=list)
    measure_id: str | None = None
    clef: dict | None = None
    accidental: dict = field(default_factory=dict)
    notated_duration: dict = field(default_factory=dict)
    cue: bool = False


@dataclass
class Voice:
    id: str
    events: list[Event] = field(default_factory=list)


@dataclass
class Measure:
    id: str
    number: str
    index: int
    divisions: str | None
    time_signature: list[dict]
    key_signature: list[dict]
    staves: int
    expected_duration: str | None
    actual_duration: str | None
    validation_state: str
    voices: list[Voice]
    clefs: list[dict] = field(default_factory=list)
    context_changes: list[dict] = field(default_factory=list)
    barlines: list[dict] = field(default_factory=list)
    partial: dict = field(default_factory=dict)
    meter_context: list[dict] = field(default_factory=list)
    rhythm_status: str = "STRUCTURALLY_AMBIGUOUS"
    conflict_state: str = "NONE"


@dataclass
class Part:
    id: str
    name: str
    measures: list[Measure]
    staffs: list[dict] = field(default_factory=list)


@dataclass
class EditableScore:
    metadata: dict
    parts: list[Part]
    lyrics: list[dict]
    harmonies: list[dict]
    schema_version: str = "4F.1"
    pages: list[dict] = field(default_factory=list)
    systems: list[dict] = field(default_factory=list)
    layout: dict = field(default_factory=dict)


class Request(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def xml_characters(self):
        def check(value):
            if isinstance(value, str) and any(not (c in "\t\n\r" or 0x20 <= ord(c) <= 0xD7FF or 0xE000 <= ord(c) <= 0xFFFD or 0x10000 <= ord(c) <= 0x10FFFF) for c in value):
                raise ValueError("Text contains characters that XML cannot represent")
            if isinstance(value, dict):
                for child in value.values():
                    check(child)
        check(self.model_dump())
        return self


class PitchInput(Request):
    step: Literal["A", "B", "C", "D", "E", "F", "G"]
    alter: str = Field(default="0", max_length=32, pattern=r"^[+-]?\d+(?:\.\d+)?$")
    octave: StrictInt = Field(ge=0, le=9)


class EventPatch(Request):
    tie_direction: Literal["up", "down"] | None = None
    duration_scope: Literal["note", "chord"] = "chord"
    preserve_onsets: StrictBool = False
    written_accidental: Literal["flat-flat", "flat", "natural", "sharp", "double-sharp"] | None = None
    tie_to_event_id: str | None = Field(default=None, min_length=1, max_length=128)
    pitch: PitchInput | None = None
    duration: str | None = Field(default=None, max_length=32)
    voice: str | None = Field(default=None, min_length=1, max_length=32, pattern=r"^\S+$")
    staff: StrictInt | None = Field(default=None, ge=1, le=128)
    display_size: Literal["normal", "small", "cue"] | None = None
    grace: StrictBool | None = None


class EventAdd(Request):
    same_onset_id: str | None = Field(default=None, min_length=1, max_length=128)
    onset: str | None = Field(default=None, max_length=32)
    written_accidental: Literal["flat-flat", "flat", "natural", "sharp", "double-sharp"] | None = None
    tie_to_event_id: str | None = Field(default=None, max_length=128)
    measure_id: str = Field(max_length=128)
    after_event_id: str | None = Field(default=None, max_length=128)
    before_event_id: str | None = Field(default=None, max_length=128)
    chord_with_id: str | None = Field(default=None, max_length=128)
    kind: Literal["note", "rest"] = "note"
    pitch: PitchInput | None = None
    duration: str = Field(default="1", max_length=32)
    voice: str | None = Field(default=None, min_length=1, max_length=32, pattern=r"^\S+$")
    staff: StrictInt | None = Field(default=None, ge=1, le=128)
    display_size: Literal["normal", "small", "cue"] = "normal"
    grace: StrictBool = False


class TextPatch(Request):
    text: str = Field(max_length=2000)
    segment_index: StrictInt = Field(default=0, ge=0, le=100)


class LyricAdd(Request):
    text: str = Field(max_length=2000)
    number: str = Field(default="1", min_length=1, max_length=16)


class HarmonyPatch(Request):
    root_step: Literal["A", "B", "C", "D", "E", "F", "G"] | None = None
    root_alter: str | None = Field(default=None, max_length=32, pattern=r"^[+-]?\d+(?:\.\d+)?$")
    kind: Literal[
        "major", "minor", "augmented", "diminished", "dominant", "major-seventh",
        "minor-seventh", "diminished-seventh", "augmented-seventh", "half-diminished",
        "major-minor", "major-sixth", "minor-sixth", "dominant-ninth", "major-ninth",
        "minor-ninth", "dominant-11th", "major-11th", "minor-11th", "dominant-13th",
        "major-13th", "minor-13th", "suspended-second", "suspended-fourth",
        "Neapolitan", "Italian", "French", "German", "pedal", "power", "Tristan", "other", "none",
    ] | None = None
    text: str | None = Field(default=None, max_length=256)


class VerifyRequest(Request):
    confirmed_source_comparison: StrictBool

    @model_validator(mode="after")
    def must_confirm(self):
        if not self.confirmed_source_comparison:
            raise ValueError("Confirm comparison with the original source before verification")
        return self


class HarmonyAdd(HarmonyPatch):
    measure_id: str = Field(max_length=128)
    before_event_id: str | None = Field(default=None, max_length=128)
    root_step: Literal["A", "B", "C", "D", "E", "F", "G"] = "C"
    root_alter: str = Field(default="0", max_length=32, pattern=r"^[+-]?\d+(?:\.\d+)?$")


class ReviewTranspose(Request):
    semitones: StrictInt


class SourceConfirmation(Request):
    diagnostic_id: str = Field(min_length=1, max_length=128)
    note: str = Field(min_length=1, max_length=2000)

    @model_validator(mode="after")
    def meaningful_note(self):
        if not self.note.strip():
            raise ValueError("Explain the comparison with the original source")
        return self


class EventMove(Request):
    measure_id: str = Field(min_length=1, max_length=128)
    onset: str = Field(min_length=1, max_length=32)
    voice: str = Field(min_length=1, max_length=32, pattern=r"^\S+$")
    staff: StrictInt = Field(ge=1, le=128)
