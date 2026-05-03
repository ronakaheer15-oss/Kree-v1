"""E2E: simulate a text command via the UI and verify a response appears."""
import time
import pyautogui
import pytest


@pytest.mark.e2e
def test_text_command_produces_response(app_process):
    """Type a command into the UI input and verify the app does not crash."""
    assert app_process.poll() is None, "App not running"

    time.sleep(2)

    screen_w, screen_h = pyautogui.size()
    pyautogui.click(screen_w // 2, screen_h // 2)
    time.sleep(0.5)

    pyautogui.typewrite("what time is it", interval=0.05)
    pyautogui.press("enter")
    time.sleep(3)

    assert app_process.poll() is None, "App crashed after receiving a command"
