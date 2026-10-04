from io import BytesIO
import json
from pathlib import Path

from PIL import Image
import pytest

from app.core.config import Settings
from app.music.recognition.benchmark import main, musicxml_metrics, run_benchmark, write_debug
from app.music.recognition.errors import RecognitionError
from app.music.recognition.result import ProviderOutput


XML = (Path(__file__).parent / "music/fixtures/simple_score.musicxml").read_bytes()


def png():
    stream = BytesIO()
    Image.new("RGB", (20, 10), "white").save(stream, format="PNG")
    return stream.getvalue()


class Provider:
    def __init__(self, output=None, error=None):
        self.output, self.error, self.workspace = output, error, None
    def recognize_result(self, source, directory, options):
        self.workspace = source.parent
        if self.error:
            raise self.error
        return self.output


def symbolic_output():
    return ProviderOutput(None, "SMT", symbolic={
        "success": True, "model_reference": "antoniorv6/smt-grandstaff", "device": "cpu",
        "systems": [{"index": 1, "raw_tokens": ["4c"], "raw_transcription": "4c", "parsed": {"events": []}}],
    }, debug_artifacts={"pages/page-0001.png": png()})


def test_benchmark_keeps_independent_results_and_artifacts():
    providers = {"audiveris": Provider(ProviderOutput(XML, "Audiveris")), "smt": Provider(symbolic_output())}
    report, artifacts = run_benchmark(png(), "/private/score.png", "image/png", Settings(), providers=providers)
    assert report["source"]["filename"] == "score.png"
    assert report["source"]["page_count"] == 1
    assert report["audiveris"]["success"] is True
    assert report["audiveris"]["diagnostics"]["counts"]["pitched_notes"] > 0
    assert report["smt"]["device"] == "cpu"
    assert report["smt"]["systems"][0]["raw_transcription"] == "4c"
    assert artifacts["audiveris/recognized.musicxml"] == XML
    assert artifacts["smt/transcriptions/system-0001.tokens.json"] == b'["4c"]'
    assert artifacts["smt/pages/page-0001.png"] == png()
    assert "/private" not in json.dumps(report)
    assert "accuracy" not in report
    assert all(not provider.workspace.exists() for provider in providers.values())


@pytest.mark.parametrize("failed", ["audiveris", "smt"])
def test_one_engine_failure_does_not_prevent_the_other(failed):
    providers = {"audiveris": Provider(ProviderOutput(XML, "Audiveris")), "smt": Provider(symbolic_output())}
    providers[failed].error = RecognitionError("Engine unavailable.", 503)
    report, _ = run_benchmark(png(), "score.png", "image/png", Settings(), providers=providers)
    assert report[failed]["success"] is False
    assert report[failed]["status_code"] == 503
    assert report["smt" if failed == "audiveris" else "audiveris"]["success"] is True
    assert all(not provider.workspace.exists() for provider in providers.values())


def test_musicxml_metrics_include_real_timing_chords_lyrics_and_signatures():
    xml = b'''<score-partwise><part id="P1"><measure number="1"><attributes>
    <divisions>2</divisions><key><fifths>-1</fifths></key><time><beats>2</beats><beat-type>4</beat-type></time>
    </attributes><note><pitch><step>A</step><octave>4</octave></pitch><duration>1</duration><lyric><text>ta</text></lyric></note>
    <note><chord/><pitch><step>C</step><octave>5</octave></pitch><duration>1</duration></note>
    <backup><duration>1</duration></backup><note><pitch><step>F</step><octave>3</octave></pitch><duration>1</duration></note>
    <forward><duration>1</duration></forward><note><rest/><duration>2</duration></note></measure></part></score-partwise>'''
    metrics = musicxml_metrics(xml)
    assert metrics["notes"] == 3
    assert metrics["chord_groups"] == metrics["chord_notes"] == 1
    assert metrics["simultaneous_events"] == 1
    assert metrics["rests"] == 1
    assert metrics["keys"][0]["fifths"] == "-1"
    assert metrics["time_signatures"][0]["beats"] == ["2"]
    assert metrics["events"][0]["lyrics"] == ["ta"]
    assert [event["onset_quarters"] for event in metrics["events"]] == ["0", "0", "0", "1"]
    assert metrics["system_count_from_layout"] is None


