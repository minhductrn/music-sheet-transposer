"""One bounded local job per invocation. No network downloads during inference."""

import json
import os
from pathlib import Path
import sys
from time import perf_counter

if __package__:
    from .preparation import prepare
    from .inference import load_model, predict
else:
    # -I removes the script directory. Add only this trusted directory.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from preparation import prepare
    from inference import load_model, predict
from PIL import Image


def save_result(path: Path, result: dict, limit: int) -> None:
    contents = json.dumps(result, ensure_ascii=False, allow_nan=False).encode("utf-8")
    if len(contents) > limit:
        raise ValueError("output_limit")
    temporary = path.with_suffix(".tmp")
    temporary.write_bytes(contents)
    temporary.replace(path)


def run(request: dict, output: Path, loader=load_model, predictor=predict) -> int:
    result = {
        "version": 1, "success": False, "model_reference": request["model_reference"],
        "model_revision": request["model_revision"], "device": None,
        "pages": [], "systems": [], "warnings": [], "error": None,
    }
    path = output / "result.json"
    limit = request["max_output_bytes"]
    stage = "preparation_failed"
    try:
        prepare(Path(request["source"]), request, output, result)
        save_result(path, result, limit)
        if request["prepare_only"]:
            result["warnings"].append("inference_not_run")
            save_result(path, result, limit)
            return 0
        stage = "model_load_failed"
        model, result["device"] = loader(request)
        save_result(path, result, limit)
        stage = "inference_failed"
        for system in result["systems"]:
            started = perf_counter()
            try:
                with Image.open(output / system["image"]) as image:
                    tokens, metadata = predictor(model, result["device"], image)
                system.update(metadata)
                system["raw_tokens"] = tokens
                system["raw_transcription"] = "".join(tokens)
                system["success"] = True
            except Exception:
                system["error"] = "inference_failed"
            finally:
                system["duration_seconds"] = perf_counter() - started
                save_result(path, result, limit)
        result["success"] = all(system["success"] for system in result["systems"])
        if not result["success"]:
            result["error"] = "inference_failed"
    except Exception as error:
        # Fixed codes only: raw exceptions can contain host paths or credentials.
        known = {"artifact_limit", "page_limit", "image_limit", "no_staff_systems",
                 "invalid_system_boxes", "duplicate_system_box", "checkpoint_mismatch",
                 "cuda_unavailable", "upstream_unavailable", "output_limit"}
        result["error"] = str(error) if str(error) in known else stage
        result["device"] = request.get("_selected_device", result["device"])
    save_result(path, result, limit)
    return 0 if result["success"] else 1


def main() -> int:
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    request_path = Path(sys.argv[1])
    request = json.loads(request_path.read_text())
    return run(request, request_path.parent)


if __name__ == "__main__":
    raise SystemExit(main())
