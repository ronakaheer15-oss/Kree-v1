import asyncio
import threading
import json
import re
import sys
import traceback
import functools
from pathlib import Path
from typing import Any, Optional

try:
    import pyaudio  # type: ignore[import]
except ImportError:
    pyaudio = None  # type: ignore[assignment]
    print("[JARVIS] ⚠️ PyAudio not installed — audio will be disabled.")

from google import genai  # type: ignore[import]
from google.genai import types  # type: ignore[import]
import time
import wave
from ui import JarvisUI  # type: ignore[import]
from memory.memory_manager import load_memory, update_memory, format_memory_for_prompt  # type: ignore[import]

from agent.task_queue import get_queue  # type: ignore[import]

from actions.flight_finder import flight_finder  # type: ignore[import]
from actions.open_app         import open_app  # type: ignore[import]
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

def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent

BASE_DIR        = get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"
PROMPT_PATH     = BASE_DIR / "core" / "prompt.txt"
LIVE_MODEL          = "models/gemini-2.5-flash-native-audio-preview-12-2025"
FORMAT              = pyaudio.paInt16 if pyaudio else 8  # paInt16 = 8
CHANNELS            = 1
SEND_SAMPLE_RATE    = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE          = 1024

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

def _get_api_key() -> str:
    import core.vault as vault # type: ignore[import]
    return vault.load_api_key(API_CONFIG_PATH)

def _load_system_prompt() -> str:
    try:
        return PROMPT_PATH.read_text(encoding="utf-8")
    except Exception:
        return (
            "You are Kree, an advanced AI assistant. "
            "Be concise, direct, and always use the provided tools to complete tasks. "
            "Never simulate or guess results — always call the appropriate tool."
        )

_memory_turn_counter  = 0
_memory_turn_lock     = threading.Lock()
_MEMORY_EVERY_N_TURNS = 5
_last_memory_input    = ""


def _update_memory_async(user_text: str, jarvis_text: str) -> None:
    """
    Multilingual memory updater.
    Model  : gemini-2.5-flash-lite (lowest cost)
    Stage 1: Quick YES/NO check  → ~5 tokens output
    Stage 2: Full extraction     → only if Stage 1 says YES
    Result : ~80% fewer API calls vs original
    """
    global _memory_turn_counter, _last_memory_input

    with _memory_turn_lock:
        _memory_turn_counter += 1  # type: ignore[name-defined]
        current_count = _memory_turn_counter

    if current_count % _MEMORY_EVERY_N_TURNS != 0:
        return

    text = user_text.strip()
    if len(text) < 10:
        return
    if text == _last_memory_input:
        return
    _last_memory_input = text

    try:
        import google.generativeai as genai_sync  # type: ignore[import]
        genai_sync.configure(api_key=_get_api_key())
        model = genai_sync.GenerativeModel("gemini-2.5-flash-lite")

        check = model.generate_content(
            f"Does this message contain personal facts about the user "
            f"(name, age, city, job, hobby, relationship, birthday, preference)? "
            f"Reply only YES or NO.\n\nMessage: {text[:300]}"  # type: ignore[index]
        )
        if "YES" not in check.text.upper():
            return

        raw = model.generate_content(
            f"Extract personal facts from this message. Any language.\n"
            f"Return ONLY valid JSON or {{}} if nothing found.\n"
            f"Extract: name, age, birthday, city, job, hobbies, preferences, relationships, language.\n"
            f"Skip: weather, reminders, search results, commands.\n\n"
            f"Format:\n"
            f'{{"identity":{{"name":{{"value":"..."}}}}}}, '
            f'"preferences":{{"hobby":{{"value":"..."}}}}, '
            f'"notes":{{"job":{{"value":"..."}}}}}}\n\n'
            f"Message: {text[:500]}\n\nJSON:"  # type: ignore[index]
        ).text.strip()

        raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
        if not raw or raw == "{}":
            return

        data = json.loads(raw)
        if data:
            update_memory(data)
            print(f"[Memory] ✅ Updated: {list(data.keys())}")

    except json.JSONDecodeError:
        pass
    except Exception as e:
        if "429" not in str(e):
            print(f"[Memory] ⚠️ {e}")


