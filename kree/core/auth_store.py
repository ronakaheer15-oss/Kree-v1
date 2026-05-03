from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kree.memory.config_manager import CONFIG_DIR, ensure_config_dir

from core import vault


DEFAULT_BOOTSTRAP_PIN = "143211"
AUTH_FILE = CONFIG_DIR / "user_auth.json"
USER_SECRETS_DIR = CONFIG_DIR / "user_secrets"
LEGACY_API_FILE = CONFIG_DIR / "api_keys.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _normalize_identifier(value: str | None) -> str:
    return (value or "").strip().lower()


def _default_state() -> dict[str, Any]:
    return {
        "version": 1,
        "active_user_id": None,
        "users": [],
    }


def _ensure_storage() -> None:
    ensure_config_dir()
    USER_SECRETS_DIR.mkdir(parents=True, exist_ok=True)


def _load_state() -> dict[str, Any]:
    if not AUTH_FILE.exists():
        return _default_state()
    try:
        raw = json.loads(AUTH_FILE.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            state = _default_state()
            state.update(raw)
            users = state.get("users")
            if not isinstance(users, list):
                state["users"] = []
            return state
    except Exception:
        pass
    return _default_state()


def _save_state(state: dict[str, Any]) -> None:
    _ensure_storage()
    AUTH_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _new_salt() -> str:
    return secrets.token_hex(16)


def _hash_value(value: str, salt: str) -> str:
    payload = f"{salt}::{value}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _public_user(user: dict[str, Any] | None) -> dict[str, Any] | None:
    if not user:
        return None
    return {
        "user_id": user.get("user_id"),
        "handle": user.get("handle", ""),
        "email": user.get("email", ""),
        "display_name": user.get("display_name", ""),
        "pin_requires_change": bool(user.get("pin_requires_change", False)),
        "has_api_key": user_has_api_key(str(user.get("user_id", ""))),
        "last_login_at": user.get("last_login_at"),
        "created_at": user.get("created_at"),
    }


def _find_user_index(state: dict[str, Any], identifier: str) -> int:
    normalized = _normalize_identifier(identifier)
    for index, user in enumerate(state.get("users", [])):
        if not isinstance(user, dict):
            continue
        if _normalize_identifier(user.get("handle")) == normalized:
            return index
        if _normalize_identifier(user.get("email")) == normalized:
            return index
        if _normalize_identifier(user.get("user_id")) == normalized:
            return index
    return -1


def _get_user(state: dict[str, Any], identifier: str) -> dict[str, Any] | None:
    index = _find_user_index(state, identifier)
    if index < 0:
        return None
    user = state.get("users", [])[index]
    return user if isinstance(user, dict) else None


def _get_user_by_id(state: dict[str, Any], user_id: str) -> dict[str, Any] | None:
    return _get_user(state, user_id)


def _current_user(state: dict[str, Any]) -> dict[str, Any] | None:
    active_user_id = state.get("active_user_id")
    if not active_user_id:
        return None
    return _get_user_by_id(state, str(active_user_id))


def get_auth_file_path() -> Path:
    return AUTH_FILE


def get_user_secret_path(user_id: str) -> Path:
    _ensure_storage()
    return USER_SECRETS_DIR / f"{user_id}.api"


def list_users() -> list[dict[str, Any]]:
    state = _load_state()
    return [user for user in (_public_user(item) for item in state.get("users", [])) if user]


def has_users() -> bool:
    state = _load_state()
    return bool(state.get("users"))


def get_active_user() -> dict[str, Any] | None:
    state = _load_state()
    return _public_user(_current_user(state))


def set_active_user(user_id: str | None) -> dict[str, Any]:
    state = _load_state()
    state["active_user_id"] = user_id
    _save_state(state)
    return get_auth_state()


def get_auth_state() -> dict[str, Any]:
    state = _load_state()
    current = _current_user(state)
    active_user = _public_user(current)
    return {
        "has_users": bool(state.get("users")),
        "users": list_users(),
        "active_user_id": state.get("active_user_id"),
        "active_user": active_user,
        "bootstrap_pin": DEFAULT_BOOTSTRAP_PIN,
        "needs_sign_in": not bool(active_user),
        "needs_pin_setup": bool(active_user and active_user.get("pin_requires_change")),
        "needs_api_key": bool(active_user and not active_user.get("has_api_key")),
    }


def create_user(handle: str, password: str, email: str = "", display_name: str = "") -> dict[str, Any]:
    handle_clean = (handle or "").strip()
    password_clean = password or ""
    if not handle_clean:
        raise ValueError("Handle is required.")
    if len(password_clean) < 6:
        raise ValueError("Password must be at least 6 characters.")

    state = _load_state()
    if _find_user_index(state, handle_clean) >= 0:
        raise ValueError("That handle is already registered.")
    if email and _find_user_index(state, email) >= 0:
        raise ValueError("That email is already registered.")

    user_id = uuid.uuid4().hex
    password_salt = _new_salt()
    pin_salt = _new_salt()
    user = {
        "user_id": user_id,
        "handle": handle_clean,
        "email": (email or "").strip(),
        "display_name": (display_name or handle_clean).strip(),
        "password_salt": password_salt,
        "password_hash": _hash_value(password_clean, password_salt),
        "pin_salt": pin_salt,
        "pin_hash": _hash_value(DEFAULT_BOOTSTRAP_PIN, pin_salt),
        "pin_requires_change": True,
        "created_at": _now(),
        "last_login_at": _now(),
        "api_key_path": str(get_user_secret_path(user_id)),
    }
    state.setdefault("users", []).append(user)
    state["active_user_id"] = user_id
    _save_state(state)
    return {
        "ok": True,
        "message": "Account created.",
        "next_stage": "pin_setup",
        "user": _public_user(user),
        "state": get_auth_state(),
    }


def sign_in_user(identifier: str, password: str) -> dict[str, Any]:
    state = _load_state()
    user = _get_user(state, identifier)
    if not user:
        return {"ok": False, "message": "Account not found."}

    password_salt = str(user.get("password_salt", ""))
    saved_hash = str(user.get("password_hash", ""))
    if not password_salt or _hash_value(password or "", password_salt) != saved_hash:
        return {"ok": False, "message": "Incorrect password."}

    user["last_login_at"] = _now()
    state["active_user_id"] = user.get("user_id")
    _save_state(state)

    public_user = _public_user(user)
    needs_api_key = bool(public_user and not public_user.get("has_api_key"))
    next_stage = "pin_setup" if bool(user.get("pin_requires_change", False)) else "pin_verify"

    return {
        "ok": True,
        "message": "Signed in.",
        "next_stage": next_stage,
        "needs_api_key": needs_api_key,
        "user": public_user,
        "state": get_auth_state(),
    }


def verify_user_password(identifier: str, password: str) -> bool:
    return bool(sign_in_user(identifier, password).get("ok"))


def set_user_pin(user_id: str, pin: str) -> dict[str, Any]:
    pin_clean = (pin or "").strip()
    if not pin_clean.isdigit() or len(pin_clean) != 6:
        raise ValueError("PIN must be exactly 6 digits.")

    state = _load_state()
    user = _get_user_by_id(state, user_id)
    if not user:
        raise ValueError("Active user not found.")

    pin_salt = _new_salt()
    user["pin_salt"] = pin_salt
    user["pin_hash"] = _hash_value(pin_clean, pin_salt)
    user["pin_requires_change"] = False
    user["updated_at"] = _now()
    _save_state(state)

    active = _public_user(user)
    return {
        "ok": True,
        "message": "PIN saved.",
        "next_stage": "api_setup" if not active.get("has_api_key") else "complete",
        "user": active,
        "state": get_auth_state(),
    }


def verify_user_pin(user_id: str, pin: str) -> dict[str, Any]:
    pin_clean = (pin or "").strip()
    state = _load_state()
    user = _get_user_by_id(state, user_id)
    if not user:
        return {"ok": False, "message": "Active user not found."}

    pin_salt = str(user.get("pin_salt", ""))
    pin_hash = str(user.get("pin_hash", ""))
    if not pin_salt or _hash_value(pin_clean, pin_salt) != pin_hash:
        return {"ok": False, "message": "Invalid PIN."}

    active = _public_user(user)
    next_stage = "api_setup" if not active.get("has_api_key") else "complete"
    return {
        "ok": True,
        "message": "PIN verified.",
        "next_stage": next_stage,
        "requires_change": bool(user.get("pin_requires_change", False)),
        "user": active,
        "state": get_auth_state(),
    }


def user_has_api_key(user_id: str) -> bool:
    api_path = get_user_secret_path(user_id)
    if api_path.exists() and bool(vault.load_api_key(api_path)):
        return True
    if LEGACY_API_FILE.exists() and bool(vault.load_api_key(LEGACY_API_FILE)):
        return True
    return False


def load_user_api_key(user_id: str) -> str:
    api_path = get_user_secret_path(user_id)
    key = vault.load_api_key(api_path)
    if key:
        return key
    return vault.load_api_key(LEGACY_API_FILE)


def save_user_api_key(user_id: str, api_key: str) -> dict[str, Any]:
    state = _load_state()
    user = _get_user_by_id(state, user_id)
    if not user:
        raise ValueError("Active user not found.")

    api_path = get_user_secret_path(user_id)
    vault.save_api_key(api_path, api_key)
    vault.save_api_key(LEGACY_API_FILE, api_key)
    user["updated_at"] = _now()
    _save_state(state)
    return {
        "ok": True,
        "message": "API key saved.",
        "next_stage": "complete",
        "user": _public_user(user),
        "state": get_auth_state(),
    }


def get_user_record(user_id: str) -> dict[str, Any] | None:
    state = _load_state()
    return _public_user(_get_user_by_id(state, user_id))
