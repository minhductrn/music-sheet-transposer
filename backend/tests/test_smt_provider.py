from io import BytesIO
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

from fastapi.testclient import TestClient
from PIL import Image
from pydantic import ValidationError
import pytest

from app.api.v1.recognize import get_recognition_service
from app.core.config import Settings
from app.main import app
from app.music.recognition.audiveris import AudiverisProvider
from app.music.recognition.errors import RecognitionError
from app.music.recognition.provider import MusicRecognitionProvider, create_provider
from app.music.recognition.result import SymbolicRecognitionResult
from app.music.recognition.service import MusicRecognitionService
from app.music.recognition.smt import SMTProvider


def png():
    stream = BytesIO()
    Image.new("RGB", (50, 50), "white").save(stream, format="PNG")
    return stream.getvalue()


def output():
    raw = ["**ekern_1.0", "<b>", "4a", "<s>", "4cc", "<b>", "*-"]
    return {"version": 1, "success": True, "model_reference": "antoniorv6/smt-grandstaff",
            "model_revision": Settings().smt_model_revision, "device": "cpu", "error": None,
            "pages": [{"page": 1, "image": "pages/page-0001.png", "dimensions": [50, 50], "dpi": None}],
            "systems": [{"index": 1, "page": 1, "bbox": [0, 0, 50, 50], "image": "systems/system-0001.png",
                         "segmentation": "manual", "success": True, "raw_tokens": raw,
                         "raw_transcription": "".join(raw), "duration_seconds": 0.1}], "warnings": []}


@pytest.fixture
def mocked_worker(monkeypatch, tmp_path):
    config = Settings(smt_enabled=True, smt_worker_python=tmp_path / "separate-python", smt_upstream_path=tmp_path / "upstream")
    data, calls = output(), []
    class Process:
        pid = 12345
        def __init__(self, command, **kwargs):
            request_path = Path(command[-1])
            calls.append((command, kwargs, json.loads(request_path.read_text())))
            directory = request_path.parent
            (directory / "result.json").write_text(json.dumps(data))
            for name in ("pages/page-0001.png", "systems/system-0001.png"):
                path = directory / name
                path.parent.mkdir(exist_ok=True)
                path.write_bytes(png())
        def wait(self, timeout=None):
            return 0
    monkeypatch.setattr(subprocess, "Popen", Process)
    return SMTProvider(config), data, calls, Process


def test_provider_selection_and_protocol(monkeypatch):
    monkeypatch.delenv("SMT_ENABLED", raising=False)
    monkeypatch.delenv("RECOGNITION_PROVIDER", raising=False)
    config = Settings()
    assert config.smt_enabled is False
    assert config.recognition_provider == "audiveris"
    assert isinstance(create_provider(config), AudiverisProvider)
    enabled = Settings(smt_enabled=True, recognition_provider="smt")
    assert isinstance(create_provider(enabled), SMTProvider)
    assert isinstance(create_provider(enabled), MusicRecognitionProvider)
    assert isinstance(AudiverisProvider(config), MusicRecognitionProvider)
    with pytest.raises(ValueError):
        create_provider(config, "unknown")
    assert "torch" not in sys.modules


@pytest.mark.parametrize("values", [{"recognition_provider": "remote"}, {"smt_device": "gpu"},
    {"smt_pdf_dpi": 0}, {"smt_pdf_dpi": 601}, {"smt_staves_per_system": 3},
    {"smt_timeout_seconds": 0}, {"smt_max_systems": 129}, {"smt_model_reference": "/private/model"}])
def test_invalid_smt_configuration(values):
    with pytest.raises(ValidationError):
        Settings(**values)


