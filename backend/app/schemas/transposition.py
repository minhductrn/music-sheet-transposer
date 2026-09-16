from pydantic import BaseModel

from app.music.models.score import Score


class TransposeRequest(BaseModel):
    score: Score
    semitones: int


class TransposeResponse(BaseModel):
    score: Score