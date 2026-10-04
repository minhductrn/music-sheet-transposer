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
    recognition_provider: Literal["audiveris", "smt"] = "audiveris"
    # SMT is EXPERIMENTAL / BENCHMARK ONLY; selecting it does not enable it.
    smt_enabled: bool = False
    smt_worker_python: Path | None = None
    smt_upstream_path: Path | None = None
    smt_model_reference: str = Field(default="antoniorv6/smt-grandstaff", pattern=r"^[\w.-]+/[\w.-]+$")
    smt_model_revision: str = Field(default="2eb5a45c29d63bdf063cd0427175f57675e7da9e", min_length=1, max_length=128)
    smt_device: Literal["auto", "cpu", "cuda"] = "auto"
    smt_pdf_dpi: int = Field(default=200, ge=72, le=600)
    smt_staves_per_system: int = Field(default=2, ge=1, le=2)
    smt_max_systems: int = Field(default=64, gt=0, le=128)
    smt_timeout_seconds: int = Field(default=600, gt=0)
    smt_cpu_threads: int = Field(default=4, gt=0, le=32)
    audiveris_executable: str = "audiveris"
    recognition_default_profile: Literal[
        "VOCAL_SONG", "SATB", "PIANO", "GENERAL", "ORCHESTRAL"
    ] = "VOCAL_SONG"
    audiveris_ocr_languages: str | None = Field(
        default=None, pattern=r"^[a-z]{3}(?:_[a-z]+)?(?:\+[a-z]{3}(?:_[a-z]+)?)*$",
    )
    audiveris_tessdata_path: Path | None = None
    audiveris_input_quality: Literal["Synthetic", "Standard", "Poor"] | None = None
    audiveris_semantic_recovery_enabled: bool = True
    # Optional evidence pass only; production recognition keeps small heads/beams off.
    audiveris_semantic_analysis_enabled: bool = False
    audiveris_semantic_analysis_timeout_seconds: int = Field(default=120, gt=0)
    semantic_max_expanded_bytes: int = Field(default=64 * 1024 * 1024, gt=0)
    semantic_max_xml_nodes: int = Field(default=200_000, gt=0)
    semantic_max_candidates: int = Field(default=128, gt=0, le=1000)
    recognition_max_artifact_bytes: int = Field(default=20 * 1024 * 1024, gt=0)
    recognition_max_log_bytes: int = Field(default=128 * 1024, gt=0)
    recognition_max_diagnostics: int = Field(default=100, gt=0, le=500)
    review_lifetime_seconds: int = Field(default=3600, gt=0)
    review_max_sessions: int = Field(default=8, gt=0)
    review_max_total_bytes: int = Field(default=128 * 1024 * 1024, gt=0)
    review_history_limit: int = Field(default=20, gt=0, le=100)
    review_history_max_bytes: int = Field(default=8 * 1024 * 1024, gt=0)
    review_max_xml_nodes: int = Field(default=100_000, gt=0)


settings = Settings()
