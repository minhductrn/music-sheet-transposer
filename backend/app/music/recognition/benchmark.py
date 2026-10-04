"""Local developer CLI: SMT is EXPERIMENTAL / BENCHMARK ONLY and requires SMT_ENABLED=true."""

import argparse
from collections import Counter
from dataclasses import asdict
from fractions import Fraction
from hashlib import sha256
from io import BytesIO
import json
import mimetypes
from pathlib import Path
import shutil
from time import perf_counter
from xml.etree import ElementTree as ET

from PIL import Image
from pypdf import PdfReader

from app.core.config import Settings
from app.music.recognition.errors import RecognitionError
from app.music.recognition.provider import create_provider
from app.music.recognition.result import RecognitionResult, SymbolicRecognitionResult
from app.music.recognition.service import MusicRecognitionService
from app.music.recognition.smt import SMTProvider
from app.music.recognition.symbolic import transcription_text


def musicxml_metrics(xml: bytes) -> dict:
    """Inspect already validated MusicXML, preserving original event references."""
    root = ET.fromstring(xml)
    namespace = root.tag.partition("}")[0] + "}" if root.tag.startswith("{") else ""
    def tag(name):
        return namespace + name

    def number(value):
        try:
            return Fraction(value) if value is not None else None
        except (ValueError, ZeroDivisionError):
            return None
    counts = Counter(notes=0, rests=0, chord_groups=0, chord_notes=0, grace_notes=0, simultaneous_events=0)
    keys, times, events, layout = [], [], [], set()
    measures_by_part = {}
    for part in root.findall(tag("part")):
        part_id = part.get("id")
        divisions = None
        measures = part.findall(tag("measure"))
        measures_by_part[part_id] = len(measures)
        for measure_index, measure in enumerate(measures):
            label = measure.get("number")
            reference = {"part": part_id, "measure": label, "measure_index": measure_index}
            cursor = Fraction(0)
            last_onset = None
            in_chord = False
            onsets = Counter()
            for child in measure:
                if child.tag == tag("attributes"):
                    value = child.findtext(tag("divisions"))
                    if value is not None:
                        parsed = number(value)
                        divisions = parsed if parsed is not None and parsed > 0 else None
                    for key in child.findall(tag("key")):
                        keys.append({**reference, "staff": key.get("number"),
                                     "fifths": key.findtext(tag("fifths")), "mode": key.findtext(tag("mode"))})
                    for meter in child.findall(tag("time")):
                        times.append({**reference, "staff": meter.get("number"),
                                      "beats": [e.text for e in meter.findall(tag("beats"))],
                                      "beat_types": [e.text for e in meter.findall(tag("beat-type"))]})
                elif child.tag == tag("print"):
                    if child.get("new-system") == "yes" or child.get("new-page") == "yes":
                        layout.add(measure_index)
                elif child.tag in {tag("backup"), tag("forward")}:
                    value = number(child.findtext(tag("duration")))
                    if cursor is not None and divisions and value is not None and value >= 0:
                        cursor += value / divisions * (-1 if child.tag == tag("backup") else 1)
                        if cursor < 0:
                            cursor = None
                    else:
                        cursor = None
                    last_onset = None
                elif child.tag == tag("note"):
                    chord = child.find(tag("chord")) is not None
                    grace = child.find(tag("grace")) is not None
                    rest = child.find(tag("rest")) is not None
                    pitch = child.find(tag("pitch"))
                    if pitch is not None:
                        counts["notes"] += 1
                    counts["rests"] += rest
                    counts["grace_notes"] += grace
                    counts["chord_notes"] += chord
                    if chord and not in_chord:
                        counts["chord_groups"] += 1
                    in_chord = chord
                    onset = last_onset if chord else cursor
                    value = number(child.findtext(tag("duration")))
                    duration = Fraction(0) if grace else value / divisions if value is not None and value >= 0 and divisions else None
                    event = {**reference, "kind": "note" if pitch is not None else "rest" if rest else "unpitched",
                             "voice": child.findtext(tag("voice")), "staff": child.findtext(tag("staff")),
                             "chord": chord, "grace": grace,
                             "onset_quarters": str(onset) if onset is not None else None,
                             "duration_quarters": str(duration) if duration is not None else None,
                             "lyrics": [e.text for e in child.findall(f'{tag("lyric")}/{tag("text")}')]}
                    if pitch is not None:
                        event["pitch"] = {name: pitch.findtext(tag(name)) for name in ("step", "alter", "octave")}
                        if onset is not None and not grace:
                            onsets[onset] += 1
                    events.append(event)
                    if not chord:
                        last_onset = onset
                        if duration is not None and cursor is not None:
                            cursor += duration
                        else:
                            cursor = None
            counts["simultaneous_events"] += sum(count > 1 for count in onsets.values())
    return {**counts, "measures_by_part": measures_by_part,
            "measures": sum(measures_by_part.values()),
            "system_count_from_layout": 1 + len(layout) if layout else None,
            "keys": keys, "time_signatures": times, "events": events,
            "scope": "MusicXML structure; missing layout cannot establish source system count."}


