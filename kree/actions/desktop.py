# actions/desktop.py
# AI-powered desktop & wallpaper management
#
# Flow for unknown tasks:
#   User request → Gemini generates Python/pyautogui code → Safety check → Execute
#
# Built-in: wallpaper change, icon arrangement, desktop cleanup, organize by type

import sys
import json
import shutil
import subprocess
import ctypes
import tempfile
import ast
import time
import pyautogui
from pathlib import Path
from datetime import datetime


from kree.core.runtime import CONFIG_DIR
API_CONFIG_PATH = CONFIG_DIR / "api_keys.json"


def _get_api_key() -> str:
    from kree.core import vault
    return vault.load_api_key(API_CONFIG_PATH)


def _get_desktop() -> Path:
    import os
    import platform
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


BLOCKED_KEYWORDS = [
    "os.remove", "shutil.rmtree", "shutil.rm",
    "subprocess.run", "subprocess.Popen", "subprocess.call",
    "os.system", "exec(", "eval(",
    "import os", "import subprocess",
    "__import__", "open(",
    "sys.exit", "quit()",
]


def _is_safe_code(code: str) -> tuple[bool, str]:
    if code.strip().upper() == "UNSAFE":
        return False, "Model marked task unsafe"
    try:
        ast.parse(code, mode="exec")
    except SyntaxError as exc:
        return False, f"Invalid Python: {exc}"

    code_lower = code.lower()
    
    # Absolute strict block for any exec or eval calls
    if "exec" in code_lower or "eval" in code_lower:
        return False, "Blocked operation: Use of exec/eval is strictly forbidden."

    for keyword in BLOCKED_KEYWORDS:
        if keyword.lower() in code_lower:
            return False, f"Blocked operation: '{keyword}'"
    return True, "OK"


def _ask_gemini_for_desktop_action(task: str) -> str:
    """
    Asks Gemini to generate safe Python/pyautogui code
    to accomplish a desktop-related task.
    """
    import google.generativeai as genai
    from kree.core.version import MODEL_FLASH

    genai.configure(api_key=_get_api_key())
    model = genai.GenerativeModel(MODEL_FLASH)

    desktop = str(_get_desktop())

    prompt = f"""You are a Windows desktop automation expert.
Generate safe Python code using ONLY these allowed modules:
- pyautogui (mouse, keyboard, screenshots)
- time.sleep
- print

Desktop path: {desktop}

Rules:
- Output ONLY the Python code. No explanation, no markdown, no backticks.
- NO file deletion (os.remove, shutil.rmtree, unlink, etc.)
- NO subprocess calls
- NO exec() or eval()
- NO file write operations
- NO imports, loops, function definitions, classes, or attribute access outside pyautogui/time
- If task cannot be done safely, output exactly: UNSAFE

Task: {task}

Python code:"""

    try:
        response = model.generate_content(prompt)
        code = response.text.strip()
        if code.startswith("```"):
            lines = code.split("\n")
            code = "\n".join(lines[1:-1]).strip()
        return code
    except Exception as e:
        return f"ERROR: {e}"


def _execute_generated_code(code: str) -> str:
    """Run a small, allowlisted subset of Gemini-generated desktop automation code."""
    safe, reason = _is_safe_code(code)
    if not safe:
        return f"⛔ Blocked for safety: {reason}"

    output_lines = []

    # Security Sandboxing Confirmation
    try:
        MB_OKCANCEL = 1
        MB_ICONWARNING = 0x30
        MB_TOPMOST = 0x40000
        msg = f"Kree wants to execute the following automation code on your desktop:\n\n{code[:400]}\n\nAllow this action?"
        title = "Kree Security Shield"
        
        # IDOK = 1
        result = ctypes.windll.user32.MessageBoxW(0, msg, title, MB_OKCANCEL | MB_ICONWARNING | MB_TOPMOST)
        if result != 1:
            return "⛔ Execution blocked: User denied permission."
            
        _run_allowed_desktop_code(code, output_lines)
        return "\n".join(output_lines) if output_lines else "Task completed successfully."
    except Exception as e:
        return f"Execution error: {e}\n\nCode attempted:\n{code[:200]}"


_ALLOWED_PYAUTOGUI_CALLS = {
    "click", "doubleClick", "rightClick", "moveTo", "dragTo", "scroll",
    "press", "hotkey", "write", "typewrite", "screenshot", "size",
}


