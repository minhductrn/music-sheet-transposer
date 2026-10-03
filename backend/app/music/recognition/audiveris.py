"""Audiveris CLI integration, isolated from the web and music model layers."""

from pathlib import Path
import os
import signal
import subprocess
import re

from app.core.config import Settings
from app.music.recognition.errors import RecognitionError
from app.music.recognition.mxl import read_mxl
from app.music.recognition.profiles import ProfileOptions, resolve_profile
from app.music.recognition.result import ProviderOutput, RecognitionIssue


class AudiverisProvider:
    def __init__(self, config: Settings):
        self.config = config

    def recognize(self, source: Path, output_directory: Path) -> bytes:
        return self.recognize_result(source, output_directory, resolve_profile(self.config)).musicxml

    def _check_languages(self, options: ProfileOptions) -> Path:
        # Resolve before isolating Audiveris's XDG directories. Explicit application
        # configuration wins, followed by Audiveris's own environment/default location.
        directory = self.config.audiveris_tessdata_path
        if directory is None:
            prefix = os.environ.get("TESSDATA_PREFIX")
            directory = Path(prefix) if prefix else (
                Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
                / "AudiverisLtd" / "audiveris" / "tessdata"
            )
        missing = []
        for language in options.ocr_languages.split("+"):
            try:
                with (directory / f"{language}.traineddata").open("rb") as stream:
                    if not stream.read(1):
                        missing.append(language)
            except OSError:
                missing.append(language)
        if missing:
            raise RecognitionError(
                f"Recognition OCR is unavailable: missing language data for {', '.join(missing)}. "
                "Install the required Tesseract models and configure AUDIVERIS_TESSDATA_PATH.",
                503, (RecognitionIssue(
                    "missing_ocr_languages", "Required OCR language data is unavailable.", "error",
                    details={"required_languages": options.ocr_languages.split("+"),
                             "missing_languages": missing},
                ),),
            )
        return directory.resolve()

    def build_command(self, source: Path, output_directory: Path, options: ProfileOptions) -> list[str]:
        command = [
            self.config.audiveris_executable, "-batch", "-transcribe", "-export", "-save",
        ]
        for key, value in options.constants().items():
            command.extend(["-constant", f"{key}={value}"])
        command.extend(["-output", str(output_directory), "--", str(source)])
        return command

    def recognize_result(
        self, source: Path, output_directory: Path, options: ProfileOptions,
    ) -> ProviderOutput:
        tessdata = self._check_languages(options)
        command = self.build_command(source, output_directory, options)
        environment = os.environ.copy()
        environment["TESSDATA_PREFIX"] = str(tessdata)
        # Keep engine caches, preferences and logs inside the disposable workspace.
        for kind in ("CONFIG", "DATA", "CACHE"):
            directory = source.parent / "runtime" / kind.lower()
            directory.mkdir(parents=True, exist_ok=True)
            environment[f"XDG_{kind}_HOME"] = str(directory)
        try:
            # No shell, no original upload filename, and no unbounded captured logs.
            process = subprocess.Popen(
                command, cwd=source.parent, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, start_new_session=True,
                env=environment,
            )
        except OSError as error:
            raise RecognitionError(
                "Recognition is unavailable. Configure an installed Audiveris executable.", 503
            ) from error
        try:
            code = process.wait(timeout=self.config.recognition_timeout_seconds)
        except subprocess.TimeoutExpired as error:
            # Terminate the launcher and JVM together before cleaning their workspace.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
            raise RecognitionError("Recognition timed out. Try fewer pages or a clearer scan.", 504) from error
        warnings = self._log_diagnostics(output_directory, source.parent / "runtime")
        if code != 0:
            raise RecognitionError("Recognition failed. Try a clearer sheet-music scan.", 502, (
                RecognitionIssue("provider_failed", "Audiveris did not complete recognition.", "error",
                                 details={"exit_code": code}),
            ))
        scores = [
            path for path in output_directory.rglob("*")
            if path.suffix.lower() in (".mxl", ".musicxml", ".xml") and not path.is_dir()
        ]
        if len(scores) != 1:
            raise RecognitionError(
                "Recognition must produce one score. Import each movement separately.", 502
            )
        try:
            self._check_output_path(scores[0], output_directory)
            musicxml = self._read_score(scores[0])
            omr, artifact_warnings = self._read_artifact(output_directory)
            return ProviderOutput(
                musicxml, "Audiveris", omr, warnings + artifact_warnings,
                {"input_quality": options.input_quality.value,
                 "ocr_languages": options.ocr_languages,
                 "small_heads_enabled": False, "small_beams_enabled": False},
            )
        except OSError as error:
            raise RecognitionError("Recognition produced an unreadable score.", 502) from error

    def _read_score(self, path: Path) -> bytes:
        limit = self.config.recognition_max_output_bytes
        if path.stat().st_size > limit:
            raise RecognitionError("Recognition output exceeds the size limit.", 502)
        if path.suffix.lower() != ".mxl":
            with path.open("rb") as stream:
                contents = stream.read(limit + 1)
            if len(contents) > limit:
                raise RecognitionError("Recognition output exceeds the size limit.", 502)
            return contents
        return read_mxl(
            path, max_bytes=limit,
            max_members=self.config.recognition_max_archive_members,
        )

    @staticmethod
    def _check_output_path(path: Path, directory: Path) -> None:
        if path.is_symlink() or not path.resolve().is_relative_to(directory.resolve()) or not path.is_file():
            raise RecognitionError("Recognition produced an unsafe output file.", 502)

    def _read_artifact(self, directory: Path) -> tuple[bytes | None, tuple[RecognitionIssue, ...]]:
        artifacts = list(directory.rglob("*.omr"))
        if len(artifacts) != 1:
            return None, (RecognitionIssue(
                "omr_artifact_unavailable", "One editable Audiveris project was not available to retain.",
            ),)
        path = artifacts[0]
        self._check_output_path(path, directory)
        limit = self.config.recognition_max_artifact_bytes
        if path.stat().st_size > limit:
            return None, (RecognitionIssue(
                "omr_artifact_too_large", "The Audiveris project exceeds the artifact limit and was not retained.",
            ),)
        with path.open("rb") as stream:
            contents = stream.read(limit + 1)
        if not contents or len(contents) > limit:
            return None, (RecognitionIssue("omr_artifact_unavailable", "The Audiveris project could not be retained."),)
        return contents, ()

    def _log_diagnostics(self, directory: Path, runtime: Path | None = None) -> tuple[RecognitionIssue, ...]:
        # Inspect a bounded tail, never return raw logs (they can contain private paths).
        remaining = self.config.recognition_max_log_bytes
        log = ""
        paths = [(path, directory) for path in sorted(directory.rglob("*.log"))]
        if runtime is not None:
            paths.extend((path, runtime) for path in sorted(runtime.rglob("*.log")))
        for path, root in paths[:8]:
            self._check_output_path(path, root)
            with path.open("rb") as stream:
                size = path.stat().st_size
                stream.seek(max(0, size - remaining))
                contents = stream.read(remaining)
            log += contents.decode("utf-8", errors="replace")
            remaining -= len(contents)
            if remaining == 0:
                break
        lowered = log.lower()
        if any(value in lowered for value in (
            "no language is available", "could not initialize tessbaseapi", "tesseract data could not be found",
            "error in loading local ocr languages", "error opening data file", "failed loading language",
            "collection of supported languages is empty", "missing support for",
        )):
            raise RecognitionError(
                "Audiveris could not initialize the configured OCR languages.", 503,
                (RecognitionIssue("ocr_initialization_failed", "OCR language initialization failed.", "error"),),
            )
        issues = []
        if "no correct rhythm" in lowered:
            issues.append(RecognitionIssue("provider_rhythm_warning", "Audiveris reported an unresolved measure rhythm."))
        if re.search(r"\berror\b", lowered):
            issues.append(RecognitionIssue("provider_error", "Audiveris reported recognition errors; inspect the retained project.", "error"))
        elif re.search(r"\bwarn\b", lowered):
            issues.append(RecognitionIssue("provider_warning", "Audiveris reported recognition warnings; inspect the retained project."))
        if not paths:
            issues.append(RecognitionIssue("provider_logs_unavailable", "Provider logs were unavailable; recognition warnings could not be inspected."))
        if remaining == 0 or len(paths) > 8:
            issues.append(RecognitionIssue("provider_logs_truncated", "Provider log inspection was limited; additional warnings may exist."))
        return tuple(issues)
