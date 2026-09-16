from app.music.models.measure import Measure
from app.music.models.note import Note, NoteType
from app.music.models.pitch import Pitch, PitchStep
from app.music.models.score import Part, Score
from app.schemas.transposition import (
    TransposeRequest,
    TransposeResponse,
)


def create_test_score() -> Score:
    return Score(
        title="API Test",
        parts=[
            Part(
                id="P1",
                name="Piano",
                measures=[
                    Measure(
                        number=1,
                        notes=[
                            Note(
                                pitch=Pitch(
                                    step=PitchStep.C,
                                    octave=4,
                                ),
                                duration=1,
                                note_type=NoteType.QUARTER,
                            )
                        ],
                    )
                ],
            )
        ],
    )


def test_transpose_request() -> None:
    score = create_test_score()

    request = TransposeRequest(
        score=score,
        semitones=2,
    )

    assert request.score.title == "API Test"
    assert request.semitones == 2


def test_transpose_response() -> None:
    score = create_test_score()

    response = TransposeResponse(
        score=score,
    )

    assert response.score.title == "API Test"
    assert len(response.score.parts) == 1