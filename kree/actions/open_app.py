# actions/open_app.py
# MARK XXV — Cross-Platform App Launcher

import time
import re
import subprocess
import platform
import shutil
import webbrowser
from pathlib import Path

try:
    import psutil # type: ignore[import]
    _PSUTIL = True
except ImportError:
    _PSUTIL = False

def _get_user_desktop() -> Path:
    import os
    if platform.system() == "Windows":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders") as key:
                value, _ = winreg.QueryValueEx(key, "Desktop")
                expanded = os.path.expandvars(str(value))
                return Path(expanded)
        except Exception:
            pass
        onedrive_desktop = Path.home() / "OneDrive" / "Desktop"
        if onedrive_desktop.exists():
            return onedrive_desktop
    return Path.home() / "Desktop"

_APP_ALIASES = {
    "chatgpt":            {"Windows": "ChatGPT.exe",            "Darwin": "ChatGPT",             "Linux": "chatgpt"},
    "codex":              {"Windows": "ChatGPT.exe",            "Darwin": "ChatGPT",             "Linux": "chatgpt"},
    "github":             {"Windows": "GitHubDesktop.exe",      "Darwin": "GitHub Desktop",      "Linux": "github-desktop"},
    "github desktop":     {"Windows": "GitHubDesktop.exe",      "Darwin": "GitHub Desktop",      "Linux": "github-desktop"},
    "whatsapp":           {"Windows": "WhatsApp",               "Darwin": "WhatsApp",            "Linux": "whatsapp"},
    "crome":              {"Windows": "chrome",                 "Darwin": "Google Chrome",       "Linux": "google-chrome"},
    "chorme":             {"Windows": "chrome",                 "Darwin": "Google Chrome",       "Linux": "google-chrome"},
    "vs code":            {"Windows": "code",                   "Darwin": "Visual Studio Code",  "Linux": "code"},
    "notepad++":          {"Windows": "notepad++",              "Darwin": "TextEdit",            "Linux": "gedit"},
    "vscode":             {"Windows": "code",                   "Darwin": "Visual Studio Code",  "Linux": "code"},
    "spotify":            {"Windows": "Spotify",                "Darwin": "Spotify",             "Linux": "spotify"},
    "visual studio code": {"Windows": "code",                   "Darwin": "Visual Studio Code",  "Linux": "code"},
    "discord":            {"Windows": "Discord",                "Darwin": "Discord",             "Linux": "discord"},
    "telegram":           {"Windows": "Telegram",               "Darwin": "Telegram",            "Linux": "telegram"},
    "instagram":          {"Windows": "Instagram",              "Darwin": "Instagram",           "Linux": "instagram"},
    "tiktok":             {"Windows": "TikTok",                 "Darwin": "TikTok",              "Linux": "tiktok"},
    "notepad":            {"Windows": "notepad.exe",            "Darwin": "TextEdit",            "Linux": "gedit"},
    "calculator":         {"Windows": "calc.exe",               "Darwin": "Calculator",          "Linux": "gnome-calculator"},
    "terminal":           {"Windows": "cmd.exe",                "Darwin": "Terminal",            "Linux": "gnome-terminal"},
    "cmd":                {"Windows": "cmd.exe",                "Darwin": "Terminal",            "Linux": "bash"},
    "explorer":           {"Windows": "explorer.exe",           "Darwin": "Finder",              "Linux": "nautilus"},
    "file explorer":      {"Windows": "explorer.exe",           "Darwin": "Finder",              "Linux": "nautilus"},
    "paint":              {"Windows": "mspaint.exe",            "Darwin": "Preview",             "Linux": "gimp"},
    "word":               {"Windows": "winword",                "Darwin": "Microsoft Word",      "Linux": "libreoffice --writer"},
    "excel":              {"Windows": "excel",                  "Darwin": "Microsoft Excel",     "Linux": "libreoffice --calc"},
    "powerpoint":         {"Windows": "powerpnt",               "Darwin": "Microsoft PowerPoint","Linux": "libreoffice --impress"},
    "vlc":                {"Windows": "vlc",                    "Darwin": "VLC",                 "Linux": "vlc"},
    "zoom":               {"Windows": "Zoom",                   "Darwin": "zoom.us",             "Linux": "zoom"},
    "slack":              {"Windows": "Slack",                  "Darwin": "Slack",               "Linux": "slack"},
    "steam":              {"Windows": "steam",                  "Darwin": "Steam",               "Linux": "steam"},
    "task manager":       {"Windows": "taskmgr.exe",            "Darwin": "Activity Monitor",    "Linux": "gnome-system-monitor"},
    "settings":           {"Windows": "ms-settings:",           "Darwin": "System Preferences",  "Linux": "gnome-control-center"},
    "powershell":         {"Windows": "powershell.exe",         "Darwin": "Terminal",            "Linux": "bash"},
    "edge":               {"Windows": "msedge",                 "Darwin": "Microsoft Edge",      "Linux": "microsoft-edge"},
    "brave":              {"Windows": "brave",                  "Darwin": "Brave Browser",       "Linux": "brave-browser"},
    "obsidian":           {"Windows": "Obsidian",               "Darwin": "Obsidian",            "Linux": "obsidian"},
    "notion":             {"Windows": "Notion",                 "Darwin": "Notion",              "Linux": "notion"},
    "blender":            {"Windows": "blender",                "Darwin": "Blender",             "Linux": "blender"},
    "capcut":             {"Windows": "CapCut",                 "Darwin": "CapCut",              "Linux": "capcut"},
    "postman":            {"Windows": "Postman",                "Darwin": "Postman",             "Linux": "postman"},
    "figma":              {"Windows": "Figma",                  "Darwin": "Figma",               "Linux": "figma"},
}


