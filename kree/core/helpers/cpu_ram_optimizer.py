"""
cpu_ram_optimizer.py — Automatic strategy selector for CPU/RAM optimization.

Probes system resources (available RAM, CPU cores, GPU presence) and selects
the best loading strategy from:

  1. **mmap**       — Lazy disk-backed weights (lowest RAM, good for huge models).
  2. **DeepSpeed**  — ZeRO-3 CPU/NVMe offload (best balance for training).
  3. **ONNX**       — Graph-optimized CPU inference (fastest pure-CPU inference).
  4. **default**    — Standard PyTorch loading (when RAM is plentiful).

Usage
-----
    from kree.core.helpers.cpu_ram_optimizer import auto_select_strategy, apply_strategy

    strategy = auto_select_strategy()
    model = apply_strategy(strategy, model_or_path)
"""
from __future__ import annotations

import os
import platform
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SystemProfile:
    """Snapshot of current system resources."""
    total_ram_gb: float = 0.0
    available_ram_gb: float = 0.0
    cpu_count: int = 1
    has_nvidia_gpu: bool = False
    os_name: str = ""


def probe_system() -> SystemProfile:
    """Gather live system resource info."""
    profile = SystemProfile()
    profile.os_name = platform.system()
    profile.cpu_count = os.cpu_count() or 1

    try:
        import psutil  # type: ignore[import-untyped]
        mem = psutil.virtual_memory()
        profile.total_ram_gb = round(mem.total / (1024 ** 3), 2)
        profile.available_ram_gb = round(mem.available / (1024 ** 3), 2)
    except ImportError:
        # Fallback: assume 8 GB total, 4 GB free
        profile.total_ram_gb = 8.0
        profile.available_ram_gb = 4.0

    # Quick GPU check
    try:
        import subprocess
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode == 0 and result.stdout.strip():
            profile.has_nvidia_gpu = True
    except Exception:
        pass

    return profile


@dataclass
class Strategy:
    """Describes a chosen optimization strategy."""
    name: str                          # "mmap" | "deepspeed" | "onnx" | "default"
    reason: str = ""                   # Human-readable explanation
    params: dict[str, Any] = field(default_factory=dict)


def auto_select_strategy(
    model_size_gb: float = 0.0,
    prefer: str | None = None,
) -> Strategy:
    """
    Auto-select the best CPU/RAM optimization strategy.

    Parameters
    ----------
    model_size_gb : float
        Estimated model size in GB.  If 0, we only look at system resources.
    prefer : str | None
        Force a specific strategy (``"mmap"``, ``"deepspeed"``, ``"onnx"``).

    Returns
    -------
    Strategy
    """
    profile = probe_system()

    # User override
    if prefer and prefer in ("mmap", "deepspeed", "onnx"):
        return Strategy(name=prefer, reason=f"User preference: {prefer}")

    free = profile.available_ram_gb

    # Rule 1: Very low RAM or model >> available RAM → mmap
    if free < 3.0 or (model_size_gb > 0 and model_size_gb > free * 0.8):
        return Strategy(
            name="mmap",
            reason=f"Available RAM ({free:.1f} GB) is tight — using mmap for lazy loading.",
        )

    # Rule 2: If DeepSpeed is available and we have 4–8 GB headroom → ZeRO offload
    try:
        import deepspeed  # type: ignore[import-untyped]  # noqa: F401
        if 3.0 <= free <= 12.0:
            return Strategy(
                name="deepspeed",
                reason=f"DeepSpeed installed, moderate RAM ({free:.1f} GB) — using ZeRO-3 CPU offload.",
                params={"offload_device": "cpu"},
            )
    except ImportError:
        pass

    # Rule 3: If ONNX Runtime is available → use optimized graph inference
    try:
        import onnxruntime  # type: ignore[import-untyped]  # noqa: F401
        return Strategy(
            name="onnx",
            reason="ONNX Runtime available — using graph-optimized CPU inference.",
            params={"num_threads": max(1, profile.cpu_count // 2)},
        )
    except ImportError:
        pass

    # Rule 4: Plenty of RAM, nothing fancy needed
    return Strategy(
        name="default",
        reason=f"Sufficient RAM ({free:.1f} GB) — using standard loading.",
    )


def apply_strategy(strategy: Strategy, model_or_path: Any) -> Any:
    """
    Apply the selected strategy to a model or model path.

    Parameters
    ----------
    strategy : Strategy
        Output from ``auto_select_strategy``.
    model_or_path : Any
        Either a PyTorch model instance (for deepspeed/onnx) or a file
        path string (for mmap).

    Returns
    -------
    The wrapped/loaded model, or the original object unchanged for "default".
    """
    name = strategy.name

    if name == "mmap":
        from kree.core.helpers.mmap_loader import mmap_load_weights
        if isinstance(model_or_path, str):
            handle = mmap_load_weights(model_or_path)
            print(f"[KREE-OPT] mmap active — file={handle['path']}, size={handle['size'] / 1e6:.1f} MB")
            return handle
        print("[KREE-OPT] mmap strategy selected but model is not a path — returning as-is.")
        return model_or_path

    if name == "deepspeed":
        from kree.core.helpers.deepspeed_zero import init_deepspeed_model
        return init_deepspeed_model(
            model_or_path,
            offload_device=strategy.params.get("offload_device", "cpu"),
        )

    if name == "onnx":
        from kree.core.helpers.onnx_runner import _get_ort_session
        if isinstance(model_or_path, (str, os.PathLike)):
            return _get_ort_session(
                model_or_path,
                num_threads=strategy.params.get("num_threads"),
            )
        print("[KREE-OPT] ONNX strategy selected but model is not a path — returning as-is.")
        return model_or_path

    # default — no wrapping
    return model_or_path


def print_strategy_report() -> None:
    """Print a human-readable summary of the chosen optimization strategy."""
    profile = probe_system()
    strategy = auto_select_strategy()
    print("=" * 60)
    print("  KREE CPU/RAM OPTIMIZATION REPORT")
    print("=" * 60)
    print(f"  OS            : {profile.os_name}")
    print(f"  CPU Cores     : {profile.cpu_count}")
    print(f"  Total RAM     : {profile.total_ram_gb:.1f} GB")
    print(f"  Available RAM : {profile.available_ram_gb:.1f} GB")
    print(f"  NVIDIA GPU    : {'Yes' if profile.has_nvidia_gpu else 'No'}")
    print(f"  Strategy      : {strategy.name.upper()}")
    print(f"  Reason        : {strategy.reason}")
    print("=" * 60)
