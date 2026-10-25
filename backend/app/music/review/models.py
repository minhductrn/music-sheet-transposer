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
    insertion_gaps: list[dict] = field(default_factory=list)


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
    texts: list[dict] = field(default_factory=list)


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


class TripletSelection(Request):
    event_ids: list[str] = Field(default_factory=list, max_length=128)


class TripletEdit(Request):
    measure_id: str = Field(min_length=1, max_length=128)
    voice: str = Field(min_length=1, max_length=32, pattern=r"^\S+$")
    staff: StrictInt = Field(ge=1, le=128)
    base_duration: Literal['4', '2', '1', '1/2', '1/4', '1/8', '1/16']
    pattern: Literal['equal', 'quarter-eighth'] = 'equal'
    member_counts: tuple[Literal[1, 2], Literal[1, 2]] = (2, 2)
    onset: str | None = Field(default=None, max_length=32)
    pitches: list[PitchInput] = Field(default_factory=list, max_length=4)
    event_ids: list[str] = Field(default_factory=list, max_length=4)

    @model_validator(mode="after")
    def explicit_group(self):
        mixed = self.pattern == 'quarter-eighth'
        if mixed and self.base_duration != '1':
            raise ValueError('The mixed triplet pattern uses written quarter then eighth values.')
        if self.event_ids:
            valid_count = 2 <= len(self.event_ids) <= 4 if mixed else len(self.event_ids) == 3
            if not valid_count or self.pitches or self.onset is not None:
                raise ValueError('Choose the complete existing rhythmic group or an explicit insertion location and pitches.')
        elif len(self.pitches) != (sum(self.member_counts) if mixed else 3) or self.onset is None:
            raise ValueError('Choose every pitch required by the selected triplet structure and an onset.')
        return self


class TripletReplacement(Request):
    preserve_associations: StrictBool = False
    original_member_ids: list[str] | None = Field(default=None, min_length=1, max_length=3)
    pattern: Literal['equal', 'quarter-eighth']
    member_counts: tuple[Literal[1, 2], Literal[1, 2]] = (1, 1)
    pitches: list[PitchInput] = Field(min_length=2, max_length=4)

    @model_validator(mode="after")
    def explicit_pitches(self):
        if self.pattern == 'equal' and self.member_counts != (1, 1):
            raise ValueError('Three equal notes must be single notes.')
        if len(self.pitches) != (3 if self.pattern == 'equal' else sum(self.member_counts)):
            raise ValueError('Choose every replacement pitch explicitly.')
        return self


class TextPatch(Request):
    text: str = Field(max_length=2000)
    segment_index: StrictInt = Field(default=0, ge=0, le=100)


class ScoreTextAdd(Request):
    role: Literal["work_title", "movement_title", "composer", "lyricist", "credit", "direction"]
    text: str = Field(min_length=1, max_length=2000)
    event_id: str | None = Field(default=None, min_length=1, max_length=128)


class LyricAdd(Request):
    text: str = Field(max_length=2000)
    number: str = Field(default="1", min_length=1, max_length=16)


class LyricMove(Request):
    source_event_id: str = Field(min_length=1, max_length=128)
    destination_event_id: str = Field(min_length=1, max_length=128)
    number: str = Field(min_length=1, max_length=16)


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


class SlurEdit(Request):
    source_event_id: str = Field(min_length=1, max_length=128)
    target_event_id: str = Field(min_length=1, max_length=128)
    direction: Literal["up", "down"] = "up"
    remove: StrictBool = False
