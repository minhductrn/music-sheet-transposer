from dataclasses import asdict
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import JSONResponse, Response
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.music.recognition.provider import create_provider
from app.music.recognition.service import MusicRecognitionService, RecognitionError
from app.music.recognition.profiles import InputQuality, RecognitionProfile


router = APIRouter()
_service = MusicRecognitionService(create_provider(settings), settings)


def get_recognition_service() -> MusicRecognitionService:
    return _service


@router.post("/recognize")
async def recognize(
    file: UploadFile = File(...),
    profile: RecognitionProfile | None = Form(None),
    input_quality: InputQuality | None = Form(None),
    response_format: Literal["musicxml", "json"] = Form("musicxml"),
    service: MusicRecognitionService = Depends(get_recognition_service),
) -> Response:
    try:
        contents = bytearray()
        while chunk := await file.read(64 * 1024):
            contents.extend(chunk)
            if len(contents) > service.config.recognition_max_upload_bytes:
                raise RecognitionError("The uploaded file exceeds the size limit.", 413)
        result = await run_in_threadpool(
            service.recognize_result, bytes(contents), file.filename or "", file.content_type,
            profile, input_quality,
        )
    except RecognitionError as error:
        return JSONResponse(
            status_code=error.status_code,
            content={"detail": str(error), "diagnostics": [asdict(issue) for issue in error.diagnostics]},
            headers={"Cache-Control": "no-store"},
        )
    finally:
        await file.close()
    if response_format == "json":
        # Base64 artifacts and JSON encoding can be large; keep them off the event loop.
        return await run_in_threadpool(
            lambda: JSONResponse(result.response_payload(), headers={"Cache-Control": "no-store"}),
        )
    return Response(
        result.musicxml, media_type="application/vnd.recordare.musicxml+xml",
        headers={"Content-Disposition": 'attachment; filename="recognized.musicxml"',
                 "Cache-Control": "no-store", "X-Recognition-Provider": result.provider,
                 "X-Recognition-Profile": result.profile.value,
                 "X-Recognition-Review-Required": str(result.review_required).lower()},
    )
