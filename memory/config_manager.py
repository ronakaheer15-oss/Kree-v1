import json
import sys
from pathlib import Path


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR    = get_base_dir()
CONFIG_DIR  = BASE_DIR / "config"
CONFIG_FILE = CONFIG_DIR / "api_keys.json"
AUDIO_CONFIG_FILE = CONFIG_DIR / "audio_settings.json"
TELEMETRY_CONFIG_FILE = CONFIG_DIR / "telemetry_settings.json"


DEFAULT_AUDIO_SETTINGS = {
    "input_device_index": None,
    "vad_threshold_rising": 220,
    "vad_threshold_falling": 160,
    "partial_confidence_min": 0.7,
    "partial_flush_seconds": 2.0,
    "tool_gate_window_seconds": 4.0,
    "mic_enabled": True,
}


DEFAULT_TELEMETRY_SETTINGS = {
    "enabled": True,
    "log_file": "logs/kree_events.log",
    "max_bytes": 1048576,
    "backup_count": 5,
    "level": "INFO",
}


def ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def config_exists() -> bool:
    return CONFIG_FILE.exists()


def save_api_keys(gemini_api_key: str) -> None:
    ensure_config_dir()

    data: dict = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}

    data["gemini_api_key"] = gemini_api_key.strip()

    CONFIG_FILE.write_text(
        json.dumps(data, indent=2),
        encoding="utf-8"
    )


def load_api_keys() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"❌ Failed to load api_keys.json: {e}")
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