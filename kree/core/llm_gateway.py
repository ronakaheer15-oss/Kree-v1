"""
LLM Gateway Router
Acts as the central traffic cop for Kree's intelligence.
Routes prompts either to the Cloud (Gemini) or Local GPU (Ollama/Gemma)
based on the user's active intelligence mode.
"""
import os
import json
import logging
from kree.memory.config_manager import CONFIG_DIR
from kree.core import vault

# Try to import Google's SDK for cloud mode
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None

# We use requests for local Ollama to avoid adding heavy SDK dependencies
try:
    import requests
except ImportError:
    requests = None

logger = logging.getLogger(__name__)

def _open_folder(path):
    import os
    import subprocess
    import platform
    if platform.system() == "Windows":
        os.startfile(str(path))
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])

def _get_wifi_password() -> str:
    import subprocess
    import re
    try:
        # 1. Get active SSID
        out = subprocess.check_output("netsh wlan show interfaces", shell=True, text=True, errors="replace")
        ssid_match = re.search(r"^\s*SSID\s*:\s*(.+)$", out, re.MULTILINE)
        if not ssid_match:
            return "You are not currently connected to any Wi-Fi network, sir."
        ssid = ssid_match.group(1).strip()
        
        # 2. Get password
        prof_out = subprocess.check_output(f'netsh wlan show profile name="{ssid}" key=clear', shell=True, text=True, errors="replace")
        pass_match = re.search(r"^\s*Key Content\s*:\s*(.+)$", prof_out, re.MULTILINE)
        if pass_match:
            password = pass_match.group(1).strip()
            return f"The password for your Wi-Fi network '{ssid}' is: {password}"
        else:
            return f"I found the Wi-Fi network '{ssid}', but no security password was found or permissions were insufficient."
    except Exception as e:
        return f"Could not retrieve Wi-Fi password: {e}"

def _adjust_brightness(action: str, percent: int = None) -> str:
    import subprocess
    if percent is not None:
        target = max(0, min(100, percent))
    else:
        # Get current brightness
        try:
            cmd = "powershell (Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness"
            curr = int(subprocess.check_output(cmd, shell=True, text=True).strip())
        except Exception:
            curr = 50
        if action == "up":
            target = min(100, curr + 20)
        else:
            target = max(0, curr - 20)
    
    try:
        cmd_set = f"powershell (Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, {target})"
        subprocess.run(cmd_set, shell=True, check=True)
        return f"Brightness set to {target}%, sir."
    except Exception as e:
        return f"Could not set brightness: {e}"

def _clean_temp_files() -> str:
    import os
    import shutil
    import tempfile
    temp_dir = tempfile.gettempdir()
    deleted_count = 0
    deleted_bytes = 0
    failed_count = 0
    for name in os.listdir(temp_dir):
        path = os.path.join(temp_dir, name)
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                size = os.path.getsize(path)
                os.remove(path)
                deleted_bytes += size
            deleted_count += 1
        except Exception:
            failed_count += 1
    size_mb = deleted_bytes / (1024 * 1024)
    return f"Cleaned {deleted_count} temporary files ({size_mb:.2f} MB freed). Skipped {failed_count} files currently in use."

