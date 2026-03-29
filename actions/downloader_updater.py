"""Generic downloader/updater action for Kree.

Supports:
- download files by URL
- check available app updates
- update one app or all apps (Windows via winget)
- install app (Windows via winget)
"""

from __future__ import annotations

import difflib
import platform
import re
import shutil
import subprocess
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


FUZZY_MATCH_CUTOFF = 0.85
SUGGEST_MATCH_CUTOFF = 0.65


def _run_cmd(cmd: list[str], timeout: int = 300) -> tuple[int, str]:
    try:
        cp = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        out = (cp.stdout or "") + ("\n" + cp.stderr if cp.stderr else "")
        return cp.returncode, out.strip()
    except subprocess.TimeoutExpired:
        return 124, "Command timed out."
    except Exception as e:
        return 1, f"Command failed: {e}"


_APP_CATALOG: dict[str, dict[str, str]] = {
    "github": {
        "winget_id": "GitHub.GitHubDesktop",
        "download_url": "https://desktop.github.com/download/",
    },
    "vscode": {
        "winget_id": "Microsoft.VisualStudioCode",
        "download_url": "https://code.visualstudio.com/Download",
    },
    "chrome": {
        "winget_id": "Google.Chrome",
        "download_url": "https://www.google.com/chrome/",
    },
    "firefox": {
        "winget_id": "Mozilla.Firefox",
        "download_url": "https://www.mozilla.org/firefox/new/",
    },
    "python": {
        "winget_id": "Python.Python.3.12",
        "download_url": "https://www.python.org/downloads/",
    },
    "nodejs": {
        "winget_id": "OpenJS.NodeJS.LTS",
        "download_url": "https://nodejs.org/en/download",
    },
    "chatgpt": {
        "winget_id": "OpenAI.ChatGPT",
        "download_url": "https://openai.com/chatgpt/download/",
    },
    "discord": {
        "winget_id": "Discord.Discord",
        "download_url": "https://discord.com/download",
    },
    "telegram": {
        "winget_id": "Telegram.TelegramDesktop",
        "download_url": "https://desktop.telegram.org/",
    },
}

_ALIASES = {
    "git hub": "github",
    "githup": "github",
    "gitub": "github",
    "vs code": "vscode",
    "visual studio code": "vscode",
    "code": "vscode",
    "node": "nodejs",
    "node js": "nodejs",
}

_STOPWORDS = {
    "please",
    "can",
    "you",
    "for",
    "me",
    "the",
    "a",
    "an",
    "app",
    "application",
    "software",
    "now",
}


def _normalize_target(target: str) -> str:
    t = unicodedata.normalize("NFC", str(target or "")).strip().casefold()
    if not t:
        return t

    # Normalize combining marks so accented/garbled ASR variants map to stable catalog keys.
    t = "".join(ch for ch in unicodedata.normalize("NFKD", t) if not unicodedata.combining(ch)).strip()

    if t in _ALIASES:
        return _ALIASES[t]
    if t in _APP_CATALOG:
        return t

    close = difflib.get_close_matches(
        t,
        list(_APP_CATALOG.keys()) + list(_ALIASES.keys()),
        n=1,
        cutoff=FUZZY_MATCH_CUTOFF,
    )
    if close:
        c = close[0]
        return _ALIASES.get(c, c)
    return t


def _catalog_entry(target: str) -> dict[str, str] | None:
    key = _normalize_target(target)
    return _APP_CATALOG.get(key)


def _suggest_catalog(target: str, limit: int = 4) -> list[str]:
    t = _normalize_target(target)
    base = list(_APP_CATALOG.keys())
    return difflib.get_close_matches(t, base, n=limit, cutoff=SUGGEST_MATCH_CUTOFF)


