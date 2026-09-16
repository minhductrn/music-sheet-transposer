from enum import StrEnum

from pydantic import BaseModel, Field


class KeyMode(StrEnum):
    MAJOR = "major"
    MINOR = "minor"


class KeySignature(BaseModel):
    fifths: int = Field(ge=-7, le=7)
    mode: KeyMode = KeyMode.MAJOR
