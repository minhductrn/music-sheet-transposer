"""Local review sessions with optimistic revision checks and bounded uploads."""

import re
import time

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile
from fastapi.responses import JSONResponse, Response
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.music.review.document import ReviewError
from app.music.review.models import (
    TupletWork, EventsDelete, HarmonyMove, TextToLyrics, NotationEdit, SlurEdit, TripletReplacement, TripletSelection, TripletEdit, EventAdd, EventMove, EventPatch, HarmonyAdd, HarmonyPatch, LyricAdd, LyricMove, ReviewTranspose, ScoreTextAdd, SourceConfirmation, TextPatch, VerifyRequest,
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


@router.post("/{review_id}/keepalive")
async def keepalive_review(review_id: str, service: ReviewService = Depends(get_review_service)):
    return JSONResponse(await call(service.keepalive, review_id), headers={"Cache-Control": "no-store"})


@router.delete("/{review_id}", status_code=204)
async def close_review(review_id: str, service: ReviewService = Depends(get_review_service)):
    await call(service.delete, review_id)
    return Response(status_code=204, headers={"Cache-Control": "no-store"})


@router.patch("/{review_id}/events/{event_id}")
async def update_event(review_id: str, event_id: str, patch: EventPatch,
                       revision: int = Depends(expected_revision), service: ReviewService = Depends(get_review_service)):
    return await response(await call(service.event_patch, review_id, revision, event_id, patch))


@router.post("/{review_id}/events/{event_id}/triplet-replacement/options")
async def replacement_options(review_id: str, event_id: str, revision: int = Depends(expected_revision),
                               service: ReviewService = Depends(get_review_service)):
    return JSONResponse(await call(service.replacement_options, review_id, revision, event_id), headers={"Cache-Control": "no-store"})


@router.post("/{review_id}/events/{event_id}/triplet-replacement/preview")
async def replacement_preview(review_id: str, event_id: str, request: TripletReplacement, revision: int = Depends(expected_revision),
                               service: ReviewService = Depends(get_review_service)):
    return JSONResponse(await call(service.replacement_preview, review_id, revision, event_id, request), headers={"Cache-Control": "no-store"})


@router.post("/{review_id}/events/{event_id}/replace-triplet")
async def replace_triplet(review_id: str, event_id: str, request: TripletReplacement, revision: int = Depends(expected_revision),
                           service: ReviewService = Depends(get_review_service)):
    return await response(await call(service.triplet_replace, review_id, revision, event_id, request))


@router.post("/{review_id}/triplets/preview")
async def preview_triplet(review_id: str, request: TripletSelection, revision: int = Depends(expected_revision),
                          service: ReviewService = Depends(get_review_service)):
    payload = await call(service.triplet_preview, review_id, revision, request)
    return JSONResponse(payload, headers={"Cache-Control": "no-store"})


@router.post("/{review_id}/tuplets")
async def edit_tuplet(review_id: str, request: TupletWork, revision: int = Depends(expected_revision),
                      service: ReviewService = Depends(get_review_service)):
    return await response(await call(service.tuplet_work, review_id, revision, request))


@router.post("/{review_id}/triplets")
async def edit_triplet(review_id: str, request: TripletEdit, revision: int = Depends(expected_revision),
                       service: ReviewService = Depends(get_review_service)):
    return await response(await call(service.triplet_edit, review_id, revision, request))


@router.post("/{review_id}/events")
async def insert_event(review_id: str, event: EventAdd, revision: int = Depends(expected_revision),
                       service: ReviewService = Depends(get_review_service)):
    return await response(await call(service.event_add, review_id, revision, event))


@router.delete("/{review_id}/events/{event_id}")
async def remove_event(review_id: str, event_id: str, revision: int = Depends(expected_revision),
                       service: ReviewService = Depends(get_review_service)):
    return await response(await call(service.event_delete, review_id, revision, event_id))


@router.post("/{review_id}/events/{event_id}/delete-preserve-timing")
async def remove_event_preserving_timing(review_id: str, event_id: str, revision: int = Depends(expected_revision),
                                         service: ReviewService = Depends(get_review_service)):
    return await response(await call(service.event_delete, review_id, revision, event_id, True))


@router.patch("/{review_id}/lyrics/{lyric_id}")
async def update_lyric(review_id: str, lyric_id: str, patch: TextPatch,
                       revision: int = Depends(expected_revision), service: ReviewService = Depends(get_review_service)):
    return await response(await call(service.lyric_patch, review_id, revision, lyric_id, patch))


@router.delete("/{review_id}/lyrics/{lyric_id}")
async def remove_lyric(review_id: str, lyric_id: str, revision: int = Depends(expected_revision),
                       service: ReviewService = Depends(get_review_service)):
    return await response(await call(service.lyric_delete, review_id, revision, lyric_id))


@router.post("/{review_id}/lyrics/{lyric_id}/move")
async def move_lyric(review_id: str, lyric_id: str, move: LyricMove,
                     revision: int = Depends(expected_revision), service: ReviewService = Depends(get_review_service)):
    return await response(await call(service.lyric_move, review_id, revision, lyric_id, move))


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


@router.post("/{review_id}/texts")
async def create_score_text(review_id: str, request: ScoreTextAdd, revision: int = Depends(expected_revision),
                            service: ReviewService = Depends(get_review_service)):
    return await response(await call(service.score_text_add, review_id, revision, request))


@router.patch("/{review_id}/texts/{text_id}")
async def update_score_text(review_id: str, text_id: str, patch: TextPatch, revision: int = Depends(expected_revision),
                            service: ReviewService = Depends(get_review_service)):
    return await response(await call(service.score_text_patch, review_id, revision, text_id, patch))


@router.delete("/{review_id}/texts/{text_id}")
async def delete_score_text(review_id: str, text_id: str, revision: int = Depends(expected_revision),
                            service: ReviewService = Depends(get_review_service)):
    return await response(await call(service.score_text_delete, review_id, revision, text_id))


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


@router.post("/{review_id}/music-check")
async def check_music(review_id: str, revision: int = Depends(expected_revision),
                      service: ReviewService = Depends(get_review_service)):
    payload = await call(service.music_check, review_id, revision)
    return JSONResponse(payload, headers={"Cache-Control": "no-store", "ETag": f'"{payload["revision"]}"'})


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


@router.post("/{review_id}/transpose")
async def transpose_verified_review(review_id: str, request: ReviewTranspose, revision: int = Depends(expected_revision),
                                    service: ReviewService = Depends(get_review_service)):
    contents = await call(service.transpose, review_id, revision, request.semitones)
    return Response(contents, media_type="application/vnd.recordare.musicxml+xml",
                    headers={"Cache-Control": "no-store", "ETag": f'"{revision}"',
                             "Content-Disposition": 'attachment; filename="transposed.musicxml"'})


@router.post("/{review_id}/diagnostics/confirm-source")
async def confirm_source_diagnostic(review_id: str, request: SourceConfirmation, revision: int = Depends(expected_revision),
                                    service: ReviewService = Depends(get_review_service)):
    return await response(await call(service.confirm_source, review_id, revision, request))


@router.post("/{review_id}/events/{event_id}/ownership")
async def move_note(review_id: str, event_id: str, request: EventMove, revision: int = Depends(expected_revision),
                    service: ReviewService = Depends(get_review_service)):
    return await response(await call(service.event_move, review_id, revision, event_id, request))


@router.post("/{review_id}/slurs")
async def edit_slur(review_id: str, request: SlurEdit, revision: int = Depends(expected_revision),
                    service: ReviewService = Depends(get_review_service)):
    return await response(await call(service.slur_edit, review_id, revision, request))


@router.post("/{review_id}/document-correction")
async def correct_review_document(review_id: str, musicxml: UploadFile = File(...),
                                  revision: int = Depends(expected_revision),
                                  service: ReviewService = Depends(get_review_service)):
    try:
        contents = await read_upload(musicxml, service.config.recognition_max_output_bytes)
        return await response(await call(service.document_correction, review_id, revision, contents))
    finally:
        await musicxml.close()


@router.post("/{review_id}/events/{event_id}/notation")
async def edit_notation(review_id: str, event_id: str, request: NotationEdit,
                        revision: int = Depends(expected_revision),
                        service: ReviewService = Depends(get_review_service)):
    return await response(await call(service.notation_edit, review_id, revision, event_id, request))


@router.post("/{review_id}/texts/{text_id}/to-lyrics")
async def text_to_lyrics(review_id: str, text_id: str, request: TextToLyrics,
                         revision: int = Depends(expected_revision),
                         service: ReviewService = Depends(get_review_service)):
    return await response(await call(service.text_to_lyrics, review_id, revision, text_id, request))


@router.delete("/{review_id}/marks/{mark_id}")
async def delete_omr_mark(review_id: str, mark_id: str, revision: int = Depends(expected_revision), service: ReviewService = Depends(get_review_service)):
    return await response(await call(service.mark_delete, review_id, revision, mark_id))

@router.delete("/{review_id}/harmonies/{harmony_id}")
async def delete_harmony(review_id: str, harmony_id: str, revision: int = Depends(expected_revision), service: ReviewService = Depends(get_review_service)):
    return await response(await call(service.harmony_delete, review_id, revision, harmony_id))

@router.post("/{review_id}/harmonies/{harmony_id}/move")
async def move_harmony(review_id: str, harmony_id: str, request: HarmonyMove, revision: int = Depends(expected_revision), service: ReviewService = Depends(get_review_service)):
    return await response(await call(service.harmony_move, review_id, revision, harmony_id, request))


@router.post("/{review_id}/events/delete-selection")
async def delete_selection(review_id: str, request: EventsDelete, revision: int = Depends(expected_revision), service: ReviewService = Depends(get_review_service)):
    return await response(await call(service.events_delete, review_id, revision, request.event_ids))
