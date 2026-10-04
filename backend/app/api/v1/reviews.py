"""Local review sessions with optimistic revision checks and bounded uploads."""

import re
import time

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile
from fastapi.responses import JSONResponse, Response
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.music.review.document import ReviewError
from app.music.review.models import (
    EventAdd, EventPatch, HarmonyAdd, HarmonyPatch, LyricAdd, TextPatch, VerifyRequest,
)
from app.music.review.service import ReviewService
from app.music.review.storage import MemoryReviewStore


router = APIRouter(prefix="/reviews", tags=["reviews"])
_service = ReviewService(MemoryReviewStore(settings), settings, time.time)


def get_review_service() -> ReviewService:
    return _service


def expected_revision(if_match: str | None = Header(default=None)) -> int:
    if if_match is None:
        raise HTTPException(428, "Corrections require an If-Match review revision.", headers={"Cache-Control": "no-store"})
    if not re.fullmatch(r'"?\d{1,12}"?', if_match):
        raise HTTPException(422, "If-Match must contain the numeric review revision.")
    return int(if_match.strip('"'))


async def call(method, *args):
    try:
        return await run_in_threadpool(method, *args)
    except ReviewError as error:
        raise HTTPException(error.status_code, str(error), headers={"Cache-Control": "no-store"}) from error


async def response(payload):
    return await run_in_threadpool(JSONResponse, payload, headers={"Cache-Control": "no-store", "ETag": f'"{payload["revision"]}"'})


async def read_upload(file, limit):
    data = bytearray()
    while chunk := await file.read(64 * 1024):
        data.extend(chunk)
        if len(data) > limit:
            raise HTTPException(413, "The uploaded review file exceeds the size limit.")
    return bytes(data)


@router.post("", status_code=201)
async def create_review(
    musicxml: UploadFile = File(...), source: UploadFile | None = File(None),
    omr: UploadFile | None = File(None), analysis_omr: UploadFile | None = File(None),
    service: ReviewService = Depends(get_review_service),
):
    try:
        xml = await read_upload(musicxml, service.config.recognition_max_output_bytes)
        original = await read_upload(source, service.config.recognition_max_upload_bytes) if source else None
        evidence = await read_upload(omr, service.config.recognition_max_artifact_bytes) if omr else None
        additional = await read_upload(analysis_omr, service.config.recognition_max_artifact_bytes) if analysis_omr else None
        payload = await call(service.create, xml, original, source.content_type if source else None, evidence, additional)
        result = await response(payload)
        result.status_code = 201
        return result
    finally:
        await musicxml.close()
        if source:
            await source.close()
        if omr:
            await omr.close()
        if analysis_omr:
            await analysis_omr.close()


@router.get("/{review_id}")
async def get_review(review_id: str, service: ReviewService = Depends(get_review_service)):
    return await response(await call(service.get, review_id))


@router.delete("/{review_id}", status_code=204)
async def close_review(review_id: str, service: ReviewService = Depends(get_review_service)):
    await call(service.delete, review_id)
    return Response(status_code=204, headers={"Cache-Control": "no-store"})


@router.patch("/{review_id}/events/{event_id}")
async def update_event(review_id: str, event_id: str, patch: EventPatch,
                       revision: int = Depends(expected_revision), service: ReviewService = Depends(get_review_service)):
    return await response(await call(service.event_patch, review_id, revision, event_id, patch))


@router.post("/{review_id}/events")
async def insert_event(review_id: str, event: EventAdd, revision: int = Depends(expected_revision),
                       service: ReviewService = Depends(get_review_service)):
    return await response(await call(service.event_add, review_id, revision, event))


@router.delete("/{review_id}/events/{event_id}")
async def remove_event(review_id: str, event_id: str, revision: int = Depends(expected_revision),
                       service: ReviewService = Depends(get_review_service)):
    return await response(await call(service.event_delete, review_id, revision, event_id))


@router.patch("/{review_id}/lyrics/{lyric_id}")
async def update_lyric(review_id: str, lyric_id: str, patch: TextPatch,
                       revision: int = Depends(expected_revision), service: ReviewService = Depends(get_review_service)):
    return await response(await call(service.lyric_patch, review_id, revision, lyric_id, patch))


@router.post("/{review_id}/events/{event_id}/lyrics")
async def insert_lyric(review_id: str, event_id: str, lyric: LyricAdd,
                       revision: int = Depends(expected_revision), service: ReviewService = Depends(get_review_service)):
    return await response(await call(service.lyric_add, review_id, revision, event_id, lyric))


@router.patch("/{review_id}/harmonies/{harmony_id}")
async def update_harmony(review_id: str, harmony_id: str, patch: HarmonyPatch,
                         revision: int = Depends(expected_revision), service: ReviewService = Depends(get_review_service)):
    return await response(await call(service.harmony_patch, review_id, revision, harmony_id, patch))


@router.post("/{review_id}/harmonies")
async def insert_harmony(review_id: str, harmony: HarmonyAdd, revision: int = Depends(expected_revision),
                         service: ReviewService = Depends(get_review_service)):
    return await response(await call(service.harmony_add, review_id, revision, harmony))


@router.patch("/{review_id}/metadata/title")
async def update_title(review_id: str, patch: TextPatch, revision: int = Depends(expected_revision),
                       service: ReviewService = Depends(get_review_service)):
    return await response(await call(service.title_patch, review_id, revision, patch))


@router.patch("/{review_id}/credits/{credit_id}")
async def update_credit(review_id: str, credit_id: str, patch: TextPatch,
                        revision: int = Depends(expected_revision), service: ReviewService = Depends(get_review_service)):
    return await response(await call(service.credit_patch, review_id, revision, credit_id, patch))


@router.post("/{review_id}/validate")
async def validate_review(review_id: str, revision: int = Depends(expected_revision),
                          service: ReviewService = Depends(get_review_service)):
    return await response(await call(service.validate, review_id, revision))


@router.post("/{review_id}/verify")
async def verify_review(review_id: str, confirmation: VerifyRequest, revision: int = Depends(expected_revision),
                        service: ReviewService = Depends(get_review_service)):
    return await response(await call(service.verify, review_id, revision))


@router.post("/{review_id}/undo")
async def undo_review(review_id: str, revision: int = Depends(expected_revision),
                      service: ReviewService = Depends(get_review_service)):
    return await response(await call(service.history, review_id, revision, "undo"))


@router.post("/{review_id}/redo")
async def redo_review(review_id: str, revision: int = Depends(expected_revision),
                      service: ReviewService = Depends(get_review_service)):
    return await response(await call(service.history, review_id, revision, "redo"))


@router.get("/{review_id}/musicxml")
async def corrected_musicxml(review_id: str, verified_only: bool = False, original: bool = False,
                             service: ReviewService = Depends(get_review_service)):
    contents = await call(service.musicxml, review_id, verified_only, original)
    return Response(contents, media_type="application/vnd.recordare.musicxml+xml",
                    headers={"Cache-Control": "no-store", "Content-Disposition": 'attachment; filename="corrected.musicxml"'})


@router.get("/{review_id}/source")
async def original_source(review_id: str, service: ReviewService = Depends(get_review_service)):
    source = await call(service.source, review_id)
    # Served as data in a browser viewer, never as executable HTML/SVG.
    return Response(source.contents, media_type=source.media_type,
                    headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})
