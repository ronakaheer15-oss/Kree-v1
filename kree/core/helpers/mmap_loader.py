"""
mmap_loader.py — Memory-mapped model weight loader.

Uses Python's mmap module to lazily load model weight files from disk.
Only the pages actually accessed are loaded into physical RAM, drastically
reducing the memory footprint for large models on CPU-constrained machines.
"""
from __future__ import annotations

import mmap
import os
from pathlib import Path
from typing import Any


def mmap_load_weights(path: str | Path, dtype: str = "float32") -> dict[str, Any]:
    """
    Memory-map a raw weight file and return a dict-like accessor.

    Parameters
    ----------
    path : str | Path
        Absolute path to the weight file (e.g. .bin, .safetensors shard).
    dtype : str
        Numpy-style dtype string used to interpret bytes. Default float32.

    Returns
    -------
    dict with key ``mmap`` (the mmap object) and ``size`` (file size in bytes).
    The caller is responsible for closing the mmap when done.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Weight file not found: {path}")

    fd = os.open(str(path), os.O_RDONLY)
    try:
        size = os.fstat(fd).st_size
        if size == 0:
            raise ValueError(f"Weight file is empty: {path}")
        mm = mmap.mmap(fd, 0, access=mmap.ACCESS_READ)
    except Exception:
        os.close(fd)
        raise

    return {
        "mmap": mm,
        "fd": fd,
        "size": size,
        "dtype": dtype,
        "path": str(path),
    }


def close_mmap(handle: dict[str, Any]) -> None:
    """Safely close an mmap handle returned by ``mmap_load_weights``."""
    try:
        mm = handle.get("mmap")
        if mm and not mm.closed:
            mm.close()
    except Exception:
        pass
    try:
        fd = handle.get("fd")
        if fd is not None:
            os.close(fd)
    except Exception:
        pass


def estimate_resident_mb(handle: dict[str, Any]) -> float:
    """Rough estimate of resident memory (MB) based on file size."""
    size = handle.get("size", 0)
    # With mmap, actual RSS is typically 10-30% of total file size
    # depending on access patterns.  Return total as upper bound.
    return round(size / (1024 * 1024), 2)
