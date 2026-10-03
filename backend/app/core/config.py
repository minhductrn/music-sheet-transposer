from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Music Sheet Transposer"
    api_v1_prefix: str = "/api/v1"
    recognition_max_upload_bytes: int = Field(default=20 * 1024 * 1024, gt=0)
    recognition_max_pages: int = Field(default=10, gt=0)
    recognition_max_image_pixels: int = Field(default=40_000_000, gt=0)
    recognition_max_output_bytes: int = Field(default=20 * 1024 * 1024, gt=0)
    recognition_max_archive_members: int = Field(default=128, gt=0)
    recognition_timeout_seconds: int = Field(default=120, gt=0)
    audiveris_executable: str = "audiveris"
    recognition_default_profile: Literal[
        "VOCAL_SONG", "SATB", "PIANO", "GENERAL", "ORCHESTRAL"
    ] = "VOCAL_SONG"
    audiveris_ocr_languages: str | None = Field(
        default=None, pattern=r"^[a-z]{3}(?:_[a-z]+)?(?:\+[a-z]{3}(?:_[a-z]+)?)*$",
    )
    audiveris_tessdata_path: Path | None = None
    audiveris_input_quality: Literal["Synthetic", "Standard", "Poor"] | None = None
    recognition_max_artifact_bytes: int = Field(default=20 * 1024 * 1024, gt=0)
    recognition_max_log_bytes: int = Field(default=128 * 1024, gt=0)
    recognition_max_diagnostics: int = Field(default=100, gt=0, le=500)


settings = Settings()
