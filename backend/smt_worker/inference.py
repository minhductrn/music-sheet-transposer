"""Official SMT inference adapter; imported inside an isolated interpreter."""

from pathlib import Path
import sys


def select_device(requested: str, cuda_available: bool) -> str:
    if requested == "auto":
        return "cuda" if cuda_available else "cpu"
    if requested == "cuda" and not cuda_available:
        raise ValueError("cuda_unavailable")
    if requested not in {"cpu", "cuda"}:
        raise ValueError("invalid_device")
    return requested


def load_model(request: dict):
    import torch

    upstream = Path(request["upstream_path"])
    if not (upstream / "smt_model/modeling_smt.py").is_file():
        raise ValueError("upstream_unavailable")
    sys.path.insert(0, str(upstream))
    from smt_model import SMTModelForCausalLM

    device = select_device(request["device"], torch.cuda.is_available())
    request["_selected_device"] = device
    torch.set_num_threads(request["cpu_threads"])
    torch.manual_seed(0)
    model, loading = SMTModelForCausalLM.from_pretrained(
        request["model_reference"], revision=request["model_revision"],
        local_files_only=True, use_safetensors=True, output_loading_info=True,
    )
    if any(loading.get(key) for key in ("missing_keys", "unexpected_keys", "mismatched_keys", "error_msgs")):
        raise ValueError("checkpoint_mismatch")
    model.eval().to(device)
    return model, device


def predict(model, device: str, image):
    import numpy as np
    import torch
    from torchvision.transforms import Compose, Grayscale, ToPILImage, ToTensor
    from PIL import Image

    original = image.size
    # Respect the checkpoint's positional-encoding limits, maintaining aspect ratio.
    scale = min(1.0, model.config.maxw / image.width, model.config.maxh / image.height)
    size = (int(image.width * scale), int(image.height * scale))
    if min(size) < 16:
        raise ValueError("input_too_small")
    if size != original:
        image = image.resize(size, Image.Resampling.LANCZOS)
    # Same deterministic conversion as upstream convert_img_to_tensor; no augmentation.
    tensor = Compose([ToPILImage(), Grayscale(), ToTensor()])(np.asarray(image))
    with torch.inference_mode():
        tokens, _ = model.predict(tensor.unsqueeze(0).to(device), convert_to_str=True)
    if not isinstance(tokens, list) or any(not isinstance(token, str) for token in tokens):
        raise ValueError("invalid_prediction")
    return tokens, {"inference_dimensions": list(size), "resize_scale": scale,
                   "at_token_limit": len(tokens) >= model.maxlen - 1}
