"""Optional TurboQuant/HuggingFace helper utilities.

Kree currently runs on Gemini, so this module stays dependency-light and only
prepares filesystem and environment state for future HF-style model workflows.
"""

from __future__ import annotations

import importlib.util
import os
import platform
import sys
from pathlib import Path
from typing import Any


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = get_base_dir()
TURBOQUANT_DIR = BASE_DIR / "config" / "turboquant"


def _module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _safe_model_slug(model_id: str) -> str:
    raw = str(model_id or "").strip()
    if not raw:
        return "default-model"
    slug = []
    for char in raw:
        if char.isalnum() or char in {"-", "_", "."}:
            slug.append(char)
        else:
            slug.append("-")
    return "".join(slug).strip("-_.") or "default-model"


def _cache_root(cache_root: str | None = None) -> Path:
    if cache_root and str(cache_root).strip():
        return Path(cache_root).expanduser().resolve()
    env_root = os.environ.get("KREE_TQ_CACHE_ROOT", "").strip()
    if env_root:
        return Path(env_root).expanduser().resolve()
    return TURBOQUANT_DIR


def _cache_paths(model_id: str = "", cache_root: str | None = None) -> dict[str, str]:
    root = _cache_root(cache_root)
    model_slug = _safe_model_slug(model_id)
    hf_home = root / "hf"
    hub_cache = hf_home / "hub"
    transformers_cache = hf_home / "transformers"
    turboquant_cache = root / "models" / model_slug
    return {
        "cache_root": str(root),
        "hf_home": str(hf_home),
        "hub_cache": str(hub_cache),
        "transformers_cache": str(transformers_cache),
        "turboquant_cache": str(turboquant_cache),
    }


def detect_support(model_id: str = "", cache_root: str | None = None) -> dict[str, Any]:
    paths = _cache_paths(model_id, cache_root)
    cuda_available = False
    if _module_available("torch"):
        try:
            import torch  # type: ignore[import]

            cuda_available = bool(getattr(torch.cuda, "is_available", lambda: False)())
        except Exception:
            cuda_available = False

    return {
        "turboquant_available": _module_available("turboquant"),
        "transformers_available": _module_available("transformers"),
        "torch_available": _module_available("torch"),
        "cuda_available": cuda_available,
        "platform": platform.system(),
        "app_mode": "gemini-runtime",
        "model_id": model_id or "",
        "paths": paths,
    }


def prepare_cache(model_id: str = "", cache_root: str | None = None) -> dict[str, Any]:
    paths = _cache_paths(model_id, cache_root)
    for path_value in paths.values():
        Path(path_value).mkdir(parents=True, exist_ok=True)

    state = detect_support(model_id, cache_root)
    state.update({
        "prepared": True,
        "paths": paths,
        "notes": (
            "Cache directories prepared for a future HuggingFace/TurboQuant model path. "
            "No model weights are loaded by this helper."
        ),
    })
    return state


def build_environment(model_id: str = "", cache_root: str | None = None) -> dict[str, Any]:
    paths = _cache_paths(model_id, cache_root)
    env = {
        "HF_HOME": paths["hf_home"],
        "HUGGINGFACE_HUB_CACHE": paths["hub_cache"],
        "TRANSFORMERS_CACHE": paths["transformers_cache"],
        "HF_HUB_DISABLE_TELEMETRY": "1",
        "TOKENIZERS_PARALLELISM": "false",
    }

    support = detect_support(model_id, cache_root)
    return {
        "ok": True,
        "app_name": "Kree AI",
        "model_id": model_id or "",
        "environment": env,
        "paths": paths,
        "support": support,
        "loader_hints": [
            "Use the returned environment variables before calling any HuggingFace loader.",
            "Keep TurboQuant isolated behind an optional path so Gemini startup stays unaffected.",
            "If torch is installed, the next step is to choose a device map and quantization strategy.",
        ],
    }


def export_state(model_id: str = "", cache_root: str | None = None) -> dict[str, Any]:
    """Convenience bundle for tool callers that want one JSON-ready payload."""

    state = detect_support(model_id, cache_root)
    state["prepared_paths"] = _cache_paths(model_id, cache_root)
    return state
