"""
deepspeed_zero.py — DeepSpeed ZeRO-Infinity integration helper.

Provides a thin wrapper to initialise a HuggingFace model under
DeepSpeed ZeRO Stage-3 with CPU/NVMe offloading.  This allows models
that would normally exceed GPU VRAM to be loaded and run by
offloading optimizer states, gradients, and parameters to system RAM
or an NVMe drive.

Requirements (optional — gracefully degrades if missing):
    pip install deepspeed
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def _default_zero3_config(
    offload_device: str = "cpu",
    nvme_path: str | None = None,
    pin_memory: bool = True,
) -> dict[str, Any]:
    """
    Build a ZeRO Stage-3 config dict suitable for ``deepspeed.initialize``.

    Parameters
    ----------
    offload_device : str
        ``"cpu"`` or ``"nvme"``.
    nvme_path : str | None
        Path to NVMe mount point.  Required when ``offload_device="nvme"``.
    pin_memory : bool
        Whether to use pinned (page-locked) CPU memory for faster transfers.
    """
    offload_param: dict[str, Any] = {
        "device": offload_device,
        "pin_memory": pin_memory,
    }
    offload_optimizer: dict[str, Any] = {
        "device": offload_device,
        "pin_memory": pin_memory,
    }

    if offload_device == "nvme":
        nvme = nvme_path or tempfile.gettempdir()
        offload_param["nvme_path"] = nvme
        offload_optimizer["nvme_path"] = nvme

    return {
        "zero_optimization": {
            "stage": 3,
            "offload_param": offload_param,
            "offload_optimizer": offload_optimizer,
            "overlap_comm": True,
            "contiguous_gradients": True,
            "reduce_bucket_size": 5e7,
            "stage3_prefetch_bucket_size": 5e7,
            "stage3_param_persistence_threshold": 1e5,
        },
        "fp16": {"enabled": True},
        "train_batch_size": 1,
        "gradient_accumulation_steps": 1,
        "steps_per_print": 9999999,
    }


def init_deepspeed_model(
    model: Any,
    offload_device: str = "cpu",
    nvme_path: str | None = None,
    config_override: dict[str, Any] | None = None,
) -> Any:
    """
    Wrap a HuggingFace model with DeepSpeed ZeRO-3 inference engine.

    Parameters
    ----------
    model : transformers.PreTrainedModel
        The model instance to wrap.
    offload_device : str
        ``"cpu"`` (default) or ``"nvme"``.
    nvme_path : str | None
        NVMe mount point (only used when offload_device is ``"nvme"``).
    config_override : dict | None
        Full custom DeepSpeed config dict.  If provided, replaces default.

    Returns
    -------
    The DeepSpeed-wrapped model engine, or the original model if DeepSpeed
    is not installed.
    """
    try:
        import deepspeed  # type: ignore[import-untyped]
    except ImportError:
        print("[KREE-OPT] DeepSpeed not installed — skipping ZeRO offload.")
        return model

    ds_config = config_override or _default_zero3_config(
        offload_device=offload_device,
        nvme_path=nvme_path,
    )

    # Write config to temp file (deepspeed.initialize accepts a path).
    config_path = Path(tempfile.gettempdir()) / "kree_ds_config.json"
    config_path.write_text(json.dumps(ds_config, indent=2), encoding="utf-8")

    engine, *_ = deepspeed.initialize(
        model=model,
        config=str(config_path),
    )
    print(f"[KREE-OPT] DeepSpeed ZeRO-3 active — offload={offload_device}")
    return engine
