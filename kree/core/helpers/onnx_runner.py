"""
onnx_runner.py — ONNX Runtime inference helper.

Converts or loads a pre-exported ONNX model and runs inference through
ONNX Runtime, which applies graph-level optimizations (operator fusion,
constant folding, quantization) for significantly faster CPU inference
compared to raw PyTorch.

Requirements (optional — gracefully degrades if missing):
    pip install onnxruntime          # CPU-only
    pip install onnxruntime-gpu      # CUDA accelerated
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def _get_ort_session(
    onnx_path: str | Path,
    num_threads: int | None = None,
    use_gpu: bool = False,
) -> Any:
    """
    Create an ONNX Runtime InferenceSession.

    Parameters
    ----------
    onnx_path : str | Path
        Path to the ``.onnx`` model file.
    num_threads : int | None
        Number of intra-op threads.  ``None`` = auto (use all cores).
    use_gpu : bool
        If True, try CUDA execution provider first (falls back to CPU).

    Returns
    -------
    ort.InferenceSession or None if onnxruntime is not installed.
    """
    try:
        import onnxruntime as ort  # type: ignore[import-untyped]
    except ImportError:
        print("[KREE-OPT] onnxruntime not installed — ONNX path unavailable.")
        return None

    onnx_path = Path(onnx_path)
    if not onnx_path.is_file():
        raise FileNotFoundError(f"ONNX model not found: {onnx_path}")

    sess_opts = ort.SessionOptions()
    sess_opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

    if num_threads is not None:
        sess_opts.intra_op_num_threads = num_threads
    else:
        cpu_count = os.cpu_count() or 4
        sess_opts.intra_op_num_threads = max(1, cpu_count // 2)

    providers: list[str] = []
    if use_gpu:
        providers.append("CUDAExecutionProvider")
    providers.append("CPUExecutionProvider")

    session = ort.InferenceSession(
        str(onnx_path),
        sess_options=sess_opts,
        providers=providers,
    )
    active = session.get_providers()
    print(f"[KREE-OPT] ONNX Runtime session ready — providers={active}")
    return session


def run_onnx_inference(
    session: Any,
    input_dict: dict[str, Any],
) -> list[Any]:
    """
    Run inference on a loaded ONNX session.

    Parameters
    ----------
    session : ort.InferenceSession
        A session returned by ``_get_ort_session``.
    input_dict : dict[str, np.ndarray]
        Mapping of input names → numpy arrays.

    Returns
    -------
    List of output numpy arrays.
    """
    if session is None:
        raise RuntimeError("No ONNX session available.")

    output_names = [o.name for o in session.get_outputs()]
    results = session.run(output_names, input_dict)
    return results


def export_torch_to_onnx(
    model: Any,
    dummy_input: Any,
    output_path: str | Path,
    input_names: list[str] | None = None,
    output_names: list[str] | None = None,
    opset_version: int = 14,
) -> Path:
    """
    Export a PyTorch model to ONNX format.

    Parameters
    ----------
    model : torch.nn.Module
        The model to export.
    dummy_input : torch.Tensor or tuple
        Example input(s) for tracing.
    output_path : str | Path
        Destination ``.onnx`` file path.
    input_names : list[str] | None
        Names for the model inputs in the ONNX graph.
    output_names : list[str] | None
        Names for the model outputs in the ONNX graph.
    opset_version : int
        ONNX opset version.

    Returns
    -------
    Path to the saved ONNX file.
    """
    try:
        import torch  # type: ignore[import-untyped]
    except ImportError:
        raise RuntimeError("PyTorch is required for ONNX export.")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    torch.onnx.export(
        model,
        dummy_input,
        str(output_path),
        input_names=input_names or ["input"],
        output_names=output_names or ["output"],
        opset_version=opset_version,
        do_constant_folding=True,
    )
    print(f"[KREE-OPT] Exported ONNX model → {output_path} ({output_path.stat().st_size / 1e6:.1f} MB)")
    return output_path