def run_benchmark(
    contents: bytes, filename: str, mime: str | None, config: Settings,
    *, providers: dict | None = None, boxes: list[dict] | None = None, prepare_only: bool = False,
) -> tuple[dict, dict[str, bytes]]:
    engines = providers if providers is not None else {
        "audiveris": create_provider(config, "audiveris"),
        "smt": SMTProvider(config, boxes=boxes, prepare_only=prepare_only),
    }
    source = {"filename": Path(filename).name, "sha256": sha256(contents).hexdigest(), "size_bytes": len(contents)}
    if contents.startswith(b"%PDF-"):
        try:
            source["page_count"] = len(PdfReader(BytesIO(contents), strict=True).pages)
        except Exception:
            source["page_count"] = None
    else:
        try:
            with Image.open(BytesIO(contents)) as image:
                source.update(page_count=1, original_dimensions=list(image.size))
        except OSError:
            source["page_count"] = None
    report, artifacts = {"version": 1, "source": source}, {}
    for name, provider in engines.items():
        if name not in {"audiveris", "smt"}:
            raise ValueError("Unknown benchmark provider.")
        started = perf_counter()
        try:
            result = MusicRecognitionService(provider, config).evaluate_result(contents, filename, mime)
            warnings = [asdict(issue) for issue in result.warnings]
            if isinstance(result, RecognitionResult):
                metrics = musicxml_metrics(result.musicxml)
                report[name] = {"success": True, "format": "musicxml", "provider": result.provider,
                                "metrics": metrics, "diagnostics": result.diagnostics, "warnings": warnings}
                artifacts[f"{name}/recognized.musicxml"] = result.musicxml
                if result.omr is not None:
                    artifacts[f"{name}/recognized.omr"] = result.omr
            elif isinstance(result, SymbolicRecognitionResult):
                report[name] = {**result.symbolic, "format": "symbolic", "provider": result.provider,
                                "diagnostics": result.diagnostics, "warnings": warnings}
                for system in result.symbolic["systems"]:
                    prefix = f'{name}/transcriptions/system-{system["index"]:04d}'
                    artifacts[prefix + ".tokens.json"] = json.dumps(system["raw_tokens"], ensure_ascii=False).encode()
                    artifacts[prefix + ".txt"] = transcription_text(system["raw_transcription"]).encode()
                    artifacts[prefix + ".parsed.json"] = json.dumps(system["parsed"], ensure_ascii=False).encode()
            artifacts.update({f"{name}/{key}": value for key, value in result.debug_artifacts.items()})
        except RecognitionError as error:
            report[name] = {"success": False, "error": str(error), "status_code": error.status_code,
                            "diagnostics": [asdict(issue) for issue in error.diagnostics]}
        except Exception:
            report[name] = {"success": False, "error": "Benchmark provider failed."}
        report[name]["recognition_duration_seconds"] = perf_counter() - started
    return report, artifacts


def write_debug(report: dict, artifacts: dict[str, bytes], output: Path, max_bytes: int) -> None:
    files = {**artifacts, "benchmark.json": json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False).encode()}
    if sum(len(contents) for contents in files.values()) > max_bytes:
        raise ValueError("Debug output exceeds the configured total byte limit.")
    for name in files:
        path = Path(name)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("Unsafe debug artifact name.")
    # Never overwrite an operator's existing benchmark or unrelated directory.
    output.mkdir(parents=True, exist_ok=False)
    try:
        for name, contents in files.items():
            path = output / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(contents)
    except Exception:
        shutil.rmtree(output)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="New local directory; existing directories are refused.")
    parser.add_argument("--providers", nargs="+", choices=["audiveris", "smt"], default=["audiveris", "smt"])
    parser.add_argument("--boxes", type=Path, help="Local JSON list of page/bbox records in rendered-page pixels.")
    parser.add_argument("--prepare-only", action="store_true", help="Render/crop SMT input without loading a model.")
    parser.add_argument("--max-debug-bytes", type=int, default=64 * 1024 * 1024)
    args = parser.parse_args()
    config = Settings()
    try:
        if args.max_debug_bytes <= 0 or args.source.stat().st_size > config.recognition_max_upload_bytes:
            raise ValueError("Invalid byte limit or oversized source.")
        boxes = None
        if args.boxes:
            if args.boxes.stat().st_size > 64 * 1024:
                raise ValueError("System box specification is oversized.")
            boxes = json.loads(args.boxes.read_text())
            if not isinstance(boxes, list):
                raise ValueError("System boxes must be a JSON list.")
        providers = {name: SMTProvider(config, boxes=boxes, prepare_only=args.prepare_only)
                     if name == "smt" else create_provider(config, name) for name in dict.fromkeys(args.providers)}
        report, artifacts = run_benchmark(args.source.read_bytes(), args.source.name,
                                         mimetypes.guess_type(args.source.name)[0], config, providers=providers)
        write_debug(report, artifacts, args.output, args.max_debug_bytes)
    except (OSError, ValueError) as error:
        parser.exit(2, f"Benchmark setup failed: {error}\n")
    print(json.dumps({"report": str(args.output / "benchmark.json"),
                      "success": {name: report[name]["success"] for name in providers}}))
    return int(any(not report[name]["success"] and not (
        name == "smt" and args.prepare_only and report[name].get("systems") and not report[name].get("error")
    ) for name in providers))


if __name__ == "__main__":
    raise SystemExit(main())
