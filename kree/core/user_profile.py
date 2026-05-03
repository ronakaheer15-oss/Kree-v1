import json
import os
import sys
from pathlib import Path

def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR = get_base_dir()
USER_PROFILE_FILE = BASE_DIR / "core" / "user_profile.json"

def get_user_profile() -> dict:
    if not USER_PROFILE_FILE.exists():
        return {}
    try:
        with open(USER_PROFILE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def update_user_profile(updates: dict):
    profile = get_user_profile()
    profile.update(updates)
    
    USER_PROFILE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(USER_PROFILE_FILE, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=4, ensure_ascii=False)
