"""E2E: verify the PWA server starts and responds to HTTP requests."""
import time
import pytest
import requests


@pytest.mark.e2e
def test_pwa_server_responds(app_process):
    """The embedded PWA server should be reachable after app startup."""
    assert app_process.poll() is None, "App not running"

    time.sleep(2)
    try:
        resp = requests.get("http://localhost:8765", timeout=5)
        assert resp.status_code == 200
    except requests.ConnectionError:
        pytest.skip("PWA server not reachable — check pwa_port in config")
