def test_allowed_desktop_code_runs_only_allowlisted_calls(monkeypatch):
    from kree.actions import desktop

    calls = []
    monkeypatch.setattr(desktop.pyautogui, "press", lambda key: calls.append(("press", key)))

    output = []
    desktop._run_allowed_desktop_code('pyautogui.press("enter")\nprint("done")', output)

    assert calls == [("press", "enter")]
    assert output == ["done"]


def test_desktop_code_blocks_imports():
    from kree.actions import desktop

    output = []
    try:
        desktop._run_allowed_desktop_code('import os\nos.remove("x")', output)
    except ValueError as exc:
        assert "Import" in str(exc)
    else:
        raise AssertionError("imports must not be executable")
