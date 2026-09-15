from pydantic import BaseModel, Field

from app.music.models.note import Note
from app.music.models.time_signature import TimeSignature


class Measure(BaseModel):
    number: int = Field(gt=0)
    divisions: int | None = Field(default=None, gt=0)
    time_signature: TimeSignature | None = None
    notes: list[Note] = Field(default_factory=list)