from enum import StrEnum

from pydantic import BaseModel, Field


class PitchStep(StrEnum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"
    G = "G"


class Pitch(BaseModel):
    step: PitchStep
    octave: int
    alter: float = Field(default=0.0)