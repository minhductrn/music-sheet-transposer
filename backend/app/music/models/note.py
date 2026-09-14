from pydantic import BaseModel, Field

from app.music.models.pitch import Pitch


class Note(BaseModel):
    pitch: Pitch | None = None
    duration: int = Field(gt=0)
    is_rest: bool = False