def _normalize(raw: str) -> str:
    system = platform.system()
    key    = raw.lower().strip()
    if key in _APP_ALIASES:
        return _APP_ALIASES[key].get(system, raw)
    for alias_key, os_map in _APP_ALIASES.items():
        if alias_key in key or key in alias_key:
            return os_map.get(system, raw)
    return raw


def _is_running(app_name: str) -> bool:
    if not _PSUTIL:
        return True
    app_lower = app_name.lower().replace(" ", "").replace(".exe", "")
    try:
        for proc in psutil.process_iter(["name"]):
            try:
                proc_name = proc.info["name"].lower().replace(" ", "").replace(".exe", "")
                if app_lower in proc_name or proc_name in app_lower:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception:
        pass
    return False


_WIN_URI_MAP = {
    "whatsapp": "whatsapp:",
    "settings": "ms-settings:",
    "calculator": "calculator:",
    "store": "ms-windows-store:",
    "mail": "outlookmail:",
    "calendar": "outlookcal:",
    "maps": "bingmaps:",
    "weather": "msnweather:",
    "clock": "ms-clock:",
}

_WEB_FALLBACK_URLS = {
    "codex": "https://chatgpt.com/?model=gpt-5-codex",
    "chatgpt": "https://chatgpt.com",
    "openai": "https://chatgpt.com",
    "github": "https://github.com",
    "github desktop": "https://github.com",
    "youtube": "https://www.youtube.com",
}


def _open_web_fallback(app_name: str) -> bool:
    url = _WEB_FALLBACK_URLS.get(app_name.lower().strip())
    if not url:
        return False
    try:
        webbrowser.open_new_tab(url)
        return True
    except Exception:
        return False

def _find_in_registry(exe_name: str) -> str | None:
    if platform.system() != "Windows":
        return None
    import winreg
    if not exe_name.lower().endswith(".exe"):
        exe_name = f"{exe_name}.exe"
    for hkey in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            with winreg.OpenKey(hkey, f"Software\\Microsoft\\Windows\\CurrentVersion\\App Paths\\{exe_name}") as key:
                val, _ = winreg.QueryValueEx(key, "")
                if val:
                    val = val.strip('"')
                    if Path(val).exists():
                        return val
        except Exception:
            pass
    return None


