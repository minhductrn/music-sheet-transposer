from pydantic import BaseModel, Field


class TimeSignature(BaseModel):
    beats: int = Field(gt=0)
    beat_type: int = Field(gt=0)