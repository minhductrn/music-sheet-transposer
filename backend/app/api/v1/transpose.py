from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import Response

from app.music.musicxml.exporter import export_musicxml
from app.music.musicxml.parser import parse_musicxml
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
    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        input_path = temp_path / "input.musicxml"
        output_path = temp_path / "transposed.musicxml"

        contents = await file.read()
        input_path.write_bytes(contents)

        score = parse_musicxml(input_path)

        transposed_score = transpose_score(
            score,
            semitones,
        )

        export_musicxml(
            transposed_score,
            output_path,
        )

        output_contents = output_path.read_bytes()

    return Response(
        content=output_contents,
        media_type="application/vnd.recordare.musicxml+xml",
        headers={
            "Content-Disposition":
                'attachment; filename="transposed.musicxml"'
        },
    )