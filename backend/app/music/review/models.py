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


@dataclass
class Part:
    id: str
    name: str
    measures: list[Measure]


@dataclass
class EditableScore:
    metadata: dict
    parts: list[Part]
    lyrics: list[dict]
    harmonies: list[dict]


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
    pitch: PitchInput | None = None
    duration: str | None = Field(default=None, max_length=32)
    voice: str | None = Field(default=None, min_length=1, max_length=32, pattern=r"^\S+$")
    staff: StrictInt | None = Field(default=None, ge=1, le=128)
    display_size: Literal["normal", "small", "cue"] | None = None
    grace: StrictBool | None = None


class EventAdd(Request):
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
