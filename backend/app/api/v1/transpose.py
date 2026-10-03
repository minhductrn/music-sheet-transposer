from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool

from app.music.musicxml.transposer import (
    MusicXMLTranspositionError,
    transpose_musicxml_document,
)
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


@router.post("/transpose/musicxml")
async def transpose_musicxml(
    file: UploadFile = File(...),
    semitones: int = Form(...),
) -> Response:
    contents = await file.read()
    try:
        output_contents = await run_in_threadpool(
            transpose_musicxml_document, contents, semitones,
        )
    except MusicXMLTranspositionError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    return Response(
        content=output_contents,
        media_type="application/vnd.recordare.musicxml+xml",
        headers={
            "Content-Disposition":
                'attachment; filename="transposed.musicxml"'
        },
    )
