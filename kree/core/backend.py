"""
Kree AI — Supabase Backend Client
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Cloud backend for:
  - Syncing user preferences across devices
  - Storing custom automation chains
  - Logging crash reports
  - Pulling latest release info (backup to GitHub API)

Gracefully no-ops if Supabase keys are missing or unavailable.

Tables required in Supabase:
  - user_preferences (user_id uuid, preferences jsonb, updated_at timestamp)
  - automations (user_id uuid, name text, steps jsonb, created_at timestamp)
  - error_logs (user_id text, error_type text, error_message text, kree_version text, os text, created_at timestamp)
  - releases (version text, download_url text, release_notes text, created_at timestamp, is_stable boolean)
"""

import os
import sys
import json
import platform
import threading
from pathlib import Path

# ── Resolve paths ─────────────────────────────────────────────────────────────
from kree._paths import PROJECT_ROOT
BASE_DIR = PROJECT_ROOT
SERVICE_KEYS_PATH = BASE_DIR / "config" / "service_keys.json"

# ── Lazy Supabase client ──────────────────────────────────────────────────────
_supabase_client = None
_initialized = False


def _load_service_keys() -> dict:
    try:
        with open(SERVICE_KEYS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _get_kree_version() -> str:
    return _load_service_keys().get("kree_version", "1.0.0")


def _init_supabase():
    """Lazy-init Supabase client. Only called once."""
    global _supabase_client, _initialized
    if _initialized:
        return _supabase_client
    _initialized = True

    keys = _load_service_keys()
    url = keys.get("supabase_url", "")
    anon_key = keys.get("supabase_anon_key", "")

    if not url or not anon_key:
        print("[KREE BACKEND] No Supabase keys configured. Cloud features disabled.")
        return None

    try:
        from supabase import create_client
        _supabase_client = create_client(url, anon_key)
        print("[KREE BACKEND] Supabase client initialized.")
        return _supabase_client
    except ImportError:
        print("[KREE BACKEND] Supabase SDK not installed. Cloud features disabled.")
        return None
    except Exception as e:
        print(f"[KREE BACKEND] Supabase init failed: {e}")
        return None


def _get_user_id() -> str:
    """Get the anonymous user ID from analytics module."""
    try:
        from kree.core.analytics import get_user_id
        return get_user_id()
    except Exception:
        return "unknown"


# ── Preferences Sync ──────────────────────────────────────────────────────────

def sync_preferences(prefs: dict):
    """Sync user preferences to cloud. Non-blocking."""
    def _sync():
        try:
            client = _init_supabase()
            if not client:
                return
            client.table("user_preferences").upsert({
                "user_id": _get_user_id(),
                "preferences": prefs,
            }).execute()
        except Exception as e:
            print(f"[KREE BACKEND] Preference sync failed (non-fatal): {e}")

    threading.Thread(target=_sync, daemon=True).start()


def load_cloud_preferences() -> dict | None:
    """Load preferences from cloud. Returns None if unavailable."""
    try:
        client = _init_supabase()
        if not client:
            return None
        result = client.table("user_preferences") \
            .select("preferences") \
            .eq("user_id", _get_user_id()) \
            .limit(1) \
            .execute()
        if result.data:
            return result.data[0].get("preferences", {})
    except Exception as e:
        print(f"[KREE BACKEND] Preference load failed (non-fatal): {e}")
    return None


# ── Automations ───────────────────────────────────────────────────────────────

def save_automation(chain_name: str, steps: list):
    """Save a custom automation chain to cloud. Non-blocking."""
    def _save():
        try:
            client = _init_supabase()
            if not client:
                return
            client.table("automations").upsert({
                "user_id": _get_user_id(),
                "name": chain_name,
                "steps": steps,
            }).execute()
        except Exception as e:
            print(f"[KREE BACKEND] Automation save failed (non-fatal): {e}")

    threading.Thread(target=_save, daemon=True).start()


def load_automations() -> list:
    """Load custom automations from cloud."""
    try:
        client = _init_supabase()
        if not client:
            return []
        result = client.table("automations") \
            .select("*") \
            .eq("user_id", _get_user_id()) \
            .order("created_at", desc=True) \
            .execute()
        return result.data or []
    except Exception as e:
        print(f"[KREE BACKEND] Automation load failed (non-fatal): {e}")
        return []


# ── Crash Reports ─────────────────────────────────────────────────────────────

def log_crash(error_type: str, error_details: str = ""):
    """
    Log a crash to Supabase. Non-blocking, fire-and-forget.
    Called from the global crash handler in main.py.
    """
    def _log():
        try:
            client = _init_supabase()
            if not client:
                return
            client.table("error_logs").insert({
                "user_id": _get_user_id(),
                "error_type": error_type[:200],
                "error_message": error_details[:2000],
                "kree_version": _get_kree_version(),
                "os": f"{platform.system()} {platform.version()}",
            }).execute()
            print("[KREE BACKEND] Crash report logged to cloud.")
        except Exception as e:
            print(f"[KREE BACKEND] Crash log failed (non-fatal): {e}")

    threading.Thread(target=_log, daemon=True).start()


# ── Release Info (Backup) ─────────────────────────────────────────────────────

def get_latest_release() -> dict | None:
    """Get latest release info from Supabase (backup to GitHub API)."""
    try:
        client = _init_supabase()
        if not client:
            return None
        result = client.table("releases") \
            .select("*") \
            .eq("is_stable", True) \
            .order("created_at", desc=True) \
            .limit(1) \
            .execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"[KREE BACKEND] Release check failed (non-fatal): {e}")
        return None
