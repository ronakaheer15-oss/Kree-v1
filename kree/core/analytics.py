"""
Kree AI — Analytics Engine (PostHog)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Anonymous, opt-in usage analytics via PostHog.
- Generates anonymous UUID per install (stored in config/user_id.txt)
- Respects user opt-in/opt-out (stored in audio_settings.json)
- Tracks: wake triggers, commands, errors, feature usage, sessions
- Includes OS, version, platform metadata in every event
- Gracefully no-ops if key is missing or user opted out
"""

import sys
import json
import uuid
import platform
import threading

# ── Resolve paths ─────────────────────────────────────────────────────────────
from kree._paths import PROJECT_ROOT
BASE_DIR = PROJECT_ROOT
SERVICE_KEYS_PATH = BASE_DIR / "config" / "service_keys.json"
USER_ID_PATH = BASE_DIR / "config" / "user_id.txt"
AUDIO_SETTINGS_PATH = BASE_DIR / "config" / "audio_settings.json"

# ── Lazy PostHog client ───────────────────────────────────────────────────────
_posthog_client = None
_initialized = False


def _load_service_keys() -> dict:
    try:
        with open(SERVICE_KEYS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _get_kree_version() -> str:
    return _load_service_keys().get("kree_version", "1.0.0")


def get_user_id() -> str:
    """Get or create anonymous user ID (UUID v4)."""
    try:
        if USER_ID_PATH.exists():
            return USER_ID_PATH.read_text(encoding="utf-8").strip()
    except Exception:
        pass

    user_id = str(uuid.uuid4())
    try:
        USER_ID_PATH.parent.mkdir(parents=True, exist_ok=True)
        USER_ID_PATH.write_text(user_id, encoding="utf-8")
    except Exception:
        pass
    return user_id


def analytics_enabled() -> bool:
    """Check if user opted in to analytics."""
    try:
        with open(AUDIO_SETTINGS_PATH, "r", encoding="utf-8") as f:
            settings = json.load(f)
        return settings.get("analytics_enabled", False)
    except Exception:
        return False


def set_analytics_enabled(enabled: bool):
    """Set analytics opt-in state."""
    try:
        settings = {}
        if AUDIO_SETTINGS_PATH.exists():
            with open(AUDIO_SETTINGS_PATH, "r", encoding="utf-8") as f:
                settings = json.load(f)
        settings["analytics_enabled"] = enabled
        with open(AUDIO_SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        print(f"[KREE ANALYTICS] Failed to save preference: {e}")


def _init_posthog():
    """Lazy-init PostHog client. Only called once."""
    global _posthog_client, _initialized
    if _initialized:
        return _posthog_client
    _initialized = True

    keys = _load_service_keys()
    api_key = keys.get("posthog_api_key", "")
    if not api_key:
        print("[KREE ANALYTICS] No PostHog key configured. Analytics disabled.")
        return None

    try:
        from posthog import Posthog
        _posthog_client = Posthog(
            project_api_key=api_key,
            host="https://app.posthog.com"
        )
        print("[KREE ANALYTICS] PostHog initialized.")
        return _posthog_client
    except ImportError:
        print("[KREE ANALYTICS] PostHog SDK not installed. Analytics disabled.")
        return None
    except Exception as e:
        print(f"[KREE ANALYTICS] PostHog init failed: {e}")
        return None


def track(event: str, properties: dict = None):
    """
    Track an analytics event. Non-blocking, fire-and-forget.
    Gracefully no-ops if analytics disabled or PostHog unavailable.
    
    Usage:
        track("wake_word_triggered")
        track("command_executed", {"command_type": "open_app", "app": "chrome"})
        track("error", {"error_type": "tts_failed", "message": "..."})
    """
    if not analytics_enabled():
        return

    def _send():
        try:
            client = _init_posthog()
            if not client:
                return

            merged = {
                "os": platform.system(),
                "os_version": platform.version(),
                "kree_version": _get_kree_version(),
                "python_version": platform.python_version(),
                "machine": platform.machine(),
                **(properties or {}),
            }

            client.capture(
                distinct_id=get_user_id(),
                event=event,
                properties=merged,
            )
        except Exception as e:
            # Analytics must NEVER crash the main app
            print(f"[KREE ANALYTICS] Track failed (non-fatal): {e}")

    threading.Thread(target=_send, daemon=True).start()


def track_session_start():
    """Track a new Kree session starting."""
    track("session_start", {
        "frozen": getattr(sys, "frozen", False),
    })


def track_wake(whisper: bool = False):
    """Track a wake word trigger."""
    track("wake_word_triggered", {"whisper": whisper})


def track_command(command_type: str, details: str = ""):
    """Track a command execution."""
    track("command_executed", {
        "command_type": command_type,
        "details": details[:200],
    })


def track_error(error_type: str, message: str = ""):
    """Track an error event."""
    track("error", {
        "error_type": error_type,
        "message": message[:500],
    })


def shutdown():
    """Flush remaining events on exit."""
    try:
        if _posthog_client:
            _posthog_client.flush()
    except Exception:
        pass