def test_environment_configuration(monkeypatch):
    monkeypatch.setenv("SMT_ENABLED", "true")
    monkeypatch.setenv("SMT_DEVICE", "cpu")
    monkeypatch.setenv("SMT_MODEL_REFERENCE", "antoniorv6/smt-camera-grandstaff")
    monkeypatch.setenv("SMT_MODEL_REVISION", "explicit-revision")
    monkeypatch.setenv("RECOGNITION_PROVIDER", "smt")
    config = Settings()
    assert config.smt_enabled is True
    assert config.smt_device == "cpu"
    assert config.smt_model_revision == "explicit-revision"
    assert config.recognition_provider == "smt"


def test_unconfigured_worker_is_explicit_and_retry_cleans_workspace():
    config = Settings(smt_enabled=True)
    service = MusicRecognitionService(SMTProvider(config), config)
    for _ in range(2):
        with pytest.raises(RecognitionError) as caught:
            service.evaluate_result(png(), "score.png", "image/png")
        assert caught.value.status_code == 503
        assert caught.value.diagnostics[0].code == "smt_unconfigured"


def test_audiveris_startup_and_recognition_without_smt_runtime():
    # A fresh interpreter proves default startup never even imports SMT or its runtime.
    script = '''
import importlib.abc
from pathlib import Path
import sys
sys.path.insert(0, sys.argv[1])
class RejectSMT(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        blocked = ("app.music.recognition.smt", "smt_worker", "torch", "torchvision",
                   "transformers", "huggingface_hub", "safetensors", "pypdfium2")
        if any(fullname == name or fullname.startswith(name + ".") for name in blocked):
            raise AssertionError("Normal recognition imported SMT: " + fullname)
sys.meta_path.insert(0, RejectSMT())
from app.main import app
from app.api.v1.recognize import get_recognition_service
from app.music.recognition.audiveris import AudiverisProvider
from app.music.recognition.errors import RecognitionError
from app.music.recognition.result import ProviderOutput
service = get_recognition_service()
assert isinstance(service.provider, AudiverisProvider)
assert not service.config.smt_enabled
assert service.config.smt_worker_python is None and service.config.smt_upstream_path is None
assert "/api/v1/recognize" in app.openapi()["paths"]
xml = (Path(sys.argv[1]) / "tests/music/fixtures/simple_score.musicxml").read_bytes()
contents = sys.stdin.buffer.read()
service.provider.recognize_result = lambda *_: ProviderOutput(xml, "Audiveris")
result = service.recognize_result(contents, "score.png", "image/png")
assert result.provider == "Audiveris" and result.musicxml == xml
def failed(*_):
    raise RecognitionError("Audiveris unavailable.", 503)
service.provider.recognize_result = failed
try:
    service.recognize_result(contents, "score.png", "image/png")
except RecognitionError as error:
    assert error.status_code == 503 and str(error) == "Audiveris unavailable."
else:
    raise AssertionError("Audiveris failure must not fall back to SMT.")
'''
    environment = dict(os.environ)
    for key in ("SMT_ENABLED", "RECOGNITION_PROVIDER", "SMT_WORKER_PYTHON", "SMT_UPSTREAM_PATH", "PYTHONPATH", "PYTHONHOME"):
        environment.pop(key, None)
    result = subprocess.run([sys.executable, "-I", "-c", script, str(Path(__file__).resolve().parents[1])],
                            env=environment, input=png(), capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr.decode()


@pytest.mark.parametrize("prepare_only", [False, True])
def test_disabled_smt_returns_structured_error_without_starting_worker(monkeypatch, tmp_path, prepare_only):
    monkeypatch.delenv("SMT_ENABLED", raising=False)
    config = Settings(recognition_provider="smt", smt_worker_python=tmp_path / "python", smt_upstream_path=tmp_path)
    provider = SMTProvider(config, prepare_only=True) if prepare_only else create_provider(config)
    def unexpected_worker(*args, **kwargs):
        raise AssertionError("Disabled SMT must not start a worker.")
    monkeypatch.setattr(subprocess, "Popen", unexpected_worker)
    service = MusicRecognitionService(provider, config)
    app.dependency_overrides[get_recognition_service] = lambda: service
    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/recognize", files={"file": ("score.png", png(), "image/png")})
        assert response.status_code == 503
        assert response.json()["diagnostics"][0]["code"] == "smt_disabled"
        assert "SMT_ENABLED=true" in response.json()["detail"]
        assert response.headers["cache-control"] == "no-store"
    finally:
        app.dependency_overrides.pop(get_recognition_service, None)


def test_explicitly_enabled_smt_benchmark_uses_isolated_worker(mocked_worker):
    from app.music.recognition.benchmark import run_benchmark
    provider, _, calls, _ = mocked_worker
    assert provider.config.smt_enabled is True
    report, artifacts = run_benchmark(png(), "score.png", "image/png", provider.config,
                                     providers={"smt": create_provider(provider.config, "smt")})
    assert report["smt"]["success"] is True
    assert report["smt"]["systems"][0]["raw_tokens"]
    assert "smt/transcriptions/system-0001.tokens.json" in artifacts
    assert len(calls) == 1


def test_isolated_invocation_raw_evidence_and_cleanup(mocked_worker, monkeypatch):
    provider, _, calls, _ = mocked_worker
    monkeypatch.setenv("PYTHONPATH", "/private/ROS")
    result = MusicRecognitionService(provider, provider.config).evaluate_result(png(), "score.png", "image/png")
    command, kwargs, request = calls[0]
    assert command[1] == "-I"
    assert Path(command[2]).name == "worker.py"
    assert kwargs["start_new_session"] is True
    assert "shell" not in kwargs
    assert "PYTHONPATH" not in kwargs["env"]
    assert kwargs["env"]["HF_HUB_OFFLINE"] == "1"
    assert request["model_reference"] == "antoniorv6/smt-grandstaff"
    assert request["dpi"] == 200
    assert isinstance(result, SymbolicRecognitionResult)
    assert result.symbolic["device"] == "cpu"
    assert result.symbolic["systems"][0]["parsed"]["metrics"]["chord_groups"] == 1
    assert result.symbolic["systems"][0]["raw_tokens"]
    assert len(result.debug_artifacts) == 2
    assert not Path(request["source"]).parent.exists()
    assert request["source"] not in json.dumps(result.symbolic)


def test_musicxml_api_refuses_symbolic_output_without_fabrication(mocked_worker):
    provider, _, calls, _ = mocked_worker
    service = MusicRecognitionService(provider, provider.config)
    app.dependency_overrides[get_recognition_service] = lambda: service
    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/recognize", files={"file": ("score.png", png(), "image/png")})
        assert response.status_code == 422
        assert response.json()["diagnostics"][0]["code"] == "musicxml_unavailable"
        assert "<score-partwise" not in response.text
        assert not Path(calls[0][2]["source"]).exists()
    finally:
        app.dependency_overrides.pop(get_recognition_service, None)


@pytest.mark.parametrize("mutation", ["bad_model", "path", "box", "raw", "empty", "nan", "oversized", "missing_image"])
def test_malformed_or_unsafe_worker_output(mocked_worker, mutation):
    provider, data, _, _ = mocked_worker
    if mutation == "bad_model":
        data["model_reference"] = "unexpected/model"
    elif mutation == "path":
        data["pages"][0]["image"] = "../../private.png"
    elif mutation == "box":
        data["systems"][0]["bbox"][2] = 51
    elif mutation == "raw":
        data["systems"][0]["raw_tokens"] = [7]
    elif mutation == "empty":
        data["systems"][0].update(raw_tokens=[], raw_transcription="")
    elif mutation == "nan":
        data["systems"][0]["duration_seconds"] = float("nan")
    elif mutation == "oversized":
        provider.config.recognition_max_output_bytes = 20
    elif mutation == "missing_image":
        data["pages"][0]["dimensions"] = [49, 50]
    with pytest.raises(RecognitionError) as caught:
        MusicRecognitionService(provider, provider.config).evaluate_result(png(), "score.png", "image/png")
    assert caught.value.status_code == 502


def test_partial_parsing_keeps_raw_evidence(mocked_worker):
    provider, data, _, _ = mocked_worker
    system = data["systems"][0]
    system["raw_tokens"] = ["**ekern_1.0", "<b>", "4c", "<b>", "unsupported", "<b>", "4d"]
    system["raw_transcription"] = "".join(system["raw_tokens"])
    result = MusicRecognitionService(provider, provider.config).evaluate_result(png(), "score.png", "image/png")
    assert result.symbolic["systems"][0]["raw_tokens"] == system["raw_tokens"]
    assert result.symbolic["parsing_summary"]["coverage"] < 1
    assert result.symbolic["parsing_summary"]["metrics"]["notes"] == 2


def test_timeout_kills_process_group_and_retains_partial_result(mocked_worker, monkeypatch):
    provider, data, calls, process = mocked_worker
    data["success"] = False
    killed = []
    def wait(self, timeout=None):
        if timeout is not None:
            raise subprocess.TimeoutExpired("smt", timeout)
        return -9
    monkeypatch.setattr(process, "wait", wait)
    monkeypatch.setattr("os.killpg", lambda pid, sig: killed.append((pid, sig)))
    result = MusicRecognitionService(provider, provider.config).evaluate_result(png(), "score.png", "image/png")
    assert killed == [(12345, signal.SIGKILL)]
    assert result.symbolic["error"] == "worker_timeout"
    assert result.symbolic["systems"][0]["raw_tokens"]
    assert not Path(calls[0][2]["source"]).exists()


def test_failure_without_result_and_timeout_without_result(monkeypatch, tmp_path):
    provider = SMTProvider(Settings(smt_enabled=True, smt_worker_python=tmp_path / "python", smt_upstream_path=tmp_path))
    class Failed:
        pid = 12
        def __init__(self, *args, **kwargs):
            pass
        def wait(self, timeout=None):
            return 1
    monkeypatch.setattr(subprocess, "Popen", Failed)
    service = MusicRecognitionService(provider, provider.config)
    with pytest.raises(RecognitionError) as caught:
        service.evaluate_result(png(), "score.png", "image/png")
    assert caught.value.diagnostics[0].code == "worker_failed"
    def timed_out(self, timeout=None):
        if timeout:
            raise subprocess.TimeoutExpired("smt", timeout)
        return -9
    monkeypatch.setattr(Failed, "wait", timed_out)
    monkeypatch.setattr("os.killpg", lambda *_: None)
    with pytest.raises(RecognitionError) as caught:
        service.evaluate_result(png(), "score.png", "image/png")
    assert caught.value.status_code == 504


def test_missing_worker_executable(monkeypatch, tmp_path):
    def unavailable(*_, **kwargs):
        raise FileNotFoundError("/private/python")
    monkeypatch.setattr(subprocess, "Popen", unavailable)
    config = Settings(smt_enabled=True, smt_worker_python=tmp_path / "missing", smt_upstream_path=tmp_path)
    service = MusicRecognitionService(SMTProvider(config), config)
    with pytest.raises(RecognitionError) as caught:
        service.evaluate_result(png(), "score.png", "image/png")
    assert caught.value.status_code == 503
    assert "/private" not in str(caught.value)


def test_debug_artifact_limit(mocked_worker):
    provider, _, _, _ = mocked_worker
    provider.config.recognition_max_artifact_bytes = 1
    with pytest.raises(RecognitionError):
        MusicRecognitionService(provider, provider.config).evaluate_result(png(), "score.png", "image/png")


def test_debug_symlinks_are_rejected(tmp_path):
    provider = SMTProvider(Settings())
    (tmp_path / "pages").symlink_to(tmp_path.parent)
    with pytest.raises(RecognitionError, match="unsafe"):
        provider._artifacts(tmp_path)