TOOL_DECLARATIONS = [
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
}
]

class JarvisLive:

    def __init__(self, ui: JarvisUI):
        self.ui: JarvisUI                          = ui
        self.session: Any                          = None
        self.audio_in_queue: Optional[asyncio.Queue[Any]] = None
        self.out_queue: Optional[asyncio.Queue[Any]]      = None
        self._loop: Optional[asyncio.AbstractEventLoop]   = None
        self._welcomed: bool                               = False
        self.sync_audio_out_queue: Any                     = None
        self.bot_is_speaking: bool                         = False

        self.ui.on_user_text = self._on_user_text

    def _on_user_text(self, text: str):
        """Called when user types a message in the UI."""
        print(f"[JARVIS] 💬 Received text command from UI: {text}")
        self.speak(text)

    def speak(self, text: str):
        """Thread-safe speak — any thread can call this."""
        loop = self._loop
        session = self.session
        if not loop or not session:
            return
        assert loop is not None
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        try:
            coro = session.send_client_content(
                turns={"parts": [{"text": text}]},
                turn_complete=True
            )
            if current_loop is loop:
                loop.create_task(coro)
            else:
                asyncio.run_coroutine_threadsafe(coro, loop)
        except Exception as e:
            print(f"[JARVIS] ⚠️ speak() failed: {e}")
    
    def _build_config(self) -> types.LiveConnectConfig:
        from datetime import datetime 

        memory  = load_memory()
        mem_str = format_memory_for_prompt(memory)

        # Prioritize Language Constraints at the very top of the logic
        sys_prompt = (
            "<BILINGUAL_PROTOCOL>\n"
            "USER_LANGUAGES: [Indian English (en-IN), Hindi (hi-IN)]\n"
            "USER_ACCENT: Expect the user to have an Indian subcontinent accent. They may pronounce 'v' as 'w' or use retroflex 't' and flat vowels.\n"
            "YOUR_VOICE: Use a crisp, professional American accent for all your spoken responses.\n"
            "WAKE_WORD: Your name is 'Kree'. The user MUST begin their command with 'Hey Kree', 'Ok Kree', or 'Kree'. If they do not say your name, IGNORE the speech entirely.\n"
            "STRICT_MODE: ON\n"
            "INSTRUCTIONS:\n"
            "1. You are a bilingual assistant for Indian users. Understand Indian-accented English and Hindi flawlessly.\n"
            "2. If you hear Malayalam, Arabic, Sinhala, Thai, or random static, IGNORE IT completely.\n"
            "3. Reply in Hindi if the user spoke Hindi. Reply in English if the user spoke English.\n"
            "4. Be confident — just respond to commands, do not explain your language limitations.\n"
            "</BILINGUAL_PROTOCOL>\n\n"
        )
        sys_prompt += _load_system_prompt()

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

        return types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            output_audio_transcription={},
            input_audio_transcription=types.AudioTranscriptionConfig(),
            system_instruction=sys_prompt,
            tools=[{"function_declarations": TOOL_DECLARATIONS}],
            session_resumption=types.SessionResumptionConfig(),
            realtime_input_config=types.RealtimeInputConfig(
                automatic_activity_detection=types.AutomaticActivityDetection(
                    disabled=True  # Client variance-gate has full control
                )
            ),
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Kore"  # 'Kore' is a standard American female voice
                    )
                ),
            ),
        )

    async def _execute_tool(self, fc) -> types.FunctionResponse:
        name = fc.name
        args = dict(fc.args or {})

        print(f"[JARVIS] 🔧 TOOL: {name}  ARGS: {args}")

        loop   = asyncio.get_event_loop()
        result = "Done."

        try:
            if name == "open_app":
                r = await loop.run_in_executor(
                    None, functools.partial(open_app, parameters=args, response=None, player=self.ui)  # type: ignore[arg-type]
                )
                result = r or f"Opened {args.get('app_name')} successfully."

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
            traceback.print_exc()

        print(f"[JARVIS] 📤 {name} → {str(result)[:80]}")  # type: ignore[index]

        return types.FunctionResponse(
            id=fc.id,
            name=name,
            response={"result": result}
        )

    async def _send_realtime(self):
        """Sends mic audio chunks from out_queue to Gemini."""
        _chunk_n: int = 0
        while True:
            if self.out_queue is None:
                await asyncio.sleep(0.1)
                continue
            msg = await self.out_queue.get()  # type: ignore[union-attr]
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
            device_info = pya.get_default_input_device_info()
            dev_name = device_info.get("name", "Unknown")
            print(f"[JARVIS] 🎤 Mic started (Device: {dev_name})")
            
            stream = await asyncio.to_thread(
                pya.open,
                format=FORMAT,
                channels=CHANNELS,
                rate=SEND_SAMPLE_RATE,
                input=True,
                frames_per_buffer=CHUNK_SIZE,
            )
        except Exception as e:
            print(f"[JARVIS] ❌ Mic open failed: {e}")
            return

        import collections
        try:
            _empty_chunks = 0
            _rms_history = []
            _gate_timer: int = 0
            
            # VAD Properties
            _pre_roll = collections.deque(maxlen=10)  # 640ms pre-roll buffer (keeps it fast)
            _rms_window = collections.deque(maxlen=3)  # Smoothing window
            _rms_history = collections.deque(maxlen=50) # Volume bar history
            _dynamic_thresh: float = 500.0  # Adapts via variance-gated EMA
            _prev_sample: int = 0
            _dc_offset: float = 0.0 # Mathematically centers the audio waveform
            _alpha: float = 0.85  # DSP Pre-Emphasis Speech Clarity Coefficient
            _trigger_count: int = 0 # Prevents single clicks from opening gate
            _ui_speaking_state: bool = False # Prevents JS spam
            _ambient_variance: float = 50.0  # Auto-calibrating room noise floor
            _agc_gain = 1.0 
            
            while True:
                data = await asyncio.to_thread(
                    stream.read, CHUNK_SIZE, exception_on_overflow=False
                )
                
                # IMPORTANT: Preserve the original raw audio for Gemini transmission.
                # Gemini's native audio model was trained on natural mic input.
                # We only use DSP-filtered audio for our VAD gate decisions.
                raw_data = data  # This is what Gemini will receive
                
                import math
                import array
                rms = 0
                try:
                    samples = array.array('h', data)
                    
                    # DSP Analysis Pipeline (for VAD decisions ONLY, not sent to Gemini)
                    # We calculate RMS on filtered audio to get accurate gate triggers,
                    # but Gemini receives the raw, unprocessed microphone signal.
                    for i in range(len(samples)): # type: ignore[arg-type]
                        current = int(samples[i])
                        
                        # DC-Offset Removal (for clean RMS calculation)
                        _dc_offset = 0.999 * _dc_offset + 0.001 * current # type: ignore[operator]
                        centered = current - int(_dc_offset)
                        
                        # Pre-Emphasis (for clean variance calculation)
                        filtered = centered - int(_alpha * _prev_sample) # type: ignore[operator]
                        _prev_sample = centered
                        
                        if filtered > 32767: filtered = 32767
                        elif filtered < -32768: filtered = -32768
                        samples[i] = filtered
                    
                    # NOTE: We do NOT overwrite `data` with filtered samples.
                    # `data` stays as the raw mic input for Gemini.
                    # `samples` is only used below for RMS/variance gate logic.

                    # Recalculate physical RMS on the DSP-cleaned signal (for gate only)
                    s_list = list(samples)
                    s_len = len(s_list)
                    rms = math.sqrt(sum(s*s for s in s_list) / s_len) if s_len > 0 else 0
                    
                    _rms_history.append(rms)  # type: ignore[arg-type]
                    _rms_window.append(rms)   # type: ignore[arg-type]
                except Exception:
                    pass

                # 5. Advanced Vocal Variance & Signal Logging
                # We calculate the deviation in sound. Static fans have very low variance,
                # while human speech has high dynamic range (high variance).
                s_list_var = list(_rms_window)
                rms_count = len(s_list_var) # type: ignore[arg-type]
                smoothed_rms = sum(s_list_var) / float(rms_count) if rms_count > 0 else 0 # type: ignore[arg-type]
                variance = 0.0
                if rms_count > 1:
                    avg = smoothed_rms
                    variance = math.sqrt(sum((x - avg)**2 for x in s_list_var) / float(rms_count)) # type: ignore[arg-type]

                # Log adaptive threshold info
                s_list_hist = list(_rms_history)
                hist_count = len(s_list_hist) # type: ignore[arg-type]
                if hist_count >= 23:
                    peak = max(_rms_history)
                    if peak > 150:
                        bars = [" ", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
                        bar = bars[min(7, int(peak / 2000 * 7))]
                        print(f"   [MIC VOL] {bar} (Peak: {int(peak)} | Thresh: {int(_dynamic_thresh)} | Var: {int(variance)})")
                    _rms_history.clear()
                
                # ── Variance-based Speech Gate ──────────────────────────────────────
                # Key insight from logs: Fan noise variance = 0-74, Speech variance = 300-1200+
                # We gate on VARIANCE, not energy, since fan energy overlaps with speech energy.
                
                send_data = raw_data
                
                if not getattr(self.ui, "_mic_active", True):
                    send_data = b'\x00' * len(raw_data) # type: ignore[arg-type]
                    _gate_timer = 0
                elif getattr(self, "bot_is_speaking", False):
                    # ── Breakthrough Interruption ───────────────────────────────────
                    # If the user shouts (variance > 15x ambient noise floor), break through the mute lock.
                    if variance > max(400.0, _ambient_variance * 15.0):
                        pass # Allow send_data to remain raw_data
                    else:
                        send_data = b'\x00' * len(raw_data) # type: ignore[arg-type] # Normal Echo Cancel
                        _gate_timer = 0
                else:
                    # ── Adaptive Variance VAD ──────────────────────────────────────
                    # Update ambient baseline ONLY when variance is low/steady (fan/room noise)
                    if variance < 150:
                        _ambient_variance = 0.99 * _ambient_variance + 0.01 * variance
                        _ambient_variance = max(10.0, min(500.0, _ambient_variance))
                    
                    # Gate triggers at 3x the room's noise floor (so it scales to any mic)
                    trigger_threshold = max(150.0, _ambient_variance * 3.0)
                    is_speech = variance >= trigger_threshold
                    
                    if is_speech:
                        _trigger_count = int(_trigger_count) + 1  # type: ignore
                        
                        # Zero-Latency Burst Trigger: If voice is extremely loud/clear, bypass the 2-chunk wait and open mic instantly
                        if variance > max(300.0, _ambient_variance * 6.0):
                            _trigger_count = 2
                            
                        if _trigger_count >= 2:  # type: ignore
                            q = self.out_queue
                            if _gate_timer == 0 and q is not None:
                                # Gate just opened!
                                try:
                                    q.put_nowait({"type": "activity_start"})
                                    
                                    # EMOTION INJECTION: Map volume variance to user's tone
                                    if variance < 400: # Whisper
                                        q.put_nowait({"type": "emotion", "text": "System Note: The user is speaking softly or whispering. Keep your reply extremely soft, brief, and concise."})
                                    elif variance > 4000: # Shouting
                                        q.put_nowait({"type": "emotion", "text": "System Note: The user is speaking loudly and urgently. Respond urgently."})
                                    
                                except asyncio.QueueFull:
                                    pass
                                
                                # Flush pre-roll so sentence start isn't clipped
                                while _pre_roll:
                                    try:
                                        q.put_nowait({"data": _pre_roll.popleft(), "mime_type": f"audio/pcm;rate={SEND_SAMPLE_RATE}"})  # type: ignore[union-attr]
                                    except asyncio.QueueFull:
                                        pass
                            _gate_timer = 8  # 512ms hold for blazingly fast turn-taking (true Jarvis speed)
                    else:
                        _trigger_count = 0
                    
                    if _gate_timer > 0:
                        _gate_timer -= 1 # type: ignore[operator]
                        # Gate just closed
                        q2 = self.out_queue
                        if _gate_timer == 0 and q2 is not None:
                            try:
                                q2.put_nowait({"type": "activity_end"})
                            except asyncio.QueueFull:
                                pass
                        
                        # ── STUDIO PROCESSOR: Auto Gain Control (AGC) & DRC ───────────
                        # Boost quiet voices, compress shouting so Gemini hears perfect studio audio
                        target_rms = 1500.0
                        current_rms = float(smoothed_rms) if smoothed_rms > 10 else 10.0
                        gain = target_rms / current_rms
                        
                        # Dynamic Range Compression limits
                        if gain > 4.0: gain = 4.0  # Max boost for whispers
                        if gain < 0.5: gain = 0.5  # Max reduction for shouts
                        
                        # Apply gain instantly to the audio samples
                        if abs(gain - 1.0) > 0.1:
                            for i in range(len(samples)): # type: ignore[arg-type]
                                val = int(samples[i] * gain)
                                if val > 32767: val = 32767
                                elif val < -32768: val = -32768
                                samples[i] = val
                        
                        # Send the fully cleaned, mixed Studio Audio to Gemini
                        send_data = samples.tobytes()
                    else:
                        # Gate SHUT — store raw audio in pre-roll, mute output feed
                        _pre_roll.append(raw_data) # type: ignore[attr-defined]
                        send_data = b'\x00' * len(raw_data) # type: ignore[arg-type]

                # Orb Pulsing — glow when gate is open
                _is_talking = bool(_gate_timer > 0)
                if _is_talking != _ui_speaking_state:
                    _ui_speaking_state = _is_talking
                    try:
                        self.ui.window.evaluate_js(f"setSpeaking({'true' if _is_talking else 'false'})")
                    except Exception:
                        pass

                # Send to Gemini
                if self.out_queue is not None:
                    try:
                        self.out_queue.put_nowait({"data": send_data, "mime_type": f"audio/pcm;rate={SEND_SAMPLE_RATE}"})  # type: ignore[union-attr]
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
        try:
            import cv2  # type: ignore[import]
        except ImportError:
            print("[JARVIS] ❌ cv2 not installed — camera disabled.")
            return

        cap = None
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

                if cap is None:
                    print("[JARVIS] 📷 Camera starting hardware capture...")
                    cap = await asyncio.to_thread(cv2.VideoCapture, 0, cv2.CAP_DSHOW)  # type: ignore
                    if not cap or not cap.isOpened():  # type: ignore
                        await asyncio.sleep(1)
                        continue

                success, frame = await asyncio.to_thread(cap.read)  # type: ignore
                if not success:
                    await asyncio.sleep(0.5)
                    continue

                # Resize to reduce bandwidth
                frame_resized = await asyncio.to_thread(cv2.resize, frame, (640, 480))
                encoded, buffer = await asyncio.to_thread(cv2.imencode, ".jpg", frame_resized)
                
                if encoded and self.session is not None:
                    try:
                        import google.genai.types as types # type: ignore[import]
                        blob = types.Blob(data=buffer.tobytes(), mime_type="image/jpeg")
                        await self.session.send_realtime_input(media=blob)
                    except Exception as e:
                        if "429" not in str(e):
                            print(f"[JARVIS] ⚠️ Camera send error: {e}")
                
                # Push to UI natively
                if self.ui._main_win:
                    import base64
                    try:
                        b64_str = base64.b64encode(buffer.tobytes()).decode('utf-8')
                        self.ui._eval(f"if(typeof updateWebcam==='function') updateWebcam('data:image/jpeg;base64,{b64_str}');")
                    except Exception:
                        pass
                
                await asyncio.sleep(1.0)  # 1 FPS for Gemini Live Vision
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
                                in_buf.append(txt)  # type: ignore[attr-defined]
                                # Show live in UI so user can see what Gemini heard
                                try:
                                    safe = txt.replace("'", "\\'").replace("\n", " ")
                                    self.ui.window.evaluate_js(f"appendTranscript('user', '{safe}')")
                                except Exception:
                                    pass

                        if sc.output_transcription and sc.output_transcription.text:
                            txt = sc.output_transcription.text.strip()
                            if txt:
                                out_buf.append(txt)  # type: ignore[attr-defined]

                        if sc.turn_complete:
                            print(f"[JARVIS] ✅ Turn #{_turn_n} complete ({_msg_n} messages)")
                            full_in  = ""
                            full_out = ""

                            if in_buf:
                                full_in = " ".join(in_buf).strip()
                                if full_in:
                                    self.ui.write_log(f"You: {full_in}")

                            in_buf = []

                            if out_buf:
                                full_out = " ".join(out_buf).strip()
                                if full_out:
                                    self.ui.write_log(f"Kree: {full_out}")
                            out_buf = []

                            if full_in and len(full_in) > 5:
                                threading.Thread(
                                    target=_update_memory_async,
                                    args=(full_in, full_out),
                                    daemon=True
                                ).start()

                    if response.tool_call:
                        fn_responses = []
                        for fc in response.tool_call.function_calls:
                            print(f"[JARVIS] 📞 Tool call: {fc.name}")
                            fr = await self._execute_tool(fc)
                            fn_responses.append(fr)
                        if self.session is not None:
                            await self.session.send_tool_response(
                                function_responses=fn_responses
                            )
                
                if _msg_n == 0:
                    # Connection might be dead or closed, prevent infinite CPU loop
                    await asyncio.sleep(1.0)

        except Exception as e:
            if "429" not in str(e):
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
                try:
                    stream.write(chunk)
                except Exception as e:
                    if "429" not in str(e) and "Overflow" not in str(e) and "Underflow" not in str(e):
                        pass
                
                if self.sync_audio_out_queue.empty():
                    self.bot_is_speaking = False
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
            self.sync_audio_out_queue = queue.Queue(maxsize=300)
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

    async def run(self):
        client = genai.Client(
            api_key=_get_api_key(),
            http_options={"api_version": "v1beta"}
        )

        self._welcomed = False # Initialize welcome guard

        while True:
            try:
                print("[JARVIS] 🔌 Connecting...")
                config = self._build_config()

                async with (
                    client.aio.live.connect(model=LIVE_MODEL, config=config) as session,
                    asyncio.TaskGroup() as tg,
                ):
                    self.session        = session
                    self._loop          = asyncio.get_event_loop() 
                    self.audio_in_queue = asyncio.Queue(maxsize=200)
                    self.out_queue      = asyncio.Queue(maxsize=100)

                    print("[JARVIS] \u2705 Connected.")
                    self.ui.write_log("Kree online.")
                    
                    if not self._welcomed:
                        self._welcomed = True
                        self.speak("System online. Welcome back, master.")

                    tg.create_task(self._send_realtime())
                    tg.create_task(self._listen_audio())
                    tg.create_task(self._listen_camera())
                    tg.create_task(self._receive_audio())
                    tg.create_task(self._play_audio())

            except Exception as e:
                print(f"[JARVIS] ⚠️  Error: {e}")
                traceback.print_exc()

            print("[JARVIS] 🔄 Reconnecting in 3s...")
            await asyncio.sleep(3)

def main():
    ui = JarvisUI("face.png")

    def runner():
        ui.wait_for_api_key()

        kree = JarvisLive(ui)
        try:
            asyncio.run(kree.run())
        except KeyboardInterrupt:
            print("\n🔴 Shutting down...")

    # Aegis Security ensures authentication through the UI Lock Screen directly.
    # We no longer block the main thread with OS-level dialogs during boot.

    threading.Thread(target=runner, daemon=True).start()
    ui.run()  # blocks — runs the pywebview event loop

if __name__ == "__main__":
    main()