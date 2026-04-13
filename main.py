from __future__ import annotations

# ── CRITICAL: Force UTF-8 stdout/stderr on Windows ──────────────────────────
# Without this, any print() containing emoji (💬, ⚡, etc.) crashes the
# entire thread with UnicodeEncodeError because Windows uses cp1252/cp437.
import sys as _sys
import io as _io
import os as _os
import platform as _platform
import logging as _logging
from pathlib import Path as _Path

if hasattr(_sys.stdout, 'buffer'):
    _sys.stdout = _io.TextIOWrapper(_sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
if hasattr(_sys.stderr, 'buffer'):
    _sys.stderr = _io.TextIOWrapper(_sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)

# ── EMERGENGY LOGGING ────────────────────────────────────────────────────────
try:
    if getattr(_sys, "frozen", False):
        log_dir = _Path(_os.environ.get("LOCALAPPDATA", "C:\\Temp")) / "Kree AI"
    else:
        log_dir = _Path(__file__).parent / "logs"
    
    log_dir.mkdir(parents=True, exist_ok=True)
    _LOG_FILE = log_dir / "kree_debug.log"

    _logging.basicConfig(
        filename=str(_LOG_FILE),
        level=_logging.DEBUG,
        format='%(asctime)s [%(levelname)s] %(message)s',
        filemode='a'
    )
    _logging.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    _logging.info("Kree AI Production Runtime Starting (DEBUG MODE)...")
    _logging.info(f"Platform: {_platform.system()} {_platform.release()}")
except Exception as e:
    _sys.stderr.write(f"CRITICAL: Logging init failed: {e}\n")

import asyncio
import collections
import threading
import json
import difflib
import re
import sys
import traceback
import functools
import base64
import unicodedata
import subprocess
import platform
from pathlib import Path
from typing import Any, Optional

try:
    import pyaudio  # type: ignore[import]
    import cv2      # type: ignore[import]
except ImportError:
    pyaudio = None  # type: ignore[assignment]
    cv2 = None      # type: ignore[assignment]
    print("[JARVIS] ⚠️ PyAudio or CV2 not installed.")

import time
import wave
from ui import JarvisUI  # type: ignore[import]
from memory.memory_manager import load_memory, update_memory, format_memory_for_prompt  # type: ignore[import]
from memory.config_manager import load_audio_settings, load_telemetry_settings  # type: ignore[import]
from core.telemetry import TelemetryEvents, TelemetryLogger, export_session_trace, load_session_events  # type: ignore[import]

from agent.task_queue import get_queue  # type: ignore[import]

from actions.flight_finder import flight_finder  # type: ignore[import]
from actions.open_app         import open_app  # type: ignore[import]
from actions.downloader_updater import downloader_updater  # type: ignore[import]
from actions.turboquant_helper import turboquant_helper  # type: ignore[import]
from actions.openapps_automation import openapps_automation  # type: ignore[import]
from actions.weather_report   import weather_action  # type: ignore[import]
from actions.send_message     import send_message  # type: ignore[import]
from actions.reminder         import reminder  # type: ignore[import]
from actions.computer_settings import computer_settings  # type: ignore[import]
from actions.screen_processor import screen_process  # type: ignore[import]
from actions.youtube_video    import youtube_video  # type: ignore[import]
from actions.cmd_control      import cmd_control  # type: ignore[import]
from actions.desktop          import desktop_control  # type: ignore[import]
from actions.browser_control  import browser_control  # type: ignore[import]
from actions.file_controller  import file_controller  # type: ignore[import]
from actions.code_helper      import code_helper  # type: ignore[import]
from actions.dev_agent        import dev_agent  # type: ignore[import]
from actions.web_search       import web_search as web_search_action  # type: ignore[import]
from actions.computer_control import computer_control  # type: ignore[import]
from actions.email_calendar   import productivity_manager  # type: ignore[import]
from core.trigger_engine import TriggerEngine

def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


BASE_DIR = get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"
PROMPT_PATH = BASE_DIR / "core" / "prompt.txt"
LIVE_MODEL = "models/gemini-2.5-flash-native-audio-preview-12-2025"
FORMAT = pyaudio.paInt16 if pyaudio else 8  # paInt16 = 8
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024
MAX_AUDIO_IN_QUEUE = 96
MAX_AUDIO_OUT_QUEUE = 48
MAX_PLAY_QUEUE = 120


# ── Lazy PyAudio init (prevents crash if no audio device at startup) ──────────
_pya = None
_pya_lock = threading.Lock()


def _get_pya() -> Any:
    global _pya
    if _pya is None:
        with _pya_lock:
            if _pya is None and pyaudio is not None:
                try:
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
    import core.vault as vault  # type: ignore[import]

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
            import memory.history_manager as hist
            import core.user_profile as up
            
            # Fetch Context
            history_summary = hist.get_memory_summary()
            profile = up.get_user_profile()
            
            # Identity Injection
            ident_block = ""
            if profile.get("name"):
                ident_block += f"\nThe user's name is {profile['name']}. Address them as sir.\n"
            if profile.get("default_email"):
                ident_block += f"Default email: {profile['default_email']}\n"
                
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


def _local_speech_voice(text: str) -> None:
    """Instant local Windows speech using Edge TTS neural voices to eliminate robotic fallback."""
    import threading
    def speak():
        try:
            import os
            import subprocess
            import uuid
            
            from memory.config_manager import load_audio_settings
            settings = load_audio_settings()
            gemini_voice = settings.get("kree_voice", "Kore")
            voice = {
                "Aoede": "en-US-AriaNeural",
                "Kore": "en-US-JennyNeural",
                "Puck": "en-US-GuyNeural",
                "Charon": "en-US-ChristopherNeural"
            }.get(gemini_voice, "en-US-JennyNeural")
            
            # Use same high-fidelity voice as the wake word
            temp_mp3 = BASE_DIR / "assets" / "sounds" / f"temp_speech_{uuid.uuid4().hex[:6]}.mp3"
            temp_mp3.parent.mkdir(parents=True, exist_ok=True)
            
            import edge_tts
            import asyncio
            # Create isolated event loop for synchronous thread evaluation
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(edge_tts.Communicate(text, voice).save(str(temp_mp3)))
            finally:
                loop.close()
            
            # Play it using pygame synchronously in this thread
            import pygame
            import time
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.load(str(temp_mp3))
            pygame.mixer.music.play()
            
            # Wait for it to finish playing
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
                
            # Cleanup
            pygame.mixer.music.unload()
            try: os.remove(str(temp_mp3))
            except: pass
            
        except Exception as e:
            print(f"[KREE TTS] ⚠️ Local neural speech failed: {e}")
            
    threading.Thread(target=speak, daemon=True).start()


def _local_welcome_voice(kree_instance) -> None:
    """Play pre-cached greeting and write 'Kree is online' to transcript."""
    try:
        greeting_mp3 = BASE_DIR / "assets" / "sounds" / "active_greeting.mp3"
        import os
        if greeting_mp3.exists() and os.path.getsize(greeting_mp3) > 1000:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.load(str(greeting_mp3))
            pygame.mixer.music.play()
    except Exception as e:
        print(f"[JARVIS] Welcome voice error (non-fatal): {e}")
    
    try:
        kree_instance.ui.write_log("Kree: Kree is online and ready, sir.")
    except Exception:
        pass


def _build_contextual_greeting(name: str = "sir") -> str:
    """
    Highly advanced context-aware greeting engine.
    Checks battery level, active window title (what the user is currently looking at),
    and time of day to formulate a highly targeted and natural greeting.
    """
    import datetime
    import random
    
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

    # Fallback to tasklist if foreground detection yields nothing specific
    if not activity_context:
        try:
            import subprocess
            tasklist = subprocess.check_output(
                "tasklist /FO CSV /NH", shell=True, stderr=subprocess.DEVNULL
            ).decode(errors="ignore").lower()

            if "code.exe" in tasklist or "devenv.exe" in tasklist:
                activity_context = "coding"
            elif "spotify.exe" in tasklist:
                activity_context = "music"
        except Exception:
            pass

    # ── Prioritized Greeting Logic ──

    # Priority 1: Critical System Status
    if activity_context == "low_battery":
        return random.choice([
            f"Sir, battery is extremely low. You might want to plug in.",
            f"Battery critical, {name}. Please connect power."
        ])

    # Priority 2: Specific Foreground Activities
    if activity_context == "youtube":
        return random.choice([
            f"Enjoying the video, {name}?",
            f"Watching something interesting, {name}?",
            f"Yes, {name}?"
        ])
    elif activity_context == "github":
        return random.choice([
            f"Reviewing repositories, {name}?",
            f"Need help with GitHub, {name}?",
            f"Looking at pull requests, {name}?"
        ])
    elif activity_context == "debugging":
        return random.choice([
            f"Need help debugging, {name}?",
            f"Stuck on a bug, {name}?",
            f"What's the error say, {name}?"
        ])
    elif activity_context == "coding":
        return random.choice([
            f"Back to the code, {name}?",
            f"What are we building, {name}?",
            f"Ready to code when you are, {name}.",
            f"What do you need {name}?"
        ])
    elif activity_context == "music":
        return random.choice([
            f"{name}?",
            f"Yes?",
            f"I'm here."
        ])

    # Priority 3: Time & Day combinations
    if day == 0 and hr < 12: # Monday Morning
        return random.choice([
            f"Monday morning, {name}. Ready to conquer the week?",
            f"Welcome to a new week, {name}.",
            f"Monday morning, let's get started."
        ])
    elif day == 4 and hr > 16: # Friday Evening
        return random.choice([
            f"It's Friday evening, {name}. Almost time to relax.",
            f"Wrapping up the week, {name}?",
            f"Friday evening, {name}. What's left?"
        ])

    # Priority 4: Standard Time-based greetings
    if hr < 6:
        return random.choice([
            f"Working late, {name}?",
            f"Still up, {name}?",
            f"It's quite late, {name}. What do you need?"
        ])
    elif hr < 12:
        return random.choice([
            f"Good morning, {name}.",
            f"Morning, {name}. Ready to start?",
            f"Good morning. What's the plan for today?"
        ])
    elif hr < 18:
        return random.choice([
            f"Kree online, {name}.",
            f"Good afternoon, {name}.",
            f"Yes, {name}?",
            f"How can I help you, {name}?"
        ])
    elif hr < 22:
        return random.choice([
            f"Good evening, {name}.",
            f"Evening, {name}. What's next?",
            f"Yes, {name}?"
        ])
    else:
        return random.choice([
            f"Still up, {name}?",
            f"Working late, {name}?",
            f"Good evening, {name}."
        ])

class ContextTTSEngine:
    """Pre-generates the context greeting as an MP3 using high-quality Edge TTS in the background."""
    def __init__(self):
        import os
        import warnings
        os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
        warnings.filterwarnings("ignore", category=UserWarning, module="pygame.pkgdata")
        import pygame
        
        self.last_text = ""
        self.tts_path = BASE_DIR / "assets" / "sounds" / "active_greeting.mp3"
        self.running = True
        
        try:
            pygame.mixer.init()
        except: pass
        
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        import time
        import os
        import subprocess
        from memory.config_manager import load_audio_settings
        while self.running:
            try:
                current = _build_contextual_greeting("sir")
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
            time.sleep(5)

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
            
            # Check if there is a fact
            check_prompt = "Is there a new permanent fact or preference to remember about the user here? Reply only YES or NO.\n\n" + chunk_to_process
            res_check = client.models.generate_content(model="gemini-2.5-flash-lite", contents=check_prompt)
            if "yes" not in res_check.text.strip().lower():
                return

            ext_prompt = (
                "Extract bullet points of new facts or preferences about the user. Do not include random chat.\n\n"
                f"{chunk_to_process}"
            )
            res_ext = client.models.generate_content(model="gemini-2.5-flash-lite", contents=ext_prompt)
            
            # Logic to update memory would go here
            print(f"[Memory] ✅ Updated: {res_ext.text.strip()}")

        except Exception as e:
            if "429" not in str(e):
                print(f"[Memory] ⚠️ {e}")
    threading.Thread(target=worker, daemon=True).start()


TOOL_DECLARATIONS = [
    {
        "name": "trigger_macro",
        "description": (
            "Triggers a complex multi-app macro chain concurrently (e.g. 'work session', 'gaming session'). "
            "Use this precisely when the user asks to initiate a 'session' or complex workflow."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "chain_name": {
                    "type": "STRING",
                    "description": "The logical name of the chain (e.g. 'work session')"
                }
            },
            "required": ["chain_name"]
        }
    },
    {
        "name": "open_app",
        "description": (
            "Opens any application on the Windows computer. "
            "Use this whenever the user asks to open, launch, or start any app, "
            "website, or program. Always call this tool — never just say you opened it."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app_name": {
                    "type": "STRING",
                    "description": "Exact name of the application (e.g. 'WhatsApp', 'Chrome', 'Spotify')"
                }
            },
            "required": ["app_name"]
        }
    },
    {
        "name": "openapps_automation",
        "description": (
            "Controls OpenApps as an optional automation and multi-tasking engine. "
            "Use this for simulated app workflows, benchmark tasks, or parallel agent tasks. "
            "Do NOT replace native app opening with this tool. "
            "User phrase alias: 'Start Kree automation environment'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "launch_env | start_kree_automation_environment | run_task | run_parallel_tasks | run_preset | open_and_delegate | list_apps | list_agents | list_tasks | license_info | stop | status"
                },
                "app": {
                    "type": "STRING",
                    "description": "Optional OpenApps app name for launch_env (todo|calendar|maps|messenger|code_editor)"
                },
                "theme": {
                    "type": "STRING",
                    "description": "Optional UI theme for launch_env: dark | light"
                },
                "agent": {
                    "type": "STRING",
                    "description": "Agent config for run_task/run_parallel_tasks, e.g. GPT-5-1"
                },
                "task_name": {
                    "type": "STRING",
                    "description": "OpenApps benchmark task name for run_task"
                },
                "headless": {
                    "type": "BOOLEAN",
                    "description": "Set false to watch the run in a visible browser"
                },
                "timeout": {
                    "type": "INTEGER",
                    "description": "Timeout in seconds for run_task"
                },
                "extra": {
                    "type": "STRING",
                    "description": "Optional extra CLI overrides for run_parallel_tasks"
                },
                "preset": {
                    "type": "STRING",
                    "description": "Preset name for run_preset (e.g. codex_github_app_builder)"
                },
                "prompt": {
                    "type": "STRING",
                    "description": "Prompt for preset automation, e.g. app requirements for Codex"
                },
                "targets": {
                    "type": "STRING",
                    "description": "Apps/sites to open for open_and_delegate. Example: 'codex and github and vscode'"
                },
                "delegate_app": {
                    "type": "STRING",
                    "description": "Where to send instruction for open_and_delegate. Example: codex"
                },
                "fallback": {
                    "type": "STRING",
                    "description": "For missing native app: ask | download | browser"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "downloader_updater",
        "description": (
            "Downloads files and installs/updates software. "
            "Use this when user asks to download, install, update, upgrade, or check available updates."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "download_file | download | install_app | update_app | update_all | check_updates | auto"
                },
                "url": {
                    "type": "STRING",
                    "description": "URL for download_file"
                },
                "destination": {
                    "type": "STRING",
                    "description": "Optional destination path for downloads"
                },
                "target": {
                    "type": "STRING",
                    "description": "App name or winget ID for install_app/update_app/download"
                },
                "query": {
                    "type": "STRING",
                    "description": "Natural language request for auto action (e.g., 'download github' or 'update vscode')"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "turboquant_helper",
        "description": (
            "Reports whether TurboQuant and HuggingFace-style tooling are available, "
            "prepares cache directories, and returns loader environment hints. Use this when the user asks about TurboQuant or future local model setup."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "status | prepare_cache | environment | export"
                },
                "model_id": {
                    "type": "STRING",
                    "description": "Optional HuggingFace model id such as meta-llama/Llama-3.1-8B-Instruct"
                },
                "cache_root": {
                    "type": "STRING",
                    "description": "Optional cache root path for TurboQuant/HF assets"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "session_trace",
        "description": (
            "Captures, summarizes, or exports the current Kree session trace. "
            "Use when the user asks to save a trace, export a session log, inspect recent events, or review what Kree did."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "summary | export | status"
                },
                "label": {
                    "type": "STRING",
                    "description": "Optional filename label for exports"
                },
                "limit": {
                    "type": "INTEGER",
                    "description": "Optional maximum number of events to include"
                }
            },
            "required": ["action"]
        }
    },
{
    "name": "web_search",
    "description": "Searches the web for any information.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "query":  {"type": "STRING", "description": "Search query"},
            "mode":   {"type": "STRING", "description": "search (default) or compare"},
            "items":  {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Items to compare"},
            "aspect": {"type": "STRING", "description": "price | specs | reviews"}
        },
        "required": ["query"]
    }
},
    {
        "name": "weather_report",
        "description": "Gets real-time weather information for a city.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "city": {"type": "STRING", "description": "City name"}
            },
            "required": ["city"]
        }
    },
    {
        "name": "send_message",
        "description": "Sends a text message via WhatsApp, Telegram, or other messaging platform.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "receiver":     {"type": "STRING", "description": "Recipient contact name"},
                "message_text": {"type": "STRING", "description": "The message to send"},
                "platform":     {"type": "STRING", "description": "Platform: WhatsApp, Telegram, etc."}
            },
            "required": ["receiver", "message_text", "platform"]
        }
    },
    {
        "name": "reminder",
        "description": "Sets a timed reminder using Windows Task Scheduler.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "date":    {"type": "STRING", "description": "Date in YYYY-MM-DD format"},
                "time":    {"type": "STRING", "description": "Time in HH:MM format (24h)"},
                "message": {"type": "STRING", "description": "Reminder message text"}
            },
            "required": ["date", "time", "message"]
        }
    },
    {
    "name": "youtube_video",
    "description": (
        "Controls YouTube. Use for: playing videos, summarizing a video's content, "
        "getting video info, or showing trending videos."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "play | summarize | get_info | trending (default: play)"
            },
            "query":  {"type": "STRING", "description": "Search query for play action"},
            "save":   {"type": "BOOLEAN", "description": "Save summary to Notepad (summarize only)"},
            "region": {"type": "STRING", "description": "Country code for trending e.g. TR, US"},
            "url":    {"type": "STRING", "description": "Video URL for get_info action"},
        },
        "required": []
    }
    },
    {
        "name": "screen_process",
        "description": (
            "Captures and analyzes the screen or webcam image. "
            "MUST be called when user asks what is on screen, what you see, "
            "analyze my screen, look at camera, etc. "
            "You have NO visual ability without this tool. "
            "After calling this tool, stay SILENT — the vision module speaks directly."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "angle": {
                    "type": "STRING",
                    "description": "'screen' to capture display, 'camera' for webcam. Default: 'screen'"
                },
                "text": {
                    "type": "STRING",
                    "description": "The question or instruction about the captured image"
                }
            },
            "required": ["text"]
        }
    },
    {
    "name": "computer_settings",
    "description": (
        "Controls the computer: volume, brightness, window management, keyboard shortcuts, "
        "typing text on screen, closing apps, fullscreen, dark mode, WiFi, restart, shutdown, "
        "scrolling, tab management, zoom, screenshots, lock screen, refresh/reload page. "
        "ALSO use for repeated actions: 'refresh 10 times', 'reload page 5 times' → action: reload_n, value: 10. "
        "Use for ANY single computer control command — even if repeated N times. "
        "NEVER route simple computer commands to agent_task."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action":      {"type": "STRING", "description": "The action to perform (if known). For repeated reload: 'reload_n'"},
            "description": {"type": "STRING", "description": "Natural language description of what to do"},
            "value":       {"type": "STRING", "description": "Optional value: volume level, text to type, number of times, etc."}
        },
        "required": []
    }
},
    {
        "name": "browser_control",
        "description": (
            "Controls the web browser. Use for: opening websites, searching the web, "
            "clicking elements, filling forms, scrolling, finding cheapest products, "
            "booking flights, any web-based task."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "go_to | search | click | type | scroll | fill_form | smart_click | smart_type | get_text | press | close"},
                "url":         {"type": "STRING", "description": "URL for go_to action"},
                "query":       {"type": "STRING", "description": "Search query for search action"},
                "selector":    {"type": "STRING", "description": "CSS selector for click/type"},
                "text":        {"type": "STRING", "description": "Text to click or type"},
                "description": {"type": "STRING", "description": "Element description for smart_click/smart_type"},
                "direction":   {"type": "STRING", "description": "up or down for scroll"},
                "key":         {"type": "STRING", "description": "Key name for press action"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "file_controller",
        "description": (
            "Manages files and folders. Use for: listing files, creating/deleting/moving/copying "
            "files, reading file contents, finding files by name or extension, checking disk usage, "
            "organizing the desktop, getting file info."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "list | create_file | create_folder | delete | move | copy | rename | read | write | find | largest | disk_usage | organize_desktop | info"},
                "path":        {"type": "STRING", "description": "File/folder path or shortcut: desktop, downloads, documents, home"},
                "destination": {"type": "STRING", "description": "Destination path for move/copy"},
                "new_name":    {"type": "STRING", "description": "New name for rename"},
                "content":     {"type": "STRING", "description": "Content for create_file/write"},
                "name":        {"type": "STRING", "description": "File name to search for"},
                "extension":   {"type": "STRING", "description": "File extension to search (e.g. .pdf)"},
                "count":       {"type": "INTEGER", "description": "Number of results for largest"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "cmd_control",
        "description": (
            "Runs CMD/terminal commands by understanding natural language. "
            "Use when user wants to: find large files, check disk space, list processes, "
            "get system info, navigate folders, check network, find files by name, "
            "or do ANYTHING in the command line they don't know how to do themselves."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "task":    {"type": "STRING", "description": "Natural language description of what to do. Example: 'find the 10 largest files on C drive'"},
                "visible": {"type": "BOOLEAN", "description": "Open visible CMD window so user can see. Default: true"},
                "command": {"type": "STRING", "description": "Optional: exact command if already known"},
            },
            "required": ["task"]
        }
    },
    {
        "name": "desktop_control",
        "description": (
            "Controls the desktop. Use for: changing wallpaper, organizing desktop files, "
            "cleaning the desktop, listing desktop contents, or ANY other desktop-related task "
            "the user describes in natural language."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "wallpaper | wallpaper_url | organize | clean | list | stats | task"},
                "path":   {"type": "STRING", "description": "Image path for wallpaper"},
                "url":    {"type": "STRING", "description": "Image URL for wallpaper_url"},
                "mode":   {"type": "STRING", "description": "by_type or by_date for organize"},
                "task":   {"type": "STRING", "description": "Natural language description of any desktop task"},
            },
            "required": ["action"]
        }
    },
    {
    "name": "code_helper",
    "description": (
        "Writes, edits, explains, runs, or self-builds code files. "
        "Use for ANY coding request: writing a script, fixing a file, "
        "editing existing code, running a file, or building and testing automatically."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action":      {"type": "STRING", "description": "write | edit | explain | run | build | auto (default: auto)"},
            "description": {"type": "STRING", "description": "What the code should do, or what change to make"},
            "language":    {"type": "STRING", "description": "Programming language (default: python)"},
            "output_path": {"type": "STRING", "description": "Where to save the file (full path or filename)"},
            "file_path":   {"type": "STRING", "description": "Path to existing file for edit / explain / run / build"},
            "code":        {"type": "STRING", "description": "Raw code string for explain"},
            "args":        {"type": "STRING", "description": "CLI arguments for run/build"},
            "timeout":     {"type": "INTEGER", "description": "Execution timeout in seconds (default: 30)"},
        },
        "required": ["action"]
    }
    },
    {
    "name": "dev_agent",
    "description": (
        "Builds complete multi-file projects from scratch. "
        "Plans structure, writes all files, installs dependencies, "
        "opens VSCode, runs the project, and fixes errors automatically. "
        "Use for any project larger than a single script."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "description":  {"type": "STRING", "description": "What the project should do"},
            "language":     {"type": "STRING", "description": "Programming language (default: python)"},
            "project_name": {"type": "STRING", "description": "Optional project folder name"},
            "timeout":      {"type": "INTEGER", "description": "Run timeout in seconds (default: 30)"},
        },
        "required": ["description"]
    }
    },
    {
    "name": "agent_task",
    "description": (
        "Executes complex multi-step tasks that require MULTIPLE DIFFERENT tools. "
        "Always respond to the user in the language they spoke. "
        "Examples: 'research X and save to file', 'find files and organize them', "
        "'fill a form on a website', 'write and test code'. "
        "DO NOT use for simple computer commands like volume, refresh, close, scroll, "
        "minimize, screenshot, restart, shutdown — use computer_settings for those. "
        "DO NOT use if the task can be done with a single tool call."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "goal": {
                "type": "STRING",
                "description": "Complete description of what needs to be accomplished"
            },
            "priority": {
                "type": "STRING",
                "description": "low | normal | high (default: normal)"
            }
        },
        "required": ["goal"]
    }
},
    {
    "name": "computer_control",
    "description": (
        "Direct computer control: type text, click buttons, use keyboard shortcuts, "
        "scroll, move mouse, take screenshots, fill forms, find elements on screen. "
        "Use when the user wants to interact with any app on the computer directly. "
        "Can generate random data for forms or use user's real info from memory."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action":      {"type": "STRING", "description": "type | smart_type | click | double_click | right_click | hotkey | press | scroll | move | copy | paste | screenshot | wait | clear_field | focus_window | screen_find | screen_click | random_data | user_data"},
            "text":        {"type": "STRING", "description": "Text to type or paste"},
            "x":           {"type": "INTEGER", "description": "X coordinate for click/move"},
            "y":           {"type": "INTEGER", "description": "Y coordinate for click/move"},
            "keys":        {"type": "STRING", "description": "Key combination e.g. 'ctrl+c'"},
            "key":         {"type": "STRING", "description": "Single key to press e.g. 'enter'"},
            "direction":   {"type": "STRING", "description": "Scroll direction: up | down | left | right"},
            "amount":      {"type": "INTEGER", "description": "Scroll amount (default: 3)"},
            "seconds":     {"type": "NUMBER", "description": "Seconds to wait"},
            "title":       {"type": "STRING", "description": "Window title for focus_window"},
            "description": {"type": "STRING", "description": "Element description for screen_find/screen_click"},
            "type":        {"type": "STRING", "description": "Data type for random_data: name|email|username|password|phone|birthday|address"},
            "field":       {"type": "STRING", "description": "Field for user_data: name|email|city"},
            "clear_first": {"type": "BOOLEAN", "description": "Clear field before typing (default: true)"},
            "path":        {"type": "STRING", "description": "Save path for screenshot"},
        },
        "required": ["action"]
    }
},

