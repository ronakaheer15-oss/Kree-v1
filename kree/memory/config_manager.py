import json


from kree.core.runtime import CONFIG_DIR
CONFIG_FILE = CONFIG_DIR / "api_keys.json"
AUDIO_CONFIG_FILE = CONFIG_DIR / "audio_settings.json"
TELEMETRY_CONFIG_FILE = CONFIG_DIR / "telemetry_settings.json"
EMAIL_CONFIG_FILE = CONFIG_DIR / "email_settings.json"


DEFAULT_AUDIO_SETTINGS = {
    "input_device_index": None,
    "vad_threshold_rising": 220,
    "vad_threshold_falling": 160,
    "partial_confidence_min": 0.7,
    "partial_flush_seconds": 2.0,
    "tool_gate_window_seconds": 4.0,
    "mic_enabled": True,
    "auto_face_id": False,
    "disable_lock_screen": False,
    "kree_voice": "Kore",
    "welcome_voice_enabled": True,
    "ptt_silence_timeout_seconds": 3.0,
}


DEFAULT_TELEMETRY_SETTINGS = {
    "enabled": True,
    "log_file": "logs/kree_events.log",
    "max_bytes": 1048576,
    "backup_count": 5,
    "level": "INFO",
}


DEFAULT_EMAIL_SETTINGS = {
    "USE_MOCK_EMAIL": True,
    "email_address": "",
    "app_password": "",
    "imap_server": "imap.gmail.com",
    "smtp_server": "smtp.gmail.com"
}


def ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def config_exists() -> bool:
    return CONFIG_FILE.exists()


def save_api_keys(gemini_api_key: str) -> None:
    from kree.core import vault
    vault.save_api_key(CONFIG_FILE, gemini_api_key)


def load_email_settings() -> dict:
    data = dict(DEFAULT_EMAIL_SETTINGS)
    if not EMAIL_CONFIG_FILE.exists():
        return data
    try:
        raw = json.loads(EMAIL_CONFIG_FILE.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            data.update(raw)
    except Exception as e:
        print(f"❌ Failed to load email_settings.json: {e}")
    return data


def save_email_settings(settings: dict) -> None:
    ensure_config_dir()
    EMAIL_CONFIG_FILE.write_text(
        json.dumps(settings, indent=2),
        encoding="utf-8"
    )


def load_api_keys() -> dict:
    from kree.core import vault
    key = vault.load_api_key(CONFIG_FILE)
    if key:
        return {"gemini_api_key": key}
    return {}


def get_gemini_key() -> str | None:
    return load_api_keys().get("gemini_api_key")


def is_configured() -> bool:
    key = get_gemini_key()
    return bool(key and len(key) > 15)


def load_audio_settings() -> dict:
    data = dict(DEFAULT_AUDIO_SETTINGS)
    if not AUDIO_CONFIG_FILE.exists():
        return data
    try:
        raw = json.loads(AUDIO_CONFIG_FILE.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            data.update(raw)
    except Exception as e:
        print(f"❌ Failed to load audio_settings.json: {e}")
    return data


def save_audio_settings(settings: dict) -> None:
    ensure_config_dir()
    current = load_audio_settings()
    if isinstance(settings, dict):
        current.update(settings)
    AUDIO_CONFIG_FILE.write_text(
        json.dumps(current, indent=2),
        encoding="utf-8",
    )


def load_telemetry_settings() -> dict:
    data = dict(DEFAULT_TELEMETRY_SETTINGS)
    if not TELEMETRY_CONFIG_FILE.exists():
        return data
    try:
        raw = json.loads(TELEMETRY_CONFIG_FILE.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            data.update(raw)
    except Exception as e:
        print(f"❌ Failed to load telemetry_settings.json: {e}")
    return data


def save_telemetry_settings(settings: dict) -> None:
    ensure_config_dir()
    current = load_telemetry_settings()
    if isinstance(settings, dict):
        current.update(settings)
    TELEMETRY_CONFIG_FILE.write_text(
        json.dumps(current, indent=2),
        encoding="utf-8",
    )