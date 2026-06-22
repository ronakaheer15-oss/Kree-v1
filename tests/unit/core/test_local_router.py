import pytest
import os
import sys
from kree.core.llm_gateway import KreeIntelligenceEngine

class MockUI:
    def __init__(self):
        self._zoom_level = 1.0
        self._dark_mode = False
        self.eval_scripts = []
        
    def _eval(self, script):
        self.eval_scripts.append(script)
        
    def _toggle_theme(self):
        self._dark_mode = not self._dark_mode

class MockLiveInstance:
    def __init__(self):
        self.ui = MockUI()

def test_local_router_time_date():
    engine = KreeIntelligenceEngine()
    
    # Time intent
    res_time = engine.generate_content("tell me the time")
    assert "current time is" in res_time.lower()
    
    # Date intent
    res_date = engine.generate_content("what is today's date")
    assert "today's date is" in res_date.lower()

def test_local_router_volume(monkeypatch):
    engine = KreeIntelligenceEngine()
    
    called = []
    monkeypatch.setattr("kree.actions.computer_settings.volume_up", lambda: called.append("up"))
    monkeypatch.setattr("kree.actions.computer_settings.volume_down", lambda: called.append("down"))
    monkeypatch.setattr("kree.actions.computer_settings.volume_mute", lambda: called.append("mute"))
    
    res = engine.generate_content("volume up")
    assert "increased" in res
    assert called == ["up"]
    
    res = engine.generate_content("hey kree, volume down")
    assert "decreased" in res
    assert called == ["up", "down"]
    
    res = engine.generate_content("mute")
    assert "muted" in res
    assert called == ["up", "down", "mute"]

def test_local_router_media_and_system(monkeypatch):
    engine = KreeIntelligenceEngine()
    
    # Mock system stats
    res_cpu = engine.generate_content("cpu usage")
    assert "cpu usage" in res_cpu.lower()
    
    res_ram = engine.generate_content("ram usage")
    assert "ram usage" in res_ram.lower()
    
    res_battery = engine.generate_content("battery status")
    assert "battery" in res_battery.lower() or "detect a battery" in res_battery.lower()

def test_local_router_zoom_and_theme():
    engine = KreeIntelligenceEngine()
    mock_live = MockLiveInstance()
    engine.live_instance = mock_live
    
    # Zoom In
    res = engine.generate_content("zoom in")
    assert "zoomed in" in res.lower()
    assert mock_live.ui._zoom_level == 1.1
    assert len(mock_live.ui.eval_scripts) == 1
    
    # Zoom Out
    res = engine.generate_content("zoom out")
    assert "zoomed out" in res.lower()
    assert mock_live.ui._zoom_level == 1.0
    
    # Reset Zoom
    res = engine.generate_content("reset zoom")
    assert "reset to 100%" in res.lower()
    assert mock_live.ui._zoom_level == 1.0
    
    # Theme Toggle
    res = engine.generate_content("toggle dark mode")
    assert "toggled theme" in res.lower()
    assert mock_live.ui._dark_mode is True

def test_local_router_lock_and_sleep(monkeypatch):
    engine = KreeIntelligenceEngine()
    
    if os.name == "nt":
        # Mock ctypes calls to avoid actually locking the workstation during test execution
        called_lock = []
        monkeypatch.setattr("ctypes.windll.user32.LockWorkStation", lambda: called_lock.append(True))
        
        res = engine.generate_content("lock screen")
        assert "computer locked" in res.lower()
        assert called_lock == [True]

def test_local_router_recycle_bin(monkeypatch):
    engine = KreeIntelligenceEngine()
    
    if os.name == "nt":
        called_empty = []
        monkeypatch.setattr("ctypes.windll.shell32.SHEmptyRecycleBinW", lambda a, b, c: called_empty.append(c))
        
        res = engine.generate_content("empty recycle bin")
        assert "recycle bin emptied" in res.lower()
        assert called_empty == [7]

def test_local_router_shell_folders(monkeypatch):
    engine = KreeIntelligenceEngine()
    
    called_folders = []
    monkeypatch.setattr("kree.core.llm_gateway._open_folder", lambda path: called_folders.append(str(path)))
    
    res = engine.generate_content("open downloads folder")
    assert "downloads" in res.lower()
    
    res = engine.generate_content("open documents folder")
    assert "documents" in res.lower()

