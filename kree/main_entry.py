from __future__ import annotations

# ── CRITICAL: Force UTF-8 stdout/stderr on Windows ──────────────────────────

# Without this, any print() containing emoji (💬, ⚡, etc.) crashes the

# entire thread with UnicodeEncodeError because Windows uses cp1252/cp437.

import sys as _sys

import io as _io

import os as _os
_os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import platform as _platform

import logging as _logging

from pathlib import Path as _Path

class _SafeWriter:
    def __init__(self, stream):
        self.stream = stream
    def write(self, data):
        try:
            if self.stream is not None:
                self.stream.write(data)
        except Exception:
            pass
    def flush(self):
        try:
            if self.stream is not None:
                self.stream.flush()
        except Exception:
            pass
    def __getattr__(self, attr):
        if self.stream is None:
            raise AttributeError(attr)
        return getattr(self.stream, attr)

if 'pytest' not in _sys.modules:
    # Only wrap in SafeWriter — do NOT re-wrap in TextIOWrapper
    # The TextIOWrapper was detaching the original buffer and breaking stdout
    _sys.stdout = _SafeWriter(_sys.stdout)
    _sys.stderr = _SafeWriter(_sys.stderr)

# ── Direct-to-file boot logger (bypasses stdout entirely) ─────────────────────
def _bootlog(msg):
    """Write directly to startup.log AND print. Never fails."""
    try:
        print(msg)
    except Exception:
        pass
    try:
        from kree.core.runtime import LOG_DIR
        import datetime
        with open(str(LOG_DIR / "startup.log"), "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now().isoformat()} - BOOT - {msg}\n")
    except Exception:
        pass

# ── SINGLE INSTANCE MUTEX ────────────────────────────────────────────────────
if _platform.system() == "Windows":
    import ctypes
    _MUTEX_NAME = "Kree_V1_Application_Mutex"
    _app_mutex = ctypes.windll.kernel32.CreateMutexW(None, False, _MUTEX_NAME)
    if ctypes.windll.kernel32.GetLastError() == 183 and 'pytest' not in _sys.modules: # ERROR_ALREADY_EXISTS
        _sys.exit(0)

# ── PRODUCTION LOGGING ───────────────────────────────────────────────────────
try:
    if getattr(_sys, "frozen", False):
        local_app_data = _os.environ.get("LOCALAPPDATA")
        log_dir = (_Path(local_app_data) if local_app_data else _Path.home() / "AppData" / "Local") / "Kree" / "logs"
    else:
        log_dir = _Path(__file__).resolve().parent.parent / "logs"
    
    log_dir.mkdir(parents=True, exist_ok=True)
    _LOG_FILE = log_dir / "kree_debug.log"
 
    _logger = _logging.getLogger()
    _logger.setLevel(_logging.DEBUG)
    from logging.handlers import RotatingFileHandler as _RotatingFileHandler
    _handler = _RotatingFileHandler(
        filename=str(_LOG_FILE),
        maxBytes=5 * 1024 * 1024,  # 5MB limit
        backupCount=1,
        encoding="utf-8"
    )
    _handler.setFormatter(_logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    _logger.addHandler(_handler)
    _logging.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    _logging.info("Kree Production Runtime Starting...")
    _logging.info(f"Platform: {_platform.system()} {_platform.release()}")
    _logging.info(f"Frozen: {getattr(_sys, 'frozen', False)}")
except Exception as e:
    _sys.stderr.write(f"CRITICAL: Logging init failed: {e}\n")

# ── GLOBAL CRASH HANDLER (captures fatal errors in frozen EXE) ───────────────

def _kree_crash_handler(exc_type, exc_value, exc_tb):

    import traceback as _tb

    import platform as _platform

    import datetime

    from kree.core.version import APP_VERSION

    crash_text = "".join(_tb.format_exception(exc_type, exc_value, exc_tb))

    _logging.critical(f"UNHANDLED EXCEPTION:\n{crash_text}")

    try:

        crash_file = log_dir / "crash.log"

        with open(crash_file, "a", encoding="utf-8") as f:

            f.write(

                f"\n{'='*60}\n"

                f"TIMESTAMP: {datetime.datetime.now()}\n"

                f"PLATFORM: {_platform.platform()}\n"

                f"PYTHON: {_sys.version}\n"

                f"KREE VERSION: {APP_VERSION}\n"

                f"UNHANDLED EXCEPTION:\n{crash_text}"

                f"{'='*60}\n"

            )

    except Exception:

        pass

    _sys.__excepthook__(exc_type, exc_value, exc_tb)

_sys.excepthook = _kree_crash_handler

import asyncio

import random

import threading

import json

import difflib

import re

import sys

import os

import logging

import traceback

import functools

import base64

import unicodedata

from pathlib import Path

from typing import Any, Optional

try:

    pass

except ImportError:

    pass

import time

from kree.ui import JarvisUI  # type: ignore[import]

from kree._paths import PROJECT_ROOT  # type: ignore[import]

from kree.memory.memory_manager import load_memory, format_memory_for_prompt  # type: ignore[import]

from kree.memory.config_manager import load_audio_settings, load_telemetry_settings  # type: ignore[import]

from kree.core.telemetry import TelemetryEvents, TelemetryLogger, export_session_trace, load_session_events  # type: ignore[import]

class ToolLoadError(RuntimeError):

    """Raised when a lazy-loaded tool module or function cannot be loaded."""

TOOL_MODULE_MAP = {

    "flight_finder": ("kree.actions.flight_finder", "flight_finder"),

    "open_app": ("kree.actions.open_app", "open_app"),

    "downloader_updater": ("kree.actions.downloader_updater", "downloader_updater"),

    "turboquant_helper": ("kree.actions.turboquant_helper", "turboquant_helper"),

    "openapps_automation": ("kree.actions.openapps_automation", "openapps_automation"),

    "weather_action": ("kree.actions.weather_report", "weather_action"),

    "send_message": ("kree.actions.send_message", "send_message"),

    "reminder": ("kree.actions.reminder", "reminder"),

    "computer_settings": ("kree.actions.computer_settings", "computer_settings"),

    "screen_process": ("kree.actions.screen_processor", "screen_process"),

    "youtube_video": ("kree.actions.youtube_video", "youtube_video"),

    "cmd_control": ("kree.actions.cmd_control", "cmd_control"),

    "desktop_control": ("kree.actions.desktop", "desktop_control"),

    "browser_control": ("kree.actions.browser_control", "browser_control"),

    "file_controller": ("kree.actions.file_controller", "file_controller"),

    "code_helper": ("kree.actions.code_helper", "code_helper"),

    "dev_agent": ("kree.actions.dev_agent", "dev_agent"),

    "web_search_action": ("kree.actions.web_search", "web_search"),

    "computer_control": ("kree.actions.computer_control", "computer_control"),

    "productivity_manager": ("kree.actions.email_calendar", "productivity_manager"),

    "safe_calculator": ("kree.actions.math_helper", "calculate"),

}

class LazyToolLoader:

    def __init__(self, module_map: dict[str, tuple[str, str]] | None = None):

        self.module_map = module_map or TOOL_MODULE_MAP

    def __getattr__(self, name):

        if name not in self.module_map:

            raise AttributeError(f"Tool {name} not found")

        def wrapper(*args, **kwargs):

            import importlib

            mod_name, func_name = self.module_map[name]

            try:

                mod = importlib.import_module(mod_name)

                func = getattr(mod, func_name)

            except (ImportError, AttributeError) as exc:

                logging.exception("Failed to load tool %s from %s.%s", name, mod_name, func_name)

                raise ToolLoadError(

                    f"Tool '{name}' could not be loaded from {mod_name}.{func_name}: {exc}"

                ) from exc

            return func(*args, **kwargs)

        wrapper.__name__ = name

        wrapper.__qualname__ = f"{self.__class__.__name__}.{name}"

        return wrapper

lazy_tools = LazyToolLoader()

flight_finder = lazy_tools.flight_finder

open_app = lazy_tools.open_app

downloader_updater = lazy_tools.downloader_updater

turboquant_helper = lazy_tools.turboquant_helper

openapps_automation = lazy_tools.openapps_automation

weather_action = lazy_tools.weather_action

send_message = lazy_tools.send_message

reminder = lazy_tools.reminder

computer_settings = lazy_tools.computer_settings

screen_process = lazy_tools.screen_process

youtube_video = lazy_tools.youtube_video

cmd_control = lazy_tools.cmd_control

desktop_control = lazy_tools.desktop_control

browser_control = lazy_tools.browser_control

file_controller = lazy_tools.file_controller

code_helper = lazy_tools.code_helper

dev_agent = lazy_tools.dev_agent

web_search_action = lazy_tools.web_search_action

computer_control = lazy_tools.computer_control

productivity_manager = lazy_tools.productivity_manager

safe_calculator = lazy_tools.safe_calculator

from kree.core.trigger_engine import TriggerEngine

def get_base_dir():

    if getattr(sys, "frozen", False):

        return Path(sys._MEIPASS)

    return PROJECT_ROOT

BASE_DIR = get_base_dir()

from kree.core.runtime import APP_DATA_DIR, ASSETS_DIR, CONFIG_DIR

SOUNDS_DIR = APP_DATA_DIR / "sounds"

SOUNDS_DIR.mkdir(parents=True, exist_ok=True)

API_CONFIG_PATH = CONFIG_DIR / "api_keys.json"

PROMPT_PATH = BASE_DIR / "config" / "prompt.txt"

def _get_live_model():

    # Try reading from environment variable first

    model = os.environ.get("KREE_LIVE_MODEL")

    if model:

        return model

    # Try reading from audio_settings.json

    try:

        from kree.memory.config_manager import load_audio_settings

        settings = load_audio_settings()

        model = settings.get("live_model")

        if model:

            return model

    except Exception:

        pass

    # Fallback to the latest stable multi-modal / native-audio Gemini model

    from kree.core.version import MODEL_LIVE_AUDIO

    return MODEL_LIVE_AUDIO

LIVE_MODEL = _get_live_model()

FORMAT = 8  # PyAudio paInt16 constant value

CHANNELS = 1

SEND_SAMPLE_RATE = 16000

RECEIVE_SAMPLE_RATE = 24000

CHUNK_SIZE = 1024

MAX_AUDIO_IN_QUEUE = 96

MAX_AUDIO_OUT_QUEUE = 64

MAX_PLAY_QUEUE = 180

_LOCAL_SPEECH_LIMIT = threading.BoundedSemaphore(1)

# ── Lazy PyAudio init (prevents crash if no audio device at startup) ──────────

_pya = None

_pya_lock = threading.Lock()

def _get_pya() -> Any:

    global _pya

    if _pya is None:

        with _pya_lock:

            if _pya is None:

                try:

                    import pyaudio

                    _pya = pyaudio.PyAudio()

                except Exception as e:

                    print(f"[JARVIS] ❌ PyAudio init failed: {e}")

    return _pya

# Global definitions to prevent IDE warnings

genai = None

types = None

def _get_api_key() -> str:

    import os

    if "KREE_ACTIVE_API_KEY" in os.environ:

        return os.environ["KREE_ACTIVE_API_KEY"]

    import kree.core.vault as vault  # type: ignore[import]

    return vault.load_api_key(API_CONFIG_PATH)

def _ensure_genai_sdk() -> tuple[Any, Any]:

    global genai, types

    if genai is None or types is None:

        from google import genai as genai_module  # type: ignore[import]

        from google.genai import types as types_module  # type: ignore[import]

        genai = genai_module  # type: ignore[assignment]

        types = types_module  # type: ignore[assignment]

    return genai, types

def _load_system_prompt() -> str:

    try:

        base_text = PROMPT_PATH.read_text(encoding="utf-8")

        try:

            import kree.memory.history_manager as hist

            import kree.core.user_profile as up

            # Fetch Context

            history_summary = hist.get_memory_summary()

            profile = up.get_user_profile()

            # Identity Injection

            ident_block = ""

            if profile.get("name"):

                ident_block += f"\nThe user's name is {profile['name']}. Address them by name when natural; use sir sparingly.\n"

            if profile.get("default_email"):

                ident_block += f"Default email: {profile['default_email']}\n"

            ident_block += "Do not repeat canned acknowledgements or stock phrases. Vary phrasing and answer with fresh, task-focused language.\n"

            return f"{base_text}\n\n{ident_block}\n\n=== RECENT CONTEXT ===\n{history_summary}\n"

        except Exception as e:

            print(f"[JARVIS] ⚠️ Dynamic prompt injection failed: {e}")

            return base_text

    except Exception:

        return (

            "You are Kree, an advanced AI assistant. "

            "Be concise, direct, and always use the provided tools to complete tasks. "

            "Never simulate or guess results — always call the appropriate tool."

        )

_SPEECH_LOCK = threading.Lock()

_SPEECH_CANCEL_EVENT = threading.Event()

_ACTIVE_TEMP_FILES = set()

_TEMP_FILES_LOCK = threading.Lock()

def _add_temp_file(path):

    with _TEMP_FILES_LOCK:

        _ACTIVE_TEMP_FILES.add(str(path))

def _remove_temp_file(path):

    with _TEMP_FILES_LOCK:

        _ACTIVE_TEMP_FILES.discard(str(path))

        try:

            if os.path.exists(path):

                os.remove(path)

        except Exception:

            pass

def _cleanup_all_temp_files():

    with _TEMP_FILES_LOCK:

        for path in list(_ACTIVE_TEMP_FILES):

            try:

                if os.path.exists(path):

                    os.remove(path)

            except Exception:

                pass

        _ACTIVE_TEMP_FILES.clear()

def _local_speech_voice(text: str) -> None:

    """Instant local Windows speech using Edge TTS neural voices with a parallelized background

    generator and player queue to eliminate network/playback gaps. Thread-safe and interruptible."""

    print("RAW TTS INPUT (local):", repr(text))

    try:

        print("TTS INPUT CHAR CODES (local):", [ord(c) for c in text])

    except Exception:

        pass

    import threading

    import pygame

    import os

    import queue

    import uuid

    import re

    import asyncio

    import time

    import edge_tts

    # ── Thread-safe cancellation of active speech ──

    with _SPEECH_LOCK:

        _SPEECH_CANCEL_EVENT.set()

        try:

            if pygame.mixer.get_init():

                pygame.mixer.music.stop()

                pygame.mixer.music.unload()

        except Exception:

            pass

        _cleanup_all_temp_files()

        _SPEECH_CANCEL_EVENT.clear()

    if not text.strip():

        return

    # Extract audio settings

    from kree.memory.config_manager import load_audio_settings

    settings = load_audio_settings()

    gemini_voice = settings.get("kree_voice", "Kore")

    voice = {

        "Aoede": "en-US-AriaNeural",

        "Kore": "en-US-JennyNeural",

        "Puck": "en-US-GuyNeural",

        "Charon": "en-US-ChristopherNeural"

    }.get(gemini_voice, "en-US-JennyNeural")

    print(f"[KREE TTS] Voice Name: {voice}, Rate: -15%, Pitch: default")

    # Split text into chunks by sentence

    chunks = []

    sentences = re.split(r'(?<=[.!?])\s+', text)

    current = ""

    for s in sentences:

        if len(current) + len(s) <= 250:

            current += s + " "

        else:

            if current.strip():

                chunks.append(current.strip())

            if len(s) > 250:

                import textwrap

                for wrap in textwrap.wrap(s, 240, break_long_words=False):

                    chunks.append(wrap)

                current = ""

            else:

                current = s + " "

    if current.strip():

        chunks.append(current.strip())

    print("TTS CHUNKS:", chunks)

    if not chunks:

        return

    # Queues for the pipeline

    # LIMIT prefetching to MAX_PREFETCH = 3

    generator_queue = queue.Queue()

    audio_queue = queue.Queue(maxsize=3)

    for idx, chunk in enumerate(chunks):

        generator_queue.put((idx, chunk))

    generator_active = True

    def generator_worker():

        nonlocal generator_active

        try:

            while not _SPEECH_CANCEL_EVENT.is_set():

                try:

                    item = generator_queue.get_nowait()

                except queue.Empty:

                    break

                idx, chunk = item

                if not chunk.strip():

                    continue

                print("GENERATING:", repr(chunk))

                temp_mp3 = SOUNDS_DIR / f"temp_speech_{uuid.uuid4().hex[:6]}.mp3"

                temp_mp3.parent.mkdir(parents=True, exist_ok=True)

                _add_temp_file(temp_mp3)

                loop = asyncio.new_event_loop()

                asyncio.set_event_loop(loop)

                success = False

                start_time = time.time()

                try:

                    loop.run_until_complete(

                        edge_tts.Communicate(chunk, voice, rate="-15%").save(str(temp_mp3))

                    )

                    success = True

                    print(f"[KREE TTS] Generated chunk {idx} in {time.time() - start_time:.3f}s")

                except Exception as e:

                    print(f"[KREE TTS] ⚠️ Generation failed for chunk {idx}: {e}")

                    _remove_temp_file(temp_mp3)

                finally:

                    loop.close()

                if _SPEECH_CANCEL_EVENT.is_set():

                    _remove_temp_file(temp_mp3)

                    break

                if success:

                    # Push chunk to queue. If queue is full (prefetch limit hit), loop and check cancellation

                    pushed = False

                    while not _SPEECH_CANCEL_EVENT.is_set() and not pushed:

                        try:

                            audio_queue.put((idx, temp_mp3), timeout=0.05)

                            pushed = True

                        except queue.Full:

                            continue

                    if not pushed:

                        _remove_temp_file(temp_mp3)

        finally:

            generator_active = False

    def player_worker():

        while not _SPEECH_CANCEL_EVENT.is_set():

            try:

                idx, temp_mp3 = audio_queue.get(timeout=0.1)

            except queue.Empty:

                if not generator_active and audio_queue.empty():

                    break

                continue

            if _SPEECH_CANCEL_EVENT.is_set():

                _remove_temp_file(temp_mp3)

                break

            try:

                start_play = time.time()

                try:

                    import shutil

                    shutil.copy2(str(temp_mp3), "e:\\Kree-v1-main\\debug_tts_output.mp3")

                    print("[KREE TTS] Copied debug file to e:\\Kree-v1-main\\debug_tts_output.mp3")

                except Exception as ex:

                    print(f"[KREE TTS] ⚠️ Could not copy debug file: {ex}")

                if not pygame.mixer.get_init():

                    pygame.mixer.init()

                pygame.mixer.music.load(str(temp_mp3))

                pygame.mixer.music.play()

                print(f"[KREE TTS] Playing chunk {idx}")

                while pygame.mixer.music.get_busy():

                    if _SPEECH_CANCEL_EVENT.is_set():

                        pygame.mixer.music.stop()

                        pygame.mixer.music.unload()

                        break

                    time.sleep(0.02)

                pygame.mixer.music.unload()

                print(f"[KREE TTS] Finished chunk {idx} in {time.time() - start_play:.3f}s")

            except Exception as e:

                print(f"[KREE TTS] ⚠️ Playback failed for chunk {idx}: {e}")

            finally:

                _remove_temp_file(temp_mp3)

                audio_queue.task_done()

    t_gen = threading.Thread(target=generator_worker, daemon=True)

    t_play = threading.Thread(target=player_worker, daemon=True)

    t_gen.start()

    t_play.start()

def _local_welcome_voice(kree_instance) -> None:

    """Play greeting and write 'Kree is online' to transcript."""

    import threading

    import os

    import pygame

    import time

    from pathlib import Path

    greeting = "Kree is online and ready, sir."

    try:

        kree_instance.ui.write_log(f"Kree: {greeting}")

    except Exception:

        pass

    def speak_and_cache():

        try:

            from kree.memory.config_manager import load_audio_settings

            settings = load_audio_settings()

            gemini_voice = settings.get("kree_voice", "Kore")

            voice_key = {

                "Aoede": "en-US-AriaNeural",

                "Kore": "en-US-JennyNeural",

                "Puck": "en-US-GuyNeural",

                "Charon": "en-US-ChristopherNeural"

            }.get(gemini_voice, "en-US-JennyNeural")

            cache_file = SOUNDS_DIR / f"welcome_{voice_key}.mp3"

            cache_file.parent.mkdir(parents=True, exist_ok=True)

            if not cache_file.exists():

                import edge_tts

                import asyncio

                loop = asyncio.new_event_loop()

                asyncio.set_event_loop(loop)

                try:

                    loop.run_until_complete(edge_tts.Communicate(greeting, voice_key, rate="-15%").save(str(cache_file)))

                finally:

                    loop.close()

            if not pygame.mixer.get_init():

                pygame.mixer.init()

            pygame.mixer.music.load(str(cache_file))

            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy():

                time.sleep(0.05)

        except Exception as e:

            print(f"[JARVIS] Welcome voice error (non-fatal): {e}")

    threading.Thread(target=speak_and_cache, daemon=True).start()

_GREETING_MEMORY: dict[str, list[str]] = {}

def _load_app_process_map() -> dict[str, str]:

    defaults = {

        "chrome": "chrome.exe",

        "spotify": "Spotify.exe",

        "vscode": "Code.exe",

        "discord": "Discord.exe",

        "notepad": "notepad.exe",

        "youtube": "chrome.exe",

        "github": "chrome.exe",

    }

    config_path = BASE_DIR / "config" / "app_process_map.json"

    try:

        if config_path.exists():

            raw = json.loads(config_path.read_text(encoding="utf-8"))

            if isinstance(raw, dict):

                defaults.update({str(k).lower(): str(v) for k, v in raw.items() if v})

    except Exception:

        pass

    return defaults

def _build_contextual_greeting(name: str = "sir") -> str:

    """

    Highly advanced context-aware greeting engine.

    Checks battery level, active window title (what the user is currently looking at),

    and time of day to formulate a highly targeted and natural greeting.

    """

    import datetime

    def _pick_unique(bucket: str, options: list[str]) -> str:

        recent_choices = _GREETING_MEMORY.get(bucket, [])

        usable = [item for item in options if item not in recent_choices] or options

        choice = random.choice(usable)

        _GREETING_MEMORY[bucket] = (recent_choices + [choice])[-3:]

        return choice

    now = datetime.datetime.now()

    hr = now.hour

    day = now.weekday()  # 0=Monday, 6=Sunday

    # 1. Check Battery Status

    battery_context = ""

    try:

        import psutil

        battery = psutil.sensors_battery()

        if battery and battery.percent < 20 and not battery.power_plugged:

            battery_context = "low_battery"

    except Exception:

        pass

    # 2. Check Active Window via Windows API

    active_title = ""

    try:

        import ctypes

        hwnd = ctypes.windll.user32.GetForegroundWindow()

        if hwnd:

            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)

            buf = ctypes.create_unicode_buffer(length + 1)

            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)

            active_title = buf.value.lower()

    except Exception:

        pass

    # 3. Determine specific Activity Context

    activity_context = ""

    if battery_context == "low_battery":

        activity_context = "low_battery"

    elif "youtube" in active_title:

        activity_context = "youtube"

    elif "github" in active_title or "pull request" in active_title:

        activity_context = "github"

    elif "stackoverflow" in active_title or "stack overflow" in active_title:

        activity_context = "debugging"

    elif "visual studio code" in active_title or "code.exe" in active_title:

        activity_context = "coding"

    elif "spotify" in active_title or "music" in active_title:

        activity_context = "music"

    elif any(g in active_title for g in ("steam", "epic games", "riot", "valorant", "minecraft", "fortnite", "game")):

        activity_context = "gaming"

    elif any(s in active_title for s in ("instagram", "twitter", "facebook", "reddit", "whatsapp", "telegram", "discord")):

        activity_context = "social"

    elif any(b in active_title for b in ("chrome", "firefox", "edge", "brave", "opera", "safari")):

        activity_context = "browsing"

    # Fallback to psutil if foreground detection yields nothing specific.

    if not activity_context:

        try:

            import psutil

            process_names = {

                (proc.info.get("name") or "").lower()

                for proc in psutil.process_iter(["name"])

            }

            if "code.exe" in process_names or "devenv.exe" in process_names:

                activity_context = "coding"

            elif "spotify.exe" in process_names:

                activity_context = "music"

            elif any(g in process_names for g in ("steam.exe", "epicgameslauncher.exe", "riotclientservices.exe")):

                activity_context = "gaming"

        except Exception:

            pass

    # ── Prioritized Greeting Logic ──

    # Priority 1: Critical System Status

    if activity_context == "low_battery":

        return random.choice([

            "Sir, battery is extremely low. You might want to plug in.",

            f"Battery critical, {name}. Please connect power.",

            f"We're running on fumes here, {name}. Plug in soon.",

            f"{name}, battery's about to die. Better save your work.",

            f"Power alert, {name}. We need a charger, stat."

        ])

    # Priority 2: Specific Foreground Activities

    if activity_context == "youtube":

        return random.choice([

            f"Enjoying the video, {name}?",

            f"Watching something interesting, {name}?",

            f"Yes, {name}?",

            f"Need me to find something else to watch, {name}?",

            f"Want me to summarize that for you, {name}?",

            f"Taking a break with some videos, {name}?",

            f"I see you're on YouTube. What do you need, {name}?"

        ])

    elif activity_context == "github":

        return random.choice([

            f"Reviewing repositories, {name}?",

            f"Need help with GitHub, {name}?",

            f"Looking at pull requests, {name}?",

            f"Pushing some code, {name}?",

            f"Want me to help with that repo, {name}?",

            f"I see you're on GitHub. Need a hand, {name}?",

            f"Ship it, {name}. What do you need?"

        ])

    elif activity_context == "debugging":

        return random.choice([

            f"Need help debugging, {name}?",

            f"Stuck on a bug, {name}?",

            f"What's the error say, {name}?",

            f"Let's squash that bug together, {name}.",

            f"Stack Overflow to the rescue, {name}?",

            f"Debugging at this hour, {name}? Respect.",

            f"Send me the error, {name}. I'll figure it out."

        ])

    elif activity_context == "coding":

        return random.choice([

            f"Back to the code, {name}?",

            f"What are we building, {name}?",

            f"Ready to code when you are, {name}.",

            f"What do you need, {name}?",

            f"In the zone, {name}? How can I help?",

            f"Let's ship something great, {name}.",

            f"Building the future one line at a time, {name}.",

            f"Code mode activated. What's the task, {name}?",

            f"I see VSCode is open. Need anything, {name}?"

        ])

    elif activity_context == "music":

        return random.choice([

            f"{name}?",

            "Yes?",

            "I'm here.",

            f"Enjoying the tunes, {name}?",

            f"Good playlist. What do you need, {name}?",

            f"I'm listening too, {name}. Well, sort of.",

            f"Need me to change the vibe, {name}?"

        ])

    elif activity_context == "gaming":

        return random.choice([

            f"In the middle of a game, {name}?",

            f"Need a quick assist, {name}?",

            f"Don't worry, I'll keep it quick, {name}.",

            f"Gaming session, nice. What's up, {name}?",

            f"GG. What do you need, {name}?"

        ])

    elif activity_context == "browsing":

        return random.choice([

            f"Browsing the web, {name}?",

            f"Found anything interesting, {name}?",

            f"Need me to search something for you, {name}?",

            f"Web surfing, {name}? I can help with that.",

            f"What are you looking for, {name}?"

        ])

    elif activity_context == "social":

        return random.choice([

            f"Catching up on socials, {name}?",

            f"Scrolling through the feed, {name}?",

            f"Need me to draft a message, {name}?",

            f"What's trending, {name}?",

            f"Taking a social break? What do you need, {name}?"

        ])

    # Priority 3: Time & Day combinations

    if day == 0 and hr < 12: # Monday Morning

        return _pick_unique("mon_morning", [

            f"Monday morning, {name}. Ready to conquer the week?",

            f"Welcome to a new week, {name}.",

            "Monday morning, let's get started.",

            f"New week, new goals. What's the plan, {name}?",

            f"Rise and grind, {name}. It's Monday."

        ])

    elif day == 4 and hr > 16: # Friday Evening

        return _pick_unique("fri_evening", [

            f"It's Friday evening, {name}. Almost time to relax.",

            f"Wrapping up the week, {name}?",

            f"Friday evening, {name}. What's left?",

            f"TGIF, {name}. Finishing up?",

            f"Weekend's almost here, {name}. Need anything before we wrap?"

        ])

    elif day in (5, 6): # Weekend

        return _pick_unique("weekend", [

            f"Weekend vibes, {name}. What are we doing?",

            f"It's the weekend, {name}. Working or chilling?",

            f"No rest for the ambitious, {name}?",

            f"Weekend mode, {name}. How can I help?",

            f"Even on the weekend, {name}? I respect the hustle."

        ])

    # Priority 4: Standard Time-based greetings

    if hr < 6:

        return _pick_unique("night", [

            f"Burning the midnight oil, {name}?",

            f"Night shift mode, {name}. What are we tackling?",

            f"It's quite late, {name}. What do you need?",

            f"Late night grind, {name}. I'm here for it.",

            f"The world is sleeping, but not us, {name}.",

            f"Night owl mode, {name}. What's on your mind?",

            f"Can't sleep, {name}? Let's be productive then.",

            f"It's past midnight, {name}. How can I help?"

        ])

    elif hr < 12:

        return _pick_unique("morning", [

            f"Good morning, {name}.",

            f"Morning, {name}. Ready to start?",

            "Good morning. What's the plan for today?",

            f"Top of the morning, {name}. What do you need?",

            f"Rise and shine, {name}.",

            f"Fresh day ahead, {name}. What's first?",

            f"Morning, {name}. Let's make today count.",

            f"Good morning, {name}. I'm all ears."

        ])

    elif hr < 14:

        return _pick_unique("midday", [

            f"Afternoon, {name}. What's next?",

            f"Lunchtime productivity, {name}?",

            f"Good afternoon, {name}. How can I help?",

            f"Midday check-in, {name}. Need something?",

            f"Afternoon, {name}. Let's keep the momentum going."

        ])

    elif hr < 18:

        return _pick_unique("afternoon", [

            f"Kree online, {name}.",

            f"Good afternoon, {name}.",

            f"Yes, {name}?",

            f"How can I help you, {name}?",

            f"Afternoon push, {name}. What do you need?",

            f"Still going strong, {name}?",

            f"At your service, {name}.",

        ])

    elif hr < 22:

        return _pick_unique("evening", [

            f"Good evening, {name}.",

            f"Evening, {name}. What's next?",

            f"Yes, {name}?",

            f"Winding down or gearing up, {name}?",

            f"Evening session, {name}. How can I help?",

            f"Good evening, {name}. What's on the agenda?",

            f"Evening, {name}. I'm here whenever you need me.",

            f"The evening is young, {name}. What shall we do?"

        ])

    else:

        return _pick_unique("late_evening", [

            f"Still going, {name}? Impressive.",

            f"Late night session, {name}?",

            f"Good evening, {name}.",

            f"Pulling an all-nighter, {name}?",

            f"The night is dark, but Kree is awake, {name}.",

            f"Need anything before bed, {name}?",

            f"Night mode, {name}. What can I do for you?",

            f"Late night, {name}. Let's make it count."

        ])

