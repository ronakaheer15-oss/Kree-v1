"""
core/runtime.py — Centralized path resolution for Kree AI.

Handles the critical difference between:
  - Dev mode:    __file__ points to source tree
  - Frozen mode: __file__ points inside _MEIPASS temp folder

Usage:
    from kree.core.runtime import BUNDLE_DIR, EXE_DIR, APP_DATA_DIR
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _is_frozen() -> bool:
    """True when running as a PyInstaller bundle."""
    return getattr(sys, "frozen", False)


def _get_bundle_dir() -> Path:
    """
    Where bundled *read-only* resources live (config templates, assets,
    openwakeword models, stitch dashboard HTML, etc.).

    - Frozen: sys._MEIPASS  (PyInstaller's temp extraction folder)
    - Dev:    project root   (kree/core/runtime.py → parent.parent = project root)
    """
    if _is_frozen() and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def _get_exe_dir() -> Path:
    """
    Where the actual executable (or main.py in dev) lives.
    Use this for *writable* paths that should persist (configs, logs).

    - Frozen: directory containing Kree AI.exe
    - Dev:    project root   (kree/core/runtime.py → parent.parent = project root)
    """
    if _is_frozen():
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def _get_app_data_dir() -> Path:
    """
    Per-user writable directory for logs, crash reports, voiceprints.
    Uses %LOCALAPPDATA%/Kree AI on Windows.
    Falls back to EXE_DIR if LOCALAPPDATA is missing.
    """
    base = os.environ.get("LOCALAPPDATA")
    if base:
        p = Path(base) / "Kree AI"
    else:
        p = _get_exe_dir() / "data"
    p.mkdir(parents=True, exist_ok=True)
    return p


# ── Public constants ─────────────────────────────────────────────────────────
IS_FROZEN = _is_frozen()
BUNDLE_DIR = _get_bundle_dir()       # read-only resources
EXE_DIR = _get_exe_dir()             # writable, next to exe
APP_DATA_DIR = _get_app_data_dir()   # per-user writable

# Convenience paths
CONFIG_DIR = EXE_DIR / "config"       # editable configs live next to exe
ASSETS_DIR = BUNDLE_DIR / "assets"    # read-only assets
LOG_DIR = APP_DATA_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
