"""
Kree AI — Auto-Update Engine
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Unifies and routes all update check requests to update_service.py.
Provides backwards-compatible wrappers.
"""

import os
import json
import threading
from pathlib import Path
from kree.core.runtime import CONFIG_DIR

# ── Resolve paths ─────────────────────────────────────────────────────────────
SERVICE_KEYS_PATH = CONFIG_DIR / "service_keys.json"


def _load_service_keys() -> dict:
    try:
        from kree.core.vault import decrypt_data, encrypt_data
        if not SERVICE_KEYS_PATH.exists():
            return {}
            
        raw = SERVICE_KEYS_PATH.read_bytes()
        if raw.startswith(b'{'):
            data = json.loads(raw.decode('utf-8'))
            try:
                encrypted = encrypt_data(raw.decode('utf-8'))
                SERVICE_KEYS_PATH.write_bytes(encrypted)
            except Exception:
                pass
            return data
            
        decrypted = decrypt_data(raw)
        return json.loads(decrypted)
    except Exception:
        return {}


def get_current_version() -> str:
    from kree.core.version import APP_VERSION
    return _load_service_keys().get("kree_version", APP_VERSION)


def get_github_repo() -> str:
    return _load_service_keys().get("github_repo", "YOUR_USERNAME/kree")


def check_for_update() -> dict:
    """
    Checks for the latest updates.
    Returns dict with 'available', 'version', 'download_url', 'notes'.
    Non-blocking safe — never raises.
    """
    try:
        from kree.core.update_service import check_for_updates
        res = check_for_updates()
        
        # Keep backward compatibility with old keys
        available = res.get("update_available", False)
        version = res.get("latest_version", "")
        download_url = res.get("download_url", "")
        notes = res.get("notes", "")

        return {
            "available": available,
            "version": version,
            "download_url": download_url,
            "notes": notes,
        }
    except Exception as e:
        print(f"[KREE UPDATE] Check failed (non-fatal): {e}")
        return {"available": False, "error": str(e)}


def download_only(download_url: str) -> str:
    """
    Downloads the update package in background.
    Returns the absolute path to the downloaded package.
    """
    if not download_url:
        return ""

    try:
        from kree.core.update_service import download_update
        res = download_update()
        path = res.get("download_path", "")
        if path:
            _pending_update["downloaded_path"] = path
            _pending_update["is_ready"] = True
        return path
    except Exception as e:
        print(f"[KREE UPDATE] Background download failed: {e}")
        return ""


def run_installer_and_exit(installer_path: str = "") -> bool:
    """
    Compatibility wrapper for the canonical manifest/ZIP update service.
    """
    path = installer_path or _pending_update.get("downloaded_path", "")
    if not path or not os.path.exists(path):
        return False

    try:
        from kree.core.update_service import apply_update
        result = apply_update(path)
        return bool(result.get("ok"))
    except Exception as e:
        print(f"[KREE UPDATE] Final install trigger failed: {e}")
        return False


def download_and_install(download_url: str, on_progress=None) -> bool:
    """Legacy wrapper for manual triggering."""
    path = download_only(download_url)
    if path:
        return run_installer_and_exit(path)
    return False


def check_update_background(ui=None, speak_fn=None, auto_download=True):
    """
    Non-blocking background update check routed through update_service.
    """
    def _check():
        from kree.core.update_service import check_for_updates, download_update

        result = check_for_updates()
        if not result.get("update_available"):
            return

        version = result.get("latest_version", "?")
        url = result.get("download_url", "")
        
        _pending_update.update({
            "available": True,
            "version": version,
            "download_url": url,
            "notes": result.get("notes", "")
        })

        if ui:
            ui.write_log(f"Kree: New version v{version} detected.")
            safe_version = json.dumps(version)
            ui._eval(f"try{{ showToast('Kree v' + {safe_version} + ' update detected...', '#3b82f6'); }}catch(e){{}}")

        if auto_download and url:
            if ui:
                ui._eval("try{ showToast('Downloading update in background...', '#8b5cf6'); }catch(e){}")
            
            downloaded = download_update()
            path = downloaded.get("download_path", "")
            if path:
                _pending_update["downloaded_path"] = path
                _pending_update["is_ready"] = True
                if ui:
                    ui.write_log(f"Kree: v{version} is ready to install.")
                    ui._eval(f"try{{ showToast('Kree v' + {safe_version} + ' is ready. It will be applied on restart.', '#00dc82'); }}catch(e){{}}")
                    if speak_fn:
                        speak_fn(f"Update version {version} has been downloaded and is ready to apply on restart.")

    threading.Thread(target=_check, daemon=True).start()


# ── Global State ─────────────────────────────────────────────────────────────
_pending_update = {
    "available": False,
    "is_ready": False,
    "version": "",
    "download_url": "",
    "downloaded_path": "",
    "notes": "",
}


def get_pending_update() -> dict:
    return dict(_pending_update)


def install_pending_update() -> bool:
    """Legacy manual trigger for the pending update."""
    if _pending_update.get("is_ready"):
        return run_installer_and_exit()
    if _pending_update.get("available"):
        return download_and_install(_pending_update["download_url"])
    return False