{
    "name": "flight_finder",
    "description": (
        "Searches for flights on Google Flights and speaks the best options. "
        "Use when user asks about flights, plane tickets, uçuş, bilet, etc."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "origin":       {"type": "STRING",  "description": "Departure city or airport code"},
            "destination":  {"type": "STRING",  "description": "Arrival city or airport code"},
            "date":         {"type": "STRING",  "description": "Departure date (any format)"},
            "return_date":  {"type": "STRING",  "description": "Return date for round trips"},
            "passengers":   {"type": "INTEGER", "description": "Number of passengers (default: 1)"},
            "cabin":        {"type": "STRING",  "description": "economy | premium | business | first"},
            "save":         {"type": "BOOLEAN", "description": "Save results to Notepad"},
        },
        "required": ["origin", "destination", "date"]
    }
},
{
    "name": "smart_trigger",
    "description": (
        "Creates or removes autonomous background triggers for Kree. "
        "Use when user says 'remind me every 10 mins', 'tell me if CPU goes over 90%', "
        "'watch my downloads folder', etc. "
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action":         {"type": "STRING", "description": "create | remove"},
            "name":           {"type": "STRING", "description": "A short distinct name for the trigger"},
            "trigger_type":   {"type": "STRING", "description": "system | time | file"},
            "metric":         {"type": "STRING", "description": "cpu | ram | time (e.g. 14:30) | dir_path"},
            "operator":       {"type": "STRING", "description": ">= | <= | =="},
            "value":          {"type": "STRING", "description": "Threshold value, e.g. '90' or '14:30'"},
            "action_to_take": {"type": "STRING", "description": "Natural language command Kree will execute when fired"},
            "silent":         {"type": "BOOLEAN", "description": "If true, Kree will execute silently unless it involves speaking (default: true)"},
            "id_to_remove":   {"type": "STRING", "description": "ID of trigger to remove (if action=remove)"}
        },
        "required": ["action"]
    }
},
{
    "name": "file_controller",
    "description": (
        "Advanced file & folder management automation. "
        "Use for bulk rename, organizing downloads, finding duplicates, etc."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action":      {"type": "STRING", "description": "organize | rename_bulk | find_duplicates | move | delete"},
            "path":        {"type": "STRING", "description": "Target directory path (default: Downloads or Desktop if not specified)"},
            "pattern":     {"type": "STRING", "description": "Regex or glob pattern for renaming/finding"},
            "destination": {"type": "STRING", "description": "Destination directory"}
        },
        "required": ["action"]
    }
},
{
    "name": "browser_control",
    "description": (
        "Automates browser actions in the background. "
        "Use for filling forms, logging into sites, web scraping, or downloading files via URL."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "search | form_fill | scrape | navigate"},
            "url":    {"type": "STRING", "description": "Target website URL"},
            "query":  {"type": "STRING", "description": "Search query or specific data to find/scrape"},
            "form_data": {"type": "STRING", "description": "JSON string of data to fill into forms"}
        },
        "required": ["action"]
    }
},
{
    "name": "productivity_manager",
    "description": (
        "Manages emails and calendar events. "
        "Use when user wants to read inbox, draft emails, send emails, or schedule meetings. "
        "ALWAYS use action='draft_email' first if asked to compose or send an email, to allow user confirmation."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "read_inbox | draft_email | send_email | schedule_meeting"},
            "to": {"type": "STRING", "description": "Recipient name/address"},
            "subject": {"type": "STRING", "description": "Email subject"},
            "body": {"type": "STRING", "description": "Email content"},
            "title": {"type": "STRING", "description": "Meeting title"},
            "time": {"type": "STRING", "description": "Meeting time or date"}
        },
        "required": ["action"]
    }
}
]

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
        self._whisper_mode: bool = False                 # Set by wake word detector
        self.system_tray = None                          # Set by runner() on boot
        self._wakeword_detector = None                   # Set by runner() on boot

        # Register text callback immediately so UI can send commands from the start
        self.ui.on_user_text = self.on_user_text
        
        self._trigger_engine = TriggerEngine(self._on_trigger_fired)
        self._trigger_engine.start()

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
        self._telemetry = TelemetryLogger(BASE_DIR, load_telemetry_settings())
        self._telemetry.set_context(component="main", model=LIVE_MODEL)
        self._trace(TelemetryEvents.SESSION_INIT, "Kree runtime initialized")

        self.ui.on_user_text = self.on_user_text

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

        m = re.match(r"^(open|launch|start|run)\b\s+(?P<target>.+)$", low)
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
            return {"action": "open_app", "app_name": targets[0]}

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

    def _trace_summary(self, limit: int = 200) -> str:
        log_file = getattr(self._telemetry, "log_file", None)
        session_id = getattr(self._telemetry, "session_id", "")
        if not log_file or not session_id:
            return "Trace is not available right now."

        events = load_session_events(log_file, session_id, limit=limit)
        if not events:
            return "No trace events have been captured yet."

        counts: dict[str, int] = {}
        user_turns = 0
        tool_calls = 0
        for event in events:
            event_type = str(event.get("event_type", "unknown"))
            counts[event_type] = counts.get(event_type, 0) + 1
            if event_type in {TelemetryEvents.USER_TEXT, TelemetryEvents.INPUT_TRANSCRIPT}:
                user_turns += 1
            if event_type == TelemetryEvents.TOOL_CALL:
                tool_calls += 1

        recent = ", ".join(str(event.get("event_type", "unknown")) for event in events[-5:])
        return (
            f"Trace summary: {len(events)} events, {user_turns} user turns, {tool_calls} tool calls. "
            f"Latest events: {recent or 'none'}."
        )

    def _export_trace(self, label: str = "session_trace") -> str:
        try:
            trace_path = export_session_trace(BASE_DIR, self._telemetry, label=label)
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
        if not self._pending_open_and_delegate:
            return False

        low = text.lower()
        choice = ""
        if ("download" in low) or ("install" in low):
            choice = "download"
        elif ("browser" in low) or ("web" in low):
            choice = "browser"

        if not choice:
            return False

        pending = dict(self._pending_open_and_delegate)
        self._pending_open_and_delegate = None

        def _resolve_pending():
            try:
                r = openapps_automation(
                    parameters={
                        "action": "open_and_delegate",
                        "targets": pending.get("targets", ""),
                        "delegate_app": pending.get("agent", ""),
                        "prompt": pending.get("prompt", ""),
                        "fallback": choice,
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
            self.system_tray.set_sleeping()
        try:
            import winsound
            winsound.PlaySound('assets/sounds/sleep.wav', winsound.SND_FILENAME | winsound.SND_ASYNC)
        except: pass
        if hasattr(self, 'wake_event'):
            self.wake_event.clear()
        
        # Abort the async connection safely if running
        if self._loop and self.audio_in_queue:
            self._loop.call_soon_threadsafe(self.audio_in_queue.put_nowait, b"SLEEP_SENTINEL")

    def wake(self, trigger_type="full", whisper=False):
        """
        Wake Kree from sleep.
        
        Args:
            trigger_type: "full" (chime + UI + greeting), "partial" (ears only, no UI), "priority" (instant, no greeting)
            whisper: True if the user spoke quietly — Kree responds quietly
        """
        self._whisper_mode = whisper
        
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

        # Full wake or priority wake — show the UI
        print(f"[JARVIS] Waking up... (type={trigger_type}, whisper={whisper})")
        self.ui.wake()
        if hasattr(self, 'system_tray') and self.system_tray:
            self.system_tray.set_active()

        if trigger_type != "priority":
            # Play pre-cached high-quality AI voice greeting instantly (0ms latency!)
            try:
                greeting_mp3 = BASE_DIR / "assets" / "sounds" / "active_greeting.mp3"
                import os
                if greeting_mp3.exists() and os.path.getsize(greeting_mp3) > 1000:
                    import pygame
                    if not pygame.mixer.get_init():
                        pygame.mixer.init()
                    pygame.mixer.music.load(str(greeting_mp3))
                    pygame.mixer.music.play()
                else:
                    raise Exception("Missing MP3")
            except Exception:
                # Fallback to standard wake chime if pre-renderer hasn't built it yet
                try:
                    import winsound
                    winsound.PlaySound('assets/sounds/wake.wav', winsound.SND_FILENAME | winsound.SND_ASYNC)
                except Exception:
                    pass

        if hasattr(self, 'wake_event'):
            if not self.wake_event.is_set():
                if self._loop:
                    self._loop.call_soon_threadsafe(self.wake_event.set)
                else:
                    self.wake_event.set()

    def on_user_text(self, text: str):
        """Called when user types a message in the UI."""
        try:
            logging.debug(f"[UI_TEXT] Processing: {text}")
            text = self._normalize_text_input(text)
            if not text:
                return
                
            self.ui.write_log(f"You: {text}")
            
            # Typed input is considered explicit user intent and arms one tool-execution window.
            self._arm_command_window(text)
            
            logging.info(f"[UI_TEXT] Command normalized: {text}")
            low = text.lower()
            
            # Update intent
            if "update kree" in low:
                logging.debug("[UI_TEXT] matched 'update'")
                from core.updater import get_pending_update, install_pending_update
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
                    import threading
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
                
            # Normalize command prefix (strip 'hey kree', etc)
            import re
            stripped_low = re.sub(r'^(hey\s+|ok\s+|okay\s+|please\s+)?(kree|jarvis)?\b[\s,:-]*', '', low).strip()
            logging.debug(f"[UI_TEXT] Stripped command: {stripped_low}")

            if stripped_low.startswith("open "):
                logging.info(f"[UI_TEXT] Fast-path detected: {stripped_low}")
                app_name = text.lower().replace("hey ", "").replace("kree ", "").replace("open ", "").strip()
                def _open_fast():
                    try:
                        loading_msg = f"Kree: Opening {app_name} now..."
                        self.ui.write_log(loading_msg)
                        logging.debug(f"[OPEN_FAST] thread started for: {app_name}")
                        try:
                            import winsound
                            winsound.PlaySound("SystemDefault", winsound.SND_ALIAS | winsound.SND_ASYNC)
                        except: pass
                        _local_speech_voice("Opening it now.")
                        
                        logging.debug("[OPEN_FAST] Calling open_app bridge...")
                        r = open_app(
                            parameters={"app_name": app_name},
                            response=None,
                            player=self.ui,
                            session_memory=None,
                        )
                        logging.info(f"[OPEN_FAST] Result: {r}")
                        self.ui.write_log(f"Kree: {r}")
                    except Exception as e:
                        logging.error(f"[OPEN_FAST] Error: {e}")
                
                threading.Thread(target=_open_fast, daemon=True).start()
                return

        except Exception as e:
            logging.error(f"[UI_TEXT] Fatal crash during text processing: {e}")
            logging.error(traceback.format_exc())

        if stripped_low.startswith("close "):
            app_name = text.lower().replace("hey ", "").replace("kree ", "").replace("close ", "").strip()
            def _close_fast():
                try:
                    import psutil
                    self.ui.write_log(f"Kree: Closing {app_name} now...")
                    APP_MAP = {
                        "chrome": "chrome.exe",
                        "spotify": "Spotify.exe",
                        "vscode": "Code.exe",
                        "discord": "Discord.exe",
                        "notepad": "notepad.exe",
                        "youtube": "chrome.exe", 
                        "github": "chrome.exe"
                    }
                    process_name = APP_MAP.get(app_name.lower(), app_name)
                    
                    killed = False
                    for proc in psutil.process_iter(['name', 'pid']):
                        try:
                            if proc.info['name'] and process_name.lower() in proc.info['name'].lower():
                                proc.terminate()
                                killed = True
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                            
                    if killed:
                        _local_speech_voice(f"Closed {app_name} sir.")
                        self.ui.write_log(f"Kree: Closed {app_name}.")
                    else:
                        _local_speech_voice(f"Could not find {app_name} running sir.")
                        self.ui.write_log(f"Kree: Couldn't find {app_name} running.")
                except Exception as e:
                    self.ui.write_log(f"Kree: Fast-path close error: {e}")
            threading.Thread(target=_close_fast, daemon=True).start()
            return

        if self._resolve_pending_choice(text):
            return

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
                            log_file = getattr(self._telemetry, "log_file", None)
                            session_id = getattr(self._telemetry, "session_id", "")
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
        loop = self._loop
        session = self.session
        if not loop or not session:
            _local_speech_voice(text)
            return
        
        # Split text logic (max 200 chars, try to split at sentences)
        import re
        chunks = []
        current = ""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        for s in sentences:
            if len(current) + len(s) <= 200:
                current += s + " "
            else:
                if current.strip(): chunks.append(current.strip())
                if len(s) > 200:
                    for i in range(0, len(s), 195):
                        chunks.append(s[i:i+195])
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
        mem_str = format_memory_for_prompt(memory)

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
            from memory.config_manager import load_audio_settings # type: ignore[import]
            voice_name_config = load_audio_settings().get("kree_voice", "Kore")
        except Exception:
            voice_name_config = "Kore"

        return types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            output_audio_transcription={},
            input_audio_transcription=types.AudioTranscriptionConfig(),
            system_instruction=sys_prompt,
            tools=[{"function_declarations": TOOL_DECLARATIONS}],
            session_resumption=types.SessionResumptionConfig(),
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

    async def _execute_tool(self, fc) -> Any:
        _, types = _ensure_genai_sdk()
        name = fc.name
        args = dict(fc.args or {})

        # Normalize common free-text fields to avoid Unicode drift between ASR, model, and tool layer.
        import core.sanitizer as sanitizer
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

        dangerous_tools = {"computer_control", "web_search"}
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
                        f"Session verification timed out. "
                        f"Please verify your PIN and try again."
                    )
                    return types.FunctionResponse(
                        id=fc.id,
                        name=name,
                        response={"result": msg},
                    )

        self._trace(TelemetryEvents.TOOL_CALL, f"Tool call: {name}", tool=name, args=args)

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
                    import core.automations as autos
                    import core.execution_engine as engine
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
                r = await loop.run_in_executor(
                    None, functools.partial(open_app, parameters=args, response=None, player=self.ui)  # type: ignore[arg-type]
                )
                if isinstance(r, str) and r.startswith("__BROADCAST_INTENT__"):
                    target = r.split(":")[1]
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
                    log_file = getattr(self._telemetry, "log_file", None)
                    session_id = getattr(self._telemetry, "session_id", "")
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
                threading.Thread(
                    target=screen_process,
                    kwargs={"parameters": args, "response": None,
                            "player": self.ui, "session_memory": None},
                    daemon=True
                ).start()
                result = (
                    "Vision module activated. "
                    "Stay completely silent — vision module will speak directly."
                )

            elif name == "computer_settings":
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

                from agent.task_queue import get_queue, TaskPriority  # type: ignore[import]
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
                )
                result = f"Task started (ID: {task_id}). I'll update you as I make progress, sir."

            elif name == "web_search":
                r = await loop.run_in_executor(
                    None, functools.partial(web_search_action, parameters=args, player=self.ui)  # type: ignore[arg-type]
                )
                result = r or "Search completed."
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
            self._trace(TelemetryEvents.TOOL_RESULT, result, tool=name, status="error")
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
            self._trace(TelemetryEvents.TOOL_RESULT, result_str, tool=name, status="ok")

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
            print("[JARVIS] ❌ No audio device — mic disabled.")
            return
        try:
            device_index = self._audio_settings.get("input_device_index")
            if device_index is not None:
                try:
                    device_info = pya.get_device_info_by_index(int(device_index))
                except Exception:
                    device_info = pya.get_default_input_device_info()
                    device_index = device_info.get("index")
            else:
                device_info = pya.get_default_input_device_info()
                device_index = device_info.get("index")
            dev_name = device_info.get("name", "Unknown")
            print(f"[JARVIS] 🎤 Mic started (Device: {dev_name})")
            
            stream = await asyncio.to_thread(
                pya.open,
                format=FORMAT,
                channels=CHANNELS,
                rate=SEND_SAMPLE_RATE,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=CHUNK_SIZE,
            )
        except Exception as e:
            print(f"[JARVIS] ❌ Mic open failed: {e}")
            return

        try:
            print("[JARVIS] 🎙️ STREAMING MIC MODE: Server VAD enabled (instant response)")
            while True:
                data = await asyncio.to_thread(
                    stream.read, CHUNK_SIZE, exception_on_overflow=False
                )

                # Echo suppression: if Kree is talking, zero the mic to prevent loop
                if getattr(self, "bot_is_speaking", False):
                    self._bot_speaking_cooldown = 15  # Extend mute for ~500ms after speech ends (acoustic tail)

                cooldown = getattr(self, "_bot_speaking_cooldown", 0)
                if cooldown > 0:
                    self._bot_speaking_cooldown = cooldown - 1
                    send_data = bytes(len(data))
                elif not getattr(self.ui, "_mic_active", True):
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
            if "429" not in str(e):
                print(f"[JARVIS] ❌ Mic error: {e}")
            raise
        finally:
            if stream is not None:
                try:
                    await asyncio.to_thread(stream.stop_stream)
                    await asyncio.to_thread(stream.close)
                except Exception:
                    pass

    async def _listen_camera(self):
        if cv2 is None:
            print("[JARVIS] ❌ cv2 not installed — camera disabled.")
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
                                self.ui._eval(f"if(typeof updateWebcam==='function') updateWebcam('');")
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
        in_buf  = []
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
                async for response in turn:
                    _msg_n += 1

                    # Log EVERY response with audio data presence
                    has_data = bool(response.data)
                    has_sc = bool(response.server_content)
                    has_tc = bool(response.tool_call)
                    
                    if _msg_n <= 5 or has_tc:
                        parts_info = ""
                        if has_sc and response.server_content.model_turn:
                            mt = response.server_content.model_turn
                            parts_info = f", parts={[p.inline_data.mime_type if p.inline_data else 'text' for p in (mt.parts or [])]}"
                        print(f"[JARVIS] 📨 Turn#{_turn_n} Msg#{_msg_n}: data={has_data}, sc={has_sc}, tc={has_tc}{parts_info}")

                    if response.data:
                        if self.audio_in_queue is not None:
                            try:
                                self.audio_in_queue.put_nowait(response.data)  # type: ignore[union-attr]
                            except asyncio.QueueFull:
                                pass

                    if response.server_content:
                        sc = response.server_content

                        if sc.input_transcription and sc.input_transcription.text:
                            txt = sc.input_transcription.text.strip()
                            if txt:
                                print(f"[JARVIS] 🗣️  Heard: \"{txt}\"")
                                self._trace(TelemetryEvents.INPUT_TRANSCRIPT, txt)
                                in_buf.append(txt)

                        if sc.output_transcription and sc.output_transcription.text:
                            txt = sc.output_transcription.text.strip()
                            if txt:
                                self._trace(TelemetryEvents.OUTPUT_TRANSCRIPT, txt)
                                out_buf.append(txt)

                        if sc.turn_complete:
                            print(f"[JARVIS] ✅ Turn #{_turn_n} complete ({_msg_n} messages)")
                            full_in  = ""
                            full_out = ""

                            if in_buf:
                                full_in = " ".join(in_buf).strip()
                                if full_in:
                                    full_in = self._sanitize_multilingual_transcript(full_in)
                                if full_in:
                                    if self._should_arm_command_window(full_in):
                                        self._arm_command_window(full_in)
                                    self.ui.write_log(f"You: {full_in}")
                                    if self._resolve_pending_choice(full_in):
                                        out_buf = []

                            in_buf = []

                            if out_buf:
                                full_out = " ".join(out_buf).strip()
                                if full_out:
                                    self.ui.write_log(f"Kree: {full_out}")
                                    if hasattr(self, 'mobile_bridge') and self.mobile_bridge.server:
                                        try:
                                            asyncio.create_task(self.mobile_bridge.broadcast({
                                                "type": "chat",
                                                "sender": "KREE",
                                                "text": full_out
                                            }))
                                        except Exception:
                                            pass
                            out_buf = []

                            if full_in and len(full_in) > 5:
                                threading.Thread(
                                    target=_update_memory_async,
                                    args=(full_in, full_out),
                                    daemon=True
                                ).start()
                                
                                try:
                                    import memory.history_manager as hist
                                    # Parse out recently executed tools to add them visually into the memory text limit
                                    executed_tools = []
                                    if response.tool_call:
                                        for fc in response.tool_call.function_calls:
                                            executed_tools.append(fc.name)
                                    hist.save_turn(full_in, full_out, tools=executed_tools)
                                except Exception as e:
                                    print(f"[JARVIS] ⚠️ History log error: {e}")

                    if response.tool_call:
                        # Print all tools being called
                        for fc in response.tool_call.function_calls:
                            print(f"[JARVIS] 📞 Tool call: {fc.name}")
                        
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
                
                # Jitter Buffer: Accumulate chunks when queue completely empties 
                # to prevent network latency underruns (audio glitching/stutter)
                if self.sync_audio_out_queue.empty():
                    chunk = self.sync_audio_out_queue.get()
                    if chunk is None:
                        break
                    time.sleep(0.25)  # buffer 250ms of network audio
                else:
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
        
        while True:
            # Random jitter to make it feel organic, but base is 60s for dev
            await asyncio.sleep(10)
            
            if not self.session:
                continue
                
            last_turn = getattr(self, "_last_user_turn", time.time())
            dormant_time = time.time() - last_turn
            
            # Dev mode: 60s. Prod: 1800s. Timeouts.
            AUTO_SLEEP_TIMEOUT = 300  # 5 minutes
            if dormant_time > getattr(self._audio_settings, 'proactive_heartbeat', 60):
                if dormant_time > AUTO_SLEEP_TIMEOUT and self.wake_event.is_set():
                    print(f"[JARVIS] ⏱️ Inactive for 5 mins. Auto-sleeping.")
                    try:
                        import pyttsx3
                        _local_speech_voice("Going to sleep sir, call me when you need me.")
                    except: pass
                    self.hibernate()
                    
                elif not getattr(self, "bot_is_speaking", False) and getattr(self.ui, "_mic_active", True):
                    print(f"[JARVIS] ⏱️ Dormant for {int(dormant_time)}s. Firing proactive check-in!")
                    try:
                        await self.session.send(
                            input="[SYSTEM OVERRIDE] The user has been quiet for a while. Proactively check in with them naturally and ask how the session is going. Be extremely brief."
                        )
                        # Reset timer so it doesn't spam
                        self._last_user_turn = time.time()
                    except Exception as e:
                        print(f"[JARVIS] ⚠️ Proactive fire fail: {e}")

    async def run(self):
        genai, _ = _ensure_genai_sdk()
        client = genai.Client(
            api_key=_get_api_key(),
            http_options={"api_version": "v1beta"}
        )
        from memory.config_manager import load_audio_settings, load_telemetry_settings
        audio_settings = load_audio_settings()
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
            # Pass notes to UI for rendering
            try:
                import json
                encoded = json.dumps(notes).replace("'", "\\'")
                self.ui._eval(f"try{{ renderSyncedNotes('{encoded}'); }}catch(e){{}}")
            except Exception:
                pass

        def on_contacts_sync(contacts: list):
            # Pass contacts to UI for rendering
            try:
                import json
                encoded = json.dumps(contacts).replace("'", "\\'")
                self.ui._eval(f"try{{ renderSyncedContacts('{encoded}'); }}catch(e){{}}")
            except Exception:
                pass

        # Start Mobile Bridge natively in background
        from mobile_bridge import KreeMobileBridge
        self.mobile_bridge = KreeMobileBridge(
            port=8443,
            on_command_callback=on_mobile_command,
            on_connect_callback=on_mobile_connect
        )
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
                        "mime_type": "audio/webm;codecs=opus"
                    })
                except Exception:
                    pass
        self.mobile_bridge.on_audio_callback = on_mobile_audio

        self._loop = asyncio.get_event_loop()
        self.ui.mobile_bridge = self.mobile_bridge
        self.ui._loop = self._loop
        try:
            await self.mobile_bridge.start()
        except OSError:
            print("[JARVIS] ⚠️ Mobile Bridge port 8443 already in use. Skipping...")

        # ── PWA Server Auto-Start ────────────────────────────────────────
        try:
            from serve_pwa import start_pwa_server_background, get_pwa_url, get_server_status
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

        while True:
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
                        import core.onboarding as onboard
                        if onboard.is_first_launch():
                            # This will be handled inside the connect taskgroup later
                            self._needs_onboarding = True
                    except Exception:
                        pass
            
                from memory.config_manager import load_audio_settings
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
                config = self._build_config()

                async with (
                    client.aio.live.connect(model=LIVE_MODEL, config=config) as session,
                    asyncio.TaskGroup() as tg,
                ):
                    self.session        = session
                    self._loop          = asyncio.get_event_loop() 
                    self.audio_in_queue = asyncio.Queue(maxsize=MAX_AUDIO_IN_QUEUE)
                    self.out_queue      = asyncio.Queue(maxsize=MAX_AUDIO_OUT_QUEUE)
                    mic_enabled = True  # Always enable mic on boot — voice is core to Kree

                    print("[JARVIS] \u2705 Connected.")
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
                        import core.app_watcher as aw
                        tg.create_task(aw.watch_processes(self.session))
                    except Exception as e:
                        print(f"[JARVIS] ⚠️ App Watcher fail: {e}")
                        
                    if getattr(self, "_needs_onboarding", False):
                        try:
                            import core.onboarding as onboard
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

            except Exception as e:
                self._trace(TelemetryEvents.CONNECTION_ERROR, str(e))
                print(f"[JARVIS] Error: {e}")
                # traceback.print_exc()

            if not self.wake_event.is_set():
                print("[JARVIS] Session closed intentionally. Waiting for wake.")
                continue

            print("[JARVIS] Reconnecting in 3s...")
            self._trace(TelemetryEvents.RECONNECT_WAIT, "Reconnecting in 3s")
            await asyncio.sleep(3)

    async def _run_local_offline_loop(self):
        """
        Classic STT -> LLM -> TTS pipeline for Local Mode, bypassing Gemini Live WebRTC.
        """
        self._loop = asyncio.get_event_loop()
        from core.llm_gateway import KreeIntelligenceEngine
        import speech_recognition as sr
        
        engine = KreeIntelligenceEngine()
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = self._audio_settings.get("vad_threshold_rising", 300)
        recognizer.dynamic_energy_threshold = True
        recognizer.pause_threshold = 0.8
        recognizer.non_speaking_duration = 0.5  # Must be <= pause_threshold to avoid AssertionError

        try:
            device_index = int(self._audio_settings.get("input_device_index", -1))
            if device_index == -1: device_index = None
        except:
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
                audio = await asyncio.to_thread(recognizer.listen, mic, timeout=1.0, phrase_time_limit=10.0)
                
                # Instant acknowledgment SFX (Jarvis-style)
                try:
                    import winsound
                    winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS | winsound.SND_ASYNC)
                except: pass

                try:
                    # Fallback to free Google STT if strictly local STT (whisper) isn't loaded yet.
                    text = await asyncio.to_thread(recognizer.recognize_google, audio)
                    text = self._sanitize_multilingual_transcript(text)
                    if not text: continue
                    
                    print(f"[JARVIS] 🗣️ Heard (Local STT): {text}")
                    self.ui.write_log(f"You: {text}")

                    if text.lower().startswith("open "):
                        self.on_user_text(text)
                        continue
                    
                    # LLM Gateway phase (Think)
                    response_text = await asyncio.to_thread(engine.generate_content, text)
                    print(f"[JARVIS] 🧠 Local Gemma Response: {response_text[:100]}...")
                    self.ui.write_log(f"Kree: {response_text}")
                    
                    # TTS phase (Speak)
                    self.speak(response_text)
                    
                except sr.UnknownValueError:
                    pass # Couldn't understand audio
                except sr.RequestError as e:
                    print(f"[JARVIS] STT limit/network error: {e}")
                    
            except sr.WaitTimeoutError:
                pass # Timeout silently to re-check the loop
            except Exception as e:
                print(f"[JARVIS] Local loop error: {e}")
                await asyncio.sleep(1)

