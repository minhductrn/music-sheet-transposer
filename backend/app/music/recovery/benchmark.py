"""Local Audiveris-only benchmark: baseline, evidence, decisions and corrected XML."""

import argparse
from dataclasses import asdict
from hashlib import sha256
import json
import mimetypes
from pathlib import Path
import shutil
from time import perf_counter

from app.core.config import Settings
from app.music.recognition.audiveris import AudiverisProvider
from app.music.recognition.errors import RecognitionError
from app.music.recognition.service import MusicRecognitionService
from app.music.recovery.musicxml import XmlContext, rhythm
from app.music.review.document import Document, ReviewError
from app.music.review.patcher import group


def metrics(xml):
    context = XmlContext(Document.parse(xml))
    doc = context.document
    notes = [x for x in context.events.values() if x.event.kind == "note"]
    return {"pitched_notes": len(notes), "rests": sum(x.event.kind == "rest" for x in context.events.values()),
            "measures": len(context.measures), "chord_groups": len({x.event.chord_id for x in notes if x.event.chord_id}),
            "grace_notes": sum(x.event.grace for x in notes),
            "small_display_notes": sum(x.event.display_size == "small" for x in notes),
            "ties": sum(len(doc.children(x.node, "tie")) for x in notes),
            "slurs": sum(len(x.node.findall(f'{doc.namespace}notations/{doc.namespace}slur')) for x in notes),
            "rhythm": rhythm(context)}


def lyric_locations(xml):
    """Benchmark reporting only. No lyric text enters production recovery logic."""
    context = XmlContext(Document.parse(xml))
    doc = context.document
    result = {word: [] for word in ("ta", "cùng", "đem")}
    for lyric in context.score.lyrics:
        word = lyric["text"].strip().casefold()
        if word not in result:
            continue
        event = context.events[lyric["event_id"]]
        members = group(doc, event.node)
        result[word].append({"measure": event.measure.number, "onset": event.event.onset,
                             "voice": event.event.voice, "staff": event.event.staff,
                             "notes": [asdict(x.event) for x in context.events.values() if x.node in members]})
    return result


def run(source: Path, config: Settings):
    class Capture:
        def __init__(self):
            self.provider, self.output = AudiverisProvider(config), None
        def recognize_result(self, *args):
            self.output = self.provider.recognize_result(*args)
            return self.output
    if source.stat().st_size > config.recognition_max_upload_bytes:
        raise ValueError("Benchmark source exceeds the upload limit.")
    contents = source.read_bytes()
    provider = Capture()
    started = perf_counter()
    result = MusicRecognitionService(provider, config).recognize_result(contents, source.name, mimetypes.guess_type(source.name)[0])
    baseline = provider.output
    recovery = result.diagnostics.get("semantic_recovery", {})
    report = {"source": {"filename": source.name, "sha256": sha256(contents).hexdigest()},
              "duration_seconds": perf_counter() - started, "provider_metadata": baseline.metadata,
              "A_baseline": metrics(baseline.musicxml), "B_evidence": recovery.get("evidence", []),
              "C_candidates": recovery.get("candidates", []),
              "D_auto_recovered": [c for c in recovery.get("candidates", []) if c["state"] == "AUTO_RECOVERED"],
              "E_review_required": [c for c in recovery.get("candidates", []) if c["state"] == "REVIEW_REQUIRED"],
              "F_corrected": metrics(result.musicxml), "recovery": recovery,
              "baseline_locations": lyric_locations(baseline.musicxml), "corrected_locations": lyric_locations(result.musicxml),
              "warnings": [asdict(warning) for warning in result.warnings]}
    artifacts = {"source" + source.suffix.lower(): contents, "baseline.musicxml": baseline.musicxml,
                 "corrected.musicxml": result.musicxml}
    if baseline.omr:
        artifacts["baseline.omr"] = baseline.omr
    if baseline.evidence_omr:
        artifacts["analysis.omr"] = baseline.evidence_omr
    return report, artifacts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="New local directory, never overwritten.")
    parser.add_argument("--analysis-pass", action="store_true", help="Explicitly enable a second bounded Audiveris LINKS pass; no export.")
    args = parser.parse_args()
    try:
        if args.output.exists():
            raise ValueError("Benchmark output already exists.")
        config = Settings()
        if args.analysis_pass:
            config = config.model_copy(update={"audiveris_semantic_analysis_enabled": True})
        report, artifacts = run(args.source, config)
        artifacts["benchmark.json"] = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False).encode()
        if sum(map(len, artifacts.values())) > 64 * 1024 * 1024:
            raise ValueError("Benchmark artifacts exceed 64 MiB.")
        args.output.mkdir(parents=True, exist_ok=False)
        try:
            for name, contents in artifacts.items():
                (args.output / name).write_bytes(contents)
        except OSError:
            shutil.rmtree(args.output)
            raise
    except (OSError, ValueError, RecognitionError, ReviewError) as error:
        parser.exit(2, f"Semantic benchmark failed: {error}\n")
    print(json.dumps({"report": str(args.output / "benchmark.json"),
                      "baseline_notes": report["A_baseline"]["pitched_notes"],
                      "corrected_notes": report["F_corrected"]["pitched_notes"],
                      "auto_recovered": len(report["D_auto_recovered"]),
                      "review_required": len(report["E_review_required"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