def _extract_target_from_text(text: str) -> str:
    t = unicodedata.normalize("NFC", str(text or "")).strip().casefold()
    if not t:
        return ""

    t = re.sub(r"\b(hey\s+)?(kree|jarvis)\b", "", t)
    t = re.sub(r"\s+", " ", t).strip()

    # Drop common command prefixes while preserving actual app name.
    t = re.sub(
        r"^(please\s+)?(can\s+you\s+)?(kindly\s+)?"
        r"(download|install|update|upgrade|open|get)\s+",
        "",
        t,
    )

    # Keep Unicode letters intact; avoid ASCII-only splitting that corrupts ASR output.
    words = [w for w in re.split(r"[^\w.+-]+", t, flags=re.UNICODE) if w]
    words = [w for w in words if w not in _STOPWORDS]
    return " ".join(words).strip()


def _ensure_winget() -> tuple[bool, str]:
    if platform.system() != "Windows":
        return False, "App update/install is currently implemented for Windows only."
    winget = shutil.which("winget")
    if not winget:
        return False, "winget was not found on this system."
    return True, winget


def _download_file(url: str, destination: str | None) -> str:
    if not url:
        return "Please provide a valid URL."

    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return "Only http/https URLs are supported for download."

    file_name = Path(parsed.path).name or "download.bin"
    if destination:
        dest_path = Path(destination)
        if dest_path.is_dir() or destination.endswith(("\\", "/")):
            dest_path = dest_path / file_name
    else:
        dest_path = Path.home() / "Downloads" / file_name

    dest_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        urllib.request.urlretrieve(url, str(dest_path))
        return f"Downloaded successfully to: {dest_path}"
    except Exception as e:
        return f"Download failed: {e}"


def _check_updates() -> str:
    ok, winget_or_msg = _ensure_winget()
    if not ok:
        return winget_or_msg

    rc, out = _run_cmd([winget_or_msg, "upgrade", "--accept-source-agreements"], timeout=120)
    if rc == 0:
        preview = out[-2000:] if len(out) > 2000 else out
        return "Available updates:\n" + preview
    return f"Could not check updates.\n{out[-800:]}"


def _search_apps(query: str, limit: int = 8) -> str:
    q = _extract_target_from_text(query) or query.strip()
    if not q:
        return "Please provide an app name to search."

    ok, winget_or_msg = _ensure_winget()
    if not ok:
        suggestions = _suggest_catalog(q)
        if suggestions:
            return "winget not available. Known apps: " + ", ".join(suggestions)
        return winget_or_msg

    rc, out = _run_cmd(
        [winget_or_msg, "search", q, "--accept-source-agreements"],
        timeout=120,
    )
    if rc == 0 and out:
        preview = out[-2400:] if len(out) > 2400 else out
        return f"Search results for '{q}':\n{preview}"

    suggestions = _suggest_catalog(q)
    if suggestions:
        return "No strong winget result. Did you mean: " + ", ".join(suggestions)
    return f"Could not search apps for '{q}'."


def _status_app(target: str) -> str:
    q = _extract_target_from_text(target) or target.strip()
    if not q:
        return "Please provide an app name to check status."

    ok, winget_or_msg = _ensure_winget()
    if not ok:
        return winget_or_msg

    entry = _catalog_entry(q)
    candidates = [q]
    if entry and entry.get("winget_id"):
        candidates.insert(0, entry["winget_id"])

    for cand in candidates:
        rc, out = _run_cmd([winget_or_msg, "list", "--id", cand], timeout=120)
        if rc == 0 and out and ("No installed package found" not in out):
            preview = out[-1500:] if len(out) > 1500 else out
            return f"Installed status for '{cand}':\n{preview}"

    # fallback by name
    rc2, out2 = _run_cmd([winget_or_msg, "list", q], timeout=120)
    if rc2 == 0 and out2 and ("No installed package found" not in out2):
        preview = out2[-1500:] if len(out2) > 1500 else out2
        return f"Installed status for '{q}':\n{preview}"

    suggestions = _suggest_catalog(q)
    hint = f" Known catalog matches: {', '.join(suggestions)}." if suggestions else ""
    return f"I could not find '{q}' as installed.{hint}"


def _update_all() -> str:
    ok, winget_or_msg = _ensure_winget()
    if not ok:
        return winget_or_msg

    cmd = [
        winget_or_msg,
        "upgrade",
        "--all",
        "--silent",
        "--accept-package-agreements",
        "--accept-source-agreements",
    ]
    rc, out = _run_cmd(cmd, timeout=1800)
    if rc == 0:
        return "Update-all completed successfully."
    return f"Update-all finished with issues.\n{out[-1000:]}"