def _literal_value(node: ast.AST, variables: dict[str, object]) -> object:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.List):
        return [_literal_value(item, variables) for item in node.elts]
    if isinstance(node, ast.Tuple):
        return tuple(_literal_value(item, variables) for item in node.elts)
    if isinstance(node, ast.Dict):
        return {
            _literal_value(key, variables): _literal_value(value, variables)
            for key, value in zip(node.keys, node.values)
            if key is not None
        }
    if isinstance(node, ast.Name) and node.id in variables:
        return variables[node.id]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _literal_value(node.operand, variables)
        if not isinstance(value, (int, float)):
            raise ValueError("Unary operators are only allowed for numbers.")
        return value if isinstance(node.op, ast.UAdd) else -value
    raise ValueError(f"Unsupported expression: {type(node).__name__}")


def _resolve_allowed_call(node: ast.Call, output_lines: list[str]):
    func = node.func
    if isinstance(func, ast.Name) and func.id == "print":
        return lambda *args, **kwargs: output_lines.append(" ".join(str(arg) for arg in args))

    if not isinstance(func, ast.Attribute) or not isinstance(func.value, ast.Name):
        raise ValueError("Only allowlisted direct calls are permitted.")

    root = func.value.id
    name = func.attr
    if name.startswith("_"):
        raise ValueError("Private attributes are not allowed.")
    if root == "pyautogui" and name in _ALLOWED_PYAUTOGUI_CALLS:
        return getattr(pyautogui, name)
    if root == "time" and name == "sleep":
        return time.sleep

    raise ValueError(f"Call not allowed: {root}.{name}")


def _call_allowed(node: ast.Call, variables: dict[str, object], output_lines: list[str]) -> object:
    func = _resolve_allowed_call(node, output_lines)
    args = [_literal_value(arg, variables) for arg in node.args]
    kwargs = {
        kw.arg: _literal_value(kw.value, variables)
        for kw in node.keywords
        if kw.arg is not None
    }
    return func(*args, **kwargs)


def _run_allowed_desktop_code(code: str, output_lines: list[str]) -> None:
    tree = ast.parse(code, mode="exec")
    variables: dict[str, object] = {}

    for stmt in tree.body:
        if isinstance(stmt, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.ClassDef, ast.For, ast.While, ast.Try, ast.With)):
            raise ValueError(f"Statement not allowed: {type(stmt).__name__}")
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            _call_allowed(stmt.value, variables, output_lines)
            continue
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
            value = _call_allowed(stmt.value, variables, output_lines) if isinstance(stmt.value, ast.Call) else _literal_value(stmt.value, variables)
            variables[stmt.targets[0].id] = value
            continue
        raise ValueError(f"Statement not allowed: {type(stmt).__name__}")


def set_wallpaper(image_path: str) -> str:
    """Sets desktop wallpaper from a local image path."""
    path = Path(image_path).expanduser().resolve()
    if not path.exists():
        return f"Image not found: {image_path}"
    if path.suffix.lower() not in [".jpg", ".jpeg", ".png", ".bmp"]:
        return f"Unsupported format: {path.suffix}. Use jpg, png or bmp."

    try:
        if sys.platform == "win32":

            abs_path = str(path.resolve())
            ctypes.windll.user32.SystemParametersInfoW(20, 0, abs_path, 3)
            return f"Wallpaper set: {path.name}"

        elif sys.platform == "darwin":
            script = f'tell application "Finder" to set desktop picture to POSIX file "{path}"'
            subprocess.run(["osascript", "-e", script])
            return f"Wallpaper set: {path.name}"

        else:
            subprocess.run(["gsettings", "set", "org.gnome.desktop.background",
                          "picture-uri", f"file://{path}"])
            return f"Wallpaper set: {path.name}"

    except Exception as e:
        return f"Could not set wallpaper: {e}"


def set_wallpaper_from_web(url: str) -> str:
    """Downloads an image from URL and sets it as wallpaper."""
    try:
        import urllib.request
        suffix = Path(url.split("?")[0]).suffix or ".jpg"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            tmp = Path(tmp_file.name)
        urllib.request.urlretrieve(url, str(tmp))
        result = set_wallpaper(str(tmp))
        return result
    except Exception as e:
        return f"Could not download wallpaper: {e}"


def get_current_wallpaper() -> str:
    """Returns the current wallpaper path."""
    try:
        if sys.platform == "win32":
            import winreg
            key  = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                  r"Control Panel\Desktop")
            val, _ = winreg.QueryValueEx(key, "Wallpaper")
            return f"Current wallpaper: {val}"
        else:
            return "Wallpaper path retrieval not supported on this OS."
    except Exception as e:
        return f"Could not get wallpaper: {e}"


