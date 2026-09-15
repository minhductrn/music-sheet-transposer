from enum import StrEnum

from pydantic import BaseModel, Field

from app.music.models.pitch import Pitch


class NoteType(StrEnum):
    WHOLE = "whole"
    HALF = "half"
    QUARTER = "quarter"
    EIGHTH = "eighth"
    SIXTEENTH = "16th"
    THIRTY_SECOND = "32nd"
    SIXTY_FOURTH = "64th"


class Note(BaseModel):
    pitch: Pitch | None = None
    duration: int = Field(gt=0)
    note_type: NoteType | None = None
    is_rest: bool = False