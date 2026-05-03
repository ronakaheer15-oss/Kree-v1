# actions/open_app.py
# MARK XXV — Cross-Platform App Launcher

import time
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
    "vscode":             {"Windows": "code",                   "Darwin": "Visual Studio Code",  "Linux": "code"},
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

def _launch_windows(app_name: str) -> bool:
    import os
    app_lower = app_name.lower().strip()
    create_flags = 0
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        create_flags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]

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


def _open_single_app(app_name: str, player=None) -> str:
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
    print(f"[open_app] 🚀 Launching: {app_name} → {normalized} ({system})")
    
    # [Dynamic Custom Chrome Profile Bypasser]
    if "chrome" in normalized:
        import kree.core.user_profile as up
        profile = up.get_user_profile()
        target_profile = profile.get("browser_profile", "Default")
        
        try:
            import subprocess
            import shutil
            chrome_exe = profile.get("browser") or shutil.which("chrome") or shutil.which("google-chrome")
            if chrome_exe:
                # If they asked for a specific site (e.g. "gmail in chrome")
                if "gmail" in app_name.lower() or "email" in app_name.lower():
                    subprocess.Popen([chrome_exe, f"--profile-directory={target_profile}", "https://gmail.com"])
                elif "youtube" in app_name.lower():
                    subprocess.Popen([chrome_exe, f"--profile-directory={target_profile}", "https://youtube.com"])
                else:
                    subprocess.Popen([chrome_exe, f"--profile-directory={target_profile}"])
                
                return f"Opened Chrome securely to {target_profile}, sir."
        except Exception as e:
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
    app_name = (parameters or {}).get("app_name", "").strip()

    if not app_name:
        return "Please specify which application to open, sir."

    import re
    # Split on " and ", commas, or semicolons
    raw_apps = re.split(r'\s+and\s+|,|;', app_name)
    apps_to_open = [a.strip() for a in raw_apps if a.strip()]

    results = []
    # If the user's intent to open multiple apps was embedded in one command ("open Chrome and VS code"), 
    # we un-nest it here to ensure both apps actually launch properly in sequence.
    for target_app in apps_to_open:
        res = _open_single_app(target_app, player=player)
        # Mobile intents override the entire flow
        if res.startswith("__BROADCAST_INTENT__"):
            return res
        results.append(res)

    if len(results) == 1:
        return results[0]
    
    return "\n".join(results)