FILE_TYPE_MAP = {
    "Images":    [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico", ".heic"],
    "Documents": [".pdf", ".doc", ".docx", ".txt", ".xls", ".xlsx", ".ppt", ".pptx", ".csv", ".odt"],
    "Videos":    [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v"],
    "Music":     [".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"],
    "Archives":  [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"],
    "Code":      [".py", ".js", ".html", ".css", ".json", ".xml", ".ts", ".cpp", ".java", ".cs", ".php"],
    "Executables": [".exe", ".msi", ".bat", ".cmd", ".sh"],
}


def organize_desktop(mode: str = "by_type") -> str:
    """
    Organizes desktop files and directories, scanning both personal and public directories.
    mode: 'by_type' — groups by file type (Images, Documents, Apps, Folders, etc.)
          'by_date'  — groups by month (2024-01, 2024-02, etc.)
    """
    import sys
    import os
    desktop = _get_desktop()
    print(f"[Desktop] Organizing items at: {desktop}")
    moved   = []
    skipped = []

    # Protected system directories and organization folders
    protected = {
        "apps", "folders", "images", "documents", "music", "archives", "code", "executables", "others", "others/"
    }

    # Gather directories to organize
    targets = [desktop]
    if sys.platform == "win32":
        public_desktop = Path(os.environ.get("PUBLIC", "C:\\Users\\Public")) / "Desktop"
        if public_desktop.exists() and public_desktop != desktop:
            targets.append(public_desktop)

    for target_dir in targets:
        for item in target_dir.iterdir():
            name_lower = item.name.lower()
            if name_lower.startswith(".") or name_lower == "desktop.ini" or name_lower in protected or name_lower.startswith("desktop archive"):
                continue

            folder_name = None

            if item.is_dir():
                # It's a directory: move it to the "Folders" folder
                folder_name = "Folders"
            else:
                ext = item.suffix.lower()
                # If it's a shortcut or executable, move to "Apps" folder
                if ext in (".lnk", ".url", ".exe", ".msi", ".bat", ".cmd", ".sh"):
                    folder_name = "Apps"
                elif mode == "by_date":
                    mtime = datetime.fromtimestamp(item.stat().st_mtime)
                    folder_name = mtime.strftime("%Y-%m")
                else:
                    folder_name = "Others"
                    for folder, exts in FILE_TYPE_MAP.items():
                        if ext in exts:
                            folder_name = folder
                            break

            if not folder_name:
                continue

            # We always move the items to the USER's personal desktop folders to ensure they don't mix/pollute public spaces
            dest_dir = desktop / folder_name
            dest_dir.mkdir(exist_ok=True)
            new_path = dest_dir / item.name

            if new_path.exists():
                skipped.append(item.name)
                continue

            try:
                # Try moving
                shutil.move(str(item), str(new_path))
                moved.append(f"{item.name} → {folder_name}/")
            except PermissionError:
                # If we can't move from Public desktop due to permission, try copying it and then deleting it.
                # If deletion fails, we delete the copied file to avoid duplicates, and skip.
                try:
                    if item.is_dir():
                        shutil.copytree(str(item), str(new_path))
                        try:
                            shutil.rmtree(str(item))
                            moved.append(f"{item.name} → {folder_name}/")
                        except Exception:
                            shutil.rmtree(str(new_path)) # clean up copy
                            skipped.append(f"{item.name} (Permission Denied)")
                    else:
                        shutil.copy2(str(item), str(new_path))
                        try:
                            os.remove(str(item))
                            moved.append(f"{item.name} → {folder_name}/")
                        except Exception:
                            os.remove(str(new_path)) # clean up copy
                            skipped.append(f"{item.name} (Permission Denied)")
                except Exception as e:
                    skipped.append(f"{item.name} ({e})")
            except Exception as e:
                skipped.append(f"{item.name} ({e})")

    result = f"Desktop organized ({mode}). {len(moved)} items moved."
    if moved:
        preview = moved[:8]
        result += "\n" + "\n".join(preview)
        if len(moved) > 8:
            result += f"\n... and {len(moved)-8} more."
    if skipped:
        result += f"\nSkipped {len(skipped)} items (already exist or in use)."
    
    print(f"[Desktop] Organize result: {result}")
    return result


def list_desktop() -> str:
    """Lists everything on the desktop, scanning both personal and public directories."""
    import os
    import sys
    import platform
    desktop = _get_desktop()
    print(f"[Desktop] Detecting desktop items at: {desktop}")
    
    # Open the desktop folder in Explorer
    try:
        if platform.system() == "Windows":
            os.startfile(str(desktop))
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", str(desktop)])
        else:
            subprocess.Popen(["xdg-open", str(desktop)])
    except Exception as e:
        print(f"[Desktop] Could not open folder: {e}")

    items = []
    seen = set()

    def scan_dir(d_path):
        if not d_path.exists():
            return
        for item in d_path.iterdir():
            name_lower = item.name.lower()
            if name_lower.startswith(".") or name_lower == "desktop.ini":
                continue
            if name_lower in seen:
                continue
            seen.add(name_lower)
            if item.is_dir():
                try:
                    count = len(list(item.iterdir()))
                except Exception:
                    count = 0
                items.append(f"📁 {item.name}/ ({count} items)")
            else:
                try:
                    size = item.stat().st_size
                    size_str = f"{size/1024:.1f} KB" if size < 1024*1024 else f"{size/1024/1024:.1f} MB"
                    items.append(f"📄 {item.name} ({size_str})")
                except Exception:
                    items.append(f"📄 {item.name}")

    scan_dir(desktop)
    
    # Scan public desktop on Windows
    if sys.platform == "win32":
        public_desktop = Path(os.environ.get("PUBLIC", "C:\\Users\\Public")) / "Desktop"
        if public_desktop.exists() and public_desktop != desktop:
            scan_dir(public_desktop)

    items.sort()
    print(f"[Desktop] Detected {len(items)} items: {items}")
    if not items:
        return "Desktop is empty."
    return f"Desktop ({len(items)} items):\n" + "\n".join(items)


def clean_desktop() -> str:
    """
    Moves all files on desktop into a 'Desktop Archive' folder
    with today's date — fast cleanup without deleting anything.
    """
    desktop     = _get_desktop()
    today       = datetime.now().strftime("%Y-%m-%d")
    archive_dir = desktop / f"Desktop Archive {today}"
    archive_dir.mkdir(exist_ok=True)

    moved = 0
    for item in desktop.iterdir():
        if item.is_dir() or item.name.startswith("."):
            continue
        if item.suffix.lower() == ".lnk":
            continue
        new_path = archive_dir / item.name
        if not new_path.exists():
            shutil.move(str(item), str(new_path))
            moved += 1

    return f"Desktop cleaned. {moved} files moved to '{archive_dir.name}'."


def get_desktop_stats() -> str:
    """Returns stats about the desktop."""
    desktop     = _get_desktop()
    files       = [i for i in desktop.iterdir() if i.is_file()]
    folders     = [i for i in desktop.iterdir() if i.is_dir()]
    total_size  = sum(f.stat().st_size for f in files)
    size_str    = f"{total_size/1024:.1f} KB" if total_size < 1024*1024 else f"{total_size/1024/1024:.1f} MB"

    return (
        f"Desktop stats:\n"
        f"  Files   : {len(files)}\n"
        f"  Folders : {len(folders)}\n"
        f"  Total size: {size_str}"
    )


def desktop_control(
    parameters: dict,
    response=None,
    player=None,
    session_memory=None
) -> str:
    """
    Called from main.py.

    parameters:
        action      : wallpaper | wallpaper_url | current_wallpaper |
                      organize | clean | list | stats |
                      task (AI-powered — anything else)

        path        : image path for 'wallpaper'
        url         : image URL for 'wallpaper_url'
        mode        : 'by_type' or 'by_date' for 'organize'
        task        : Natural language description for AI-powered actions.
                      Example: "arrange icons by size"
                               "show me what's on my desktop"
                               "move all screenshots to a folder"
    """
    action = (parameters or {}).get("action", "").lower().strip()
    task   = (parameters or {}).get("task", "").strip()

    result = "Unknown action."

    try:
        if action == "wallpaper":
            path   = parameters.get("path", "")
            result = set_wallpaper(path) if path else "No image path provided."

        elif action == "wallpaper_url":
            url    = parameters.get("url", "")
            result = set_wallpaper_from_web(url) if url else "No URL provided."

        elif action == "current_wallpaper":
            result = get_current_wallpaper()

        elif action == "organize":
            mode   = parameters.get("mode", "by_type")
            result = organize_desktop(mode)

        elif action == "clean":
            result = clean_desktop()

        elif action == "list":
            result = list_desktop()

        elif action == "stats":
            result = get_desktop_stats()

        elif action == "task" or task:
            actual_task = task or parameters.get("description", "")
            if not actual_task:
                return "Please describe what you want to do on the desktop, sir."

            print(f"[Desktop] 🤖 Asking Gemini: {actual_task}")
            if player:
                player.write_log("[Desktop] Generating action...")

            code = _ask_gemini_for_desktop_action(actual_task)

            if code == "UNSAFE":
                result = "I cannot perform that desktop action safely, sir."
            elif code.startswith("ERROR:"):
                result = f"Could not generate action: {code}"
            else:
                print(f"[Desktop] ✅ Generated code:\n{code[:200]}")
                result = _execute_generated_code(code)

        else:
            full_task = task or action
            if full_task:
                code   = _ask_gemini_for_desktop_action(full_task)
                result = _execute_generated_code(code) if code not in ("UNSAFE",) else "Cannot do that safely."
            else:
                result = "No action or task specified."

    except Exception as e:
        result = f"Desktop control error: {e}"

    print(f"[Desktop] {result[:100]}")
    if player:
        player.write_log(f"[desktop] {result[:60]}")

    return result
