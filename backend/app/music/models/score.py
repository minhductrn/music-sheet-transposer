from pydantic import BaseModel, Field

from app.music.models.measure import Measure


class Part(BaseModel):
    id: str
    name: str
    measures: list[Measure] = Field(default_factory=list)


class Score(BaseModel):
    title: str | None = None
    parts: list[Part] = Field(default_factory=list)