class ContextTTSEngine:

    """Pre-generates the context greeting as an MP3 using high-quality Edge TTS in the background."""

    REFRESH_INTERVAL_SECONDS = 300

    def __init__(self):

        import os

        import warnings

        os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

        warnings.filterwarnings("ignore", category=UserWarning, module="pygame.pkgdata")

        import pygame

        self.last_text = ""

        self.tts_path = SOUNDS_DIR / "active_greeting.mp3"

        self.running = True

        self.stop_event = threading.Event()

        try:

            pygame.mixer.init()

        except: pass

        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self):

        self.running = False

        self.stop_event.set()

    def _loop(self):

        from kree.memory.config_manager import load_audio_settings

        try:

            from kree.core.user_profile import get_user_profile

        except Exception:

            get_user_profile = None

        while self.running:

            try:

                profile_name = "friend"

                if get_user_profile is not None:

                    try:

                        profile = get_user_profile() or {}

                        profile_name = (profile.get("name") or "friend").strip() or "friend"

                    except Exception:

                        profile_name = "friend"

                current = _build_contextual_greeting(profile_name)

                settings = load_audio_settings()

                gemini_voice = settings.get("kree_voice", "Kore")

                edge_voice = {

                    "Aoede": "en-US-AriaNeural",

                    "Kore": "en-US-JennyNeural",

                    "Puck": "en-US-GuyNeural",

                    "Charon": "en-US-ChristopherNeural"

                }.get(gemini_voice, "en-US-JennyNeural")

                import edge_tts

                import asyncio

                if current != self.last_text or not hasattr(self, 'last_voice') or self.last_voice != edge_voice:

                    self.tts_path.parent.mkdir(parents=True, exist_ok=True)

                    loop = asyncio.new_event_loop()

                    asyncio.set_event_loop(loop)

                    try:

                        loop.run_until_complete(edge_tts.Communicate(current, edge_voice).save(str(self.tts_path)))

                    finally:

                        loop.close()

                    self.last_text = current

                    self.last_voice = edge_voice

            except Exception:

                pass

            if self.stop_event.wait(self.REFRESH_INTERVAL_SECONDS):

                break

_memory_turn_counter = 0

_memory_turn_lock = threading.Lock()

_MEMORY_EVERY_N_TURNS = 5

_last_memory_input = ""

def _update_memory_async(user_text: str, jarvis_text: str) -> None:

    """

    Multilingual memory updater.

    Model  : gemini-2.5-flash-lite (lowest cost)

    Stage 1: Quick YES/NO check  -> ~5 tokens output

    Stage 2: Full extraction     -> only if Stage 1 says YES

    Result : ~80% fewer API calls vs original

    """

    global _memory_turn_counter, _last_memory_input

    with _memory_turn_lock:

        _memory_turn_counter += 1

        _last_memory_input += f"USER: {user_text}\nKREE: {jarvis_text}\n"

        if _memory_turn_counter < _MEMORY_EVERY_N_TURNS:

            return

        chunk_to_process = _last_memory_input

        _last_memory_input = ""

        _memory_turn_counter = 0

    def worker():

        try:

            from google import genai as genai_sync # type: ignore[import]

            client = genai_sync.Client(api_key=_get_api_key())

            from kree.core.version import MODEL_FLASH_LITE

            # Check if there is a fact

            check_prompt = "Is there a new permanent fact or preference to remember about the user here? Reply only YES or NO.\n\n" + chunk_to_process

            res_check = client.models.generate_content(model=MODEL_FLASH_LITE, contents=check_prompt)

            if "yes" not in res_check.text.strip().lower():

                return

            ext_prompt = (

                "Extract bullet points of new facts or preferences about the user. Do not include random chat.\n\n"

                f"{chunk_to_process}"

            )

            res_ext = client.models.generate_content(model=MODEL_FLASH_LITE, contents=ext_prompt)

            # Logic to update memory would go here

            print(f"[Memory] ✅ Updated: {res_ext.text.strip()}")

        except Exception as e:

            if "429" not in str(e):

                print(f"[Memory] ⚠️ {e}")

    threading.Thread(target=worker, daemon=True).start()

from kree.core.tool_registry import TOOL_DECLARATIONS

