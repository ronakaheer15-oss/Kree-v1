"""E2E test fixtures: launch the real app, provide pyautogui helpers, tear down."""
import subprocess
import sys
import time
from pathlib import Path

import pyautogui
import pytest

APP_STARTUP_WAIT = 8  # seconds — adjust if app takes longer to show window


@pytest.fixture(scope="session")
def app_process():
    """Launch Kree via `python main.py`, yield, then terminate."""
    project_root = Path(__file__).resolve().parent.parent.parent
    proc = subprocess.Popen(
        [sys.executable, str(project_root / "main.py")],
        cwd=str(project_root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(APP_STARTUP_WAIT)
    yield proc
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture(scope="session", autouse=True)
def pyautogui_safety():
    """Reduce pyautogui speed so clicks land correctly on slower CI machines."""
    pyautogui.PAUSE = 0.5
    pyautogui.FAILSAFE = True
    yield