def _launch_windows(app_name: str) -> bool:
    import os
    app_lower = app_name.lower().strip()
    create_flags = 0
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        create_flags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]

    # Try Windows App Paths Registry first (guarantees Chrome, Outlook, Word, etc. resolve perfectly)
    registry_path = _find_in_registry(app_name)
    if registry_path:
        try:
            subprocess.Popen([registry_path], creationflags=create_flags)
            return True
        except Exception:
            pass

    # Try desktop shortcut search (.lnk, .url, .exe)
    try:
        user_desktop = _get_user_desktop()
        public_desktop = Path(os.environ.get("PUBLIC", "C:\\Users\\Public")) / "Desktop"
        
        shortcut_path = None
        candidates = []
        for dt_path in (user_desktop, public_desktop):
            if dt_path.exists():
                for item in dt_path.iterdir():
                    if item.is_file() and item.suffix.lower() in (".lnk", ".url", ".exe"):
                        candidates.append(item)
                        
        # 1. Match exact stem (name without extension)
        for item in candidates:
            if item.stem.lower().strip() == app_lower:
                shortcut_path = item
                break
                
        # 2. Match partial stem
        if not shortcut_path:
            for item in candidates:
                stem_lower = item.stem.lower()
                if app_lower in stem_lower or stem_lower in app_lower:
                    shortcut_path = item
                    break
                    
        if shortcut_path:
            print(f"[open_app] Launching shortcut found on desktop: {shortcut_path}")
            os.startfile(str(shortcut_path))
            return True
    except Exception as e:
        print(f"[open_app] Shortcut search failed: {e}")

    def _resolve_known_exe(name: str) -> str | None:
        exe = name.strip()
        if not exe.lower().endswith('.exe'):
            return None
        if Path(exe).is_absolute() and Path(exe).exists():
            return exe

        local = os.environ.get('LOCALAPPDATA', '')
        if not local:
            return None
        programs = Path(local) / 'Programs'
        if not programs.exists():
            return None

        fast_candidates = [
            programs / 'ChatGPT' / exe,
            programs / 'GitHub Desktop' / exe,
            programs / 'GitHubDesktop' / exe,
        ]
        for p in fast_candidates:
            if p.exists():
                return str(p)

        return None
    
    # Fast-Path: UWP URIs
    if app_lower in _WIN_URI_MAP:
        try:
            os.startfile(_WIN_URI_MAP[app_lower]) # type: ignore
            return True
        except Exception:
            pass

    # Fast-Path: Known executables that exist in PATH
    try:
        resolved = _resolve_known_exe(app_name)
        if resolved:
            try:
                subprocess.Popen([resolved], creationflags=create_flags) # type: ignore[arg-type]
                return True
            except Exception:
                pass

        # If it has .exe, run it directly. If not, Windows is smart enough to find it via startfile if mapped in App Paths
        target = app_name if app_name.endswith(".exe") else f"{app_name}.exe"

        resolved_target = _resolve_known_exe(target)
        if resolved_target:
            try:
                subprocess.Popen([resolved_target], creationflags=create_flags) # type: ignore[arg-type]
                return True
            except Exception:
                pass

        # If available in PATH, launch directly without shell popups.
        in_path = shutil.which(app_name) or shutil.which(target)
        if in_path:
            try:
                subprocess.Popen([in_path], creationflags=create_flags) # type: ignore[arg-type]
                return True
            except Exception:
                pass

        # Final fallback: let Windows resolve the registered application path.
        for candidate in (app_name, target):
            try:
                os.startfile(candidate)  # type: ignore[attr-defined]
                return True
            except Exception:
                continue
        
        # Avoid unresolved startfile/shell start popups; fail gracefully instead.
        return False
            
    except Exception as e:
        print(f"[open_app] ⚠️ Windows execution failed: {e}")
        
    return False

