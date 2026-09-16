from fastapi import APIRouter

from app.music.transposition.score_transposer import transpose_score
from app.schemas.transposition import (
    TransposeRequest,
    TransposeResponse,
)


router = APIRouter()


@router.post(
    "/transpose",
    response_model=TransposeResponse,
)
def transpose(
    request: TransposeRequest,
) -> TransposeResponse:
    transposed_score = transpose_score(
        request.score,
        request.semitones,
    )

    return TransposeResponse(
        score=transposed_score,
    )