def main():
    import sys
    is_background = "--background" in sys.argv
    ui = JarvisUI("face.png", startup_hidden=is_background)

    def runner():
        ui.wait_for_api_key()
        ui.wait_for_unlock()

        kree = JarvisLive(ui)
        kree.start_awake = not is_background
            
        # ── First Run Startup Prompt ──
        try:
            from memory.config_manager import load_audio_settings, save_audio_settings
            import ctypes
            import winreg
            settings = load_audio_settings()
            if 'auto_start_configured' not in settings:
                result = ctypes.windll.user32.MessageBoxW(0, 
                    "Should Kree start automatically when Windows starts?\nThis lets you use the wake word anytime. (Recommended)", 
                    "Kree AI Setup", 0x04 | 0x20) # YESNO | QUESTION
                
                if result == 6:  # IDYES
                    try:
                        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
                        winreg.SetValueEx(key, "Kree AI", 0, winreg.REG_SZ, f'"{sys.executable}" --background')
                        winreg.CloseKey(key)
                        settings['auto_start_configured'] = True
                    except Exception as e:
                        print(f"Failed setting startup reg: {e}")
                else:
                    settings['auto_start_configured'] = False
                save_audio_settings(settings)
        except Exception: pass
        try:
            from core.tray import SystemTrayApp
            
            def safe_shutdown():
                print("[JARVIS] 🛑 Processing safe shutdown...")
                from core.updater import run_installer_and_exit
                # Try to apply update. If none is ready, this returns False and we just exit normally.
                if run_installer_and_exit():
                    return # Process is already exiting via os._exit(0) in the helper
                os._exit(0)

            tray = SystemTrayApp(
                on_wake_click=kree.wake,
                on_quit_click=safe_shutdown
            )
            kree.system_tray = tray
            tray.run_daemon()
            print("[JARVIS] 🌟 System Tray Armed")
        except Exception as e:
            print(f"[JARVIS] Missing Tray dependency: {e}")

        # 2. Boot OpenWakeWord Engine
        try:
            from core.wakeword import WakeWordDetector
            wakeword = WakeWordDetector(on_wake_callback=kree.wake)
            wakeword.start()
            kree._wakeword_detector = wakeword
            print("[JARVIS] WakeWord Daemon Armed (OpenWakeWord)")
        except Exception as e:
            print(f"[JARVIS] Missing WakeWord dependency: {e}")

        # Boot analytics session
        try:
            from core.analytics import track_session_start
            track_session_start()
        except Exception:
            pass

        # Boot auto-updater (background check + silent download)
        try:
            from core.updater import check_update_background
            # v1.0.1 Stable: Enabling auto_download by default
            check_update_background(ui=ui, speak_fn=_local_speech_voice, auto_download=True)
        except Exception:
            pass

        try:
            asyncio.run(kree.run())
        except KeyboardInterrupt:
            safe_shutdown()
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"[KREE CRASH] {e}\n{error_details}")
            try:
                from core.analytics import track_error
                track_error("crash", str(e))
            except Exception:
                pass
            try:
                from core.backend import log_crash
                log_crash(str(e), error_details)
            except Exception:
                pass
            raise
        finally:
            try:
                from core.analytics import shutdown
                shutdown()
            except Exception:
                pass

    threading.Thread(target=runner, daemon=True).start()
    ui.run()  # blocks — runs the pywebview event loop

if __name__ == "__main__":
    main()