def _launch_macos(app_name: str) -> bool:
    try:
        result = subprocess.run(["open", "-a", app_name], capture_output=True, timeout=8)
        if result.returncode == 0:
            return True
    except Exception:
        pass

    try:
        result = subprocess.run(["open", "-a", f"{app_name}.app"], capture_output=True, timeout=8)
        if result.returncode == 0:
            return True
    except Exception:
        pass

    try:
        import pyautogui # type: ignore[import]
        pyautogui.hotkey("command", "space")
        time.sleep(0.6)
        pyautogui.write(app_name, interval=0.05)
        time.sleep(0.8)
        pyautogui.press("enter")
        time.sleep(1.5)
        return True
    except Exception as e:
        print(f"[open_app] ⚠️ macOS Spotlight failed: {e}")
        return False



def _launch_linux(app_name: str) -> bool:
    binary = (
        shutil.which(app_name) or
        shutil.which(app_name.lower()) or
        shutil.which(app_name.lower().replace(" ", "-"))
    )
    if binary:
        try:
            subprocess.Popen([binary], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            pass

    try:
        subprocess.run(["xdg-open", app_name], capture_output=True, timeout=5)
        return True
    except Exception:
        pass

    try:
        desktop_name = app_name.lower().replace(" ", "-")
        subprocess.run(["gtk-launch", desktop_name], capture_output=True, timeout=5)
        return True
    except Exception:
        pass

    return False


_OS_LAUNCHERS = {
    "Windows": _launch_windows,
    "Darwin":  _launch_macos,
    "Linux":   _launch_linux,
}


def parse_open_command(text: str):
    """
    Parses commands like 'open chrome', 'open new window of chrome', 'switch to chrome'.
    Returns (app_name, force_new, switch_only)
    """
    text = text.lower().strip()
    
    # Remove wake words/politeness
    text = re.sub(r"^\s*(?:hey\s+|ok\s+|okay\s+|please\s+)?(?:kree|jarvis)\b[\s,:-]*", "", text)
    text = re.sub(
        r"^\s*(?:can you|could you|would you|will you|can u|could u|would u|will u|please|hey|ok|okay)\b[\s,.-]*",
        "",
        text
    )
    text = text.strip(" .,!?:;\"")
    
    # Check for force new window patterns
    m = re.match(r"^(?:open|launch)?\s*(?:a\s+)?new\s+window\s+of\s+(.+)$", text)
    if m:
        return m.group(1).strip(), True, False
        
    m = re.match(r"^(?:open|launch)?\s*(?:another|new|second|a\s+new)\s+(.+?)(?:\s+window)?$", text)
    if m:
        rem = m.group(1).strip()
        if rem and rem != "window":
            return rem, True, False
            
    m = re.match(r"^(?:open|launch|start|run)?\s*(.+?)\s+again$", text)
    if m:
        return m.group(1).strip(), True, False
        
    # Check for switch only patterns
    m = re.match(r"^(?:switch\s+to|focus\s+on|focus|bring\s+(.+?)\s+to\s+front)$", text)
    if m:
        app = m.group(1) if m.group(1) else text.replace("switch to", "").replace("focus on", "").replace("focus", "").strip()
        return app.strip(), False, True
        
    if text.startswith("switch to "):
        return text[10:].strip(), False, True
    if text.startswith("focus on "):
        return text[9:].strip(), False, True
    if text.startswith("focus "):
        return text[6:].strip(), False, True
    if text.endswith(" to front"):
        app = text.replace("bring", "").replace("to front", "").strip()
        return app, False, True

    # Normal open patterns
    m = re.match(r"^(?:open|launch|start|run)\s+(.+)$", text)
    if m:
        return m.group(1).strip(), False, False
        
    return text, False, False

def _get_process_pids(app_name: str, normalized_name: str) -> list[int]:
    if not _PSUTIL:
        return []
    
    targets = set()
    for name in (app_name, normalized_name):
        if name:
            cleaned = name.lower().replace(" ", "").replace(".exe", "")
            targets.add(cleaned)
            if "visualstudio" in cleaned:
                targets.add("code")
            if "vscode" in cleaned:
                targets.add("code")
            if "googlechrome" in cleaned:
                targets.add("chrome")
                
    pids = []
    try:
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                proc_name = proc.info["name"].lower().replace(" ", "").replace(".exe", "")
                if any(t in proc_name or proc_name in t for t in targets if t):
                    pids.append(proc.info["pid"])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception:
        pass
    return pids

def _focus_hwnd(hwnd) -> bool:
    if platform.system() != "Windows":
        return False
    try:
        import ctypes
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        
        # Restore if minimized
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, 9) # SW_RESTORE
        else:
            user32.ShowWindow(hwnd, 5) # SW_SHOW
            
        fore_hwnd = user32.GetForegroundWindow()
        if fore_hwnd and fore_hwnd != hwnd:
            fore_thread_id = user32.GetWindowThreadProcessId(fore_hwnd, None)
            curr_thread_id = kernel32.GetCurrentThreadId()
            target_thread_id = user32.GetWindowThreadProcessId(hwnd, None)
            
            if fore_thread_id and target_thread_id and fore_thread_id != target_thread_id:
                user32.AttachThreadInput(fore_thread_id, target_thread_id, True)
                user32.AttachThreadInput(curr_thread_id, target_thread_id, True)
                
                user32.SetForegroundWindow(hwnd)
                user32.SetFocus(hwnd)
                
                user32.AttachThreadInput(curr_thread_id, target_thread_id, False)
                user32.AttachThreadInput(fore_thread_id, target_thread_id, False)
            else:
                user32.SetForegroundWindow(hwnd)
                user32.SetFocus(hwnd)
        else:
            user32.SetForegroundWindow(hwnd)
            user32.SetFocus(hwnd)
            
        user32.SwitchToThisWindow(hwnd, True)
        return True
    except Exception as e:
        print(f"[open_app] Failed to focus HWND {hwnd}: {e}")
        return False

