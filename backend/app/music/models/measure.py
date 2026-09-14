from pydantic import BaseModel, Field

from app.music.models.note import Note


class Measure(BaseModel):
    number: int = Field(gt=0)
    notes: list[Note] = Field(default_factory=list)