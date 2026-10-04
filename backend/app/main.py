import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from starlette.concurrency import run_in_threadpool

from app.api.v1.health import router as health_router
from app.api.v1.transpose import router as transpose_router
from app.api.v1.recognize import router as recognize_router
from app.api.v1.reviews import get_review_service, router as reviews_router
from app.core.config import settings


async def cleanup_reviews():
    while True:
        await asyncio.sleep(min(60, settings.review_lifetime_seconds))
        await run_in_threadpool(get_review_service().store.cleanup)


@asynccontextmanager
async def lifespan(app: FastAPI):
    cleanup = asyncio.create_task(cleanup_reviews())
    try:
        yield
    finally:
        cleanup.cancel()
        with suppress(asyncio.CancelledError):
            await cleanup


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.include_router(
    health_router,
    prefix=settings.api_v1_prefix,
)

app.include_router(
    transpose_router,
    prefix=settings.api_v1_prefix,
)

app.include_router(recognize_router, prefix=settings.api_v1_prefix)
app.include_router(reviews_router, prefix=settings.api_v1_prefix)