def _focus_existing_window(pids: list[int], app_name: str, normalized_name: str) -> bool:
    if platform.system() != "Windows":
        return False
    try:
        import ctypes
        user32 = ctypes.windll.user32
        
        hwnd_matches = []
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        
        def enum_windows_callback(hwnd, lParam):
            if user32.IsWindowVisible(hwnd):
                pid = ctypes.c_ulong()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                if pid.value in pids:
                    length = user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        ex_style = user32.GetWindowLongW(hwnd, -20)
                        if not (ex_style & 0x00000080):
                            hwnd_matches.append(hwnd)
            return True
            
        user32.EnumWindows(EnumWindowsProc(enum_windows_callback), 0)
        
        if not hwnd_matches:
            app_lower = app_name.lower().strip()
            norm_lower = normalized_name.lower().strip()
            
            def enum_windows_callback_fallback(hwnd, lParam):
                if user32.IsWindowVisible(hwnd):
                    length = user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buff = ctypes.create_unicode_buffer(length + 1)
                        user32.GetWindowTextW(hwnd, buff, length + 1)
                        title = buff.value.lower()
                        ex_style = user32.GetWindowLongW(hwnd, -20)
                        if not (ex_style & 0x00000080):
                            if app_lower in title or norm_lower in title or (
                                "chrome" in app_lower and "chrome" in title
                            ) or (
                                "code" in app_lower and "visual studio code" in title
                            ):
                                hwnd_matches.append(hwnd)
                return True
                
            user32.EnumWindows(EnumWindowsProc(enum_windows_callback_fallback), 0)
            
        if hwnd_matches:
            target_hwnd = hwnd_matches[0]
            print(f"[open_app] Focusing existing window: HWND={target_hwnd}")
            return _focus_hwnd(target_hwnd)
    except Exception as e:
        print(f"[open_app] Error focusing existing window: {e}")
    return False