class KreeIntelligenceEngine:
    def __init__(self, mode="CLOUD_GEMINI", live_instance=None):
        """
        Available modes:
        - CLOUD_GEMINI
        - LOCAL_NEXUS_E4B (Ollama: gemma2:2b)
        - LOCAL_CORE_26B  (Ollama: gemma2:27b)
        - LOCAL_APEX_31B  (Ollama: command-r or similar 30B+)
        """
        self.mode = mode
        self.ollama_host = os.environ.get("KREE_OLLAMA_HOST", "http://127.0.0.1:11434")
        
        # Load real mode from config if it exists
        config_path = CONFIG_DIR / "audio_settings.json"
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    self.mode = cfg.get("intelligence_mode", self.mode)
                    self.ollama_host = cfg.get("ollama_host", self.ollama_host)
            except Exception:
                pass

        self.client = None
        self._last_api_key = None
        self.live_instance = live_instance

    def _get_client(self):
        active_key = os.environ.get("KREE_ACTIVE_API_KEY", "").strip()
        if not active_key:
            try:
                from kree.core.auth_store import get_active_user, load_user_api_key
                active = get_active_user()
                if active and active.get("user_id"):
                    active_key = (load_user_api_key(active["user_id"]) or "").strip()
            except Exception:
                pass

        if not active_key:
            try:
                active_key = vault.load_api_key(CONFIG_DIR / "api_keys.json").strip()
            except Exception:
                pass

        if not active_key:
            active_key = os.environ.get("GEMINI_API_KEY", "").strip()

        if getattr(self, "_last_api_key", None) == active_key and self.client is not None:
            return self.client

        if active_key and genai:
            self._last_api_key = active_key
            self.client = genai.Client(api_key=active_key)
            return self.client

        return self.client

    def _get_local_model_name(self):
        if "NEXUS" in self.mode:
            return "gemma2:2b"
        elif "CORE" in self.mode:
            return "gemma2:27b"
        elif "APEX" in self.mode:
            # Fallback to an available large model, or just use 27b if standard
            return "gemma2:27b"
        return "gemma2:2b"

    def is_local_mode(self):
        return "LOCAL" in self.mode

    def try_local_route(self, prompt: str) -> str | None:
        """
        Attempts to route the prompt locally.
        Returns the string response if matched and executed, or None if not matched.
        """
        # --- Local Intent Router ---
        import re
        import os
        from pathlib import Path
        p_lower = prompt.lower().strip()
        p_clean = re.sub(r'^(hey\s+|ok\s+|okay\s+|please\s+)?(kree|jarvis)?\b[\s,:-]*', '', p_lower).strip()

        if p_clean in ("volume up", "increase volume", "raise volume", "louder"):
            try:
                from kree.actions.computer_settings import volume_up
                volume_up()
                return "Volume increased, sir."
            except Exception as e:
                return f"Could not adjust volume: {e}"
        elif p_clean in ("volume down", "decrease volume", "lower volume", "quieter"):
            try:
                from kree.actions.computer_settings import volume_down
                volume_down()
                return "Volume decreased, sir."
            except Exception as e:
                return f"Could not adjust volume: {e}"
        elif p_clean in ("mute", "silence", "mute volume"):
            try:
                from kree.actions.computer_settings import volume_mute
                volume_mute()
                return "Audio muted, sir."
            except Exception as e:
                return f"Could not mute: {e}"
        elif p_clean in ("unmute", "enable sound", "unmute volume"):
            try:
                from kree.actions.computer_settings import volume_mute
                volume_mute()
                return "Audio unmuted, sir."
            except Exception as e:
                return f"Could not unmute: {e}"

        # Media Playback Controls
        elif p_clean in ("pause music", "play music", "play pause", "pause", "resume music", "play", "pause song"):
            if os.name == "nt":
                import ctypes
                ctypes.windll.user32.keybd_event(0xB3, 0, 0, 0)
                return "Media toggled, sir."
            return "Media controls are only supported on Windows, sir."
        elif p_clean in ("next track", "next song", "skip song", "skip"):
            if os.name == "nt":
                import ctypes
                ctypes.windll.user32.keybd_event(0xB0, 0, 0, 0)
                return "Playing next track, sir."
            return "Media controls are only supported on Windows, sir."
        elif p_clean in ("previous track", "previous song", "prev song", "previous"):
            if os.name == "nt":
                import ctypes
                ctypes.windll.user32.keybd_event(0xB1, 0, 0, 0)
                return "Playing previous track, sir."
            return "Media controls are only supported on Windows, sir."
        elif p_clean in ("stop music", "stop playback", "stop"):
            if os.name == "nt":
                import ctypes
                ctypes.windll.user32.keybd_event(0xB2, 0, 0, 0)
                return "Media stopped, sir."
            return "Media controls are only supported on Windows, sir."

        # Desktop Lock & Sleep Control
        elif p_clean in ("lock my computer", "lock screen", "lock computer", "lock pc"):
            if os.name == "nt":
                import ctypes
                ctypes.windll.user32.LockWorkStation()
                return "Computer locked, sir."
            return "Locking workstation is only supported on Windows, sir."
        elif p_clean in ("put pc to sleep", "put computer to sleep", "sleep computer", "sleep pc", "pc sleep"):
            if os.name == "nt":
                import subprocess
                subprocess.Popen(["rundll32.exe", "powrprof.dll,SetSuspendState", "0", "1", "0"])
                return "Putting PC to sleep, sir."
            return "Sleep is only supported on Windows, sir."

        # Hardware System Statistics
        elif p_clean in ("what is my cpu usage", "check my cpu usage", "cpu usage", "cpu status"):
            import psutil
            cpu = psutil.cpu_percent(interval=0.1)
            return f"Your current CPU usage is {cpu}%."
        elif p_clean in ("check my ram usage", "ram usage", "ram status", "check memory usage", "memory usage", "memory status"):
            import psutil
            ram = psutil.virtual_memory().percent
            return f"Your current RAM usage is {ram}%."
        elif p_clean in ("battery status", "check battery", "battery percent", "is my battery charging", "battery level"):
            import psutil
            battery = psutil.sensors_battery()
            if not battery:
                return "I couldn't detect a battery. Are you on a desktop PC, sir?"
            plugged = "charging" if battery.power_plugged else "discharging"
            return f"Your battery is at {battery.percent}% and is currently {plugged}."

        # Emptying the Recycle Bin
        elif p_clean in ("empty recycle bin", "clean trash", "empty trash", "clear recycle bin"):
            if os.name == "nt":
                import ctypes
                try:
                    ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 7)
                    return "Recycle bin emptied, sir."
                except Exception as e:
                    return f"Failed to empty recycle bin: {e}"
            return "Emptying trash is only supported on Windows, sir."

        # Opening System Shell Folders
        elif p_clean in ("open downloads folder", "show downloads", "open downloads", "downloads folder"):
            downloads = Path.home() / "Downloads"
            if downloads.exists():
                _open_folder(downloads)
                return "Opening Downloads folder, sir."
            return "Downloads folder not found, sir."
        elif p_clean in ("open documents folder", "show documents", "open documents", "documents folder"):
            documents = Path.home() / "Documents"
            if documents.exists():
                _open_folder(documents)
                return "Opening Documents folder, sir."
            return "Documents folder not found, sir."
        elif p_clean in ("go to desktop", "open desktop", "open desktop folder", "desktop folder"):
            try:
                from kree.actions.desktop import _get_desktop
                desktop_path = _get_desktop()
                _open_folder(desktop_path)
                return "Opening Desktop folder, sir."
            except Exception as e:
                return f"Could not open desktop folder: {e}"

        # Global Screenshot Capture
        elif p_clean in ("take a screenshot", "capture my screen", "take screenshot", "capture screen"):
            try:
                from kree.actions.computer_settings import take_screenshot
                r = take_screenshot()
                if r != "failed":
                    return f"Screenshot captured and saved to: {r}"
                return "Triggered system screenshot tool, sir."
            except Exception as e:
                return f"Could not capture screenshot: {e}"

        # Webview Zoom / Theme Controls
        elif p_clean in ("zoom in", "make screen bigger", "increase zoom"):
            if self.live_instance and self.live_instance.ui:
                ui = self.live_instance.ui
                current_zoom = getattr(ui, "_zoom_level", 1.0)
                new_zoom = min(2.0, current_zoom + 0.1)
                ui._zoom_level = new_zoom
                ui._eval(f"document.body.style.zoom = '{new_zoom}';")
                return f"Zoomed in to {int(new_zoom * 100)}%, sir."
            return "UI instance not registered for zoom control, sir."
        elif p_clean in ("zoom out", "make screen smaller", "decrease zoom"):
            if self.live_instance and self.live_instance.ui:
                ui = self.live_instance.ui
                current_zoom = getattr(ui, "_zoom_level", 1.0)
                new_zoom = max(0.5, current_zoom - 0.1)
                ui._zoom_level = new_zoom
                ui._eval(f"document.body.style.zoom = '{new_zoom}';")
                return f"Zoomed out to {int(new_zoom * 100)}%, sir."
            return "UI instance not registered for zoom control, sir."
        elif p_clean in ("reset zoom", "normal zoom", "actual size"):
            if self.live_instance and self.live_instance.ui:
                ui = self.live_instance.ui
                ui._zoom_level = 1.0
                ui._eval("document.body.style.zoom = '1.0';")
                return "Zoom reset to 100%, sir."
            return "UI instance not registered for zoom control, sir."
        elif p_clean in ("toggle dark mode", "toggle theme", "switch theme", "dark mode", "light mode"):
            if self.live_instance and self.live_instance.ui:
                ui = self.live_instance.ui
                ui._toggle_theme()
                mode_str = "Dark" if ui._dark_mode else "Light"
                return f"Toggled theme to {mode_str} mode, sir."
            return "UI instance not registered for theme control, sir."



        # --- Window & Keyboard Control ---
        if p_clean in ("show desktop", "minimize all windows", "minimize all", "minimize windows"):
            try:
                import pyautogui
                pyautogui.hotkey('win', 'd')
                return "Showing desktop, sir."
            except Exception as e:
                return f"Failed to show desktop: {e}"
        elif p_clean in ("close tab", "close browser tab", "close current tab"):
            try:
                import pyautogui
                pyautogui.hotkey('ctrl', 'w')
                return "Closed active tab, sir."
            except Exception as e:
                return f"Failed to close tab: {e}"
        elif p_clean in ("reopen tab", "restore closed tab", "reopen closed tab"):
            try:
                import pyautogui
                pyautogui.hotkey('ctrl', 'shift', 't')
                return "Reopened last closed tab, sir."
            except Exception as e:
                return f"Failed to reopen tab: {e}"
        elif p_clean in ("alt tab", "switch window", "switch application", "switch apps"):
            try:
                import pyautogui
                pyautogui.hotkey('alt', 'tab')
                return "Switched active application, sir."
            except Exception as e:
                return f"Failed to switch window: {e}"
        elif p_clean in ("maximize window", "fullscreen this app", "maximize current window", "maximize active window"):
            try:
                import pyautogui
                pyautogui.hotkey('win', 'up')
                return "Window maximized, sir."
            except Exception as e:
                return f"Failed to maximize window: {e}"
        elif p_clean in ("snap window left", "dock window left", "snap left"):
            try:
                import pyautogui
                pyautogui.hotkey('win', 'left')
                return "Snapped window left, sir."
            except Exception as e:
                return f"Failed to snap window left: {e}"
        elif p_clean in ("snap window right", "dock window right", "snap right"):
            try:
                import pyautogui
                pyautogui.hotkey('win', 'right')
                return "Snapped window right, sir."
            except Exception as e:
                return f"Failed to snap window right: {e}"

        # --- Windows System Utility Launching ---
        elif p_clean in ("open task manager", "start task manager", "launch task manager"):
            try:
                import subprocess
                subprocess.Popen("taskmgr.exe")
                return "Opening Task Manager, sir."
            except Exception as e:
                return f"Failed to open Task Manager: {e}"
        elif p_clean in ("open device manager", "start device manager", "launch device manager"):
            try:
                import subprocess
                subprocess.Popen("devmgmt.msc", shell=True)
                return "Opening Device Manager, sir."
            except Exception as e:
                return f"Failed to open Device Manager: {e}"
        elif p_clean in ("open settings", "show settings", "open settings app"):
            try:
                import subprocess
                subprocess.Popen("start ms-settings:", shell=True)
                return "Opening settings, sir."
            except Exception as e:
                return f"Failed to open settings: {e}"
        elif p_clean in ("open control panel", "show control panel"):
            try:
                import subprocess
                subprocess.Popen("control.exe")
                return "Opening Control Panel, sir."
            except Exception as e:
                return f"Failed to open Control Panel: {e}"
        elif p_clean in ("take a snip", "screen snip", "crop screenshot", "open snipping tool", "snipping tool"):
            try:
                import pyautogui
                pyautogui.hotkey('win', 'shift', 's')
                return "Triggered Snipping Tool, sir."
            except Exception as e:
                return f"Failed to trigger Snipping Tool: {e}"

        # --- Network & Connectivity Control ---
        elif p_clean in ("turn off wifi", "disable wifi", "turn wifi off"):
            try:
                import subprocess
                subprocess.run('netsh interface set interface name="Wi-Fi" admin=disabled', shell=True, capture_output=True)
                return "Wi-Fi disabled, sir."
            except Exception as e:
                return f"Failed to disable Wi-Fi: {e}"
        elif p_clean in ("turn on wifi", "enable wifi", "turn wifi on"):
            try:
                import subprocess
                subprocess.run('netsh interface set interface name="Wi-Fi" admin=enabled', shell=True, capture_output=True)
                return "Wi-Fi enabled, sir."
            except Exception as e:
                return f"Failed to enable Wi-Fi: {e}"
        elif p_clean in ("what is my wifi password", "show wifi security key", "wifi password"):
            return _get_wifi_password()
        elif p_clean in ("am i online", "test internet speed", "check internet connection", "is internet working", "check ping"):
            try:
                import socket
                socket.setdefaulttimeout(2.0)
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect(("8.8.8.8", 53))
                s.close()
                return "Yes, sir, you are online and the internet connection is active."
            except Exception:
                return "No, sir, you appear to be offline."

        # --- Screen & Brightness Control ---
        elif p_clean in ("increase brightness", "brighter screen", "make screen brighter"):
            return _adjust_brightness("up")
        elif p_clean in ("dim screen", "make screen darker", "decrease brightness"):
            return _adjust_brightness("down")
        # Match set brightness to XX%
        elif re.search(r'\b(?:set\s+)?brightness\s+(?:to\s+)?(\d+)\b', p_clean):
            m = re.search(r'\b(?:set\s+)?brightness\s+(?:to\s+)?(\d+)\b', p_clean)
            val = int(m.group(1))
            return _adjust_brightness("set", val)

        # --- Clipboard Manipulations ---
        elif p_clean in ("clear clipboard", "empty my clipboard", "empty clipboard", "clear my clipboard"):
            try:
                import pyperclip
                pyperclip.copy("")
                return "Clipboard cleared, sir."
            except Exception as e:
                return f"Failed to clear clipboard: {e}"
        elif p_clean in ("what is on my clipboard", "read my clipboard", "read clipboard"):
            try:
                import pyperclip
                text = pyperclip.paste().strip()
                if not text:
                    return "Your clipboard is currently empty, sir."
                return f"Here is what is on your clipboard: {text}"
            except Exception as e:
                return f"Failed to read clipboard: {e}"
        elif p_clean in ("copy current date", "put time on clipboard", "copy time", "copy date"):
            try:
                import pyperclip
                import datetime
                now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                pyperclip.copy(now_str)
                return f"Copied current date and time to clipboard: {now_str}"
            except Exception as e:
                return f"Failed to copy date to clipboard: {e}"

        # --- Disk & Directory Maintenance ---
        elif p_clean in ("clean my disk", "run disk cleanup", "open disk cleanup", "disk cleanup"):
            try:
                import subprocess
                subprocess.Popen("cleanmgr.exe")
                return "Opening Disk Cleanup, sir."
            except Exception as e:
                return f"Failed to launch Disk Cleanup: {e}"
        elif p_clean in ("clean temp files", "clear cache", "delete temporary files", "clean temporary files"):
            return _clean_temp_files()

        # --- Virtual Desktops ---
        elif p_clean in ("new virtual desktop", "create desktop", "add virtual desktop"):
            try:
                import pyautogui
                pyautogui.hotkey('ctrl', 'win', 'd')
                return "Created a new virtual desktop, sir."
            except Exception as e:
                return f"Failed to create virtual desktop: {e}"
        elif p_clean in ("go to next desktop", "switch desktop right", "switch to next desktop"):
            try:
                import pyautogui
                pyautogui.hotkey('ctrl', 'win', 'right')
                return "Switched to next virtual desktop, sir."
            except Exception as e:
                return f"Failed to switch virtual desktop: {e}"
        elif p_clean in ("go to previous desktop", "switch desktop left", "switch to previous desktop"):
            try:
                import pyautogui
                pyautogui.hotkey('ctrl', 'win', 'left')
                return "Switched to previous virtual desktop, sir."
            except Exception as e:
                return f"Failed to switch virtual desktop: {e}"
        elif p_clean in ("close current desktop", "close virtual desktop", "delete virtual desktop"):
            try:
                import pyautogui
                pyautogui.hotkey('ctrl', 'win', 'f4')
                return "Closed current virtual desktop, sir."
            except Exception as e:
                return f"Failed to close virtual desktop: {e}"

        # Generic open/focus app routing
        is_app_intent = False
        for verb in ("open", "launch", "start", "run", "switch to", "focus on", "focus"):
            if p_clean.startswith(verb + " "):
                is_app_intent = True
                break
        if p_clean.startswith("bring ") and p_clean.endswith(" to front"):
            is_app_intent = True

        if is_app_intent:
            try:
                from kree.actions.open_app import open_app
                res = open_app(p_clean)
                if isinstance(res, str) and res.startswith("__BROADCAST_INTENT__"):
                    target = res.split(":", 1)[1]
                    if self.live_instance and hasattr(self.live_instance, 'mobile_bridge') and getattr(self.live_instance, '_loop', None):
                        import asyncio
                        asyncio.run_coroutine_threadsafe(
                            self.live_instance.mobile_bridge.broadcast({"type": "intent", "action": "open_app", "target": target}),
                            self.live_instance._loop
                        )
                    return f"Opening {target} on your mobile device, sir."
                return res
            except Exception as e:
                return f"Could not open/focus app: {e}"

        # Generic close app routing
        for verb in ("close", "exit", "quit", "stop", "kill", "terminate"):
            if p_clean.startswith(verb + " ") or p_clean == verb:
                app_name = p_clean[len(verb)+1:].strip() if p_clean.startswith(verb + " ") else ""
                if app_name.endswith(" app"):
                    app_name = app_name[:-4].strip()
                try:
                    from kree.actions.computer_settings import computer_settings
                    desc = f"close {app_name}" if app_name else "close"
                    if app_name in ("active window", "active app", "foreground window", "foreground app", "this app", "this window"):
                        desc = "close"
                    r = computer_settings({"action": "close_app", "description": desc})
                    return r or f"Closed {app_name or 'app'}, sir."
                except Exception as e:
                    return f"Could not close {app_name or 'app'}: {e}"

        if p_clean in ("time", "what time is it", "tell me the time", "current time"):
            import datetime
            return f"The current time is {datetime.datetime.now().strftime('%I:%M %p')}."
        elif p_clean in ("date", "what is the date", "what is today's date", "today's date", "current date"):
            import datetime
            return f"Today's date is {datetime.datetime.now().strftime('%B %d, %Y')}."

        return None

    def generate_content(self, prompt, system_instruction=None):
        """
        Main text generation interface used across Kree codebase.
        Returns a string response.
        """
        local_res = self.try_local_route(prompt)
        if local_res is not None:
            return local_res

        # --- Fallback to original Gemini/Ollama generation ---
        if self.is_local_mode():
            return self._generate_local(prompt, system_instruction)
        else:
            return self._generate_cloud(prompt, system_instruction)

    def _generate_cloud(self, prompt, system_instruction=None):
        client = self._get_client()
        if not client:
            return "Error: Gemini API key not found or genai SDK missing."
        
        try:
            config = types.GenerateContentConfig(
                temperature=0.7,
                system_instruction=system_instruction
            ) if system_instruction else types.GenerateContentConfig(temperature=0.7)
            
            # Use flash-lite for basic operations
            from kree.core.version import MODEL_FLASH_LITE
            response = client.models.generate_content(
                model=MODEL_FLASH_LITE,
                contents=prompt,
                config=config,
            )
            return response.text
        except Exception as e:
            logger.error(f"[Gateway] Cloud generation failed: {e}")
            return f"Error connecting to Cloud Intelligence: {str(e)}"

    def _generate_local(self, prompt, system_instruction=None):
        if not requests:
            return "Error: Python 'requests' module not installed."

        model_name = self._get_local_model_name()
        
        # Build the conversation for Ollama
        messages = []
        if system_instruction:
            messages.append({
                "role": "system",
                "content": system_instruction
            })
        messages.append({
            "role": "user",
            "content": prompt
        })

        payload = {
            "model": model_name,
            "messages": messages,
            "stream": False
        }

        try:
            url = f"{self.ollama_host}/api/chat"
            res = requests.post(url, json=payload, timeout=60)
            res.raise_for_status()
            data = res.json()
            return data.get("message", {}).get("content", "")
        except requests.exceptions.ConnectionError:
            err_msg = f"[OFFLINE MODE] Ollama is not running on {self.ollama_host}. Please start Ollama and ensure the '{model_name}' model is installed."
            logger.error(err_msg)
            return err_msg
        except requests.exceptions.Timeout:
            err_msg = f"[OFFLINE MODE] Local model '{model_name}' timed out. Your PC might be too slow to run this model in real-time."
            logger.error(err_msg)
            return err_msg
        except Exception as e:
            logger.error(f"[Gateway] Local generation failed: {e}")
            return f"Error interacting with Local Intelligence: {str(e)}"

# Singleton for easy importing
gateway = KreeIntelligenceEngine()
