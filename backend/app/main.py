from fastapi import FastAPI

from app.api.v1.health import router as health_router
from app.api.v1.transpose import router as transpose_router
from app.core.config import settings


app = FastAPI(title=settings.app_name)

app.include_router(
    health_router,
    prefix=settings.api_v1_prefix,
)

app.include_router(
    transpose_router,
    prefix=settings.api_v1_prefix,
)