def test_on_user_text_local_routing(monkeypatch):
    from unittest.mock import MagicMock
    from kree.main_entry import JarvisLive
    
    monkeypatch.setattr("kree.main_entry.TelemetryLogger", MagicMock())
    monkeypatch.setattr("kree.main_entry.load_telemetry_settings", lambda: {})
    
    class MockJarvisLive(JarvisLive):
        def __init__(self):
            self.ui = MagicMock()
            self._audio_settings = {}
            self._welcomed = False
            self._pending_choice = None
            self._command_window_active = False
            self.spoken_text = None
            
        def speak(self, text):
            self.spoken_text = text
            
        def _normalize_text_input(self, t):
            return t
            
        def _normalize_conversational_routing(self, t):
            return t
            
        def _resolve_pending_choice(self, t):
            return False
            
        def _arm_command_window(self, t):
            pass

    jarvis = MockJarvisLive()
    
    # Test routing "volume up"
    called_volume_up = []
    monkeypatch.setattr("kree.actions.computer_settings.volume_up", lambda: called_volume_up.append(True))
    
    jarvis.on_user_text("volume up")
    
    assert called_volume_up == [True]
    assert jarvis.spoken_text == "Volume increased, sir."

def test_local_router_expanded(monkeypatch):
    engine = KreeIntelligenceEngine()
    
    # 1. Window Control - show desktop
    called_keys = []
    monkeypatch.setattr("pyautogui.hotkey", lambda *args: called_keys.append(args))
    
    res = engine.generate_content("show desktop")
    assert "showing desktop" in res.lower()
    assert ('win', 'd') in called_keys
    
    # 2. System Utility - device manager
    called_popens = []
    monkeypatch.setattr("subprocess.Popen", lambda cmd, **kwargs: called_popens.append(cmd))
    
    res = engine.generate_content("open device manager")
    assert "opening device manager" in res.lower()
    assert "devmgmt.msc" in called_popens
    
    # 3. Wifi Toggle - disable wifi
    called_runs = []
    monkeypatch.setattr("subprocess.run", lambda cmd, **kwargs: called_runs.append(cmd))
    res = engine.generate_content("turn off wifi")
    assert "disabled" in res.lower()
    assert any("disabled" in str(c) for c in called_runs)
    
    # 4. Check online ping
    monkeypatch.setattr("socket.socket.connect", lambda self, addr: None)
    
    res = engine.generate_content("am i online")
    assert "online" in res.lower()
    
    # 5. Brightness adjustment - set brightness to 70%
    called_brightness = []
    monkeypatch.setattr("kree.core.llm_gateway._adjust_brightness", lambda act, val=None: called_brightness.append((act, val)))
    res = engine.generate_content("set brightness to 70%")
    assert called_brightness == [("set", 70)]
    
    # 6. Clipboard
    called_copies = []
    monkeypatch.setattr("pyperclip.copy", lambda text: called_copies.append(text))
    res = engine.generate_content("clear clipboard")
    assert "cleared" in res.lower()
    assert called_copies == [""]
    
    # 7. Virtual Desktops
    called_keys.clear()
    res = engine.generate_content("new virtual desktop")
    assert "created a new virtual desktop" in res.lower()
    assert ('ctrl', 'win', 'd') in called_keys

def test_local_router_mobile_intent(monkeypatch):
    class MockMobileBridge:
        def __init__(self):
            self.broadcasts = []
        async def broadcast(self, payload):
            self.broadcasts.append(payload)

    class MockLive:
        def __init__(self):
            self.mobile_bridge = MockMobileBridge()
            self._loop = "mock_loop"

    mock_live = MockLive()
    called_coroutines = []
    def mock_run_coroutine_threadsafe(coro, loop):
        called_coroutines.append(coro)
        coro.close()
    monkeypatch.setattr("asyncio.run_coroutine_threadsafe", mock_run_coroutine_threadsafe)

    engine = KreeIntelligenceEngine(live_instance=mock_live)
    monkeypatch.setattr("kree.actions.open_app.open_app", lambda app_name: "__BROADCAST_INTENT__:youtube")
    
    res = engine.generate_content("open youtube on mobile")
    assert "opening youtube on your mobile device, sir." in res.lower()
    assert len(called_coroutines) == 1

def test_smart_focus_or_launch_parser():
    from kree.actions.open_app import parse_open_command
    
    # Normal open
    app, force_new, switch_only = parse_open_command("open chrome")
    assert app == "chrome"
    assert not force_new
    assert not switch_only
    
    # Force new
    app, force_new, switch_only = parse_open_command("open new chrome window")
    assert app == "chrome"
    assert force_new
    assert not switch_only
    
    app, force_new, switch_only = parse_open_command("launch chrome again")
    assert app == "chrome"
    assert force_new
    assert not switch_only
    
    app, force_new, switch_only = parse_open_command("open another chrome")
    assert app == "chrome"
    assert force_new
    assert not switch_only

    # Switch only
    app, force_new, switch_only = parse_open_command("switch to chrome")
    assert app == "chrome"
    assert not force_new
    assert switch_only
    
    app, force_new, switch_only = parse_open_command("focus on vscode")
    assert app == "vscode"
    assert not force_new
    assert switch_only

    app, force_new, switch_only = parse_open_command("bring notepad to front")
    assert app == "notepad"
    assert not force_new
    assert switch_only

