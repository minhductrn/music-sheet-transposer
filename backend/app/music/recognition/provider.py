"""Native provider contract and configuration, independent of HTTP responses."""

from pathlib import Path
from typing import Protocol, runtime_checkable

from app.core.config import Settings
from app.music.recognition.profiles import ProfileOptions
from app.music.recognition.result import ProviderOutput


@runtime_checkable
class MusicRecognitionProvider(Protocol):
    def recognize_result(
        self, source: Path, output_directory: Path, options: ProfileOptions,
    ) -> ProviderOutput:
        """Return MusicXML or native symbolic evidence, never invented MusicXML."""


def create_provider(config: Settings, name: str | None = None) -> MusicRecognitionProvider:
    selected = name or config.recognition_provider
    if selected == "audiveris":
        from app.music.recognition.audiveris import AudiverisProvider
        return AudiverisProvider(config)
    if selected == "smt":
        from app.music.recognition.smt import SMTProvider
        return SMTProvider(config)
    raise ValueError("Unknown recognition provider.")