def _update_app(target: str) -> str:
    target = _extract_target_from_text(target)
    if not target.strip():
        return "Please provide an app name or winget ID to update."

    ok, winget_or_msg = _ensure_winget()
    if not ok:
        return winget_or_msg

    target = target.strip()
    entry = _catalog_entry(target)
    if entry and entry.get("winget_id"):
        target = entry["winget_id"]

    # Try by id first (exact), then by name.
    cmd_id = [
        winget_or_msg,
        "upgrade",
        "--id",
        target,
        "--exact",
        "--silent",
        "--accept-package-agreements",
        "--accept-source-agreements",
    ]
    rc, out = _run_cmd(cmd_id, timeout=900)
    if rc == 0:
        return f"Updated {target} successfully."

    cmd_name = [
        winget_or_msg,
        "upgrade",
        "--name",
        target,
        "--silent",
        "--accept-package-agreements",
        "--accept-source-agreements",
    ]
    rc2, out2 = _run_cmd(cmd_name, timeout=900)
    if rc2 == 0:
        return f"Updated {target} successfully."

    tail = (out2 or out or "")[-1000:]
    return f"Could not update {target}.\n{tail}"


def _install_app(target: str) -> str:
    original_target = target
    target = _extract_target_from_text(target)
    if not target.strip():
        return "Please provide an app name or winget ID to install."

    ok, winget_or_msg = _ensure_winget()
    if not ok:
        return winget_or_msg

    target = target.strip()
    entry = _catalog_entry(target)
    if entry and entry.get("winget_id"):
        target = entry["winget_id"]

    print(f"[downloader_updater] install target original={original_target!r} normalized={target!r}")

    cmd_id = [
        winget_or_msg,
        "install",
        "--id",
        target,
        "--exact",
        "--silent",
        "--accept-package-agreements",
        "--accept-source-agreements",
    ]
    rc, out = _run_cmd(cmd_id, timeout=1800)
    if rc == 0:
        return f"Installed {target} successfully."

    cmd_name = [
        winget_or_msg,
        "install",
        "--name",
        target,
        "--silent",
        "--accept-package-agreements",
        "--accept-source-agreements",
    ]
    rc2, out2 = _run_cmd(cmd_name, timeout=1800)
    if rc2 == 0:
        return f"Installed {target} successfully."

    tail = (out2 or out or "")[-1000:]
    suggestions = _suggest_catalog(target)
    hint = f"\nPossible matches: {', '.join(suggestions)}" if suggestions else ""
    return f"Could not install {target}.\n{tail}{hint}"


def _split_targets(raw: Any) -> list[str]:
    if isinstance(raw, list):
        items = [str(x).strip() for x in raw]
    else:
        txt = str(raw or "").strip()
        items = [x.strip() for x in re.split(r",|\band\b|\&", txt) if x.strip()]
    cleaned = []
    for item in items:
        t = _extract_target_from_text(item)
        if t:
            cleaned.append(t)
    return cleaned


def _install_many(targets: Any) -> str:
    items = _split_targets(targets)
    if not items:
        return "Please provide one or more apps to install."

    results = []
    for item in items:
        results.append(f"- {item}: {_install_app(item)}")
    return "Batch install results:\n" + "\n".join(results)


def _update_many(targets: Any) -> str:
    items = _split_targets(targets)
    if not items:
        return "Please provide one or more apps to update."

    results = []
    for item in items:
        results.append(f"- {item}: {_update_app(item)}")
    return "Batch update results:\n" + "\n".join(results)


def _supported_apps() -> str:
    names = sorted(_APP_CATALOG.keys())
    return "Supported app aliases: " + ", ".join(names)


