import pytest
import sys
from unittest.mock import MagicMock

from kree.core.llm_gateway import KreeIntelligenceEngine
import kree.actions.computer_settings as cs
import kree.actions.open_app as oa

@pytest.fixture(autouse=True)
def mock_system_actions(monkeypatch):
    monkeypatch.setattr(cs, "volume_up", MagicMock())
    monkeypatch.setattr(cs, "volume_down", MagicMock())
    monkeypatch.setattr(cs, "volume_mute", MagicMock())
    monkeypatch.setattr(cs, "take_screenshot", MagicMock(return_value="kree_screenshot.png"))
    def mock_open_app(app_name):
        from kree.actions.open_app import parse_open_command
        parsed_name, _, _ = parse_open_command(app_name)
        return f"Opening {parsed_name}, sir."
    monkeypatch.setattr(oa, "open_app", mock_open_app)

@pytest.fixture
def engine():
    engine = KreeIntelligenceEngine()
    
    class MockUI:
        def __init__(self):
            self._dark_mode = True
            self._zoom_level = 1.0
            self.logs = []
        def _eval(self, js):
            self.logs.append(f"eval: {js}")
        def _toggle_theme(self):
            self._dark_mode = not self._dark_mode
            self.logs.append("toggle_theme")

    class MockLiveInstance:
        def __init__(self):
            self.ui = MockUI()

    engine.live_instance = MockLiveInstance()
    return engine

@pytest.mark.parametrize("prompt,expected", [
    ("volume up", "Volume increased, sir."),
    ("volume down", "Volume decreased, sir."),
    ("mute", "Audio muted, sir."),
    ("unmute", "Audio unmuted, sir."),
    ("open calculator", "Opening calculator, sir."),
    ("open notepad", "Opening notepad, sir."),
    ("open chrome", "Opening chrome, sir."),
    ("time", "The current time is"),
    ("date", "Today's date is"),
    ("cpu usage", "CPU"),
    ("ram usage", "RAM"),
    ("battery status", "battery"),
    ("zoom in", "Zoomed in to"),
    ("zoom out", "Zoomed out to"),
    ("reset zoom", "Zoom reset to"),
    ("toggle dark mode", "Toggled theme to"),
    ("take screenshot", "Screenshot"),
    ("go to desktop", "Opening Desktop folder"),
])
def test_local_router_intents(engine, prompt, expected):
    res = engine.generate_content(prompt)
    assert expected.lower() in res.lower(), f"Expected '{expected}' in '{res}'"