def _open_single_app(app_name: str, player=None, force_new: bool = False, switch_only: bool = False) -> str:
    if not app_name:
        return "Please specify which application to open, sir."

    lower_app = app_name.lower()
    mobile_keywords = ["mobile", "phone", "ios", "iphone", "ipad", "android", "my device"]
    is_mobile = any(kw in lower_app for kw in mobile_keywords)
    if is_mobile:
        clean_target = lower_app
        for kw in ["in mobile", "on mobile", "in phone", "on phone", "in ios", "on ios",
                    "in iphone", "on iphone", "in ipad", "on ipad", "in android", "on android",
                    "in my device", "on my device", "my mobile", "my phone",
                    "mobile", "ios", "iphone", "ipad", "android"]:
            clean_target = clean_target.replace(kw, "")
        clean_target = clean_target.strip().strip(".,!?")
        if clean_target:
            return f"__BROADCAST_INTENT__:{clean_target}"

    system   = platform.system()
    launcher = _OS_LAUNCHERS.get(system)

    if launcher is None:
        return f"Unsupported OS: {system}"

    normalized = _normalize(app_name)
    print(f"[open_app] 🚀 Launching/Focusing: {app_name} → {normalized} ({system})")
    
    if system == "Windows" and not force_new:
        pids = _get_process_pids(app_name, normalized)
        if pids:
            if _focus_existing_window(pids, app_name, normalized):
                return f"{app_name} is already open. Bringing it to the front, sir."
        if switch_only:
            return f"Could not switch to {app_name} as it does not appear to be running, sir."

    if switch_only:
        return f"Could not switch to {app_name} as it does not appear to be running, sir."

    # [Dynamic Custom Chrome Profile Bypasser]
    if "chrome" in normalized.lower():
        import kree.core.user_profile as up
        profile_settings = up.get_user_profile()
        
        target_profile = profile_settings.get("browser_profile", "Default")
        
        print(f"[PROFILE] app_name={app_name}")
        lower_app = app_name.lower().replace("chrome", "").replace("account", "").strip()
        if lower_app:
            discovered = up.discover_chrome_profiles()
            print(f"[PROFILE] discovered={discovered}")
            
            alias_map = {
                "work": ["work", "office"],
                "seller": ["seller", "flipkart", "business"],
                "ronak": ["ronak", "personal", "main"],
                "default": ["default"]
            }
            
            for p in discovered:
                p_name = p["name"].lower().strip()
                p_folder = p["folder"].lower().strip()
                
                aliases = [p_name, p_folder]
                for key, key_aliases in alias_map.items():
                    if key in p_name or key in p_folder:
                        aliases.extend(key_aliases)
                
                if lower_app in aliases or any(a in lower_app for a in aliases if len(a) >= 3):
                    target_profile = p["folder"]
                    if target_profile != profile_settings.get("browser_profile"):
                        up.update_user_profile({"browser_profile": target_profile})
                    break
            print(f"[PROFILE] selected={target_profile}")
        
        try:
            import subprocess
            import shutil
            import os
            
            raw_browser = profile_settings.get("browser")
            chrome_exe = None
            if raw_browser and raw_browser != "Chrome execution not found":
                chrome_exe = raw_browser
            else:
                chrome_exe = shutil.which("chrome") or shutil.which("google-chrome")
            
            if not chrome_exe and system == "Windows":
                chrome_exe = _find_in_registry("chrome.exe")
                if not chrome_exe:
                    pf = os.environ.get("ProgramFiles", "C:\\Program Files")
                    pf86 = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")
                    local_app = os.environ.get("LocalAppData", "")
                    candidates = [
                        Path(pf) / "Google" / "Chrome" / "Application" / "chrome.exe",
                        Path(pf86) / "Google" / "Chrome" / "Application" / "chrome.exe",
                    ]
                    if local_app:
                        candidates.append(Path(local_app) / "Google" / "Chrome" / "Application" / "chrome.exe")
                    for c in candidates:
                        if c.exists():
                            chrome_exe = str(c)
                            break

            exe_path = None
            if chrome_exe:
                exe_path = shutil.which(chrome_exe) or (chrome_exe if Path(chrome_exe).exists() else None)

            sys_os = platform.system()
            base_path = ""
            if sys_os == "Windows":
                base_path = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")
            elif sys_os == "Darwin":
                base_path = os.path.expanduser("~/Library/Application Support/Google/Chrome")
            else:
                base_path = os.path.expanduser("~/.config/google-chrome")
            
            profile_dir = Path(base_path) / target_profile
            print(f"[PROFILE] launching={profile_dir}")
            profile_exists = profile_dir.exists()

            if not profile_exists:
                discovered = up.discover_chrome_profiles()
                if discovered:
                    target_profile = discovered[0]["folder"]
                    profile_dir = Path(base_path) / target_profile
                    profile_exists = profile_dir.exists()
                else:
                    target_profile = None
                    profile_exists = True

            print(f"[CHROME] Executable path: {exe_path}")
            print(f"[CHROME] Profile path: {target_profile}")
            
            if not exe_path or not Path(exe_path).exists():
                raise FileNotFoundError(f"Chrome executable not found: {chrome_exe}")

            cmd = [exe_path]
            if target_profile:
                cmd.append(f"--profile-directory={target_profile}")

            if "gmail" in app_name.lower() or "email" in app_name.lower():
                cmd.append("https://gmail.com")
            elif "youtube" in app_name.lower():
                cmd.append("https://youtube.com")
            
            subprocess.Popen(cmd)
            
            p_desc = f"profile {target_profile}" if target_profile else "default settings"
            return f"Opened Chrome securely to {p_desc}, sir."
        except Exception as e:
            print(f"[CHROME] Dynamic Chrome failure: {e}")
            print(f"[open_app] ⚠️ Dynamic Chrome fail, falling back: {e}")

    if player:
        player.write_log(f"[open_app] {app_name}")

    try:
        success = launcher(normalized)

        if success:
            return f"Opened {app_name} successfully, sir."

        if normalized != app_name:
            success = launcher(app_name)
            if success:
                return f"Opened {app_name} successfully, sir."

        if _open_web_fallback(app_name) or _open_web_fallback(normalized):
            return f"Opened {app_name} in your browser, sir."

        import os
        try:
            user_desktop = _get_user_desktop()
            public_desktop = Path(os.environ.get("PUBLIC", "C:\\Users\\Public")) / "Desktop"
            if user_desktop.exists():
                os.startfile(str(user_desktop))
            
            shortcuts = []
            for dt_path in (user_desktop, public_desktop):
                if dt_path.exists():
                    for item in dt_path.iterdir():
                        if item.is_file() and item.suffix.lower() in (".lnk", ".url", ".exe"):
                            if item.stem not in shortcuts:
                                shortcuts.append(item.stem)
            seen_list = ", ".join(shortcuts[:15]) + ("..." if len(shortcuts) > 15 else "")
            return (
                f"I tried to open {app_name}, sir, but couldn't find it installed. "
                f"I have opened your Desktop folder so you can verify. The shortcuts I found there are: {seen_list}."
            )
        except Exception as e:
            print(f"[open_app] Desktop folder open fallback failed: {e}")
            return (
                f"I tried to open {app_name}, sir, but couldn't confirm it launched. "
                f"It may still be loading or might not be installed."
            )

    except Exception as e:
        print(f"[open_app] ❌ {e}")
        return f"Failed to open {app_name}, sir: {e}"

def open_app(
    parameters=None,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    import time
    if isinstance(parameters, str):
        parameters = {"app_name": parameters}
    
    params = parameters or {}
    app_name = params.get("app_name", "").strip()
    force_new = params.get("force_new", False)
    switch_only = params.get("switch_only", False)
    
    print(f"[OPEN_APP] {time.time()} {app_name} (force_new={force_new}, switch_only={switch_only})")

    if not app_name:
        return "Please specify which application to open, sir."

    import re
    # Split on " and ", commas, or semicolons
    raw_apps = re.split(r'\s+and\s+|,|;', app_name)
    apps_to_open = [a.strip() for a in raw_apps if a.strip()]

    results = []
    for target_app in apps_to_open:
        parsed_name, p_force_new, p_switch_only = parse_open_command(target_app)
        
        final_force_new = force_new or p_force_new
        final_switch_only = switch_only or p_switch_only
        
        res = _open_single_app(parsed_name, player=player, force_new=final_force_new, switch_only=final_switch_only)
        if res.startswith("__BROADCAST_INTENT__"):
            return res
        results.append(res)

    if len(results) == 1:
        return results[0]
    
    return "\n".join(results)