def test_debug_output_is_bounded_safe_and_never_overwrites(tmp_path):
    target = tmp_path / "results"
    with pytest.raises(ValueError, match="byte limit"):
        write_debug({}, {"safe.txt": b"123"}, target, 1)
    assert not target.exists()
    with pytest.raises(ValueError, match="Unsafe"):
        write_debug({}, {"../private": b"secret"}, target, 100)
    write_debug({"success": True}, {"smt/raw.txt": b"4c"}, target, 1000)
    assert (target / "smt/raw.txt").read_bytes() == b"4c"
    assert json.loads((target / "benchmark.json").read_text())["success"] is True
    with pytest.raises(FileExistsError):
        write_debug({}, {}, target, 1000)
    assert (target / "smt/raw.txt").read_bytes() == b"4c"


def test_cli_uses_explicit_source_and_returns_failure_report(monkeypatch, tmp_path, capsys):
    source = tmp_path / "score.png"
    source.write_bytes(png())
    provider = Provider(error=RecognitionError("Unavailable.", 503))
    monkeypatch.setattr("app.music.recognition.benchmark.create_provider", lambda *_: provider)
    monkeypatch.setattr("sys.argv", ["benchmark", "--source", str(source), "--output", str(tmp_path / "results"),
                                      "--providers", "audiveris"])
    assert main() == 1
    result = json.loads((tmp_path / "results/benchmark.json").read_text())
    assert result["audiveris"]["success"] is False
    assert "benchmark.json" in capsys.readouterr().out


@pytest.mark.parametrize("error", [None, "artifact_limit"])
def test_cli_prepare_only_reports_prepared_not_recognized(monkeypatch, tmp_path, error):
    source = tmp_path / "score.png"
    source.write_bytes(png())
    output = symbolic_output()
    output.symbolic["success"] = False
    output.symbolic["error"] = error
    monkeypatch.setattr("app.music.recognition.benchmark.SMTProvider", lambda *_, **kwargs: Provider(output))
    monkeypatch.setattr("sys.argv", ["benchmark", "--source", str(source), "--output", str(tmp_path / "results"),
                                      "--providers", "smt", "--prepare-only"])
    assert main() == int(error is not None)
    assert not json.loads((tmp_path / "results/benchmark.json").read_text())["smt"]["success"]


def test_symbolic_output_cannot_bypass_native_output_bound():
    provider = Provider(symbolic_output())
    config = Settings(recognition_max_output_bytes=1)
    report, artifacts = run_benchmark(png(), "score.png", "image/png", config, providers={"smt": provider})
    assert report["smt"]["success"] is False
    assert artifacts == {}
    assert not provider.workspace.exists()


@pytest.mark.parametrize("invalid", [float("nan"), object()])
def test_invalid_symbolic_values_are_sanitized_and_cleaned(invalid):
    provider = Provider(ProviderOutput(None, "SMT", symbolic={"invalid": invalid}))
    report, _ = run_benchmark(png(), "score.png", "image/png", Settings(), providers={"smt": provider})
    assert report["smt"]["success"] is False
    assert report["smt"]["status_code"] == 502
    assert not provider.workspace.exists()


def test_invalid_musicxml_timing_keeps_structural_counts_without_guessed_onsets():
    xml = b'''<score-partwise><part id="P"><measure number="1"><attributes><divisions>bad</divisions></attributes>
    <note><pitch><step>C</step><octave>4</octave></pitch><duration>bad</duration></note>
    <backup><duration>2</duration></backup><note><rest/><duration>1</duration></note>
    </measure></part></score-partwise>'''
    metrics = musicxml_metrics(xml)
    assert metrics["notes"] == metrics["rests"] == 1
    assert all(event["duration_quarters"] is None for event in metrics["events"])
    assert metrics["events"][1]["onset_quarters"] is None
