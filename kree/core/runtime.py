"""
core/runtime.py — Centralized path resolution for Kree AI.

Handles the critical difference between:
  - Dev mode:    __file__ points to source tree
  - Frozen mode: __file__ points inside _MEIPASS temp folder

Usage:
    from kree.core.runtime import BUNDLE_DIR, EXE_DIR, APP_DATA_DIR
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _is_frozen() -> bool:
    """True when running as a PyInstaller bundle."""
    return getattr(sys, "frozen", False)


def _get_bundle_dir() -> Path:
    """
    Where bundled *read-only* resources live (config templates, assets,
    openwakeword models, stitch dashboard HTML, etc.).

    - Frozen: sys._MEIPASS  (PyInstaller's temp extraction folder)
    - Dev:    project root   (kree/core/runtime.py -> parent.parent.parent)
    """
    if _is_frozen() and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent.parent


def _get_exe_dir() -> Path:
    """
    Where the actual executable (or main.py in dev) lives.
    Use this for *writable* paths that should persist (configs, logs).

    - Frozen: directory containing Kree AI.exe
    - Dev:    project root   (kree/core/runtime.py -> parent.parent.parent)
    """
    if _is_frozen():
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent.parent


def _get_app_data_dir() -> Path:
    """
    Per-user writable directory for logs, crash reports, voiceprints.
    Uses %LOCALAPPDATA%/Kree on Windows.
    Falls back to EXE_DIR if LOCALAPPDATA is missing.
    """
    candidates = []
    base = os.environ.get("LOCALAPPDATA")
    if base:
        candidates.append(Path(base) / "Kree")
    candidates.append(_get_exe_dir() / "data")

    for path in candidates:
        try:
            path.mkdir(parents=True, exist_ok=True)
            return path
        except OSError:
            continue

    return _get_exe_dir()


# ── Public constants ─────────────────────────────────────────────────────────
IS_FROZEN = _is_frozen()
BUNDLE_DIR = _get_bundle_dir()       # read-only resources
EXE_DIR = _get_exe_dir()             # writable, next to exe
APP_DATA_DIR = _get_app_data_dir()   # per-user writable

# Convenience paths (auto-created on startup)
CONFIG_DIR = APP_DATA_DIR / "config"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
MEMORY_DIR = APP_DATA_DIR / "memory"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)
ASSETS_DIR = BUNDLE_DIR / "assets"
LOG_DIR = APP_DATA_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

VAULT_DIR = APP_DATA_DIR / "vault"
VAULT_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_DIR = APP_DATA_DIR / "history"
HISTORY_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR = APP_DATA_DIR / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def setup_rotating_logger(name: str, log_file: Path, max_bytes: int = 5 * 1024 * 1024, backup_count: int = 1):
    import logging
    from logging.handlers import RotatingFileHandler
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    if logger.handlers:
        logger.handlers.clear()
    handler = RotatingFileHandler(str(log_file), maxBytes=max_bytes, backupCount=backup_count, encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def _migrate_old_storage() -> None:
    """
    Migrates legacy config and memory files from PROJECT_ROOT/config and PROJECT_ROOT/memory
    to APP_DATA_DIR/config and APP_DATA_DIR/memory when upgrading (v1 -> v2).
    Also migrates from old APP_DATA_DIR ("Kree AI") to the new APP_DATA_DIR ("Kree") with ZIP backups.
    """
    import shutil
    import datetime
    from kree._paths import PROJECT_ROOT
    
    # 1. Migrate old "%LOCALAPPDATA%\Kree AI" folder with a ZIP backup
    base_local = os.environ.get("LOCALAPPDATA")
    if base_local:
        old_kree_ai = Path(base_local) / "Kree AI"
        if old_kree_ai.exists() and old_kree_ai.resolve() != APP_DATA_DIR.resolve():
            # Check if there are actually files to migrate
            files_to_migrate = [f for f in old_kree_ai.glob("**/*") if f.is_file()]
            if files_to_migrate:
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_zip_base = BACKUP_DIR / f"backup_{timestamp}"
                try:
                    shutil.make_archive(str(backup_zip_base), 'zip', root_dir=str(old_kree_ai))
                    print(f"[Migration] Created backup of old 'Kree AI' directory: {backup_zip_base}.zip")
                except Exception as be:
                    print(f"[Migration] ⚠️ Failed to create backup of old 'Kree AI' directory: {be}")
                
                # Non-destructively copy all files
                for src_path in files_to_migrate:
                    rel = src_path.relative_to(old_kree_ai)
                    dest_path = APP_DATA_DIR / rel
                    if not dest_path.exists():
                        try:
                            dest_path.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(src_path, dest_path)
                        except Exception as ce:
                            print(f"[Migration] ⚠️ Failed to copy {src_path} during folder migration: {ce}")
                
                # Rename old folder to prevent repeating migration
                try:
                    old_kree_ai.rename(Path(base_local) / "Kree AI.migrated")
                    print("[Migration] Legacy 'Kree AI' folder renamed to 'Kree AI.migrated'")
                except Exception as re:
                    print(f"[Migration] ⚠️ Failed to rename legacy 'Kree AI' folder: {re}")

    # 2. Reorganize internal directories to their final homes
    # Move users.json to vault/users.json
    old_users = MEMORY_DIR / "users.json"
    new_users = VAULT_DIR / "users.json"
    if old_users.exists() and not new_users.exists():
        try:
            shutil.copy2(old_users, new_users)
            print(f"[Migration] Reorganized users database: {old_users} -> {new_users}")
        except Exception as ue:
            print(f"[Migration] ⚠️ Failed to reorganize users: {ue}")

    # Move kree_memory.json to history/kree_memory.json
    old_history = MEMORY_DIR / "kree_memory.json"
    new_history = HISTORY_DIR / "kree_memory.json"
    if old_history.exists() and not new_history.exists():
        try:
            shutil.copy2(old_history, new_history)
            print(f"[Migration] Reorganized history file: {old_history} -> {new_history}")
        except Exception as he:
            print(f"[Migration] ⚠️ Failed to reorganize history: {he}")

    # Move legacy roaming ~/.kree/config vault hashes to vault/
    appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
    legacy_kree_config = Path(appdata) / ".kree" / "config"
    if legacy_kree_config.exists():
        for filename in ["master_pin.hash", "trusted_unlock.json"]:
            src_file = legacy_kree_config / filename
            dest_file = VAULT_DIR / filename
            if src_file.exists() and not dest_file.exists():
                try:
                    shutil.copy2(src_file, dest_file)
                    print(f"[Migration] Migrated vault file: {src_file} -> {dest_file}")
                except Exception as ve:
                    print(f"[Migration] ⚠️ Failed to migrate vault file {filename}: {ve}")

    # 3. Dev Project Root migration
    old_folders = {
        PROJECT_ROOT / "config": CONFIG_DIR,
        PROJECT_ROOT / "memory": MEMORY_DIR,
    }
    for old_dir, new_dir in old_folders.items():
        if old_dir.exists() and old_dir.resolve() != new_dir.resolve():
            for src_path in old_dir.glob("**/*"):
                if src_path.is_file():
                    rel = src_path.relative_to(old_dir)
                    dest_path = new_dir / rel
                    if not dest_path.exists():
                        try:
                            dest_path.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(src_path, dest_path)
                            print(f"[Migration] Copied legacy storage file: {src_path} -> {dest_path}")
                        except Exception as e:
                            print(f"[Migration] ⚠️ Failed to copy {src_path}: {e}")

    # 4. Strip hardware-specific device indices from migrated audio_settings.json
    # Device indices are ephemeral and meaningless across different PCs.
    # Fingerprint fields (input_device_name, input_device_host_api) are preserved
    # so the wake word engine can resolve by name on the new machine.
    migrated_audio = CONFIG_DIR / "audio_settings.json"
    if migrated_audio.exists():
        try:
            import json
            audio_data = json.loads(migrated_audio.read_text(encoding="utf-8"))
            if isinstance(audio_data, dict) and audio_data.get("input_device_index") is not None:
                audio_data["input_device_index"] = None
                migrated_audio.write_text(json.dumps(audio_data, indent=2), encoding="utf-8")
                print("[Migration] Stripped hardware-specific input_device_index from audio_settings.json")
        except Exception as ae:
            print(f"[Migration] ⚠️ Failed to sanitize audio_settings.json: {ae}")

_migrate_old_storage()

PLAYWRIGHT_BROWSERS_PATH = APP_DATA_DIR / "playwright_browsers"

def run_health_check() -> dict:
    """
    Performs a fast, non-blocking check of the application's environment.
    Does NOT launch the browser. Writes results to health.json.
    """
    import json
    import datetime
    import socket
    import os
    
    health = {
        "timestamp": datetime.datetime.now().isoformat(),
        "vault": False,
        "dashboard": False,
        "chromium": False,
        "write_access": False,
        "internet": False
    }
    
    # 1. Test Vault Encryption
    try:
        from kree.core import vault
        test_str = "health_check_test_123"
        enc = vault.encrypt_data(test_str)
        dec = vault.decrypt_data(enc)
        if dec == test_str:
            health["vault"] = True
    except Exception:
        pass
        
    # 2. Test Dashboard Readability
    try:
        dash_file = BUNDLE_DIR / "stitch_core_system_dashboard" / "core_system_dashboard_1" / "code.html"
        if not dash_file.exists():
            dash_file = BUNDLE_DIR / "stitch_core_system_dashboard" / "stitch_core_system_dashboard" / "core_system_dashboard_1" / "code.html"
        if dash_file.exists():
            health["dashboard"] = True
    except Exception:
        pass
        
    # 3. Test Chromium Executable Presence (without launching)
    try:
        exec_found = False
        if PLAYWRIGHT_BROWSERS_PATH.exists():
            # Shallow search to avoid traversing thousands of files recursively (Windows performance optimization)
            patterns = [
                "chromium-*/chrome-win/chrome.exe",
                "chromium-*/chrome-linux/chrome",
                "chromium-*/*/Chromium.app/Contents/MacOS/Chromium"
            ]
            for pattern in patterns:
                for p in PLAYWRIGHT_BROWSERS_PATH.glob(pattern):
                    if p.is_file():
                        exec_found = True
                        break
                if exec_found:
                    break
        health["chromium"] = exec_found
    except Exception:
        pass
        
    # 4. Test Write Access
    try:
        test_file = APP_DATA_DIR / ".write_test"
        test_file.write_text("ok", encoding="utf-8")
        if test_file.read_text(encoding="utf-8") == "ok":
            health["write_access"] = True
        test_file.unlink(missing_ok=True)
    except Exception:
        pass
        
    # 5. Test Internet Connection
    try:
        socket.setdefaulttimeout(1.5)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("8.8.8.8", 53))
        s.close()
        health["internet"] = True
    except Exception:
        pass
        
    # Save health check
    try:
        health_file = APP_DATA_DIR / "health.json"
        health_file.write_text(json.dumps(health, indent=2), encoding="utf-8")
    except Exception:
        pass
        
    return health
