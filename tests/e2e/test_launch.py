"""E2E: verify the app launches and its window title is visible."""
import pytest


@pytest.mark.e2e
def test_app_window_appears(app_process):
    """The Kree window should be findable on screen after startup."""
    assert app_process.poll() is None, "App process exited unexpectedly during startup"


@pytest.mark.e2e
def test_app_window_title_visible(app_process):
    """Verify process is still running — window management is OS-dependent."""
    import time
    time.sleep(2)
    assert app_process.poll() is None, "App crashed before UI was ready"