class JarvisLive:

    # ── Sensitive tools that require PIN re-verification after session timeout ──

    _SENSITIVE_TOOLS = {

        "productivity_manager", "file_controller", "cmd_control",

        "browser_control", "desktop_control", "computer_control",

    }

    _SESSION_TIMEOUT_SECONDS = 1800  # 30 minutes

    def __init__(self, ui: JarvisUI):

        self.ui: JarvisUI                          = ui

        self.session: Any                          = None

        self.audio_in_queue: Optional[asyncio.Queue[Any]] = None

        self.out_queue: Optional[asyncio.Queue[Any]]      = None

        self._loop: Optional[asyncio.AbstractEventLoop]   = None

        self._welcomed: bool                               = False

        self.sync_audio_out_queue: Any                     = None

        self.bot_is_speaking: bool                         = False

        self._pending_open_and_delegate: Optional[dict[str, str]] = None

        self._quick_task_lock = threading.Lock()

        self._audio_settings = load_audio_settings()

        self._mic_active = True  # FORCE MIC ACTIVE ON BOOT SO VOICE WORKS IMMEDIATELY

        self._cam_active = bool(self._audio_settings.get("cam_enabled", False))

        self._vad_rising = int(self._audio_settings.get("vad_threshold_rising", 220) or 220)

        self._vad_falling = int(self._audio_settings.get("vad_threshold_falling", 160) or 160)

        self._partial_confidence_min = float(self._audio_settings.get("partial_confidence_min", 0.62) or 0.62)

        self._partial_flush_seconds = float(self._audio_settings.get("partial_flush_seconds", 2.6) or 2.6)

        self._tool_gate_window_seconds = float(self._audio_settings.get("tool_gate_window_seconds", 8.0) or 8.0)

        self._voice_command_armed_until = 0.0

        self._armed_tool_budget = 0

        self._last_pin_verified_at: float = time.time()  # V4 session timeout

        self._session_pin_verified: bool = True          # assume verified at boot

        self._last_user_turn: float = time.time()        # Initialize last user turn timestamp

        self._whisper_mode: bool = False                 # Set by wake word detector

        self.system_tray = None                          # Set by runner() on boot

        self._wakeword_detector = None                   # Set by runner() on boot

        # Push-to-talk-on-wake: temporary mic unmute triggered by wake word while mic is off

        self._mic_ptt_active: bool = False               # True while PTT window is open

        self._mic_ptt_silence_chunks: int = 0            # Consecutive silent chunks counted

        self._shutting_down: bool = False                 # Set True during shutdown to stop mic recovery

        # Register text callback immediately so UI can send commands from the start

        self.ui.on_user_text = self.on_user_text

        self._trigger_engine = TriggerEngine(self._on_trigger_fired)

        self._trigger_engine.start()

        try:

            self.context_tts = ContextTTSEngine()

        except Exception as e:

            print(f"[JARVIS] Failed to initialize ContextTTSEngine: {e}")

            self.context_tts = None

        self._telemetry = TelemetryLogger(BASE_DIR, load_telemetry_settings())

        self._telemetry.set_context(component="main", model=LIVE_MODEL)

        self._trace(TelemetryEvents.SESSION_INIT, "Kree runtime initialized")

        from kree.core.llm_gateway import gateway

        gateway.live_instance = self

    def _on_trigger_fired(self, action: dict, bypass_voice: bool = False):

        payload = action.get("payload", "")

        if action.get("type") == "voice_command" and payload:

            print(f"[JARVIS] ⚡ Trigger Event: {payload} (Silent: {bypass_voice})")

            self._arm_command_window(payload)

            if bypass_voice:

                self.ui.write_log(f"System Trigger: {payload}")

                self.on_user_text(payload)

            else:

                if self.session and self._loop:

                    async def _send():

                         try:

                             await self.session.send_client_content(

                                 turns={"parts": [{"text": f"SYSTEM EVENT: {payload}. Please analyze and respond to the user immediately."}]},

                                 turn_complete=True

                             )

                         except Exception as e:

                             print(f"[JARVIS] Failed to inject trigger: {e}")

                    asyncio.run_coroutine_threadsafe(_send(), self._loop)

        self._last_user_transcript = ""

    def _trace(self, event_type: str, message: str = "", **fields: Any) -> None:

        telemetry = getattr(self, "_telemetry", None)

        if telemetry is None:

            return

        try:

            telemetry.event(event_type, message, **fields)

        except Exception:

            pass

    @staticmethod

    def _normalize_text_input(text: Any) -> str:

        return unicodedata.normalize("NFC", str(text or "")).strip()

    @staticmethod

    def _sanitize_multilingual_transcript(text: str) -> str:

        t = JarvisLive._normalize_text_input(text)

        if not t:

            return ""

        low = t.casefold()

        if "<noise>" in low or "[noise]" in low:

            return ""

        # Reject repeated-character fragments often produced by ambient noise.

        for ch in "abcdefghijklmnopqrstuvwxyz":

            if ch * 4 in low:

                return ""

        # Reject mostly punctuation fragments.

        punct = sum(c in ".,;:!?-_/\\|[]{}()<>" for c in t)

        if punct / max(len(t), 1) > 0.5:

            return ""

        return t

    @staticmethod

    def _strip_leading_noise(text: str) -> str:

        cleaned = re.sub(r"^[\s\d\W_]+", "", (text or "").casefold())

        cleaned = re.sub(r"^(hey|ok|okay|please|uh|um|yo|listen)\b[\s,.-]*", "", cleaned)

        return cleaned.strip()

    def _should_arm_command_window(self, text: str) -> bool:

        cleaned = self._strip_leading_noise(text)

        if not cleaned:

            return False

        words = [part for part in cleaned.split() if part]

        first_five = " ".join(words[:5])

        # Direct or polite command, but only when it is clearly actionable.

        command_markers = (

            "open", "launch", "start", "run", "install", "download", "update",

            "search", "find", "check", "weather", "send", "remind", "call",

            "chrome", "youtube", "browser", "app",

        )

        polite_prefixes = (

            "can you", "could you", "would you", "will you",

            "please", "hey", "ok", "okay",

        )

        action_window = " ".join(words[:6])

        has_action = any(marker in action_window for marker in command_markers)

        short_enough = len(words) <= 10

        starts_like_command = cleaned.startswith(("open ", "launch ", "start ", "run ", "install ", "download ", "update ", "search ", "find ", "check ", "send ", "remind ", "call "))

        polite_request = cleaned.startswith(polite_prefixes)

        return has_action and short_enough and (starts_like_command or polite_request or any(marker in first_five for marker in command_markers))

    def _arm_command_window(self, source_text: str) -> None:

        self._last_user_transcript = self._sanitize_multilingual_transcript(source_text)

        self._voice_command_armed_until = time.monotonic() + self._tool_gate_window_seconds

        self._armed_tool_budget = 2

        # Manually trigger the trigger engine to force context accumulation immediately if supported

        try:

            if hasattr(self, '_trigger') and hasattr(self._trigger, 'manual_trigger'):

                self._trigger.manual_trigger(source_text)

        except Exception as e:

            print(f"[JARVIS] trigger engine manual_trigger skip: {e}")

    def _is_command_window_armed(self) -> bool:

        return time.monotonic() <= self._voice_command_armed_until and self._armed_tool_budget > 0

    def _consume_command_window(self) -> None:

        self._armed_tool_budget = max(0, int(self._armed_tool_budget) - 1)

        if self._armed_tool_budget <= 0:

            self._voice_command_armed_until = 0.0

    @staticmethod

    def _has_explicit_command_intent(text: str) -> bool:

        low = (text or "").casefold()

        if not low:

            return False

        markers = (

            "open", "launch", "start", "run", "install", "download", "update",

            "search", "weather", "send", "set reminder", "call", "chrome", "youtube",

            "kree", "jarvis", "please", "hey", "ok", "can you", "could you", "would you", "will you",

        )

        return any(m in low for m in markers)

    @staticmethod

    def _merge_partial(prev: str, new: str) -> str:

        """Merge streaming transcription chunks into a best-effort full sentence."""

        p = (prev or "").strip()

        n = (new or "").strip()

        if not n:

            return p

        if not p:

            return n

        # Common streaming case: latest text is cumulative.

        if n.startswith(p):

            return n

        if p.startswith(n):

            return p

        if n in p:

            return p

        if p in n:

            return n

        # Overlap-aware stitch (prefix/suffix) for fragmented chunks.

        max_olap = min(len(p), len(n), 40)

        for k in range(max_olap, 2, -1):

            if p[-k:].lower() == n[:k].lower():

                return (p + n[k:]).strip()

        # If partials are very different, prefer latest hypothesis instead of forcing append.

        sim = difflib.SequenceMatcher(None, p.lower(), n.lower()).ratio()

        if sim < 0.35:

            return n

        # Last resort: append unseen chunk.

        return (p + " " + n).strip()

    @staticmethod

    def _extract_open_and_ask_intent(text: str) -> dict[str, str] | None:

        """Parse requests like: open X and Y and ask Z to do Q."""

        pattern = re.compile(

            r"\bopen\s+(?P<targets>.+?)\s+and\s+ask\s+(?P<agent>[^,.;!?]+?)\s+to\s+(?P<prompt>.+)",

            re.IGNORECASE,

        )

        m = pattern.search(text)

        if not m:

            return None

        targets = m.group("targets").strip()

        agent = m.group("agent").strip()

        prompt = m.group("prompt").strip()

        if not targets or not agent or not prompt:

            return None

        return {"targets": targets, "agent": agent, "prompt": prompt}

    @staticmethod

    def _parse_direct_open_intent(text: str) -> dict[str, str] | None:

        """Parse direct launch requests like: open codex or open codex and github."""

        normalized = JarvisLive._normalize_text_input(text)

        if not normalized:

            return None

        low = normalized.lower()

        low = re.sub(r"^\s*(?:hey\s+|ok\s+|okay\s+|please\s+)?(?:kree|jarvis)\b[\s,:-]*", "", low, flags=re.IGNORECASE)

        low = re.sub(

            r"^\s*(?:can you|could you|would you|will you|can u|could u|would u|will u|please|hey|ok|okay)\b[\s,.-]*",

            "",

            low,

            flags=re.IGNORECASE,

        )

        if " and ask " in low:

            return None

        m = re.match(

            r"^(open|launch|start|run|switch\s+to|focus\s+on|focus|bring)\b\s+(?P<target>.+)$",

            low,

        )

        if not m:

            return None

        target = m.group("target").strip(" .,!?:;\"")

        if not target:

            return None

        # Detect mobile device markers BEFORE stripping helper phrases

        mobile_markers = ["on mobile", "on phone", "on android", "on ios", "on iphone", "on ipad", "in mobile", "in phone", "in android", "in ios", "in iphone", "my phone", "my mobile"]

        is_mobile = any(mk in target for mk in mobile_markers)

        target = re.split(r"\b(?:for me|please|so you can|so i can)\b", target, maxsplit=1)[0].strip(" .,!?:;\"")

        if not target:

            return None

        # For mobile commands, pass the FULL target (with mobile keywords) to open_app

        if is_mobile:

            return {"action": "open_app", "app_name": target}

        targets = [piece.strip(" .,!?:;\"") for piece in re.split(r"\s+(?:and|&)\s+|,\s*", target) if piece.strip(" .,!?:;\"")]

        if not targets:

            return None

        if len(targets) == 1:

            return {"action": "open_app", "app_name": low}

        return {

            "action": "openapps_automation",

            "targets": " and ".join(targets),

            "fallback": "browser",

        }

    @staticmethod

    def _parse_trace_intent(text: str) -> dict[str, Any] | None:

        normalized = JarvisLive._normalize_text_input(text).lower()

        if not normalized:

            return None

        normalized = re.sub(r"^\s*(hey\s+|ok\s+|okay\s+|please\s+)?(kree|jarvis)\b[\s,:-]*", "", normalized, flags=re.IGNORECASE)

        if not any(marker in normalized for marker in ("trace", "log", "session bundle", "export session")):

            return None

        if any(marker in normalized for marker in ("save", "export", "download")):

            return {"action": "export", "label": "session_trace"}

        if any(marker in normalized for marker in ("summary", "summarize", "summarise", "overview")):

            return {"action": "summary"}

        if any(marker in normalized for marker in ("status", "show", "view", "recent")):

            return {"action": "status"}

        return {"action": "export", "label": "session_trace"}

    def _trace_summary(self, limit: int = 500) -> str:

        telemetry = getattr(self, "_telemetry", None)

        log_file = getattr(telemetry, "log_file", None) if telemetry else None

        session_id = getattr(telemetry, "session_id", "") if telemetry else ""

        if not log_file or not session_id:

            return "Trace is not available right now."

        events = load_session_events(log_file, session_id, limit=limit)

        if not events:

            return "No trace events have been captured yet."

        # Aggregate metrics

        tool_use_counts: dict[str, int] = {}

        tool_fail_counts: dict[str, int] = {}

        durations: list[float] = []

        for event in events:

            event_type = event.get("event_type")

            if event_type == TelemetryEvents.TOOL_CALL:

                tool_name = event.get("tool", "unknown")

                tool_use_counts[tool_name] = tool_use_counts.get(tool_name, 0) + 1

            elif event_type == TelemetryEvents.TOOL_RESULT:

                tool_name = event.get("tool", "unknown")

                status = event.get("status")

                duration = event.get("duration")

                if status == "error" or (isinstance(event.get("message"), str) and "failed" in str(event.get("message")).lower()):

                    tool_fail_counts[tool_name] = tool_fail_counts.get(tool_name, 0) + 1

                if duration is not None:

                    try:

                        durations.append(float(duration))

                    except (ValueError, TypeError):

                        pass

        # Calculate statistics

        sorted_used = sorted(tool_use_counts.items(), key=lambda x: x[1], reverse=True)

        sorted_failed = sorted(tool_fail_counts.items(), key=lambda x: x[1], reverse=True)

        most_used_str = ", ".join(f"{name} ({count}x)" for name, count in sorted_used[:3]) or "None"

        most_failed_str = ", ".join(f"{name} ({count}x)" for name, count in sorted_failed[:3]) or "None"

        avg_time = f"{sum(durations) / len(durations):.2f}s" if durations else "N/A"

        return (

            "--- Anonymous User Analytics Summary ---\n"

            f"• Most Used Commands: {most_used_str}\n"

            f"• Most Failed Tools: {most_failed_str}\n"

            f"• Average Task Execution Time: {avg_time}\n"

            "---------------------------------------"

        )

    def _export_trace(self, label: str = "session_trace") -> str:

        try:

            telemetry = getattr(self, "_telemetry", None)

            if not telemetry:

                return "Telemetry logger not initialized, sir."

            trace_path = export_session_trace(BASE_DIR, telemetry, label=label)

            return f"Saved trace to {trace_path}"

        except Exception as e:

            return f"Failed to export trace: {e}"

    @staticmethod

    def _tool_context(name: str, args: dict[str, Any]) -> tuple[str, str]:

        app = (

            str(args.get("app_name") or args.get("app") or args.get("delegate_app") or "")

            .strip()

        )

        cmd = ""

        for k in ("command", "task", "goal", "description", "action", "task_name", "prompt"):

            val = args.get(k)

            if val:

                cmd = str(val).strip()

                break

        if not cmd:

            cmd = json.dumps(args)[:220]

        if not app and name == "openapps_automation":

            app = "Kree automation"

        return app, cmd

    def _resolve_pending_choice(self, text: str) -> bool:

        if hasattr(self, "pending_action") and self.pending_action and self.pending_action.get("type") == "chrome_profile_select":

            print("[PROFILE] Pending selection active")

            low = text.lower().strip()

            # Clean punctuation from user input

            low = re.sub(r'[.,\/#!$%\^&\*;:{}=\-_`~()?]', '', low).strip()

            profiles = self.pending_action.get("profiles", [])

            matched_profile = None

            for p in profiles:

                name = p["name"].lower().strip()

                folder = p["folder"].lower().strip()

                # Custom alias patterns

                aliases = [

                    name,

                    f"{name} account",

                    f"open {name}",

                    f"open {name} account",

                    f"launch {name}",

                    f"launch {name} account",

                    f"run {name}",

                    f"run {name} account",

                    f"start {name}",

                    f"start {name} account",

                    folder,

                    f"{folder} account"

                ]

                if low in aliases or any(alias == low for alias in aliases) or low == name or low == folder:

                    matched_profile = p

                    break

            if matched_profile:

                print(f"[PROFILE] Matched profile: {matched_profile['name']}")

                print(f"[PROFILE] Launching profile: {matched_profile['folder']}")

                self.pending_action = None

                # Set duplication check

                self._last_fast_path_app = "chrome"

                self._last_fast_path_time = time.time()

                def _launch():

                    try:

                        from kree.core.user_profile import update_user_profile

                        update_user_profile({"browser_profile": matched_profile['folder']})

                        r = open_app(

                            parameters={"app_name": "chrome"},

                            response=None,

                            player=self.ui,

                            session_memory=None,

                        )

                        self.ui.write_log(f"Kree: {r}")

                        self.speak(f"Opened Chrome account {matched_profile['name']}, sir.")

                    except Exception as e:

                        self.ui.write_log(f"Kree: Profile launch failed: {e}")

                threading.Thread(target=_launch, daemon=True).start()

                return True

            else:

                return False

        if not self._pending_open_and_delegate:

            return False

        def _resolve_pending():

            try:
                pending = self._pending_open_and_delegate
                
                r = openapps_automation(

                    parameters={

                        "action": "open_and_delegate",

                        "targets": pending.get("targets", ""),

                        "delegate_app": pending.get("agent", ""),

                        "prompt": pending.get("prompt", ""),

                        "fallback": text,

                    },

                    response=None,

                    player=self.ui,

                    session_memory=None,

                )

                self.ui.write_log(f"Kree: {r}")

                self.speak("Done. Proceeding with your selected option.")

            except Exception as e:

                self.ui.write_log(f"Kree: Failed to continue workflow: {e}")

        threading.Thread(target=_resolve_pending, daemon=True).start()

        return True

    @staticmethod

    def _parse_quick_package_intent(text: str) -> dict[str, str] | None:

        t = JarvisLive._normalize_text_input(text)

        if not t:

            return None

        low = t.lower()

        # Remove common assistant-address prefixes from the front for cleaner parsing.

        low = re.sub(r"^\s*(hey\s+|ok\s+|okay\s+|please\s+)?(kree|jarvis)\b[\s,:-]*", "", low, flags=re.IGNORECASE)

        if "check updates" in low or "check update" in low:

            return {"action": "check_updates"}

        if "update all" in low or "upgrade all" in low:

            return {"action": "update_all"}

        url_match = re.search(r"https?://\S+", low)

        if low.startswith("download ") and url_match:

            return {"action": "download_file", "url": url_match.group(0)}

        # Route broader natural-language commands to smart mode.

        quick_keywords = (

            "download",

            "install",

            "update",

            "upgrade",

            "search app",

            "find app",

            "is installed",

            "status",

        )

        if any(k in low for k in quick_keywords):

            return {"action": "auto", "query": low}

        m_install = re.match(r"^(install|download)\s+(.+)$", low)

        if m_install:

            target = m_install.group(2).strip(" .,!?")

            if target:

                return {"action": "install_app", "target": target}

        m_update = re.match(r"^(update|upgrade)\s+(.+)$", low)

        if m_update:

            target = m_update.group(2).strip(" .,!?")

            if target:

                return {"action": "update_app", "target": target}

        return None

    def hibernate(self):

        """Put Kree to sleep."""

        print("[JARVIS] 💤 Going to sleep mode...")

        self.ui.hibernate()

        if hasattr(self, 'system_tray') and self.system_tray:

            self.system_tray.set_offline()

        try:

            import winsound

            winsound.PlaySound(str(ASSETS_DIR / "sounds" / "sleep.wav"), winsound.SND_FILENAME | winsound.SND_ASYNC)

        except: pass

        if hasattr(self, 'wake_event'):

            self.wake_event.clear()

        self._welcomed = False

        # Abort the async connection safely if running

        if self._loop and self.out_queue:

            self._loop.call_soon_threadsafe(self.out_queue.put_nowait, b"SLEEP_SENTINEL")

    def wake(self, trigger_type="full", whisper=False):

        """

        Wake Kree from sleep.

        Args:

            trigger_type: "full" (chime + UI + greeting), "partial" (ears only, no UI), "priority" (instant, no greeting)

            whisper: True if the user spoke quietly — Kree responds quietly

        """

        if hasattr(self, 'wake_event') and self.wake_event.is_set():

            return

        self._whisper_mode = whisper

        self._last_user_turn = time.time()

        if trigger_type == "full":
            try:
                self.ui.wake()
            except Exception: pass

        if trigger_type == "partial":

            # Partial wake: just set the event so WebRTC connects, no UI or chime

            print("[JARVIS] Partial wake (ears only)")

            if hasattr(self, 'wake_event'):

                if not self.wake_event.is_set():

                    if self._loop:

                        self._loop.call_soon_threadsafe(self.wake_event.set)

                    else:

                        self.wake_event.set()

            return

        # Full wake or priority wake — prepare STT and play chime, and reveal UI
        print(f"[JARVIS] Waking up... (type={trigger_type}, whisper={whisper})")
        
        if hasattr(self, 'system_tray') and self.system_tray:
            self.system_tray.set_listening()

        # Immediately reveal the UI window so the user sees Kree respond
        if hasattr(self, 'ui') and self.ui:
            try:
                self.ui.wake()
                print("[JARVIS] UI window revealed")
            except Exception as e:
                print(f"[JARVIS] UI wake failed: {e}")

        if trigger_type != "priority":

            # Play short activation ding immediately
            try:
                import winsound
                winsound.PlaySound(str(ASSETS_DIR / "sounds" / "wake.wav"), winsound.SND_FILENAME | winsound.SND_ASYNC)
            except Exception: pass

        if hasattr(self, 'wake_event'):

            if not self.wake_event.is_set():

                if self._loop:

                    self._loop.call_soon_threadsafe(self.wake_event.set)

                else:

                    self.wake_event.set()

            # ALWAYS trigger PTT unmute if the mic is muted, even if this is the first wake!
            # Kree is awake — check if mic is muted and trigger PTT unmute

            mic_is_muted = not getattr(self.ui, "_mic_active", True)

            if mic_is_muted and not getattr(self, "_mic_ptt_active", False):

                print("[JARVIS] 🎙️ Wake word while mic muted — PTT unmute activated")

                self.push_to_talk_unmute()

    def push_to_talk_unmute(self, max_silence_seconds: float = None) -> None:

        """

        Temporarily unmute the mic after a wake-word trigger while mic is off.

        The mic stays open until the user has been silent for `max_silence_seconds`

        (measured by RMS of incoming audio chunks), then it automatically remutes.

        A hard timeout of 12 seconds is enforced as a safety net.

        """

        if max_silence_seconds is None:
            max_silence_seconds = float(self._audio_settings.get("ptt_silence_timeout_seconds", 3.0))

        import time as _time

        self._mic_ptt_active = True

        self._mic_ptt_silence_chunks = 0

        # Calculate silence threshold: chunks per second × max_silence_seconds

        # CHUNK_SIZE=1024, SEND_SAMPLE_RATE=16000 → ~15.6 chunks/sec

        chunks_per_sec = SEND_SAMPLE_RATE / CHUNK_SIZE

        self._mic_ptt_silence_limit = int(chunks_per_sec * max_silence_seconds)  # ~46 chunks at 3.0s

        self._mic_ptt_speech_rms_threshold = 100  # RMS below this = silence

        # Hard timeout fallback — auto-remute after 12 seconds no matter what

        _ptt_start = _time.monotonic()

        _MAX_PTT_SECONDS = 12.0

        def _safety_timeout():

            import time as _t

            _t.sleep(_MAX_PTT_SECONDS)

            if self._mic_ptt_active:

                print("[JARVIS] ⏱️ PTT safety timeout — remuting mic")

                self._mic_ptt_active = False

                self._mic_ptt_silence_chunks = 0

        threading.Thread(target=_safety_timeout, daemon=True).start()

        print(f"[JARVIS] 🔓 PTT unmuted (silence threshold: {self._mic_ptt_silence_limit} chunks, max: {_MAX_PTT_SECONDS}s)")

    def _normalize_conversational_routing(self, text: str) -> str:

        # Lowercase and clean

        t = text.lower().strip()

        # Trim punctuation

        t = re.sub(r'[.,\/#!$%\^&\*;:{}=\-_`~()?]', '', t).strip()

        # Strip trailing "please"

        t = re.sub(r'\s+please\s*$', '', t)

        # Action verbs

        action_verbs = ['open', 'close', 'launch', 'start', 'run', 'exit', 'quit', 'stop']

        # Check if conversational prefix exists before action verbs

        for verb in action_verbs:

            pattern = r'^(?:can\s+you\s+|could\s+you\s+|would\s+you\s+|will\s+you\s+|please\s+|hey\s+kree\s+|hey\s+jarvis\s+|kree\s+|jarvis\s+|hey\s+|okay\s+|ok\s+|yo\s+|listen\s+)*\b(' + verb + r'\b)'

            match = re.search(pattern, t)

            if match:

                start_idx = match.start(1)

                return t[start_idx:].strip()

        return t

    def on_user_text(self, text: str, from_voice: bool = False):

        """Called when user types a message in the UI or via voice."""

        try:

            logging.debug(f"[UI_TEXT] Processing: {text}")

            text = self._normalize_text_input(text)

            if not text:

                return

            print(f"[ROUTER] Raw: {text}")

            normalized = self._normalize_conversational_routing(text)

            print(f"[ROUTER] Normalized: {normalized}")

            # Resolve pending actions first!

            if self._resolve_pending_choice(text):

                return

            if not from_voice:

                self.ui.write_log(f"You: {text}")

            # --- Check Local Intent Router ---

            from kree.core.llm_gateway import KreeIntelligenceEngine

            router_engine = KreeIntelligenceEngine(live_instance=self)

            local_res = router_engine.try_local_route(normalized)

            if local_res is not None:

                self.ui.write_log(f"Kree: {local_res}")

                self.speak(local_res)

                return

            # Typed/processed input is considered explicit user intent and arms one tool-execution window.

            self._arm_command_window(text)

            logging.info(f"[UI_TEXT] Command normalized: {normalized}")

            low = normalized.lower().strip()

            # Update intent

            if "update kree" in low:

                logging.debug("[UI_TEXT] matched 'update'")

                from kree.core.updater import get_pending_update, install_pending_update

                pending = get_pending_update()

                if pending.get("available"):

                    _local_speech_voice(f"Installing update version {pending['version']} now sir. Kree will restart.")

                    self.ui.write_log(f"Kree: Installing update v{pending['version']}...")

                    install_pending_update()

                else:

                    _local_speech_voice("You're already on the latest version sir.")

                    self.ui.write_log("Kree: Already on the latest version.")

                return

            # Sleep intent

            sleep_triggers = ["go to sleep", "kree sleep", "goodnight kree", "that's all kree", "dismiss"]

            if any(trigger in low for trigger in sleep_triggers):

                logging.debug("[UI_TEXT] matched 'sleep'")

                _local_speech_voice("Sleeping sir.")

                self.hibernate()

                return

            # Voice enrollment command

            if "enroll my voice" in low or "register my voice" in low:

                logging.debug("[UI_TEXT] matched 'enroll'")

                detector = getattr(self, '_wakeword_detector', None)

                if detector:

                    _local_speech_voice("Recording your voiceprint. Please speak naturally for ten seconds.")

                    def _enroll():

                        try:

                            import time

                            time.sleep(2)  # Wait for TTS to finish

                            if detector.enroll_owner_voice():

                                _local_speech_voice("Voiceprint saved. I will only respond to your voice now.")

                            else:

                                _local_speech_voice("Voiceprint enrollment failed. Please try again.")

                        except Exception as e:

                            logging.error(f"[ENROLL] Thread failed: {e}")

                    threading.Thread(target=_enroll, daemon=True).start()

                else:

                    _local_speech_voice("Wake word detector not available.")

                return

            # ── Synonyms mapping ──

            # OPEN: open, launch, start, run

            # CLOSE: close, exit, quit, stop

            action_verb = None

            target = ""

            for v in ["open", "launch", "start", "run"]:

                if low.startswith(v + " "):

                    action_verb = "open"

                    target = low[len(v)+1:].strip()

                    break

            if not action_verb:

                for v in ["close", "exit", "quit", "stop"]:

                    if low.startswith(v + " "):

                        action_verb = "close"

                        target = low[len(v)+1:].strip()

                        break

            if action_verb:

                print(f"[ROUTER] Fast-path: {action_verb}")

                print(f"[ROUTER] Target: {target}")

                # ── Duplicate execution guard ────────────────────────

                # If the same app was launched via fast-path within the

                # last 3 seconds (e.g. LLM tool-call already handled

                # it), skip to avoid double-opening.

                _dedup_window = 3.0

                _prev_app = getattr(self, "_last_fast_path_app", None)

                _prev_time = getattr(self, "_last_fast_path_time", 0)

                if _prev_app and _prev_app == target and (time.time() - _prev_time) < _dedup_window:

                    print(f"[ROUTER] Duplicate blocked: '{target}' was opened {time.time() - _prev_time:.1f}s ago")

                    return

                # Dynamic Chrome profile matching logic

                from kree.core.user_profile import discover_chrome_profiles, update_user_profile

                profiles = discover_chrome_profiles()

                if "chrome" in target or any(p["name"].lower() in target for p in profiles):

                    # Check if user specified a profile in the command

                    matched_profile = None

                    if target != "chrome":

                        clean_target = target.replace("chrome", "").replace("account", "").strip()

                        for p in profiles:

                            p_name = p["name"].lower().strip()

                            p_folder = p["folder"].lower().strip()

                            if clean_target == p_name or clean_target == p_folder or clean_target in p_name:

                                matched_profile = p

                                break

                    if matched_profile:

                        # User specified profile - launch it directly!

                        self._last_fast_path_app = "chrome"

                        self._last_fast_path_time = time.time()

                        def _launch_profile():

                            try:

                                update_user_profile({"browser_profile": matched_profile['folder']})

                                r = open_app(

                                    parameters={"app_name": "chrome"},

                                    response=None,

                                    player=self.ui,

                                    session_memory=None,

                                )

                                self.ui.write_log(f"Kree: {r}")

                                self.speak(f"Opened Chrome account {matched_profile['name']}, sir.")

                            except Exception as e:

                                self.ui.write_log(f"Kree: Profile launch failed: {e}")

                        threading.Thread(target=_launch_profile, daemon=True).start()

                        return

                if action_verb == "open":

                    self._last_fast_path_app = target

                    self._last_fast_path_time = time.time()

                    def _open_fast():

                        try:

                            loading_msg = f"Kree: Opening {target} now..."

                            self.ui.write_log(loading_msg)

                            try:

                                import winsound

                                winsound.PlaySound("SystemDefault", winsound.SND_ALIAS | winsound.SND_ASYNC)

                            except: pass

                            self.speak("Opening it now.")

                            r = open_app(

                                parameters={"app_name": target},

                                response=None,

                                player=self.ui,

                                session_memory=None,

                            )

                            self.ui.write_log(f"Kree: {r}")

                        except Exception as e:

                            logging.error(f"[OPEN_FAST] Error: {e}")

                    threading.Thread(target=_open_fast, daemon=True).start()

                    return

                elif action_verb == "close":

                    self._last_fast_path_app = target

                    self._last_fast_path_time = time.time()

                    def _close_fast():

                        try:

                            self.ui.write_log(f"Kree: Closing {target} now...")

                            APP_MAP = _load_app_process_map()

                            process_name = APP_MAP.get(target.lower(), target)

                            killed = False

                            import psutil

                            for proc in psutil.process_iter(['name', 'pid']):

                                try:

                                    if proc.info['name'] and process_name.lower() in proc.info['name'].lower():

                                        proc.terminate()

                                        killed = True

                                except (psutil.NoSuchProcess, psutil.AccessDenied):

                                    pass

                            if killed:

                                self.speak(f"Closed {target} sir.")

                                self.ui.write_log(f"Kree: Closed {target}.")

                            else:

                                self.speak(f"Could not find {target} running sir.")

                                self.ui.write_log(f"Kree: Couldn't find {target} running.")

                        except Exception as e:

                            self.ui.write_log(f"Kree: Fast-path close error: {e}")

                    threading.Thread(target=_close_fast, daemon=True).start()

                    return

        except Exception as e:

            logging.error(f"[UI_TEXT] Fatal crash during text processing: {e}")

            logging.error(traceback.format_exc())

        quick_intent = self._parse_quick_package_intent(text)

        if quick_intent:

            def _run_quick_package_task():

                with self._quick_task_lock:

                    try:

                        r = downloader_updater(

                            parameters=quick_intent,

                            response=None,

                            player=self.ui,

                            session_memory=None,

                        )

                        self.ui.write_log(f"Kree: {r}")

                        self.speak(str(r))

                    except Exception as e:

                        self.ui.write_log(f"Kree: Package task failed: {e}")

            threading.Thread(target=_run_quick_package_task, daemon=True).start()

            return

        if "start kree automation environment" in low:

            def _start_env():

                try:

                    r = openapps_automation(

                        parameters={"action": "start_kree_automation_environment"},

                        response=None,

                        player=self.ui,

                        session_memory=None,

                    )

                    self.ui.write_log(f"Kree: {r}")

                    self.speak("Kree automation environment is starting now.")

                except Exception as e:

                    self.ui.write_log(f"Kree: Failed to start automation environment: {e}")

            threading.Thread(target=_start_env, daemon=True).start()

            return

        trace_intent = self._parse_trace_intent(text)

        if trace_intent:

            def _run_trace_action():

                with self._quick_task_lock:

                    try:

                        action = trace_intent.get("action")

                        if action == "summary":

                            r = self._trace_summary()

                        elif action == "status":

                            telemetry = getattr(self, "_telemetry", None)

                            log_file = getattr(telemetry, "log_file", None) if telemetry else None

                            session_id = getattr(telemetry, "session_id", "") if telemetry else ""

                            event_count = len(load_session_events(log_file, session_id, limit=25)) if log_file and session_id else 0

                            r = f"Trace is active for session {session_id}. Recent events captured: {event_count}."

                        else:

                            r = self._export_trace(trace_intent.get("label", "session_trace"))

                        self.ui.write_log(f"Kree: {r}")

                        self.speak(str(r))

                    except Exception as e:

                        self.ui.write_log(f"Kree: Trace action failed: {e}")

            threading.Thread(target=_run_trace_action, daemon=True).start()

            return

        direct_open = self._parse_direct_open_intent(text)

        if direct_open:

            def _run_direct_open():

                with self._quick_task_lock:

                    try:

                        if direct_open.get("action") == "open_app":

                            r = open_app(

                                parameters={"app_name": direct_open.get("app_name", "")},

                                response=None,

                                player=self.ui,

                                session_memory=None,

                            )

                            if isinstance(r, str) and r.startswith("__BROADCAST_INTENT__"):

                                target = r.split(":", 1)[1]

                                if hasattr(self, 'mobile_bridge') and hasattr(self, '_loop'):

                                    asyncio.run_coroutine_threadsafe(

                                        self.mobile_bridge.broadcast({"type": "intent", "action": "open_app", "target": target}),

                                        self._loop

                                    )

                                r = f"Opening {target} on your mobile device, sir."

                        else:

                            r = openapps_automation(

                                parameters={

                                    "action": "open_and_delegate",

                                    "targets": direct_open.get("targets", ""),

                                    "delegate_app": "",

                                    "prompt": "",

                                    "fallback": direct_open.get("fallback", "browser"),

                                },

                                response=None,

                                player=self.ui,

                                session_memory=None,

                            )

                        self.ui.write_log(f"Kree: {r}")

                        self.speak(str(r))

                    except Exception as e:

                        self.ui.write_log(f"Kree: Direct open failed: {e}")

            threading.Thread(target=_run_direct_open, daemon=True).start()

            return

        parsed = self._extract_open_and_ask_intent(text)

        # Heuristic fallback for imperfect ASR when user clearly asks Codex+GitHub app workflow.

        if not parsed and ("codex" in low and "github" in low and ("app" in low or "build" in low or "make" in low)):

            parsed = {

                "targets": "codex and github",

                "agent": "codex",

                "prompt": text if len(text.strip()) >= 8 else "Build an app based on the user request.",

            }

        if parsed:

            delegate = parsed["agent"].strip().lower()

            if delegate in {"it", "them", "that", "this"}:

                first_target = parsed["targets"].split(" and ")[0].split(",")[0].strip()

                if first_target:

                    parsed["agent"] = first_target

            def _macro_generic():

                try:

                    r = openapps_automation(

                        parameters={

                            "action": "open_and_delegate",

                            "targets": parsed["targets"],

                            "delegate_app": parsed["agent"],

                            "prompt": parsed["prompt"],

                            "fallback": "ask",

                        },

                        response=None,

                        player=self.ui,

                        session_memory=None,

                    )

                    if isinstance(r, str) and r.startswith("QUESTION:"):

                        self._pending_open_and_delegate = {

                            "targets": parsed["targets"],

                            "agent": parsed["agent"],

                            "prompt": parsed["prompt"],

                        }

                        q = r.replace("QUESTION:", "").strip()

                        self.ui.write_log(f"Kree: {q}")

                        self.speak(q)

                        return

                    # If native Codex path likely opened, try to type user prompt directly.

                    if ("native:" in str(r).lower()) and ("codex" in parsed["agent"].lower()):

                        try:

                            computer_control(

                                parameters={"action": "focus_window", "title": "ChatGPT"},

                                player=self.ui,

                            )

                            time.sleep(0.4)

                            computer_control(

                                parameters={

                                    "action": "smart_type",

                                    "text": parsed["prompt"],

                                    "clear_first": False,

                                },

                                player=self.ui,

                            )

                            computer_control(

                                parameters={"action": "press", "key": "enter"},

                                player=self.ui,

                            )

                        except Exception:

                            pass

                    self.ui.write_log(f"Kree: {r}")

                    self.speak("Launching your automation workflow now.")

                except Exception as e:

                    self.ui.write_log(f"Kree: Automation failed: {e}")

            threading.Thread(target=_macro_generic, daemon=True).start()

            return

        if getattr(self, "_loop", None) and getattr(self, "out_queue", None):

            self._loop.call_soon_threadsafe(self.out_queue.put_nowait, {"text": text})

        else:

            self.ui.write_log("SYS: Gemini Live connection not active.")

    def speak(self, text: str):

        """Thread-safe chunked speak — prevents Gemini Live TTS glitches on long text."""

        print("RAW TTS INPUT (speak):", repr(text))

        try:

            print("TTS INPUT CHAR CODES (speak):", [ord(c) for c in text])

        except Exception:

            pass

        import re

        loop = self._loop

        session = self.session

        if not loop or not session:

            _local_speech_voice(text)

            return

        # Long replies are smoother and more stable when rendered through the local

        # Edge TTS path instead of being broken into multiple Gemini Live chunks.

        if len(text) > 360 or len(re.split(r'(?<=[.!?])\s+', text)) > 4:

            _local_speech_voice(text)

            return

        # Split text logic (keep chunks larger to avoid voice restarts).

        chunks = []

        current = ""

        sentences = re.split(r'(?<=[.!?])\s+', text)

        for s in sentences:

            if len(current) + len(s) <= 320:

                current += s + " "

            else:

                if current.strip(): chunks.append(current.strip())

                if len(s) > 320:

                    import textwrap

                    for wrap in textwrap.wrap(s, 300, break_long_words=False):

                        chunks.append(wrap)

                    current = ""

                else:

                    current = s + " "

        if current.strip():

            chunks.append(current.strip())

        if not chunks: return

        async def _chunked_sender():

            for i, chunk in enumerate(chunks):

                # Wait for previous chunk audio to finish playing

                if i > 0:

                    import asyncio

                    while self.bot_is_speaking or not self.sync_audio_out_queue.empty():

                        await asyncio.sleep(0.1)

                try:

                    await session.send_client_content(

                        turns={"parts": [{"text": chunk}]},

                        turn_complete=True

                    )

                except Exception as e:

                    print(f"[JARVIS] ⚠️ speak() failed on chunk: {e}")

        try:

            current_loop = asyncio.get_running_loop()

            if current_loop is loop:

                loop.create_task(_chunked_sender())

            else:

                asyncio.run_coroutine_threadsafe(_chunked_sender(), loop)

        except RuntimeError:

            asyncio.run_coroutine_threadsafe(_chunked_sender(), loop)

    def _build_config(self) -> Any:

        _, types = _ensure_genai_sdk()

        from datetime import datetime 

        memory  = load_memory()

        mem_str, self._injected_keys = format_memory_for_prompt(memory)

        # Prioritize Language Constraints at the very top of the logic

        sys_prompt = (

            "<STRICT_ENGLISH_PROTOCOL>\n"

            "YOUR_VOICE & LANGUAGE: You MUST ALWAYS speak and reply in English ONLY.\n"

            "USER_INPUT: The user may speak with an Indian subcontinent accent or use broken English. Understand their intent but NEVER reply or output in Vernacular scripts (like Malayalam, Hindi, Tamil) or any language other than English.\n"

            "ADDRESSING: Respond to direct user commands without requiring a wake phrase.\n"

            "STRICT_MODE: ON\n"

            "INSTRUCTIONS:\n"

            "1. You are Kree, an advanced, highly capable AI assistant for a power user.\n"

            "2. Ignore random static/noise.\n"

            "3. ALWAYS reply in crisp, professional American English.\n"

            "4. Be confident — just respond to commands, do not explain your language limitations.\n"

            "</STRICT_ENGLISH_PROTOCOL>\n\n"

        )

        sys_prompt += _load_system_prompt()

        sys_prompt += (

            "\n\n<KREE_AUTOMATION_ROUTING>\n"

            "When user asks 'Start Kree automation environment', call tool openapps_automation "

            "with action='start_kree_automation_environment'.\n"

            "When user asks things like 'open X and Y and ask Z to ...', call openapps_automation "

            "with action='open_and_delegate', targets='X and Y', delegate_app='Z', prompt='...'.\n"

            "When user asks to save, export, summarize, or inspect the current session trace, call tool session_trace.\n"

            "When user asks to inspect OpenApps capabilities, use list_apps/list_agents/list_tasks and summarize.\n"

            "When user asks about legal/copyright safety for OpenApps, call action='license_info'.\n"

            "For opening normal desktop apps, continue using open_app.\n"

            "When user asks for real-time information, news, current events, or requests to search/find on the web, use the web_search tool with the search query.\n"

            "</KREE_AUTOMATION_ROUTING>\n"

        )

        now      = datetime.now()

        time_str = now.strftime("%A, %B %d, %Y — %I:%M %p")

        time_ctx = (

            f"[CURRENT DATE & TIME]\n"

            f"Right now it is: {time_str}\n"

            f"Use this to calculate exact times for reminders. "

            f"If user says 'in 2 minutes', add 2 minutes to this time.\n\n"

        )

        if mem_str:

            sys_prompt = time_ctx + mem_str + "\n\n" + sys_prompt

        else:

            sys_prompt = time_ctx + sys_prompt

        try:

            from kree.memory.config_manager import load_audio_settings # type: ignore[import]

            voice_name_config = load_audio_settings().get("kree_voice", "Kore")

        except Exception:

            voice_name_config = "Kore"

        # Build realtime VAD config — tighter end-of-speech window for faster responses

        try:

            realtime_cfg = types.RealtimeInputConfig(

                automatic_activity_detection=types.AutomaticActivityDetection(

                    # Reduce silence required before Gemini declares end-of-speech.

                    # Default is 1.0s. Set to 0.45s for fast, snappy speakers.

                    silence_duration_threshold=0.45,

                    # Prefix padding — how much speech must be detected before it's "real"

                    speech_start_buffer_duration=0.1,

                )

            )

        except Exception:

            # Fallback: older SDK builds may not have these fields yet

            realtime_cfg = None

        cfg_kwargs = dict(

            response_modalities=["AUDIO"],

            output_audio_transcription={},

            input_audio_transcription=types.AudioTranscriptionConfig(),

            system_instruction=sys_prompt,

            tools=[{"function_declarations": TOOL_DECLARATIONS}],

            # Server-side VAD enabled — Gemini handles turn detection for instant response

            speech_config=types.SpeechConfig(

                language_code="en-US",

                voice_config=types.VoiceConfig(

                    prebuilt_voice_config=types.PrebuiltVoiceConfig(

                        voice_name=voice_name_config

                    )

                ),

            ),

        )

        if realtime_cfg is not None:

            cfg_kwargs["realtime_input_config"] = realtime_cfg

        return types.LiveConnectConfig(**cfg_kwargs)

    async def _execute_tool(self, fc) -> Any:

        _, types = _ensure_genai_sdk()

        name = fc.name

        args = dict(fc.args or {})

        # Normalize common free-text fields to avoid Unicode drift between ASR, model, and tool layer.

        import kree.core.sanitizer as sanitizer

        for k in ("target", "query", "app", "app_name", "description", "task", "prompt", "text", "command"):

            if k in args and args[k] is not None:

                val = self._normalize_text_input(args[k])

                # Sanitize Command Checking

                safe_val, err = sanitizer.sanitize_command(val)

                if err:

                    print(f"[JARVIS] 🛡️ Security Block: {err}")

                    return types.FunctionResponse(

                        id=fc.id,

                        name=name,

                        response={"result": err},

                    )

                args[k] = safe_val

        if name == "downloader_updater" and "target" in args:

            target_val = str(args.get("target") or "").strip()

            if len(target_val) > 120:

                target_val = target_val[:120].strip()

            args["target"] = target_val

        dangerous_tools = {"computer_control"}

        if name in dangerous_tools and not self._is_command_window_armed():

            msg = (

                "Blocked tool execution because no recent command window is active. "

                "Speak your command clearly and directly."

            )

            self._trace(TelemetryEvents.TOOL_BLOCKED, msg, tool=name, reason="unarmed", args=args)

            print(f"[JARVIS] 🛡️ Tool blocked: {name} (unarmed)")

            return types.FunctionResponse(

                id=fc.id,

                name=name,

                response={"result": msg},

            )

        if name in dangerous_tools and not self._has_explicit_command_intent(self._last_user_transcript):

            msg = (

                "Blocked tool execution because transcript intent was not explicit enough. "

                "Please repeat with a clear command."

            )

            self._trace(TelemetryEvents.TOOL_BLOCKED, msg, tool=name, reason="weak-intent", args=args)

            print(f"[JARVIS] 🛡️ Tool blocked: {name} (weak-intent)")

            return types.FunctionResponse(

                id=fc.id,

                name=name,

                response={"result": msg},

            )

        # Consume the window only for gated tools so safe app launches are not blocked.

        if name in dangerous_tools:

            self._consume_command_window()

        # ── V4 SESSION TIMEOUT: Re-verify PIN for sensitive tools ─────────────

        if name in self._SENSITIVE_TOOLS:

            elapsed = time.time() - self._last_pin_verified_at

            if elapsed > self._SESSION_TIMEOUT_SECONDS:

                self._session_pin_verified = False

                print(f"[JARVIS] 🔒 Tool blocked: {name} (session timeout — PIN needed)")

                self._trace(TelemetryEvents.TOOL_BLOCKED, f"Session expired for {name}", tool=name, reason="session_timeout")

                # Trigger the PIN challenge overlay on the UI

                try:

                    self.ui._api.request_pin_challenge()

                except Exception:

                    pass

                try:

                    _local_speech_voice("Just confirming it's you. What's your PIN?")

                except Exception:

                    pass

                # Poll for the flag file written by verify_session_pin in ui.py

                pin_flag = BASE_DIR / "memory" / "session_pin_ok.json"

                waited = 0

                while waited < 120:  # Wait up to 2 minutes for PIN

                    if pin_flag.exists():

                        try:

                            data = json.loads(pin_flag.read_text())

                            self._last_pin_verified_at = data.get("verified_at", time.time())

                            self._session_pin_verified = True

                            pin_flag.unlink(missing_ok=True)

                            print("[JARVIS] ✅ Session re-verified via PIN. Continuing tool execution.")

                            break  # PIN accepted — fall through to run the tool

                        except Exception:

                            pass

                    await asyncio.sleep(1)

                    waited += 1

                if not self._session_pin_verified:

                    msg = (

                        "Session verification timed out. "

                        "Please verify your PIN and try again."

                    )

                    return types.FunctionResponse(

                        id=fc.id,

                        name=name,

                        response={"result": msg},

                    )

        tool_start_time = time.time()

        self._trace(TelemetryEvents.TOOL_CALL, f"Tool call: {name}", tool=name, args=args, start_time=tool_start_time)

        print(f"[JARVIS] 🔧 TOOL: {name}  ARGS: {args}")

        loop   = asyncio.get_event_loop()

        result = "Done."

        app_ctx, cmd_ctx = self._tool_context(name, args)

        self.ui.show_action_loading(name, app_ctx, cmd_ctx)

        self.ui.push_action_log(f"Starting {name}")

        if app_ctx:

            self.ui.push_action_log(f"App: {app_ctx}")

        if cmd_ctx:

            self.ui.push_action_log(f"Command: {cmd_ctx[:180]}")

        self._broadcast_mobile_state('executing')

        try:

            if name == "trigger_macro":

                try:

                    import kree.core.automations as autos

                    import kree.core.execution_engine as engine

                    chain_name = args.get("chain_name")

                    chain_tasks = autos.get_chain(chain_name)

                    if chain_tasks:

                        # Launch concurrently but do not block the entire event loop so Gemini can still respond instantly

                        loop.create_task(engine.run_parallel_tasks(chain_tasks, self.session))

                        result = f"Successfully triggered macro chain: {chain_name}."

                    else:

                        result = f"Failed to find a configured chain named '{chain_name}'."

                except Exception as e:

                    result = f"Failed to execute macro: {e}"

            elif name == "open_app":

                app_name = args.get("app_name", "").strip()

                _prev_app = getattr(self, "_last_fast_path_app", None)

                _prev_time = getattr(self, "_last_fast_path_time", 0)

                if _prev_app and _prev_app.lower() == app_name.lower() and (time.time() - _prev_time) < 3.5:

                    print(f"[ROUTER] Duplicate blocked (tool-call): '{app_name}' was opened recently via fast-path")

                    r = f"App '{app_name}' is already open."

                else:

                    r = await loop.run_in_executor(

                        None, functools.partial(open_app, parameters=args, response=None, player=self.ui)  # type: ignore[arg-type]

                    )

                if isinstance(r, str) and r.startswith("__BROADCAST_INTENT__"):

                    target = r.split(":", 1)[1]

                    if hasattr(self, 'mobile_bridge'):

                        await self.mobile_bridge.broadcast({"type": "intent", "action": "open_app", "target": target})

                    result = f"Sent mobile intent to open {target}."

                elif isinstance(r, str) and r.strip():

                    result = r

                else:

                    result = f"Opened {args.get('app_name')} successfully."

            elif name == "openapps_automation":

                r = await loop.run_in_executor(

                    None, functools.partial(  # type: ignore[arg-type]

                        openapps_automation,

                        parameters=args,

                        response=None,

                        player=self.ui,

                        session_memory=None,

                    )

                )

                if isinstance(r, str) and r.strip():

                    result = r

                else:

                    result = "OpenApps automation completed."

                if isinstance(result, str) and result.startswith("QUESTION:"):

                    q = result.replace("QUESTION:", "").strip()

                    self._pending_open_and_delegate = {

                        "targets": str(args.get("targets", "")),

                        "agent": str(args.get("delegate_app", "")),

                        "prompt": str(args.get("prompt", "")),

                    }

                    self.ui.write_log(f"Kree: {q}")

                    self.speak(q)

                    result = q

            elif name == "downloader_updater":

                r = await loop.run_in_executor(

                    None, functools.partial(  # type: ignore[arg-type]

                        downloader_updater,

                        parameters=args,

                        response=None,

                        player=self.ui,

                        session_memory=None,

                    )

                )

                result = r or "Download/update action completed."

            elif name == "turboquant_helper":

                r = await loop.run_in_executor(

                    None, functools.partial(  # type: ignore[arg-type]

                        turboquant_helper,

                        parameters=args,

                        response=None,

                        player=self.ui,

                        session_memory=None,

                    )

                )

                result = r or "TurboQuant helper completed."

            elif name == "session_trace":

                trace_action = str(args.get("action", "")).strip().lower()

                trace_label = str(args.get("label", "session_trace")).strip() or "session_trace"

                trace_limit = int(args.get("limit", 200) or 200)

                if trace_action == "summary":

                    result = self._trace_summary(limit=trace_limit)

                elif trace_action == "status":

                    telemetry = getattr(self, "_telemetry", None)

                    log_file = getattr(telemetry, "log_file", None) if telemetry else None

                    session_id = getattr(telemetry, "session_id", "") if telemetry else ""

                    event_count = len(load_session_events(log_file, session_id, limit=min(trace_limit, 50))) if log_file and session_id else 0

                    result = f"Trace is active for session {session_id}. Recent events captured: {event_count}."

                else:

                    result = self._export_trace(label=trace_label)

            elif name == "weather_report":

                r = await loop.run_in_executor(

                    None, functools.partial(weather_action, parameters=args, player=self.ui)  # type: ignore[arg-type]

                )

                result = r or f"Weather report for {args.get('city')} delivered."

            elif name == "browser_control":

                r = await loop.run_in_executor(

                    None, functools.partial(browser_control, parameters=args, player=self.ui)  # type: ignore[arg-type]

                )

                result = r or "Browser action completed."

            elif name == "file_controller":

                r = await loop.run_in_executor(

                    None, functools.partial(file_controller, parameters=args, player=self.ui)  # type: ignore[arg-type]

                )

                result = r or "File operation completed."

            elif name == "productivity_manager":

                r = await loop.run_in_executor(

                    None, functools.partial(productivity_manager, parameters=args, player=self.ui)  # type: ignore[arg-type]

                )

                result = r or "Productivity task completed."

            elif name == "safe_calculator":

                expression = args.get("expression", "")

                r = await loop.run_in_executor(

                    None, functools.partial(safe_calculator, expression=expression)

                )

                result = r

            elif name == "smart_trigger":

                try:

                    action_type = args.get("action", "")

                    if action_type == "create":

                        # We must send it to the trigger engine instance

                        self._trigger_engine.add_trigger({

                            "id": f"trig_{int(time.time())}",

                            "name": args.get("name", "Unnamed Trigger"),

                            "type": args.get("trigger_type"),

                            "condition": {

                                "metric": args.get("metric"),

                                "operator": args.get("operator"),

                                "value": args.get("value")

                            },

                            "action": {"type": "voice_command", "payload": args.get("action_to_take")},

                            "silent": args.get("silent", True),

                            "cooldown_seconds": 300

                        })

                        result = f"Created trigger: {args.get('name')}"

                    elif action_type == "remove":

                        self._trigger_engine.remove_trigger(args.get("id_to_remove", ""))

                        result = "Trigger removed."

                    else:

                        result = "Invalid action for smart_trigger."

                except Exception as e:

                    result = f"Failed to modify trigger: {e}"

            elif name == "send_message":

                r = await loop.run_in_executor(

                    None, functools.partial(  # type: ignore[arg-type]

                        send_message,

                        parameters=args, response=None,

                        player=self.ui, session_memory=None

                    )

                )

                result = r or f"Message sent to {args.get('receiver')}."

            elif name == "reminder":

                r = await loop.run_in_executor(

                    None, functools.partial(reminder, parameters=args, response=None, player=self.ui)  # type: ignore[arg-type]

                )

                result = r or f"Reminder set for {args.get('date')} at {args.get('time')}."

            elif name == "youtube_video":

                r = await loop.run_in_executor(

                    None, functools.partial(youtube_video, parameters=args, response=None, player=self.ui)  # type: ignore[arg-type]

                )

                result = r or "Done."

            elif name == "screen_process":

                angle = str(args.get("angle") or "screen").lower().strip()

                text_prompt = str(args.get("text") or "").strip()

                # Import capture functions from screen_processor

                from kree.actions.screen_processor import _capture_screenshot, _capture_camera

                try:

                    if angle == "camera":

                        image_bytes = _capture_camera()

                        mime_type = "image/jpeg"

                        print("[JARVIS] screen_process: captured camera")

                    else:

                        image_bytes = _capture_screenshot()

                        # We use image/jpeg since it's universally accepted and smaller

                        mime_type = "image/jpeg"

                        print("[JARVIS] screen_process: captured screenshot")

                except Exception as e:

                    print(f"[JARVIS] screen_process: capture failed: {e}")

                    image_bytes = None

                if image_bytes and self.session:

                    # Send the image directly to the main live session

                    from google.genai import types as _types

                    blob = _types.Blob(data=image_bytes, mime_type=mime_type)

                    # We send the image first, then follow it with the text/question as normal response

                    await self.session.send_realtime_input(media=blob)

                    # Use the user text prompt as the result of the tool execution so that Kree continues

                    # in the context of the user's question, looking at the image we just pushed.

                    result = f"Captured screen/camera image successfully. Here is the user's specific request about this image: {text_prompt}. Please look at the image and suggest any help or perform actions based on this request."

                else:

                    result = "Failed to capture the image or main live session is not active."

            elif name == "computer_settings":

                action_param = str(args.get("action") or "").strip().lower()

                desc_param = str(args.get("description") or "").strip().lower()

                is_close = False

                target_app = ""

                if action_param == "close_app":

                    is_close = True

                    if desc_param:

                        for v in ["close", "exit", "quit", "stop", "kill"]:

                            if v in desc_param:

                                target_app = desc_param.split(v, 1)[1].strip()

                                break

                elif not action_param and desc_param:

                    for v in ["close", "exit", "quit", "stop", "kill"]:

                        if desc_param.startswith(v + " ") or desc_param == v:

                            is_close = True

                            target_app = desc_param.split(v, 1)[1].strip()

                            break

                if target_app.endswith("app"):

                    target_app = target_app[:-3].strip()

                _prev_app = getattr(self, "_last_fast_path_app", None)

                _prev_time = getattr(self, "_last_fast_path_time", 0)

                if is_close and _prev_app and (time.time() - _prev_time) < 3.5:

                    if not target_app or target_app.lower() in _prev_app.lower() or _prev_app.lower() in target_app.lower():

                        print(f"[JARVIS] 🛡️ Blocked duplicate tool execution for close_app: '{target_app}' (handled by fast-path)")

                        result = f"Closed {target_app or _prev_app} sir (already handled)."

                    else:

                        r = await loop.run_in_executor(

                            None, functools.partial(  # type: ignore[arg-type]

                                computer_settings,

                                parameters=args, response=None, player=self.ui

                            )

                        )

                        result = r or "Done."

                else:

                    r = await loop.run_in_executor(

                        None, functools.partial(  # type: ignore[arg-type]

                            computer_settings,

                            parameters=args, response=None, player=self.ui

                        )

                    )

                    result = r or "Done."

            elif name == "cmd_control":

                r = await loop.run_in_executor(

                    None, functools.partial(cmd_control, parameters=args, player=self.ui)  # type: ignore[arg-type]

                )

                result = r or "Command executed."

            elif name == "desktop_control":

                r = await loop.run_in_executor(

                    None, functools.partial(desktop_control, parameters=args, player=self.ui)  # type: ignore[arg-type]

                )

                result = r or "Desktop action completed."

            elif name == "code_helper":

                r = await loop.run_in_executor(

                    None, functools.partial(  # type: ignore[arg-type]

                        code_helper,

                        parameters=args,

                        player=self.ui,

                        speak=self.speak

                    )

                )

                result = r or "Done."

            elif name == "dev_agent":

                r = await loop.run_in_executor(

                    None, functools.partial(  # type: ignore[arg-type]

                        dev_agent,

                        parameters=args,

                        player=self.ui,

                        speak=self.speak

                    )

                )

                result = r or "Done."

            elif name == "agent_task":

                goal         = args.get("goal", "")

                priority_str = args.get("priority", "normal").lower()

                tier         = args.get("tier")

                timeout      = args.get("timeout")

                if tier is not None:

                    try: tier = int(tier)

                    except: tier = None

                if timeout is not None:

                    try: timeout = float(timeout)

                    except: timeout = None

                from kree.agent.task_queue import get_queue, TaskPriority  # type: ignore[import]

                priority_map = {

                    "low":    TaskPriority.LOW,

                    "normal": TaskPriority.NORMAL,

                    "high":   TaskPriority.HIGH,

                }

                priority = priority_map.get(priority_str, TaskPriority.NORMAL)

                queue   = get_queue()

                task_id = queue.submit(

                    goal=goal,

                    priority=priority,

                    speak=self.speak,

                    tier=tier,

                    timeout=timeout,

                )

                result = f"Task started (ID: {task_id}). I'll update you as I make progress, sir."

            elif name == "web_search":

                r = await loop.run_in_executor(

                    None, functools.partial(web_search_action, parameters=args, player=self.ui)  # type: ignore[arg-type]

                )

                if isinstance(r, str) and r.strip():

                    result = r

                elif r is None:

                    result = "Web search failed to return a result."

                else:

                    result = "Web search returned no usable results."

            elif name == "computer_control":

                r = await loop.run_in_executor(

                    None, functools.partial(computer_control, parameters=args, player=self.ui)  # type: ignore[arg-type]

                )

                result = r or "Done."

            elif name == "flight_finder":

                r = await loop.run_in_executor(

                    None, functools.partial(flight_finder, parameters=args, player=self.ui)  # type: ignore[arg-type]

                )

                result = r or "Done."

            else:

                result = f"Unknown tool: {name}"

        except Exception as e:

            result = f"Tool '{name}' failed: {e}"

            self._trace(TelemetryEvents.TOOL_RESULT, result, tool=name, status="error", duration=time.time() - tool_start_time)

            traceback.print_exc()

        finally:

            self.ui.push_action_log(f"Finished {name}")

            self.ui.hide_action_loading()

        result_str = str(result)

        # --- STRICT MOBILE CROSS-ROUTING ABORT ---

        if "__BROADCAST_INTENT__" in result_str:

            import re

            m = re.search(r'__BROADCAST_INTENT__:([A-Za-z0-9_.-]+)', result_str)

            target = m.group(1) if m else "app"

            if hasattr(self, 'mobile_bridge') and hasattr(self, '_loop'):

                asyncio.run_coroutine_threadsafe(

                    self.mobile_bridge.broadcast({"type": "intent", "action": "open_app", "target": target}),

                    self._loop

                )

            result_str = "Successfully executed on mobile device."

        if "failed" not in result_str.lower():

            self._trace(TelemetryEvents.TOOL_RESULT, result_str, tool=name, status="ok", duration=time.time() - tool_start_time)

        print(f"[JARVIS] 📤 {name} → {result_str[:80]}")  # type: ignore[index]

        self._broadcast_mobile_state('listening')

        return types.FunctionResponse(

            id=fc.id,

            name=name,

            response={"result": result_str}

        )

    async def _send_realtime(self):

        """Sends mic audio chunks from out_queue to Gemini."""

        _chunk_n: int = 0

        while True:

            if self.out_queue is None:

                await asyncio.sleep(0.1)

                continue

            msg = await self.out_queue.get()  # type: ignore[union-attr]

            if isinstance(msg, bytes) and msg == b"SLEEP_SENTINEL":

                raise ConnectionAbortedError("Sleep Triggered")

            if self.session is None:

                continue

            try:

                # Handle explicit turn signals (required when server AAD is disabled)

                if msg.get("type") == "activity_start":

                    await self.session.send_realtime_input(activity_start={})

                    print("[JARVIS] MIC: 🟢 Activity START sent")

                    continue

                elif msg.get("type") == "activity_end":

                    await self.session.send_realtime_input(activity_end={})

                    print("[JARVIS] MIC: 🔴 Activity END sent")

                    continue

                elif msg.get("type") == "emotion":

                    await self.session.send_realtime_input(text=msg.get("text"))

                    print(f"[JARVIS] MIC: 🎭 Emotion Injected: {msg.get('text')[:40]}...")

                    continue

                if "data" not in msg or "mime_type" not in msg:

                    continue

                # Handle normal audio frames

                await self.session.send_realtime_input(

                    media=types.Blob(data=msg["data"], mime_type=msg["mime_type"])

                )

                _chunk_n += 1  # type: ignore

                if _chunk_n == 1:

                    print("[JARVIS] MIC: First chunk sent successfully.")

                elif _chunk_n % 200 == 0:

                    print(f"[JARVIS] MIC: Sent {_chunk_n} audio chunks")

            except Exception as e:

                if "429" not in str(e):

                    print(f"[JARVIS] WARN: send audio error: {e}")

                raise

    async def _listen_audio(self):

        pya = _get_pya()

        if pya is None:

            print("[JARVIS] No audio device -- mic disabled.")

            return

        _MAX_MIC_RETRIES = 5

        _consecutive_failures = 0

        stream = None

        device_index = None

        try:

            while _consecutive_failures < _MAX_MIC_RETRIES:

                # ── Shutdown guard: exit immediately if app is shutting down ──

                if self._shutting_down:

                    print("[JARVIS] Mic loop exiting: shutdown in progress.")

                    break

                # ── Open / reopen the mic stream ─────────────────────────────

                if stream is None:

                    try:

                        saved_idx = self._audio_settings.get("input_device_index")
                        try:
                            default_info = pya.get_default_input_device_info()
                            default_idx = default_info.get("index")
                        except Exception:
                            default_idx = None
                            default_info = {}

                        # Fix: Prefer the dynamic working mic found by the wake word detector
                        device_index = default_idx
                        device_info = default_info
                        
                        if hasattr(self, "_wakeword_detector") and hasattr(self._wakeword_detector, "selected_idx"):
                            if self._wakeword_detector.selected_idx is not None:
                                device_index = self._wakeword_detector.selected_idx
                                try:
                                    device_info = pya.get_device_info_by_index(device_index)
                                except Exception:
                                    pass
                        elif saved_idx is not None and saved_idx != 99:
                            device_index = saved_idx
                            try:
                                device_info = pya.get_device_info_by_index(device_index)
                            except Exception:
                                pass

                        print(f"[JARVIS Mic Config] Saved device index: {saved_idx}")
                        print(f"[JARVIS Mic Config] Default device index: {default_idx}")
                        print(f"[JARVIS Mic Config] Forcing default device index: {device_index}")

                        dev_name = device_info.get("name", "Unknown")

                        suffix = " (recovered)" if _consecutive_failures > 0 else ""

                        print(f"[JARVIS] Mic started (Device: {dev_name}){suffix}")

                        stream = await asyncio.to_thread(

                            pya.open,

                            format=FORMAT,

                            channels=CHANNELS,

                            rate=SEND_SAMPLE_RATE,

                            input=True,

                            input_device_index=device_index,

                            frames_per_buffer=CHUNK_SIZE,

                        )

                        _consecutive_failures = 0  # successful open resets counter

                    except Exception as e:

                        _consecutive_failures += 1

                        print(f"[JARVIS] Mic open failed (attempt {_consecutive_failures}/{_MAX_MIC_RETRIES}): {e}")

                        await asyncio.sleep(2)

                        continue

                # ── Stream read loop ─────────────────────────────────────────

                try:

                    if _consecutive_failures == 0:

                        print("[JARVIS] STREAMING MIC MODE: Server VAD enabled (instant response)")

                    while True:

                        data = await asyncio.to_thread(

                            stream.read, CHUNK_SIZE, exception_on_overflow=False

                        )

                        # Echo suppression: if Kree is talking, zero the mic to prevent loop

                        if getattr(self, "bot_is_speaking", False):

                            self._bot_speaking_cooldown = 5  # ~320ms acoustic tail (5 x 64ms chunks)

                            # Cancel PTT if Kree starts speaking -- prevents echo loop

                            if getattr(self, "_mic_ptt_active", False):

                                self._mic_ptt_active = False

                                self._mic_ptt_silence_chunks = 0

                        cooldown = getattr(self, "_bot_speaking_cooldown", 0)

                        ptt_active = getattr(self, "_mic_ptt_active", False)

                        mic_ui_on = getattr(self.ui, "_mic_active", True)

                        if cooldown > 0:

                            self._bot_speaking_cooldown = cooldown - 1

                            send_data = bytes(len(data))

                        elif ptt_active:

                            # PTT mode: mic is normally muted but wake word opened it temporarily

                            send_data = data

                            # Measure RMS to detect silence and auto-remute

                            import struct

                            rms_samples = struct.unpack(f"{len(data)//2}h", data)

                            rms = int((sum(s * s for s in rms_samples) / max(len(rms_samples), 1)) ** 0.5)

                            silence_limit = getattr(self, "_mic_ptt_silence_limit", 23)

                            speech_threshold = getattr(self, "_mic_ptt_speech_rms_threshold", 200)

                            if rms < speech_threshold:

                                self._mic_ptt_silence_chunks = getattr(self, "_mic_ptt_silence_chunks", 0) + 1

                                if self._mic_ptt_silence_chunks >= silence_limit:

                                    print("[JARVIS] PTT silence detected -- remuting mic")

                                    self._mic_ptt_active = False

                                    self._mic_ptt_silence_chunks = 0
                                    
                                    try:
                                        self.ui.hibernate()
                                    except Exception: pass

                            else:

                                # User is speaking -- reset silence counter

                                self._mic_ptt_silence_chunks = 0

                        elif not mic_ui_on:

                            send_data = bytes(len(data))

                        else:

                            send_data = data

                        # Send raw stream to Gemini

                        if self.out_queue is not None:

                            try:

                                self.out_queue.put_nowait({"data": send_data, "mime_type": f"audio/pcm;rate={SEND_SAMPLE_RATE}"})

                            except asyncio.QueueFull:

                                pass

                except Exception as e:

                    err_str = str(e)

                    if "429" in err_str:

                        raise  # rate-limit errors must propagate to the session handler

                    # ── Shutdown detection: if executor is dead, stop immediately ──

                    if self._shutting_down or "cannot schedule new futures after shutdown" in err_str:

                        print("[JARVIS] Mic recovery aborted: executor shutdown detected.")

                        return

                    _consecutive_failures += 1

                    print(f"[JARVIS] Mic read error (attempt {_consecutive_failures}/{_MAX_MIC_RETRIES}): {e}")

                    # Clean up the dead stream

                    if stream is not None:

                        try:

                            await asyncio.to_thread(stream.stop_stream)

                            await asyncio.to_thread(stream.close)

                        except Exception:

                            pass

                        stream = None

                    # Wait before retry to allow device reconnection

                    await asyncio.sleep(2)

            # Exhausted retries

            print(f"[JARVIS] Mic recovery failed after {_MAX_MIC_RETRIES} attempts. Voice input disabled.")

        finally:

            if stream is not None:

                print("[JARVIS] Cleaning up mic stream on exit.")

                try:

                    stream.stop_stream()

                    stream.close()

                except Exception:

                    pass

    async def _listen_camera(self):

        try:

            import cv2

        except ImportError:

            print("[JARVIS] ❌ cv2 not installed — camera disabled.")

            self._cam_active = False

            return

        cap = None

        last_ui_push = 0.0

        last_gemini_push = 0.0

        try:

            print("[JARVIS] 📷 Camera ready. Awaiting UI trigger...")

            while True:

                if not self.ui._cam_active:

                    if cap is not None:

                        await asyncio.to_thread(cap.release)  # type: ignore

                        cap = None

                        if self.ui._main_win:

                            try:

                                self.ui._eval("if(typeof updateWebcam==='function') updateWebcam('');")

                            except Exception:

                                pass

                    await asyncio.sleep(0.5)

                    continue

                if getattr(self.ui, "_disable_backend_camera_stream", False):

                    if cap is not None:

                        await asyncio.to_thread(cap.release)  # type: ignore

                        cap = None

                        try:

                            self.ui._eval("if(typeof updateWebcam==='function') updateWebcam('');")

                        except Exception:

                            pass

                    await asyncio.sleep(0.5)

                    continue

                if cap is None:

                    print("[JARVIS] 📷 Camera starting hardware capture...")

                    cap = await asyncio.to_thread(cv2.VideoCapture, 0, cv2.CAP_DSHOW)  # type: ignore

                    if not cap or not cap.isOpened():  # type: ignore

                        await asyncio.sleep(1)

                        continue

                    try:

                        await asyncio.to_thread(cap.set, cv2.CAP_PROP_FRAME_WIDTH, 640)  # type: ignore

                        await asyncio.to_thread(cap.set, cv2.CAP_PROP_FRAME_HEIGHT, 360)  # type: ignore

                    except Exception:

                        pass

                success, frame = await asyncio.to_thread(cap.read)  # type: ignore

                if not success:

                    await asyncio.sleep(0.5)

                    continue

                # Resize and lower JPEG quality to reduce CPU and bandwidth.

                frame_resized = await asyncio.to_thread(cv2.resize, frame, (640, 360))

                encoded, buffer = await asyncio.to_thread(

                    cv2.imencode,

                    ".jpg",

                    frame_resized,

                    [cv2.IMWRITE_JPEG_QUALITY, 65],

                )

                if not encoded:

                    await asyncio.sleep(0.1)

                    continue

                now = time.monotonic()

                jpeg_bytes = buffer.tobytes()

                # Smooth fallback UI preview at ~8 FPS.

                if self.ui._main_win and (now - last_ui_push) >= 0.125:

                    try:

                        b64_str = base64.b64encode(jpeg_bytes).decode('utf-8')

                        self.ui._eval(

                            f"if(typeof updateWebcam==='function') updateWebcam('data:image/jpeg;base64,{b64_str}');"

                        )

                    except Exception:

                        pass

                    last_ui_push = now

                # Gemini camera feed is intentionally low-rate to control bandwidth and CPU.

                if self.session is not None and (now - last_gemini_push) >= 1.0:

                    try:

                        blob = types.Blob(data=jpeg_bytes, mime_type="image/jpeg")

                        await self.session.send_realtime_input(media=blob)

                    except Exception as e:

                        if "429" not in str(e):

                            print(f"[JARVIS] ⚠️ Camera send error: {e}")

                    last_gemini_push = now

                await asyncio.sleep(0.03)

        except Exception as e:

            print(f"[JARVIS] ❌ Camera stream error: {e}")

        finally:

            if cap:

                await asyncio.to_thread(cap.release)  # type: ignore

    async def _receive_audio(self):

        print("[JARVIS] 👂 Recv started")

        out_buf = []

        current_in_transcript = ""

        _turn_n = 0

        try:

            while True:

                if self.session is None:

                    await asyncio.sleep(0.1)

                    continue

                _turn_n += 1

                print(f"[JARVIS] 👂 Waiting for turn #{_turn_n}...")

                turn = self.session.receive()

                _msg_n = 0

                tool_call_count = 0

                turn_tools = []

                async for response in turn:

                    self._last_server_message_at = time.time()

                    _msg_n += 1

                    # Log EVERY response with audio data presence

                    has_data = bool(response.data)

                    has_sc = bool(response.server_content)

                    has_tc = bool(response.tool_call)

                    if response.tool_call:

                        tool_call_count += len(response.tool_call.function_calls)

                    if _msg_n <= 5 or has_tc:

                        parts_info = ""

                        if has_sc and response.server_content.model_turn:

                            mt = response.server_content.model_turn

                            parts_info = f", parts={[p.inline_data.mime_type if p.inline_data else 'text' for p in (mt.parts or [])]}"

                        print(f"[JARVIS] 📨 Turn#{_turn_n} Msg#{_msg_n}: data={has_data}, sc={has_sc}, tc={has_tc}{parts_info}")

                    if response.data:

                        if self.audio_in_queue is not None and not getattr(self, "_suppress_audio_response", False):

                            try:

                                self.audio_in_queue.put_nowait(response.data)  # type: ignore[union-attr]

                            except asyncio.QueueFull:

                                pass

                        if hasattr(self, 'mobile_bridge') and self.mobile_bridge and self.mobile_bridge.clients:

                            try:

                                asyncio.create_task(self.mobile_bridge.send_audio_chunk(response.data))

                            except Exception:

                                pass

                    if response.server_content:
                        if hasattr(self, 'ui') and getattr(self.ui, '_main_win', None):
                            self.ui.wake()
                            if hasattr(self, 'system_tray') and self.system_tray:
                                self.system_tray.set_processing()

                        sc = response.server_content

                        if sc.input_transcription and sc.input_transcription.text:

                            txt = sc.input_transcription.text.strip()

                            if txt:

                                print(f"[TRANSCRIPT] Previous: \"{current_in_transcript}\"")

                                print(f"[TRANSCRIPT] Incoming: \"{txt}\"")

                                self._suppress_audio_response = False

                                print(f"[STREAM] ts={time.time()} partial='{txt}'")

                                self._last_user_turn = time.time()

                                self._trace(TelemetryEvents.INPUT_TRANSCRIPT, txt)

                                if not current_in_transcript:

                                    current_in_transcript = txt

                                elif txt.startswith(current_in_transcript):

                                    current_in_transcript = txt

                                else:

                                    words_prev = current_in_transcript.split()

                                    words_next = txt.split()

                                    overlap = 0

                                    for i in range(1, min(len(words_prev), len(words_next)) + 1):

                                        if words_prev[-i:] == words_next[:i]:

                                            overlap = i

                                    if overlap > 0:

                                        merged_words = words_prev + words_next[overlap:]

                                        current_in_transcript = " ".join(merged_words)

                                    else:

                                        char_overlap = 0

                                        for i in range(1, min(len(current_in_transcript), len(txt)) + 1):

                                            if current_in_transcript[-i:].lower() == txt[:i].lower():

                                                char_overlap = i

                                        if char_overlap > 0:

                                            current_in_transcript = current_in_transcript + txt[char_overlap:]

                                        else:

                                            current_in_transcript = current_in_transcript + " " + txt

                                print(f"[TRANSCRIPT] Merged: \"{current_in_transcript}\"")

                        if sc.output_transcription and sc.output_transcription.text:

                            txt = sc.output_transcription.text.strip()

                            if txt:

                                self._trace(TelemetryEvents.OUTPUT_TRANSCRIPT, txt)

                                out_buf.append(txt)

                        if sc.turn_complete:

                            print(f"[JARVIS] ✅ Turn #{_turn_n} complete ({_msg_n} websocket messages, {tool_call_count} tool calls)")

                            full_in  = ""

                            full_out = ""

                            if current_in_transcript:

                                full_in = current_in_transcript.strip()

                                if full_in:

                                    full_in = self._sanitize_multilingual_transcript(full_in)

                                    print(f"[TURN_COMPLETE] ts={time.time()} text='{full_in}'")

                                if full_in:

                                    if self._should_arm_command_window(full_in):

                                        self._arm_command_window(full_in)

                                     # ── Voice fast-path intercept ────────────────

                                     # Normalize conversational prefixes and check

                                     # if this is a fast-path command that should

                                     # bypass the LLM round-trip entirely.

                                    _voice_normalized = self._normalize_conversational_routing(full_in)

                                    _fast_path_verbs = ("open ", "close ", "launch ", "start ", "run ", "exit ", "quit ", "stop ")

                                    _voice_intercepted = False

                                    if _voice_normalized.lower().startswith(_fast_path_verbs):

                                        print(f"[ROUTER] Voice fast-path intercept: '{full_in}' -> '{_voice_normalized}'")

                                        self.ui.write_log(f"You: {full_in}")

                                        try:

                                            self._suppress_audio_response = True  # Block LLM voice response

                                            # Clear any queued audio playback

                                            if self.audio_in_queue is not None:

                                                while not self.audio_in_queue.empty():

                                                    try: self.audio_in_queue.get_nowait()

                                                    except: break

                                            if getattr(self, "sync_audio_out_queue", None) is not None:

                                                while not self.sync_audio_out_queue.empty():

                                                    try: self.sync_audio_out_queue.get_nowait()

                                                    except: break

                                            self.on_user_text(full_in, from_voice=True)

                                            _voice_intercepted = True

                                            out_buf = []  # Suppress LLM output — we handled it locally

                                        except Exception as e:

                                            print(f"[ROUTER] Voice fast-path error, falling through to LLM: {e}")

                                    if not _voice_intercepted:

                                        self.ui.write_log(f"You: {full_in}")

                                    if self._resolve_pending_choice(full_in):

                                        out_buf = []

                            current_in_transcript = ""

                            if out_buf:

                                full_out = " ".join(out_buf).strip()

                                if full_out:

                                    self.ui.write_log(f"Kree: {full_out}")

                            out_buf = []

                            if full_in and len(full_in) > 5:

                                start_post = time.perf_counter()

                                timings = {}

                                start_mem = time.perf_counter()

                                threading.Thread(

                                    target=_update_memory_async,

                                    args=(full_in, full_out),

                                    daemon=True

                                ).start()

                                t_mem = (time.perf_counter() - start_mem) * 1000

                                timings["_update_memory_async thread launch"] = t_mem

                                print(f"[PROFILE] _update_memory_async thread launch: {t_mem:.2f}ms")

                                try:

                                    import kree.memory.history_manager as hist

                                    start_save = time.perf_counter()

                                    hist.save_turn(full_in, full_out, tools=turn_tools)

                                    t_save = (time.perf_counter() - start_save) * 1000

                                    timings["hist.save_turn"] = t_save

                                    print(f"[PROFILE] hist.save_turn: {t_save:.2f}ms")

                                    if hasattr(self, "_injected_keys") and self._injected_keys:

                                        start_access = time.perf_counter()

                                        from kree.memory.memory_manager import record_memory_access

                                        record_memory_access(self._injected_keys)

                                        t_access = (time.perf_counter() - start_access) * 1000

                                        timings["record_memory_access"] = t_access

                                        print(f"[PROFILE] record_memory_access: {t_access:.2f}ms")

                                except Exception as e:

                                    print(f"[JARVIS] ⚠️ History log or memory access error: {e}")

                                timings["trigger scans"] = 0.0

                                print("[PROFILE] trigger scans: 0.00ms (asynchronous/background)")

                                timings["reconnect/watchdog tasks"] = 0.0

                                print("[PROFILE] reconnect/watchdog tasks: 0.00ms (asynchronous/disabled)")

                                total_post = (time.perf_counter() - start_post) * 1000

                                print(f"[PROFILE] Total post-turn processing: {total_post:.2f}ms")

                                slowest_comp = max(timings, key=timings.get)

                                print(f"[PROFILE] Slowest component: {slowest_comp} ({timings[slowest_comp]:.2f}ms)")

                    if response.tool_call:

                        print(f"[TOOL_CALL] {time.time()}")

                        # Print all tools being called

                        for fc in response.tool_call.function_calls:

                            print(f"[JARVIS] 📞 Tool call: {fc.name}")

                            turn_tools.append(fc.name)

                            self.ui.write_log(f"Kree: [Tool Executing: {fc.name}]")

                        # Execute all tools concurrently (Parallel Execution)

                        fn_responses = list(await asyncio.gather(

                            *[self._execute_tool(fc) for fc in response.tool_call.function_calls]

                        ))

                        if self.session is not None:

                            await self.session.send_tool_response(

                                function_responses=fn_responses

                            )

                if _msg_n == 0:

                    # Connection might be dead or closed, prevent infinite CPU loop

                    await asyncio.sleep(1.0)

        except Exception as e:

            if "429" not in str(e):

                self._trace(TelemetryEvents.RECEIVE_ERROR, str(e))

                print(f"[JARVIS] ❌ Recv error: {e}")

                traceback.print_exc()

            raise

    def _play_worker(self):

        pya = _get_pya()

        if pya is None:

            return

        stream = None

        is_playing = False

        try:

            stream = pya.open(

                format=FORMAT,

                channels=CHANNELS,

                rate=RECEIVE_SAMPLE_RATE,

                output=True,

            )

            while True:

                if getattr(self, "sync_audio_out_queue", None) is None:

                    time.sleep(0.1)

                    continue

                # If we are not currently playing, buffer some chunks to absorb network jitter

                if not is_playing:

                    start_wait = time.time()

                    while self.sync_audio_out_queue.qsize() < 4 and (time.time() - start_wait) < 0.15:

                        time.sleep(0.01)

                    is_playing = True

                chunk = self.sync_audio_out_queue.get()

                if chunk is None:

                    break

                self.bot_is_speaking = True

                self._broadcast_mobile_state('speaking')

                try:

                    stream.write(chunk)

                except Exception as e:

                    if "429" not in str(e) and "Overflow" not in str(e) and "Underflow" not in str(e):

                        pass

                if self.sync_audio_out_queue.empty():

                    self.bot_is_speaking = False

                    self._broadcast_mobile_state('listening')

                    is_playing = False

        except Exception as e:

            if "429" not in str(e):

                pass

        finally:

            self.bot_is_speaking = False

            if stream is not None:

                try:

                    stream.stop_stream()

                    stream.close()

                except Exception:

                    pass

    async def _play_audio(self):

        pya = _get_pya()

        if pya is None:

            print("[JARVIS] ❌ No audio device — playback disabled.")

            return

        print("[JARVIS] 🔊 Play started")

        if getattr(self, "sync_audio_out_queue", None) is None:

            import queue

            self.sync_audio_out_queue = queue.Queue(maxsize=MAX_PLAY_QUEUE)

            t = threading.Thread(target=self._play_worker, daemon=True)

            t.start()

        try:

            while True:

                if self.audio_in_queue is None:

                    await asyncio.sleep(0.1)

                    continue

                chunk = await self.audio_in_queue.get()  # type: ignore[union-attr]

                try:

                    self.sync_audio_out_queue.put_nowait(chunk)

                except Exception: # queue.Full

                    pass

        except Exception as e:

            if "429" not in str(e):

                print(f"[JARVIS] ❌ Play error: {e}")

            raise

    def _broadcast_mobile_state(self, state):

        """Thread-safe push of Kree's state to all connected mobile clients."""

        try:

            if hasattr(self, 'mobile_bridge') and self.mobile_bridge and self._loop:

                asyncio.run_coroutine_threadsafe(

                    self.mobile_bridge.broadcast_state(state),

                    self._loop

                )

        except Exception:

            pass

    async def _proactive_check_loop(self):

        """Silently monitors user activity. Triggers Kree if dormant."""

        print("[JARVIS] ⏱️ Proactive Monitor started (60s timer)")

        check_in_phrases = [

            "Need anything else?",

            "I’m here if you need me.",

            "Want me to keep going?",

            "Anything else on your mind?",

        ]

        while True:

            # Random jitter to make it feel organic, but base is 60s for dev

            await asyncio.sleep(10)

            if not self.session:

                continue

            # Watchdog check disabled to prevent continuous reconnection when silent

            pass

            last_turn = getattr(self, "_last_user_turn", time.time())

            dormant_time = time.time() - last_turn

            # Dev mode: 60s. Prod: 1800s. Timeouts.

            AUTO_SLEEP_TIMEOUT = 1800  # 30 minutes

            proactive_timeout = 60

            if isinstance(self._audio_settings, dict):

                proactive_timeout = int(self._audio_settings.get("proactive_heartbeat", proactive_timeout) or proactive_timeout)

            if proactive_timeout > 0 and dormant_time > proactive_timeout:

                if dormant_time > AUTO_SLEEP_TIMEOUT and self.wake_event.is_set():

                    print("[JARVIS] ⏱️ Inactive for 30 mins. Auto-sleeping.")

                    try:

                        _local_speech_voice("Going to sleep sir, call me when you need me.")

                    except: pass

                    self.hibernate()

                elif not getattr(self, "bot_is_speaking", False):

                    if getattr(self.ui, "_mic_active", True):

                        print(f"[JARVIS] ⏱️ Dormant for {int(dormant_time)}s. Firing proactive check-in!")

                        try:

                            await self.session.send_client_content(

                                turns={"parts": [{"text": random.choice(check_in_phrases)}]},

                                turn_complete=True,

                            )

                        except Exception as e:

                            print(f"[JARVIS] ⚠️ Proactive fire fail: {e}")

                    # Reset timer so it doesn't loop / trigger auto-sleep when muted

                    self._last_user_turn = time.time()

    async def run(self):

        genai, _ = _ensure_genai_sdk()

        client = genai.Client(

            api_key=_get_api_key(),

            http_options={"api_version": "v1beta"}

        )

        from kree.memory.config_manager import load_audio_settings, load_telemetry_settings

        load_audio_settings()

        telemetry_settings = load_telemetry_settings()

        # Define internal bridge callbacks

        _mobile_cmd_dedup = set()

        def on_mobile_command(text: str):

            # Deduplicate rapid-fire commands

            import time as _t

            key = text.strip().lower() + str(int(_t.time()))

            if key in _mobile_cmd_dedup:

                return

            _mobile_cmd_dedup.add(key)

            if len(_mobile_cmd_dedup) > 50:

                _mobile_cmd_dedup.clear()

            print(f"[JARVIS] 📱 Mobile Command: {text}")

            if hasattr(self, 'on_user_text'):

                try:

                    self.on_user_text(text)

                except Exception as e:

                    print(f"[JARVIS] ⚠️ Mobile command error: {e}")

        def on_mobile_connect(pinfo):

            try:

                ip = pinfo[0] if isinstance(pinfo, tuple) else str(pinfo)

                js_str = f'''try{{

                    var l=document.getElementById("kree-connect-label");if(l)l.innerText="📱 KREE MOBILE LINKED";

                    var u=document.getElementById("kree-connect-url");if(u)u.innerText="Telemetry stream active";

                    var i=document.getElementById("kree-connect-qr-loading");if(i){{i.innerText="check_circle";i.classList.remove("text-primary/30","animate-pulse");i.classList.add("text-primary","flex");i.style.fontSize="80px";}};

                    var q=document.getElementById("kree-connect-qr");if(q)q.style.display="none";

                    var bs=document.getElementById("phone-bridge-status");if(bs){{bs.innerText="BRIDGE ONLINE ({ip})";bs.style.color="#00DC82";}};

                }}catch(e){{}}'''

                self.ui._eval(js_str)

            except Exception:

                pass

        def on_quick_action(action: str):

            if action == 'lock': self.ui.lock_desktop()

            elif action == 'sleep': self.ui.sleep_desktop()

            elif action == 'mute': self.ui.mute_desktop()

            elif action == 'screenshot': self.ui.take_screenshot()

        def on_clipboard_sync(content: str):

            self.ui.set_clipboard(content)

        import os

        _file_transfers = {}

        def on_file_transfer(data: dict):

            direction = data.get('direction', '')

            action = data.get('action', '')

            desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop", "Kree Bridge")

            os.makedirs(desktop_dir, exist_ok=True)

            # New single-blob format from rebuilt PWA

            if direction == 'phone_to_desktop' and data.get('data'):

                filename = data.get('filename', f"{int(time.time())}.file")

                try:

                    import base64

                    filepath = os.path.join(desktop_dir, filename)

                    with open(filepath, 'wb') as f:

                        f.write(base64.b64decode(data['data']))

                    print(f"[JARVIS] ✅ File received from mobile: {filepath} ({data.get('size', 0)} bytes)")

                except Exception as e:

                    print(f"[JARVIS] ❌ File save failed: {e}")

                return

            # Legacy chunked format

            file_id = data.get('fileId')

            if not file_id: return

            if action == 'start':

                filename = data.get('name', f"{int(time.time())}.file")

                filepath = os.path.join(desktop_dir, filename)

                _file_transfers[file_id] = {'path': filepath, 'chunks': []}

            elif action == 'chunk':

                if file_id in _file_transfers:

                    _file_transfers[file_id]['chunks'].append((data.get('index', 0), data.get('data', '')))

            elif action == 'complete':

                if file_id in _file_transfers:

                    info = _file_transfers.pop(file_id)

                    chunks = sorted(info['chunks'], key=lambda x: x[0])

                    try:

                        import base64

                        with open(info['path'], 'wb') as f:

                            for _, b64_data in chunks:

                                f.write(base64.b64decode(b64_data))

                        print(f"[JARVIS] ✅ Saved {info['path']}")

                    except Exception as e:

                        print(f"[JARVIS] ❌ File save failed: {e}")

        def on_notes_sync(notes: list):

            # Pass notes to UI for rendering safely using Base64

            try:

                import json

                import base64

                encoded_b64 = base64.b64encode(json.dumps(notes).encode('utf-8')).decode('utf-8')

                self.ui._eval(f"try{{ renderSyncedNotes(new TextDecoder().decode(Uint8Array.from(atob('{encoded_b64}'), c=>c.charCodeAt(0)))); }}catch(e){{}}")

            except Exception as e:

                print(f"[JARVIS] ❌ Notes rendering failed: {e}")

        def on_contacts_sync(contacts: list):

            # Pass contacts to UI for rendering safely using Base64

            try:

                import json

                import base64

                encoded_b64 = base64.b64encode(json.dumps(contacts).encode('utf-8')).decode('utf-8')

                self.ui._eval(f"try{{ renderSyncedContacts(new TextDecoder().decode(Uint8Array.from(atob('{encoded_b64}'), c=>c.charCodeAt(0)))); }}catch(e){{}}")

            except Exception as e:

                print(f"[JARVIS] ❌ Contacts rendering failed: {e}")

        # Fetch Mobile Bridge from FastAPI Server

        from kree.fastapi_server import get_bridge

        self.mobile_bridge = get_bridge()

        self.mobile_bridge.on_command_callback = on_mobile_command

        self.mobile_bridge.on_connect_callback = on_mobile_connect

        self.mobile_bridge.on_quick_action_callback = on_quick_action

        self.mobile_bridge.on_clipboard_callback = on_clipboard_sync

        self.mobile_bridge.on_file_transfer_callback = on_file_transfer

        self.mobile_bridge.on_notes_sync_callback = on_notes_sync

        self.mobile_bridge.on_contacts_sync_callback = on_contacts_sync

        # Mobile mic → Kree audio pipeline

        def on_mobile_audio(audio_bytes):

            """Receives raw audio from mobile mic and pushes to Gemini."""

            if self.out_queue and not self.bot_is_speaking:

                try:

                    self.out_queue.put_nowait({

                        "data": audio_bytes,

                        "mime_type": "audio/pcm;rate=16000"

                    })

                except Exception:

                    pass

        self.mobile_bridge.on_audio_callback = on_mobile_audio

        self._loop = asyncio.get_event_loop()

        self.ui.mobile_bridge = self.mobile_bridge

        self.ui._loop = self._loop

        try:

            await self.mobile_bridge.start()

        except Exception as e:

            print(f"[JARVIS] ⚠️ Mobile Bridge init error: {e}")

        # ── PWA Server Auto-Start ────────────────────────────────────────

        try:

            from kree.serve_pwa import start_pwa_server_background

            pwa_url, pwa_error = start_pwa_server_background()

            if pwa_url:

                self._trace(TelemetryEvents.SESSION_INIT, f"PWA server started: {pwa_url}")

                # Generate QR code and push to UI

                try:

                    import qrcode

                    import io

                    qr = qrcode.QRCode(version=1, box_size=6, border=2)

                    qr.add_data(pwa_url)

                    qr.make(fit=True)

                    qr_img = qr.make_image(fill_color="#00DC82", back_color="#0e0e10")

                    buf = io.BytesIO()

                    qr_img.save(buf, format='PNG')

                    qr_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')

                    qr_js = f'''try{{

                        var qrEl=document.getElementById("kree-connect-qr");

                        if(qrEl){{qrEl.src="data:image/png;base64,{qr_b64}";qrEl.style.display="block";}}

                        var loadEl=document.getElementById("kree-connect-qr-loading");

                        if(loadEl)loadEl.style.display="none";

                        var urlEl=document.getElementById("kree-connect-url");

                        if(urlEl)urlEl.innerText="{pwa_url}";

                    }}catch(e){{}}'''

                    self.ui._eval(qr_js)

                except ImportError:

                    print("[KREE PWA] qrcode library not installed. Run: pip install qrcode[pil]")

                except Exception as e:

                    print(f"[KREE PWA] QR code generation failed: {e}")

            elif pwa_error:

                print(f"[KREE PWA] ⚠️ {pwa_error}")

                err_js = f'''try{{

                    var urlEl=document.getElementById("kree-connect-url");

                    if(urlEl){{urlEl.innerText="{pwa_error}";urlEl.style.color="#ff716c";}}

                }}catch(e){{}}'''

                self.ui._eval(err_js)

        except ImportError:

            print("[KREE PWA] serve_pwa module not found. PWA server disabled.")

        except Exception as e:

            print(f"[KREE PWA] Failed to start PWA server: {e}")

        # Initialize wake event

        self.wake_event = asyncio.Event()

        if getattr(self, "start_awake", False):

            self.wake_event.set()

        else:

            self.wake_event.clear()

        backoff = 3.0

        retry_count = 0

        while True:

            e = None

            try:

                # Sleep Barrier Engine

                if not self.wake_event.is_set():

                    print("[JARVIS] 💤 System sleeping. Awaiting Wake Word...")

                    await self.wake_event.wait()

                # Trigger the welcome voice and session context analyzer ONLY on first wake

                if not self._welcomed:

                    self._welcomed = True

                    _local_welcome_voice(self)

                    try:

                        if not getattr(self, "_checked_onboarding", False):

                            self._checked_onboarding = True

                            import kree.core.onboarding as onboard

                            if onboard.is_first_launch():

                                # This will be handled inside the connect taskgroup later

                                self._needs_onboarding = True

                    except Exception:

                        pass

                from kree.memory.config_manager import load_audio_settings

                self._audio_settings = load_audio_settings()

                intel_mode = self._audio_settings.get("intelligence_mode", "CLOUD_GEMINI")

                if "LOCAL" in intel_mode:

                    print(f"[JARVIS] 🔌 Starting LOCAL AIR-GAPPED MODE ({intel_mode})...")

                    self.ui.write_log(f"Kree switched to {intel_mode}.")

                    self._trace(TelemetryEvents.CONNECTION_OPEN, "Local Mode initialized")

                    await self._run_local_offline_loop()

                    await asyncio.sleep(3)

                    continue

                print("[JARVIS] Connecting to Cloud WebRTC...")

                self.ui.write_log("Kree: Connecting to Gemini Cloud...")

                config = self._build_config()

                async with (

                    client.aio.live.connect(model=LIVE_MODEL, config=config) as session,

                    asyncio.TaskGroup() as tg,

                ):

                    self.session        = session

                    self._loop          = asyncio.get_event_loop() 

                    self.audio_in_queue = asyncio.Queue(maxsize=MAX_AUDIO_IN_QUEUE)

                    self.out_queue      = asyncio.Queue(maxsize=MAX_AUDIO_OUT_QUEUE)

                    self._last_server_message_at = time.time()

                    mic_enabled = True  # Always enable mic on boot — voice is core to Kree

                    print("[JARVIS] ✅ Connected.")

                    self.ui.write_log("Kree: Connected to Gemini Cloud.")

                    backoff = 3.0  # Reset backoff on successful connection

                    retry_count = 0

                    self._trace(TelemetryEvents.CONNECTION_OPEN, "Realtime connection opened")

                    tg.create_task(self._send_realtime())

                    if mic_enabled:

                        tg.create_task(self._listen_audio())

                    tg.create_task(self._listen_camera())

                    tg.create_task(self._receive_audio())

                    tg.create_task(self._play_audio())

                    self._last_user_turn = time.time()

                    tg.create_task(self._proactive_check_loop())

                    try:

                        import kree.core.app_watcher as aw

                        tg.create_task(aw.watch_processes(self.session))

                    except Exception as e:

                        print(f"[JARVIS] ⚠️ App Watcher fail: {e}")

                    if getattr(self, "_needs_onboarding", False):

                        try:

                            import kree.core.onboarding as onboard

                            tg.create_task(onboard.first_time_setup(self.session))

                            self._needs_onboarding = False

                        except Exception as e:

                            print(f"[JARVIS] ⚠️ Base Onboarding Trigger Fail: {e}")

                    # Start PWA Background Telemetry

                    async def _pwa_telemetry_loop():

                        start_time = time.time()

                        tick = 0

                        while True:

                            await asyncio.sleep(5)

                            tick += 1

                            uptime = int(time.time() - start_time)

                            m, s = divmod(uptime, 60)

                            h, m = divmod(m, 60)

                            if self.mobile_bridge.clients:

                                await self.mobile_bridge.broadcast({

                                    "type": "telemetry",

                                    "status": "Online",

                                    "latency": "<1",

                                    "uptime": f"{h:02d}:{m:02d}:{s:02d}"

                                })

                            # Every ~15 seconds, send system stats for Desktop Monitor tab

                            if tick % 3 == 0 and self.mobile_bridge.clients:

                                try:

                                    import psutil

                                    procs = []

                                    for p in psutil.process_iter(['name', 'cpu_percent']):

                                        try:

                                            info = p.info

                                            if info['cpu_percent'] and info['cpu_percent'] > 0:

                                                procs.append({'name': info['name'], 'cpu': round(info['cpu_percent'], 1)})

                                        except (psutil.NoSuchProcess, psutil.AccessDenied):

                                            pass

                                    procs.sort(key=lambda x: x['cpu'], reverse=True)

                                    await self.mobile_bridge.broadcast({

                                        "type": "system_stats",

                                        "processes": procs[:20],

                                        "cpu": round(psutil.cpu_percent(interval=0), 1),

                                        "ram": round(psutil.virtual_memory().percent, 1)

                                    })

                                except Exception:

                                    pass

                    # Screen Broadcast Loop (Desktop → Mobile)

                    async def _screen_broadcast_loop():

                        try:

                            import mss

                            import io

                            import base64

                            from PIL import Image

                        except ImportError:

                            print("[JARVIS] ⚠️ Screen broadcast requires mss and Pillow. pip install mss Pillow")

                            return

                        sct = mss.mss()

                        while True:

                            await asyncio.sleep(5)  # 5s interval to reduce CPU load

                            if not self.mobile_bridge.clients:

                                continue

                            try:

                                monitor = sct.monitors[1]

                                img = sct.grab(monitor)

                                pil = Image.frombytes('RGB', img.size, img.rgb)

                                pil = pil.resize((640, 360), Image.LANCZOS)

                                buf = io.BytesIO()

                                pil.save(buf, format='JPEG', quality=35)

                                b64 = base64.b64encode(buf.getvalue()).decode('utf-8')

                                await self.mobile_bridge.broadcast({

                                    "type": "screen_frame",

                                    "data": b64

                                })

                            except Exception:

                                pass

                    if telemetry_settings.get("enabled", True):

                        tg.create_task(_pwa_telemetry_loop())

                    tg.create_task(_screen_broadcast_loop())

            except Exception as exc:

                e = exc

                self._trace(TelemetryEvents.CONNECTION_ERROR, str(exc))

                print(f"[JARVIS] Error: {exc}")

                retry_count += 1

                import datetime

                import platform

                import sys

                from kree.core.version import APP_VERSION

                log_msg = (

                    f"--- WebRTC Connect Failure ---\n"

                    f"Timestamp: {datetime.datetime.now().isoformat()}\n"

                    f"Attempt: {retry_count}/8\n"

                    f"Exception: {type(exc).__name__}: {exc}\n"

                    f"Platform: {platform.platform()}\n"

                    f"Python: {sys.version}\n"

                    f"App Version: {APP_VERSION}\n"

                )

                _logging.getLogger(__name__).error(log_msg)

            if not self.wake_event.is_set():

                print("[JARVIS] Session closed intentionally. Waiting for wake.")

                continue

            if e is not None:

                # Gracefully handle 429 Rate Limits / Quotas

                err_str = str(e).lower()

                if "429" in err_str or "quota" in err_str or "limit" in err_str:

                    self.ui.write_log("Kree: Gemini API quota exceeded (Rate limit 429).")

                    self.ui._eval("try{ showToast('Gemini API Quota Exceeded (429)!', '#ff716c'); }catch(e){}")

                if retry_count >= 8:

                    msg = "Gemini server is currently unavailable after 8 reconnect attempts. Switching to Local offline mode."

                    print(f"[JARVIS] ❌ {msg}")

                    self.ui.write_log("Gemini unavailable. Switching to Local Mode.")

                    self.ui._eval("try{ showToast('Gemini Cloud Unavailable! Switching to Local Mode...', '#ff716c'); }catch(e){}")

                    # Switch settings to local mode

                    self._audio_settings["intelligence_mode"] = "LOCAL_GEMMA"

                    from kree.memory.config_manager import save_audio_settings

                    save_audio_settings(self._audio_settings)

                    retry_count = 0

                    backoff = 3.0

                    continue

                print(f"[JARVIS] Reconnecting in {backoff}s...")

                self.ui.write_log(f"Kree: Connection lost. Reconnecting in {int(backoff)}s...")

                self._trace(TelemetryEvents.RECONNECT_WAIT, f"Reconnecting in {backoff}s")

                await asyncio.sleep(backoff)

                backoff = min(backoff * 2.0, 60.0)

    def _microphone_listen(self):

        try:

            import speech_recognition as sr

        except ImportError:

            print("[JARVIS] ⚠️ speech_recognition not installed")

            return

        recognizer = sr.Recognizer()

        recognizer.energy_threshold = self._audio_settings.get("vad_threshold_rising", 300)

        recognizer.dynamic_energy_threshold = True

        recognizer.pause_threshold = 0.8

        recognizer.non_speaking_duration = 0.5  # Must be <= pause_threshold to avoid AssertionError

    async def _run_local_offline_loop(self):

        """

        Classic STT -> LLM -> TTS pipeline for Local Mode, bypassing Gemini Live WebRTC.

        """

        self._loop = asyncio.get_event_loop()

        from kree.core.llm_gateway import KreeIntelligenceEngine

        # We need speech_recognition here, but we import locally inside _microphone_listen

        import speech_recognition as sr

        engine = KreeIntelligenceEngine(live_instance=self)

        recognizer = sr.Recognizer()

        recognizer.energy_threshold = self._audio_settings.get("vad_threshold_rising", 300)

        recognizer.dynamic_energy_threshold = True

        recognizer.pause_threshold = 0.8

        recognizer.non_speaking_duration = 0.5  # Must be <= pause_threshold to avoid AssertionError

        # For testing, bypass saved configuration and force default input device
        device_index = None

        mic = sr.Microphone(device_index=device_index)

        with mic as source:

            recognizer.adjust_for_ambient_noise(source, duration=1.0)

            print("[JARVIS] 🎤 Local Air-gapped Mic ready.")

            while True:

                # Poll for mode switch back to cloud

                if "LOCAL" not in load_audio_settings().get("intelligence_mode", "CLOUD_GEMINI"):

                    print("[JARVIS] 🔌 Mode switched back to Cloud. Exiting local loop.")

                    break

                try:

                    # STT phase (Listen)

                    audio = await asyncio.to_thread(recognizer.listen, source, timeout=1.0, phrase_time_limit=10.0)

                    # Instant acknowledgment SFX (Jarvis-style)

                    try:

                        import winsound

                        winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS | winsound.SND_ASYNC)

                    except: pass

                    try:

                        # True Offline STT using Vosk

                        import json

                        text_json = await asyncio.to_thread(recognizer.recognize_vosk, audio)

                        # Vosk returns a JSON string like {"text": "something"}

                        try:

                            parsed_text = json.loads(text_json).get("text", "")

                        except (json.JSONDecodeError, TypeError, AttributeError):

                            parsed_text = ""

                        text = self._sanitize_multilingual_transcript(parsed_text)

                        if not text: continue

                        print(f"[JARVIS] 🗣️ Heard (Offline STT): {text}")

                        self.ui.write_log(f"You: {text}")

                        if text.lower().startswith("open "):

                            self.on_user_text(text)

                            continue

                        # LLM Gateway phase (Think)

                        response_text = await asyncio.to_thread(engine.generate_content, text)

                        if "[OFFLINE MODE]" in response_text:

                            print(response_text)

                            self.ui.write_log(f"⚠️ {response_text}")

                            self.speak("Sir, I cannot reach the local Ollama node. Please ensure it is running.")

                            await asyncio.sleep(5)

                            continue

                        print(f"[JARVIS] 🧠 Local Gemma Response: {response_text[:100]}...")

                        self.ui.write_log(f"Kree: {response_text}")

                        # TTS phase (Speak)

                        self.speak(response_text)

                    except sr.UnknownValueError:

                        pass # Couldn't understand audio

                    except Exception as e:

                        if "model" in str(e).lower() and "vosk" in str(e).lower():

                            print("[JARVIS] ⚠️ Vosk STT Model not found. Download 'vosk-model-small-en-us' and place it in the root folder as 'model'.")

                            self.ui.write_log("Vosk model missing. Please download it for offline voice recognition.")

                            await asyncio.sleep(10)

                        else:

                            print(f"[JARVIS] STT error: {e}")

                            await asyncio.sleep(1)

                except sr.WaitTimeoutError:

                    pass # Timeout silently to re-check the loop

                except Exception as e:

                    print(f"[JARVIS] Local loop error: {e}")

                    await asyncio.sleep(1)