def test_smart_focus_or_launch_behavior(monkeypatch):
    from kree.actions.open_app import open_app
    
    called_launches = []
    
    # Mock launchers/helpers
    monkeypatch.setattr("kree.actions.open_app._get_process_pids", lambda app, norm: [1234])
    
    # Case 1: Focus succeeds
    monkeypatch.setattr("kree.actions.open_app._focus_existing_window", lambda pids, app, norm: True)
    res = open_app("open chrome")
    assert "already open" in res
    
    # Case 2: Focus fails, so we launch
    monkeypatch.setattr("kree.actions.open_app._focus_existing_window", lambda pids, app, norm: False)
    monkeypatch.setattr("kree.actions.open_app._OS_LAUNCHERS", {"Windows": lambda app: called_launches.append(app) or True})
    monkeypatch.setattr("platform.system", lambda: "Windows")
    res = open_app("open notepad")
    assert "successfully" in res or "browser" in res
    assert any("notepad" in item for item in called_launches)
    
    # Case 3: Switch only, app running
    called_launches.clear()
    monkeypatch.setattr("kree.actions.open_app._get_process_pids", lambda app, norm: [1234])
    monkeypatch.setattr("kree.actions.open_app._focus_existing_window", lambda pids, app, norm: True)
    res = open_app("switch to chrome")
    assert "already open" in res
    assert not called_launches
    
    # Case 4: Switch only, app not running
    monkeypatch.setattr("kree.actions.open_app._get_process_pids", lambda app, norm: [])
    res = open_app("switch to chrome")
    assert "not appear to be running" in res

def test_parallel_tts_pipeline(monkeypatch):
    import time
    from kree.main_entry import _local_speech_voice, _ACTIVE_TEMP_FILES
    
    class MockCommunicate:
        def __init__(self, text, voice, rate=None):
            pass
        async def save(self, path):
            with open(path, "wb") as f:
                f.write(b"mock audio")
                
    import edge_tts
    monkeypatch.setattr(edge_tts, "Communicate", MockCommunicate)
    
    monkeypatch.setattr("pygame.mixer.get_init", lambda: True)
    monkeypatch.setattr("pygame.mixer.init", lambda: None)
    monkeypatch.setattr("pygame.mixer.music.load", lambda path: None)
    monkeypatch.setattr("pygame.mixer.music.play", lambda: None)
    monkeypatch.setattr("pygame.mixer.music.unload", lambda: None)
    monkeypatch.setattr("pygame.mixer.music.get_busy", lambda: False)
    
    _local_speech_voice("Hello sir. This is sentence one. And this is sentence two.")
    time.sleep(1.0)
    
    from kree.main_entry import _SPEECH_CANCEL_EVENT
    _SPEECH_CANCEL_EVENT.set()
    time.sleep(0.1)
    
    assert len(_ACTIVE_TEMP_FILES) == 0

def test_transcript_aggregation_lcp_merging():
    def merge_transcript(current, incoming):
        if not current:
            return incoming
        if incoming.startswith(current):
            return incoming
        
        words_prev = current.split()
        words_next = incoming.split()
        overlap = 0
        for i in range(1, min(len(words_prev), len(words_next)) + 1):
            if words_prev[-i:] == words_next[:i]:
                overlap = i
        if overlap > 0:
            merged_words = words_prev + words_next[overlap:]
            return " ".join(merged_words)
        
        char_overlap = 0
        for i in range(1, min(len(current), len(incoming)) + 1):
            if current[-i:].lower() == incoming[:i].lower():
                char_overlap = i
        if char_overlap > 0:
            return current + incoming[char_overlap:]
        return current + " " + incoming

    assert merge_transcript("ओ", "ओ पन") == "ओ पन"
    assert merge_transcript("ओपन Chro", "Chrome") == "ओपन Chrome"
    assert merge_transcript("Open Chrome", "Notepad") == "Open Chrome Notepad"
    assert merge_transcript("Chro", "Chrome") == "Chrome"
    assert merge_transcript("Note", "Notepad") == "Notepad"