def _smart_action_from_query(text: str, player: Any = None) -> str:
    t = (text or "").strip()
    if not t:
        return "Please provide a command like 'download github' or 'update vscode'."

    tl = t.lower()

    if "check update" in tl or "check updates" in tl:
        return _check_updates()
    if "update all" in tl or "upgrade all" in tl:
        return _update_all()
    if tl.startswith("search ") or "find app" in tl or "search app" in tl:
        q = t.split(" ", 1)[1] if " " in t else ""
        return _search_apps(q)
    if tl.startswith("status ") or "is installed" in tl:
        q = t.replace("status", "").replace("is installed", "").strip()
        return _status_app(q)

    # Multi-target patterns, e.g. "install github and vscode"
    if tl.startswith("install ") or tl.startswith("download "):
        payload = t.split(" ", 1)[1] if " " in t else ""
        items = _split_targets(payload)
        if len(items) > 1:
            return _install_many(items)
        if len(items) == 1:
            return downloader_updater({"action": "download", "target": items[0]}, None, player, None)

    if tl.startswith("update ") or tl.startswith("upgrade "):
        payload = t.split(" ", 1)[1] if " " in t else ""
        items = _split_targets(payload)
        if len(items) > 1:
            return _update_many(items)
        if len(items) == 1:
            return _update_app(items[0])

    # Natural fallback if command words appear in the middle.
    if any(v in tl for v in ("download", "install", "update", "upgrade")):
        target = _extract_target_from_text(t)
        if "update" in tl or "upgrade" in tl:
            return _update_app(target)
        return downloader_updater({"action": "download", "target": target}, None, player, None)

    return "Could not infer action. Try: download/install/update/check updates/search/status."


def downloader_updater(
    parameters: dict[str, Any] | None = None,
    response: Any = None,
    player: Any = None,
    session_memory: Any = None,
) -> str:
    _ = response, session_memory
    args = parameters or {}
    action = str(args.get("action", "")).strip().lower()

    if player:
        try:
            player.write_log(f"[downloader_updater] action={action}")
            for key in ("target", "query", "app", "url"):
                if args.get(key):
                    player.write_log(f"[downloader_updater] {key}={str(args.get(key))[:120]}")
        except Exception:
            pass

    if action in {"download", "download_file"}:
        url = str(args.get("url", "")).strip()
        if url:
            return _download_file(url, args.get("destination"))

        target = str(args.get("target", "")).strip()
        if not target:
            # Auto fallback from natural-language field names
            target = str(args.get("app", "")).strip() or str(args.get("query", "")).strip()

        if not target:
            return "Please provide a URL or app target to download."

        # Advanced behavior: for app names, prefer install flow; fallback to official download page.
        installed = _install_app(target)
        if "successfully" in installed.lower():
            return installed

        entry = _catalog_entry(target)
        if entry and entry.get("download_url"):
            try:
                import webbrowser

                webbrowser.open_new_tab(entry["download_url"])
                return (
                    f"Could not install {target} directly. Opened official download page: "
                    f"{entry['download_url']}"
                )
            except Exception:
                return installed

        return installed

    if action in {"check_updates", "list_updates"}:
        return _check_updates()

    if action in {"search_app", "search"}:
        query = str(args.get("query", "")).strip() or str(args.get("target", "")).strip()
        return _search_apps(query)

    if action in {"status_app", "status", "is_installed"}:
        target = str(args.get("target", "")).strip() or str(args.get("query", "")).strip()
        return _status_app(target)

    if action in {"update_all", "upgrade_all"}:
        return _update_all()

    if action in {"update_app", "upgrade_app"}:
        target = str(args.get("target", "")).strip()
        return _update_app(target)

    if action in {"install_app", "install"}:
        target = str(args.get("target", "")).strip()
        return _install_app(target)

    if action in {"install_many", "batch_install"}:
        return _install_many(args.get("targets") or args.get("target") or args.get("query"))

    if action in {"update_many", "batch_update"}:
        return _update_many(args.get("targets") or args.get("target") or args.get("query"))

    if action in {"list_supported", "supported_apps"}:
        return _supported_apps()

    if action in {"auto", "smart"}:
        text = (
            str(args.get("query", "")).strip()
            or str(args.get("task", "")).strip()
            or str(args.get("description", "")).strip()
        )
        return _smart_action_from_query(text, player)

    return (
        "Unknown action. Use one of: download_file, check_updates, search_app, status_app, "
        "update_app, update_all, install_app, install_many, update_many, list_supported, auto."
    )
