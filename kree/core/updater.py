"""
Kree AI — Auto-Update Engine
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Checks GitHub Releases API on startup for newer versions.
If found, announces via TTS, downloads installer, and runs it silently.

Flow:
  boot → background check (1s) → if new version:
    → Kree announces "Update available"
    → User confirms
    → Download in background → silent install → restart
"""

import os
import json
import threading

# ── Resolve paths ─────────────────────────────────────────────────────────────
from kree._paths import PROJECT_ROOT
BASE_DIR = PROJECT_ROOT
SERVICE_KEYS_PATH = BASE_DIR / "config" / "service_keys.json"


def _load_service_keys() -> dict:
    try:
        with open(SERVICE_KEYS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def get_current_version() -> str:
    return _load_service_keys().get("kree_version", "1.0.0")


def get_github_repo() -> str:
    return _load_service_keys().get("github_repo", "YOUR_USERNAME/kree")


def check_for_update() -> dict:
    """
    Checks GitHub Releases API for the latest release.
    Returns dict with 'available', 'version', 'download_url', 'notes'.
    Non-blocking safe — never raises.
    """
    try:
        import urllib.request
        import urllib.error

        repo = get_github_repo()
        if not repo or repo == "YOUR_USERNAME/kree":
            return {"available": False, "reason": "repo_not_configured"}

        url = f"https://api.github.com/repos/{repo}/releases/latest"
        req = urllib.request.Request(url, headers={"User-Agent": "KreeAI/1.0"})
        
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        latest_version = data.get("tag_name", "").lstrip("v")
        current = get_current_version()

        if not latest_version:
            return {"available": False}

        # Simple semver comparison
        if _version_gt(latest_version, current):
            # Find .exe asset
            download_url = ""
            for asset in data.get("assets", []):
                if asset["name"].lower().endswith(".exe"):
                    download_url = asset["browser_download_url"]
                    break

            return {
                "available": True,
                "version": latest_version,
                "download_url": download_url,
                "notes": data.get("body", ""),
            }

        return {"available": False}

    except Exception as e:
        print(f"[KREE UPDATE] Check failed (non-fatal): {e}")
        return {"available": False, "error": str(e)}


def _version_gt(a: str, b: str) -> bool:
    """True if version a > version b (semver-ish)."""
    try:
        def parts(v):
            return [int(x) for x in v.split(".")]
        return parts(a) > parts(b)
    except Exception:
        return a > b


def download_only(download_url: str) -> str:
    """
    Downloads the installer to %TEMP% without running it.
    Returns the absolute path to the downloaded installer.
    """
    if not download_url:
        return ""

    try:
        import urllib.request
        installer_path = os.path.join(os.environ.get("TEMP", "."), "kree_update.exe")
        
        # Cleanup old download if exists
        if os.path.exists(installer_path):
            try: os.remove(installer_path)
            except: pass

        print(f"[KREE UPDATE] Background download starting: {download_url}")
        urllib.request.urlretrieve(download_url, installer_path)
        print(f"[KREE UPDATE] Background download complete: {installer_path}")
        
        _pending_update["downloaded_path"] = installer_path
        _pending_update["is_ready"] = True
        return installer_path
    except Exception as e:
        print(f"[KREE UPDATE] Background download failed: {e}")
        return ""


def run_installer_and_exit(installer_path: str = "") -> bool:
    """
    Executes the installer silently and shuts down the current process.
    """
    path = installer_path or _pending_update.get("downloaded_path", "")
    if not path or not os.path.exists(path):
        return False

    try:
        import subprocess
        print(f"[KREE UPDATE] Launching final installer: {path}")
        subprocess.Popen(
            [path, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/FORCECLOSEAPPLICATIONS"],
            creationflags=0x00000008,  # DETACHED_PROCESS
        )
        # Give it a moment to start
        import time
        time.sleep(1.5)
        os._exit(0)
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
    Non-blocking background update check.
    Now optionally triggers a silent download immediately.
    """
    def _check():
        result = check_for_update()
        if not result.get("available"):
            return

        version = result.get("version", "?")
        url = result.get("download_url", "")
        
        _pending_update.update({
            "available": True,
            "version": version,
            "download_url": url,
            "notes": result.get("notes", "")
        })

        if ui:
            ui.write_log(f"Kree: New version v{version} detected.")
            ui._eval(f"try{{ showToast('Kree v{version} update detected...', '#3b82f6'); }}catch(e){{}}")

        if auto_download and url:
            if ui:
                ui._eval("try{ showToast('Downloading update in background...', '#8b5cf6'); }catch(e){}")
            
            path = download_only(url)
            if path and ui:
                ui.write_log(f"Kree: v{version} is ready to install.")
                ui._eval(f"try{{ showToast('Kree v{version} is ready sir! It will be applied on restart.', '#00dc82'); }}catch(e){{}}")
                if speak_fn:
                    speak_fn(f"Sir, update version {version} has been downloaded and is ready to be applied whenever you restart Kree.")

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
