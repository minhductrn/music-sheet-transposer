from pydantic import BaseModel, Field

from app.music.models.clef import Clef
from app.music.models.key_signature import KeySignature
from app.music.models.note import Note
from app.music.models.time_signature import TimeSignature
from app.music.models.timing import Backup, Forward


MeasureEvent = Note | Backup | Forward


class Measure(BaseModel):
    number: int = Field(gt=0)
    divisions: int | None = Field(default=None, gt=0)
    key_signature: KeySignature | None = None
    time_signature: TimeSignature | None = None
    clefs: list[Clef] = Field(default_factory=list)
    notes: list[Note] = Field(default_factory=list)
    events: list[MeasureEvent] = Field(default_factory=list)