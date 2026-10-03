from enum import StrEnum

from pydantic import BaseModel, Field


class ClefSign(StrEnum):
    G = "G"
    F = "F"
    C = "C"


class Clef(BaseModel):
    sign: ClefSign
    line: int = Field(ge=1, le=5)
    staff: int = Field(default=1, gt=0)