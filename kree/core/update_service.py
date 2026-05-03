"""Custom update client for Kree.

The update contract is intentionally simple:
- a manifest JSON hosted on a custom server
- a downloadable ZIP package for the Windows release
- an optional SHA-256 checksum for integrity checks

The client preserves the local config directory when applying updates.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests  # type: ignore[import]

from kree.core.version import APP_NAME, APP_VERSION  # type: ignore[import]


from kree._paths import PROJECT_ROOT
BASE_DIR = PROJECT_ROOT
CONFIG_DIR = BASE_DIR / "config"
UPDATE_STATE_FILE = CONFIG_DIR / "update_state.json"
UPDATE_SETTINGS_FILE = CONFIG_DIR / "update_settings.json"
UPDATE_CACHE_DIR = BASE_DIR / "updates"

DEFAULT_UPDATE_SETTINGS: dict[str, Any] = {
    "manifest_url": "",
}


def _ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _ensure_update_dir() -> None:
    UPDATE_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            return raw
    except Exception:
        pass
    return {}


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load_update_settings() -> dict[str, Any]:
    data = dict(DEFAULT_UPDATE_SETTINGS)
    data.update(_read_json(UPDATE_SETTINGS_FILE))
    env_manifest = os.environ.get("KREE_UPDATE_MANIFEST_URL", "").strip()
    if env_manifest and not data.get("manifest_url"):
        data["manifest_url"] = env_manifest
    return data


def save_update_settings(settings: dict[str, Any]) -> dict[str, Any]:
    current = load_update_settings()
    if isinstance(settings, dict):
        current.update(settings)
    _ensure_config_dir()
    _write_json(UPDATE_SETTINGS_FILE, current)
    return current


def load_update_state() -> dict[str, Any]:
    state = _read_json(UPDATE_STATE_FILE)
    state.setdefault("installed_version", APP_VERSION)
    state.setdefault("update_available", False)
    state.setdefault("status", "Idle")
    state.setdefault("manifest_url", load_update_settings().get("manifest_url", ""))
    return state


def save_update_state(state: dict[str, Any]) -> dict[str, Any]:
    current = load_update_state()
    if isinstance(state, dict):
        current.update(state)
    _ensure_config_dir()
    _write_json(UPDATE_STATE_FILE, current)
    return current


def _version_key(version_text: str) -> tuple[str, ...]:
    parts: list[str] = []
    token = ""
    for char in str(version_text or "").strip():
        if char.isdigit():
            token += char
            continue
        if token:
            parts.append(f"0{int(token):08d}")
            token = ""
        if char.isalpha():
            parts.append(f"1{char.lower()}")
    if token:
        parts.append(f"0{int(token):08d}")
    return tuple(parts or ["0"])


def _checksum_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_manifest(raw: dict[str, Any]) -> dict[str, Any]:
    manifest = dict(raw or {})
    version = str(manifest.get("version") or manifest.get("latest_version") or "").strip()
    download_url = str(manifest.get("download_url") or manifest.get("package_url") or "").strip()
    package_type = str(manifest.get("package_type") or "zip").strip().lower() or "zip"
    checksum = str(
        manifest.get("sha256")
        or manifest.get("checksum")
        or manifest.get("package_sha256")
        or ""
    ).strip()

    return {
        "name": str(manifest.get("name") or APP_NAME),
        "version": version,
        "download_url": download_url,
        "package_type": package_type,
        "checksum": checksum,
        "notes": str(manifest.get("notes") or manifest.get("release_notes") or "").strip(),
        "published_at": str(manifest.get("published_at") or "").strip(),
        "manifest_url": str(manifest.get("manifest_url") or "").strip(),
    }


def _fetch_manifest(manifest_url: str) -> dict[str, Any]:
    if not manifest_url:
        raise ValueError("No manifest URL has been configured.")

    response = requests.get(manifest_url, timeout=20)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Update manifest must be a JSON object.")
    payload.setdefault("manifest_url", manifest_url)
    manifest = _normalize_manifest(payload)
    download_url = str(manifest.get("download_url") or "").strip()
    if download_url and not urlparse(download_url).scheme:
        manifest["download_url"] = urljoin(manifest_url, download_url)
    return manifest


def _resolve_manifest_url(manifest_url: str | None = None) -> str:
    if manifest_url and str(manifest_url).strip():
        return str(manifest_url).strip()
    settings = load_update_settings()
    configured = str(settings.get("manifest_url") or "").strip()
    if configured:
        return configured
    return os.environ.get("KREE_UPDATE_MANIFEST_URL", "").strip()


def get_update_state() -> dict[str, Any]:
    state = load_update_state()
    settings = load_update_settings()
    state.setdefault("manifest_url", settings.get("manifest_url", ""))
    state.setdefault("installed_version", APP_VERSION)
    state.setdefault("app_name", APP_NAME)
    return state


def check_for_updates(manifest_url: str | None = None) -> dict[str, Any]:
    resolved_url = _resolve_manifest_url(manifest_url)
    state = get_update_state()
    state.update({"app_name": APP_NAME, "installed_version": APP_VERSION, "manifest_url": resolved_url})

    if not resolved_url:
        state.update({
            "status": "No update server configured.",
            "update_available": False,
            "error": "Missing manifest URL.",
        })
        return save_update_state(state)

    try:
        manifest = _fetch_manifest(resolved_url)
        latest_version = manifest.get("version", "")
        if not latest_version:
            raise ValueError("The manifest did not contain a version string.")

        update_available = _version_key(latest_version) > _version_key(APP_VERSION)
        state.update({
            "status": f"{'Update available' if update_available else 'Kree is up to date'}: {latest_version}",
            "update_available": update_available,
            "latest_version": latest_version,
            "download_url": manifest.get("download_url", ""),
            "package_type": manifest.get("package_type", "zip"),
            "checksum": manifest.get("checksum", ""),
            "notes": manifest.get("notes", ""),
            "published_at": manifest.get("published_at", ""),
            "error": "",
        })
    except Exception as exc:
        state.update({
            "status": f"Update check failed: {exc}",
            "update_available": False,
            "error": str(exc),
        })

    state["last_checked"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    return save_update_state(state)


def _download_to_file(download_url: str, destination: Path) -> Path:
    response = requests.get(download_url, stream=True, timeout=30)
    response.raise_for_status()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as handle:
        for chunk in response.iter_content(chunk_size=1024 * 256):
            if chunk:
                handle.write(chunk)
    return destination


def download_update(manifest_url: str | None = None) -> dict[str, Any]:
    state = check_for_updates(manifest_url)
    if not state.get("update_available"):
        return state

    download_url = str(state.get("download_url") or "").strip()
    if not download_url:
        state.update({"status": "Manifest is missing a download URL.", "error": "Missing download URL."})
        return save_update_state(state)

    package_type = str(state.get("package_type") or "zip").strip().lower()
    parsed = urlparse(download_url)
    file_name = Path(parsed.path).name or f"kree-update.{package_type or 'zip'}"
    if package_type == "zip" and not file_name.lower().endswith(".zip"):
        file_name = f"{file_name}.zip"

    _ensure_update_dir()
    destination = UPDATE_CACHE_DIR / file_name

    try:
        _download_to_file(download_url, destination)
        checksum = str(state.get("checksum") or "").strip().lower()
        if checksum:
            actual = _checksum_sha256(destination)
            if actual.lower() != checksum:
                destination.unlink(missing_ok=True)
                raise ValueError("Checksum mismatch.")

        state.update({
            "status": f"Downloaded update to {destination}",
            "downloaded": True,
            "download_path": str(destination),
            "checksum_ok": True,
            "error": "",
        })
    except Exception as exc:
        state.update({
            "status": f"Download failed: {exc}",
            "downloaded": False,
            "download_path": "",
            "checksum_ok": False,
            "error": str(exc),
        })

    return save_update_state(state)


def _build_update_helper(download_path: Path, install_dir: Path, current_pid: int) -> str:
    download_literal = str(download_path).replace("'", "''")
    install_literal = str(install_dir).replace("'", "''")
    exe_literal = str(install_dir / "Kree AI.exe").replace("'", "''")
    return (
        "$ErrorActionPreference='Stop';"
        f"$pidToWait={int(current_pid)};"
        f"$zipPath='{download_literal}';"
        f"$installDir='{install_literal}';"
        f"$exePath='{exe_literal}';"
        "$temp=Join-Path $env:TEMP ('kree-update-' + [guid]::NewGuid().ToString());"
        "New-Item -ItemType Directory -Path $temp -Force | Out-Null;"
        "Wait-Process -Id $pidToWait -ErrorAction SilentlyContinue;"
        "Expand-Archive -LiteralPath $zipPath -DestinationPath $temp -Force;"
        "Get-ChildItem -LiteralPath $temp -Force | ForEach-Object {"
        "  if ($_.Name -ieq 'config') { continue };"
        "  Copy-Item -LiteralPath $_.FullName -Destination $installDir -Recurse -Force;"
        "};"
        "Start-Process -FilePath $exePath;"
        "Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue;"
    )


def apply_update(download_path: str | None = None) -> dict[str, Any]:
    if platform.system() != "Windows":
        return {"ok": False, "status": "Windows updates are only supported on Windows.", "error": "unsupported platform"}

    state = get_update_state()
    path_text = str(download_path or state.get("download_path") or "").strip()
    if not path_text:
        return {"ok": False, "status": "No downloaded update is available.", "error": "missing package"}

    package_path = Path(path_text)
    if not package_path.exists():
        return {"ok": False, "status": "The downloaded update file could not be found.", "error": "missing file"}

    try:
        helper = _build_update_helper(package_path, BASE_DIR, os.getpid())
        subprocess.Popen(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", helper],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        state.update({
            "status": "Update helper started. Kree will restart after the current session closes.",
            "pending_install": str(package_path),
            "error": "",
        })
        save_update_state(state)
        return {"ok": True, "status": state["status"], "pending_install": str(package_path)}
    except Exception as exc:
        return {"ok": False, "status": f"Could not start update helper: {exc}", "error": str(exc)}


def open_update_folder() -> dict[str, Any]:
    _ensure_update_dir()
    try:
        os.startfile(str(UPDATE_CACHE_DIR))  # type: ignore[attr-defined]
        return {"ok": True, "path": str(UPDATE_CACHE_DIR)}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "path": str(UPDATE_CACHE_DIR)}
