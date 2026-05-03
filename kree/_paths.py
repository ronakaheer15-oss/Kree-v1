from pathlib import Path
import sys


def _find_project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    # This file lives at <project_root>/kree/_paths.py
    return Path(__file__).resolve().parent.parent


PROJECT_ROOT = _find_project_root()