def main():
    import sys
    # ── Write Startup Diagnostics ──
    try:
        import platform
        from kree.core.runtime import LOG_DIR, setup_rotating_logger
        from kree.core.version import APP_VERSION
        
        startup_log_file = LOG_DIR / "startup.log"
        startup_logger = setup_rotating_logger("KreeStartup", startup_log_file, max_bytes=5*1024*1024, backup_count=1)
        
        # Test imports / availability
        try:
            from kree.core import auth_store
            vault_status = "Available"
        except Exception as e:
            vault_status = f"Error: {e}"
            
        try:
            from kree.core.wakeword import WakeWordDetector
            wakeword_status = "Available"
        except Exception as e:
            wakeword_status = f"Error: {e}"
            
        try:
            from kree.memory import memory_manager
            memory_data = memory_manager.load_memory()
            memory_status = f"Available ({len(memory_data.get('preferences', {})) + len(memory_data.get('identity', {}))} entries)"
        except Exception as e:
            memory_status = f"Error: {e}"
            
        startup_logger.info("=========================================")
        startup_logger.info("Kree Startup Boot Sequence Started")
        startup_logger.info(f"Version: {APP_VERSION}")
        startup_logger.info(f"Python version: {sys.version.split()[0]}")
        startup_logger.info(f"OS Platform: {platform.platform()}")
        startup_logger.info(f"Arguments: {sys.argv}")
        startup_logger.info(f"Vault Status: {vault_status}")
        startup_logger.info(f"Wake Word Status: {wakeword_status}")
        startup_logger.info(f"Long-Term Memory Status: {memory_status}")
        startup_logger.info("=========================================")
    except Exception as e:
        sys.stderr.write(f"⚠️ Failed to write startup log: {e}\n")


    import sys

    from kree.core.runtime import run_health_check

    # Defer health check to a background thread to speed up UI initialization

    def run_health_check_bg():
        try:
            health = run_health_check()
            print(f"[JARVIS] Startup Health Check: {health}")
            
            # Save first_run_diagnostics for beta testers
            import os
            import json
            localappdata = os.environ.get('LOCALAPPDATA', '')
            if localappdata:
                logs_dir = os.path.join(localappdata, "Kree", "logs")
                first_run_file = os.path.join(logs_dir, "first_run.txt")
                os.makedirs(logs_dir, exist_ok=True)
                if not os.path.exists(first_run_file):
                    with open(first_run_file, 'w', encoding='utf-8') as f:
                        f.write("KREE AI FIRST RUN DIAGNOSTICS\n")
                        f.write("=============================\n")
                        f.write(json.dumps(health, indent=4))
        except Exception as e:
            print(f"[JARVIS] Health check failed: {e}")

    def run_watchdog_bg():
        import time
        print("[JARVIS] 👁️ Watchdog Service Active")
        while True:
            time.sleep(10)
            try:
                # Check Wakeword Engine
                if hasattr(ui, '_kree_instance') and ui._kree_instance:
                    kree = ui._kree_instance
                    if hasattr(kree, '_wakeword_detector') and kree._wakeword_detector:
                        ww = kree._wakeword_detector
                        if hasattr(ww, '_last_heartbeat'):
                            # Wakeword pauses when wake_event is set. Only restart if awake and no heartbeat for 30s.
                            is_paused = getattr(kree, 'wake_event', None) and kree.wake_event.is_set()
                            is_ready = getattr(ww, 'is_ready', False)
                            if is_ready and not is_paused and (time.time() - ww._last_heartbeat > 30):
                                print("[WATCHDOG] 🔴 WakeWord engine timed out! Restarting...")
                                try: ww.stop()
                                except: pass
                                try: ww.start()
                                except: pass
                                print("[WATCHDOG] 🟢 WakeWord engine resurrected")
            except Exception as e:
                print(f"[WATCHDOG] Error: {e}")

    import threading
    threading.Thread(target=run_health_check_bg, daemon=True).start()
    threading.Thread(target=run_watchdog_bg, daemon=True).start()

    is_background = "--background" in sys.argv
    if is_background:
        import time
        print("[JARVIS] ⏳ Background mode detected. Delaying startup by 25 seconds for system services...")
        time.sleep(25)

    ui = JarvisUI("face.png", startup_hidden=True)

    def runner():

        _bootlog("[BOOT] Runner thread started")
        _bootlog(f"[BOOT] _api_key_ready={ui._api_key_ready}, _is_unlocked={ui._is_unlocked}, _active_user={bool(ui._active_user)}")

        # ══════════════════════════════════════════════════════════════════
        # PHASE 1: Boot core services IMMEDIATELY (no API key needed)
        # Wake word, tray, and notification should work even without login
        # ══════════════════════════════════════════════════════════════════

        _bootlog("[BOOT] Phase 1: Creating JarvisLive (no API gate)...")
        # -- First Run Startup Prompt (non-blocking) --
        def _first_run_prompt():
            try:
                from kree.memory.config_manager import load_audio_settings, save_audio_settings
                import ctypes
                import winreg
                import sys

                settings = load_audio_settings()

                if 'auto_start_configured' not in settings:
                    result = ctypes.windll.user32.MessageBoxW(0,
                        "Should Kree start automatically when Windows starts?\nThis lets you use the wake word anytime. (Recommended)",
                        "Kree AI Setup", 0x04 | 0x20)  # YESNO | QUESTION

                    if result == 6:  # IDYES
                        try:
                            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
                            winreg.SetValueEx(key, "Kree", 0, winreg.REG_SZ, '"' + sys.executable + '" --background')
                            winreg.CloseKey(key)
                            settings['auto_start_configured'] = True
                        except Exception as e:
                            print(f"Failed setting startup reg: {e}")
                    else:
                        settings['auto_start_configured'] = False

                    save_audio_settings(settings)
            except Exception:
                pass

        import threading
        threading.Thread(target=_first_run_prompt, daemon=True).start()
        kree = JarvisLive(ui)
        _bootlog("[BOOT] Phase 1: JarvisLive created")

        ui._kree_instance = kree
        kree.start_awake = False


        # ── System Tray (no API needed) ──
        try:

            from kree.core.tray import SystemTrayApp

            def safe_shutdown():

                print("[JARVIS] 🛑 Processing safe shutdown...")

                kree._shutting_down = True

                try:

                    if hasattr(kree, "_trigger_engine") and kree._trigger_engine:

                        kree._trigger_engine.stop()

                except: pass

                try:

                    if hasattr(kree, "context_tts") and kree.context_tts:

                        kree.context_tts.stop()

                except: pass

                try:

                    import logging

                    logging.shutdown()

                except: pass

                from kree.core.updater import run_installer_and_exit

                run_installer_and_exit()

                import sys

                sys.exit(0)

            def open_ui():
                try: 
                    kree.ui.wake()
                except: pass

            def reload_wake():
                print("[JARVIS] 🔄 Reloading Wake Word...")
                try:
                    if hasattr(kree, "_wakeword_detector") and kree._wakeword_detector:
                        kree._wakeword_detector.stop()
                        kree._wakeword_detector.start()
                except Exception as e: print(e)

            def view_logs():
                try:
                    import os
                    os.startfile(_LOG_FILE.parent)
                except Exception as e: print(e)

            tray = SystemTrayApp({
                "open": open_ui,
                "restart_audio": lambda: print("[JARVIS] 🔄 Restarting Audio..."),
                "reload_wake": reload_wake,
                "diagnostics": lambda: print("[JARVIS] 🩺 System Diagnostics OK"),
                "view_logs": view_logs,
                "quit": safe_shutdown
            })

            kree.system_tray = tray

            tray.run_daemon()

            _bootlog("[BOOT] Phase 1: System Tray Armed")

        except Exception as e:

            _bootlog(f"[BOOT] Phase 1: Tray failed: {e}")

        # ── Wake Word Engine (no API needed) ──

        try:
            _bootlog("[BOOT] Phase 1: Importing WakeWordDetector...")
            from kree.core.wakeword import WakeWordDetector
            _bootlog("[BOOT] Phase 1: WakeWordDetector imported OK")

            _bootlog("[BOOT] Phase 1: Creating WakeWordDetector...")
            wakeword = WakeWordDetector(on_wake_callback=kree.wake)
            _bootlog("[BOOT] Phase 1: WakeWordDetector created OK")

            _bootlog("[BOOT] Phase 1: Starting wake word thread...")
            wakeword.start()
            _bootlog("[BOOT] Phase 1: Wake word thread started OK")

            kree._wakeword_detector = wakeword

            _bootlog("[BOOT] Phase 1: WakeWord Daemon Armed")

        except Exception as e:
            import traceback
            _bootlog(f"[BOOT] Phase 1 FATAL: WakeWord boot failed: {e}")
            _bootlog(f"[BOOT] Traceback:\n{traceback.format_exc()}")

        # ── Notify user: core services are ready ──
        try:
            import winsound
            from kree.core.runtime import ASSETS_DIR
            winsound.PlaySound(str(ASSETS_DIR / "sounds" / "wake.wav"), winsound.SND_FILENAME | winsound.SND_ASYNC)
        except Exception:
            pass

        try:
            pass
        except Exception:
            pass

        _bootlog("[BOOT] Phase 1 COMPLETE: Wake word + tray active")

        # ══════════════════════════════════════════════════════════════════
        # PHASE 2: Wait for API key, then start Gemini Live connection
        # This only blocks the AI chat — wake word keeps listening
        # ══════════════════════════════════════════════════════════════════

        _bootlog("[BOOT] Phase 2: Waiting for API key...")
        ui.wait_for_api_key()
        _bootlog("[BOOT] Phase 2: API key ready")

        _bootlog("[BOOT] Phase 2: Waiting for unlock...")
        ui.wait_for_unlock()
        _bootlog("[BOOT] Phase 2: Unlocked")

        # Boot analytics session

        try:

            from kree.core.analytics import track_session_start

            track_session_start()

        except Exception:

            pass

        # Boot auto-updater (background check + silent download)

        try:

            from kree.core.updater import check_update_background

            # v1.0.1 Stable: Enabling auto_download by default

            check_update_background(ui=ui, speak_fn=_local_speech_voice, auto_download=True)

        except Exception:

            pass

        _bootlog("[BOOT] Phase 2: Starting Gemini Live session...")
        try:

            asyncio.run(kree.run())

        except KeyboardInterrupt:

            safe_shutdown()

        except Exception as e:

            import traceback

            import sys

            import platform

            import datetime

            from kree.core.runtime import LOG_DIR

            from kree.core.version import APP_VERSION

            error_details = traceback.format_exc()

            print(f"[KREE CRASH] {e}\n{error_details}")

            # Write to logs/crash.log

            crash_file = LOG_DIR / "crash.log"

            try:

                crash_log_msg = (

                    f"=========================================\n"

                    f"CRASH TIMESTAMP: {datetime.datetime.now().isoformat()}\n"

                    f"PLATFORM: {platform.platform()}\n"

                    f"PYTHON: {sys.version}\n"

                    f"KREE VERSION: {APP_VERSION}\n"

                    f"EXCEPTION: {type(e).__name__}: {e}\n"

                    f"TRACEBACK:\n{error_details}"

                    f"=========================================\n\n"

                )

                with open(crash_file, "a", encoding="utf-8") as f:

                    f.write(crash_log_msg)

            except Exception:

                pass

            try:

                from kree.core.analytics import track_error

                track_error("crash", str(e))

            except Exception:

                pass

            try:

                from kree.core.backend import log_crash

                log_crash(str(e), error_details)

            except Exception:

                pass

            raise

        finally:

            try:

                from kree.core.analytics import shutdown

                shutdown()

            except Exception:

                pass

    threading.Thread(target=runner, daemon=True).start()

    ui.run()  # blocks — runs the pywebview event loop

if __name__ == "__main__":

    main()
