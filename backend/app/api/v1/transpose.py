from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool

from app.music.musicxml.transposer import (
    MusicXMLTranspositionError,
    transpose_musicxml_document,
)
from app.music.musicxml.concert_key import concert_key_info, transpose_concert_key
from app.music.transposition.score_transposer import transpose_score
from app.schemas.transposition import (
    TransposeRequest,
    TransposeResponse,
)


router = APIRouter()


@router.post("/concert-key")
async def inspect_concert_key(file: UploadFile = File(...)) -> dict:
    try:
        return await run_in_threadpool(concert_key_info, await file.read())
    except MusicXMLTranspositionError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/transpose/concert-key")
async def transpose_concert_musicxml(
    source_fifths: Annotated[int, Form(ge=-7, le=7)],
    source_mode: Annotated[Literal["major", "minor"], Form()],
    source_confirmed: Annotated[bool, Form()],
    file: UploadFile = File(...),
    target_fifths: Annotated[int, Form(ge=-7, le=7)] = 0,
    direction: Annotated[Literal["up", "down"], Form()] = "up",
) -> Response:
    if not source_confirmed:
        raise HTTPException(status_code=422, detail="Confirm the Source Key before transposing.")
    try:
        contents = await run_in_threadpool(
            transpose_concert_key, await file.read(), target_fifths, direction,
            source_fifths=source_fifths, source_mode=source_mode,
        )
    except MusicXMLTranspositionError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return Response(contents, media_type="application/vnd.recordare.musicxml+xml",
                    headers={"Content-Disposition": 'attachment; filename="concert-transposed.musicxml"'})


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


@router.post("/transpose/instrument")
async def transpose_instrument_musicxml(
    instrument: Annotated[Literal["alto", "soprano", "tenor"], Form()],
    direction: Annotated[Literal["up", "down"], Form()] = "up",
    file: UploadFile = File(...),
) -> Response:
    from app.music.musicxml.instruments import instrument_score
    from app.music.review.document import ReviewError
    from app.core.config import settings
    try:
        contents = await file.read(settings.recognition_max_output_bytes + 1)
        if len(contents) > settings.recognition_max_output_bytes:
            raise HTTPException(413, "The score exceeds the MusicXML size limit.")
        output = await run_in_threadpool(instrument_score, contents, instrument, direction)
        return Response(output, media_type="application/vnd.recordare.musicxml+xml",
                        headers={"Content-Disposition": f'attachment; filename="{instrument}-sax.musicxml"'})
    except (MusicXMLTranspositionError, ReviewError) as error:
        raise HTTPException(422, detail=str(error)) from error
    finally:
        await file.close()
