"""OpenApps automation bridge for Kree.

This module keeps OpenApps optional and isolated from native app launching.
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
import webbrowser
from pathlib import Path
from typing import Any

from kree.actions.open_app import open_app  # type: ignore[import]

try:
    import psutil  # type: ignore[import]
except Exception:
    psutil = None  # type: ignore[assignment]


_LOCK = threading.Lock()
_PROCS: dict[str, subprocess.Popen[str]] = {}

_OPENAPPS_LICENSE_NOTE = (
    "OpenApps uses CC-BY-NC 4.0 in this repository. Keep usage non-commercial and include attribution "
    "to OpenApps/Meta in docs or app credits when distributed."
)

_NATIVE_APP_CANDIDATES: dict[str, list[str]] = {
    "codex": ["ChatGPT", "Codex"],
    "chatgpt": ["ChatGPT"],
    "github": ["GitHub Desktop", "GitHub"],
}

_PROCESS_HINTS: dict[str, list[str]] = {
    "codex": ["chatgpt", "codex"],
    "chatgpt": ["chatgpt"],
    "github": ["githubdesktop", "github"],
}

_DOWNLOAD_URLS: dict[str, str] = {
    "codex": "https://openai.com/chatgpt/download/",
    "chatgpt": "https://openai.com/chatgpt/download/",
    "github": "https://desktop.github.com/download/",
}


def _get_openapps_dir() -> Path:
    env_path = os.environ.get("OPENAPPS_DIR", "").strip()
    if env_path:
        return Path(env_path)

    # actions/ -> project root candidates
    here = Path(__file__).resolve()
    candidates = [
        here.parents[3] / "_Related_Projects" / "OpenApps-main",
        here.parents[2] / "_Related_Projects" / "OpenApps-main",
        here.parents[1] / "_Related_Projects" / "OpenApps-main",
        here.parents[3] / "OpenApps-main",
        here.parents[2] / "OpenApps-main",
        here.parents[1] / "OpenApps-main",
        Path.cwd() / "_Related_Projects" / "OpenApps-main",
        Path.cwd() / "OpenApps-main",
        Path("E:/Mark-XXX-main/_Related_Projects/OpenApps-main"),
        Path("E:/OpenApps-main"), # Force hardcode just in case it's specifically in the E root
    ]
    for c in candidates:
        if (c / "launch.py").exists():
            return c
    return candidates[0]


def _python_cmd(openapps_dir: Path) -> list[str]:
    uv = shutil.which("uv")
    if uv:
        return [uv, "run"]

    win_venv = openapps_dir / ".venv" / "Scripts" / "python.exe"
    nix_venv = openapps_dir / ".venv" / "bin" / "python"
    if win_venv.exists():
        return [str(win_venv)]
    if nix_venv.exists():
        return [str(nix_venv)]
    return [sys.executable]


def _build_cmd(action: str, args: dict[str, Any], openapps_dir: Path) -> list[str]:
    base = _python_cmd(openapps_dir)

    if action in {"launch_env", "start", "open"}:
        cmd = base + ["launch.py"]
        app_name = str(args.get("app", "")).strip()
        theme = str(args.get("theme", "")).strip().lower()
        if app_name:
            cmd.append(f"app={app_name}")
        if theme in {"dark", "light"}:
            cmd.append(f"apps.start_page.appearance.theme={theme}")
        return cmd

    if action in {"run_task", "task"}:
        cmd = base + ["launch_agent.py"]
        agent = str(args.get("agent", "GPT-5-1")).strip() or "GPT-5-1"
        task_name = str(args.get("task_name", "")).strip()
        if not task_name:
            raise ValueError("task_name is required for run_task")
        cmd += [f"agent={agent}", f"task_name={task_name}"]
        if bool(args.get("headless", True)) is False:
            cmd.append("browsergym_env_args.headless=False")
        return cmd

    if action in {"run_parallel_tasks", "parallel"}:
        cmd = base + ["launch_parallel_agents.py"]
        agent = str(args.get("agent", "GPT-5-1")).strip() or "GPT-5-1"
        cmd += [f"agent={agent}"]
        extra = str(args.get("extra", "")).strip()
        if extra:
            cmd += shlex.split(extra)
        return cmd

    raise ValueError(f"Unsupported action: {action}")


def _terminate_process(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is not None:
        return
    if psutil is not None:
        try:
            parent = psutil.Process(proc.pid)
            children = parent.children(recursive=True)
            for c in children:
                try:
                    c.terminate()
                except Exception:
                    pass
            parent.terminate()
            psutil.wait_procs(children + [parent], timeout=3)
            return
        except Exception:
            pass
    try:
        proc.terminate()
    except Exception:
        pass


def _start_background(kind: str, cmd: list[str], cwd: Path) -> str:
    with _LOCK:
        existing = _PROCS.get(kind)
        if existing and existing.poll() is None:
            return f"OpenApps {kind} is already running (pid {existing.pid})."

        proc = subprocess.Popen(
            cmd,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        _PROCS[kind] = proc
        return f"Started OpenApps {kind} (pid {proc.pid})."


def _status() -> str:
    with _LOCK:
        if not _PROCS:
            return "Kree automation environment is not running."
        parts: list[str] = []
        for k, p in list(_PROCS.items()):
            if p.poll() is None:
                parts.append(f"{k}: running (pid {p.pid})")
            else:
                parts.append(f"{k}: stopped (exit {p.returncode})")
        return " | ".join(parts)


def _run_preset(args: dict[str, Any]) -> str:
    preset = str(args.get("preset", "")).strip().lower()

    if preset in {"codex_github_app_builder", "codex_app_builder", "open_codex_github"}:
        user_prompt = str(args.get("prompt", "")).strip() or "Make a complete production-ready app."
        encoded = urllib.parse.quote_plus(user_prompt)

        # Open GitHub first, then Codex/Chat tab with model hint and prompt payload.
        webbrowser.open_new_tab("https://github.com")
        webbrowser.open_new_tab(f"https://chatgpt.com/?model=gpt-5-codex&q={encoded}")
        return (
            "Started Kree automation preset: Codex + GitHub app builder. "
            "Opened GitHub and Codex tabs and passed your app request."
        )

    return f"Unknown preset: {preset}. Available: codex_github_app_builder"


def _known_web_target_url(name: str) -> str | None:
    n = name.strip().lower()
    mapping = {
        "github": "https://github.com",
        "git hub": "https://github.com",
        "codex": "https://chatgpt.com/?model=gpt-5-codex",
        "chatgpt": "https://chatgpt.com",
        "openai": "https://chatgpt.com",
        "google": "https://www.google.com",
    }
    return mapping.get(n)


def _is_open_success(result_text: str) -> bool:
    t = (result_text or "").lower()
    if not t:
        return False
    if "__broadcast_intent__" in t:
        return True
    if "failed" in t or "couldn't confirm" in t or "could not" in t:
        return False
    return "opened" in t or "success" in t


def _process_running(hints: list[str]) -> bool:
    if psutil is None:
        return False
    norm_hints = [h.lower().replace(" ", "") for h in hints if h]
    if not norm_hints:
        return False
    try:
        for proc in psutil.process_iter(["name"]):
            try:
                name = str(proc.info.get("name") or "").lower().replace(" ", "").replace(".exe", "")
                if any(h in name for h in norm_hints):
                    return True
            except Exception:
                continue
    except Exception:
        return False
    return False


def _try_open_native(target: str, player: Any = None) -> tuple[bool, str, str | None]:
    """Returns (success, app_name_used, raw_result_string)."""
    norm = target.strip().lower()
    candidates = _NATIVE_APP_CANDIDATES.get(norm, [target])

    for app_name in candidates:
        try:
            r = open_app(
                parameters={"app_name": app_name},
                response=None,
                player=player,
                session_memory=None,
            )
            if _is_open_success(r):
                return True, app_name, r
        except Exception:
            continue

    return False, "", None


def _download_targets(targets: list[str]) -> str:
    opened: list[str] = []
    for t in targets:
        key = t.strip().lower()
        url = _DOWNLOAD_URLS.get(key)
        if url:
            webbrowser.open_new_tab(url)
            opened.append(t)
    if opened:
        return "Opened download pages for: " + ", ".join(opened)
    return "No known native download pages for requested targets."


def _parse_targets(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    text = str(raw or "")
    if not text.strip():
        return []
    splitters = [",", " and ", " & "]
    items = [text]
    for s in splitters:
        buf: list[str] = []
        for it in items:
            buf.extend(it.split(s))
        items = buf
    return [x.strip() for x in items if x.strip()]


def _open_and_delegate(args: dict[str, Any], player: Any = None) -> str:
    targets = _parse_targets(args.get("targets") or args.get("apps") or "")
    delegate_app = str(args.get("delegate_app", "")).strip().lower()
    prompt = str(args.get("prompt", "")).strip()
    fallback = str(args.get("fallback", "ask")).strip().lower() or "ask"

    opened: list[str] = []
    launched: list[str] = []
    native_opened: list[str] = []
    missing_native: list[str] = []

    for t in targets:
        target = t.strip()
        if not target:
            continue

        ok, app_used, _ = _try_open_native(target, player=player)
        if ok:
            native_opened.append(target)
            launched.append(app_used)
            continue

        # If this target is known for native-first behavior, collect for fallback decision.
        if target.lower() in _NATIVE_APP_CANDIDATES:
            missing_native.append(target)
            continue

        # Unknown target: try native launcher once using raw name.
        try:
            raw = open_app(
                parameters={"app_name": target},
                response=None,
                player=player,
                session_memory=None,
            )
            if _is_open_success(raw):
                launched.append(target)
                continue
        except Exception:
            pass

        # As a final fallback for known web tools, open in browser.
        url = _known_web_target_url(target)
        if url:
            if fallback == "browser":
                webbrowser.open_new_tab(url)
                opened.append(target)
            else:
                missing_native.append(target)

    if missing_native and fallback == "ask":
        return (
            "QUESTION: I could not open native app(s): " + ", ".join(missing_native) +
            ". Should I download it or open in browser?"
        )

    if missing_native and fallback == "download":
        _download_targets(missing_native)

    if missing_native and fallback == "browser":
        for t in missing_native:
            url = _known_web_target_url(t)
            if url:
                webbrowser.open_new_tab(url)
                opened.append(t)

    if delegate_app in {"codex", "chatgpt", "openai"} and prompt:
        # Prefer native app for Codex/ChatGPT, only browser fallback if requested.
        codex_ok, _, _ = _try_open_native("codex", player=player)
        if codex_ok:
            native_opened.append("codex")
        elif fallback == "ask":
            return "QUESTION: I could not open native Codex. Should I download it or open in browser?"
        elif fallback == "download":
            _download_targets(["codex"])
        else:
            encoded = urllib.parse.quote_plus(prompt)
            webbrowser.open_new_tab(f"https://chatgpt.com/?model=gpt-5-codex&q={encoded}")
            if "codex" not in [x.lower() for x in opened]:
                opened.append("codex")

    if not targets and delegate_app and prompt:
        codex_ok, _, _ = _try_open_native(delegate_app, player=player)
        if codex_ok:
            return f"Opened native {delegate_app}."
        if fallback == "ask":
            return f"QUESTION: I could not open native {delegate_app}. Should I download it or open in browser?"
        if fallback == "download":
            return _download_targets([delegate_app])
        encoded = urllib.parse.quote_plus(prompt)
        webbrowser.open_new_tab(f"https://chatgpt.com/?model=gpt-5-codex&q={encoded}")
        return "Opened Codex in browser with your instruction."

    return (
        "Automation started. Opened targets: " + (", ".join(opened) if opened else "none") +
        "; launched apps: " + (", ".join(launched) if launched else "none") +
        "; native: " + (", ".join(native_opened) if native_opened else "none") +
        (f"; delegated to {delegate_app}." if delegate_app else ".")
    )


def _list_apps_tasks_agents(openapps_dir: Path, action: str) -> str:
    apps_dir = openapps_dir / "config" / "apps"
    agents_dir = openapps_dir / "config" / "agent"
    tasks_file = openapps_dir / "config" / "tasks" / "all_tasks.yaml"

    if action == "list_apps":
        if not apps_dir.exists():
            return "OpenApps apps config folder not found."
        apps = sorted([p.name for p in apps_dir.iterdir() if p.is_dir()])
        return "OpenApps apps: " + ", ".join(apps)

    if action == "list_agents":
        if not agents_dir.exists():
            return "OpenApps agent config folder not found."
        agents = sorted([p.stem for p in agents_dir.glob("*.yaml")])
        return "OpenApps agent configs: " + ", ".join(agents)

    if action == "list_tasks":
        if not tasks_file.exists():
            return "OpenApps tasks file not found."
        raw = tasks_file.read_text(encoding="utf-8", errors="replace")
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip() and not ln.strip().startswith("#")]
        preview = lines[:20]
        if not preview:
            return "OpenApps tasks list appears empty."
        return "OpenApps task config preview:\n" + "\n".join(preview)

    return "Unsupported list action."


def openapps_automation(
    parameters: dict[str, Any] | None = None,
    response: Any = None,
    player: Any = None,
    session_memory: Any = None,
) -> str:
    """Control OpenApps as an optional automation feature."""
    _ = response, session_memory
    args = parameters or {}
    action = str(args.get("action", "status")).strip().lower()

    openapps_dir = _get_openapps_dir()
    if not (openapps_dir / "launch.py").exists():
        return (
            "The OpenApps automation environment isn't installed. "
            "Please tell the user they need to clone OpenApps-main into the current drive."
        )

    if action in {"status", "health"}:
        return _status()

    if action in {"license_info", "license", "copyright_info"}:
        return _OPENAPPS_LICENSE_NOTE

    if action in {"list_apps", "list_agents", "list_tasks"}:
        return _list_apps_tasks_agents(openapps_dir, action)

    if action in {"run_preset", "preset"}:
        return _run_preset(args)

    if action in {"open_and_delegate", "workflow_open_and_ask", "multi_open_and_ask"}:
        return _open_and_delegate(args, player=player)

    if action in {"stop", "stop_env", "stop_all"}:
        with _LOCK:
            if not _PROCS:
                return "No Kree automation environment process is running."
            for proc in list(_PROCS.values()):
                _terminate_process(proc)
            _PROCS.clear()
        return "Stopped all Kree automation environment processes."

    kind = "env"
    if action in {"run_task", "task"}:
        kind = "agent_task"
        timeout = int(args.get("timeout", 0) or 0)
        cmd = _build_cmd(action, args, openapps_dir)
        if player:
            try:
                player.write_log(f"[openapps] {' '.join(cmd)}")
            except Exception:
                pass
        try:
            cp = subprocess.run(
                cmd,
                cwd=str(openapps_dir),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout if timeout > 0 else None,
            )
            out = (cp.stdout or "")[-900:]
            if cp.returncode == 0:
                return f"OpenApps task completed successfully.\n{out}".strip()
            return f"OpenApps task failed (exit {cp.returncode}).\n{out}".strip()
        except subprocess.TimeoutExpired:
            return "OpenApps task timed out. Increase timeout and try again."

    if action in {"run_parallel_tasks", "parallel"}:
        kind = "parallel"

    if action in {"start_kree_automation_environment", "start_kree_automation_env", "start_kree_automation"}:
        action = "launch_env"

    cmd = _build_cmd(action, args, openapps_dir)
    if player:
        try:
            player.write_log(f"[openapps] {' '.join(cmd)}")
        except Exception:
            pass
    started = _start_background(kind, cmd, openapps_dir)
    if action == "launch_env":
        msg = started.replace("OpenApps env", "Kree automation environment")
        return f"{msg} {_OPENAPPS_LICENSE_NOTE}"
    return started
