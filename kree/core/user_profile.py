import json

from kree.core.runtime import CONFIG_DIR
USER_PROFILE_FILE = CONFIG_DIR / "user_profile.json"

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

def discover_chrome_profiles() -> list[dict]:
    import os
    import platform
    sys_os = platform.system()
    base_path = ""
    if sys_os == "Windows":
        base_path = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")
    elif sys_os == "Darwin":
        base_path = os.path.expanduser("~/Library/Application Support/Google/Chrome")
    else:
        base_path = os.path.expanduser("~/.config/google-chrome")
        
    if not os.path.exists(base_path):
        return []
        
    profiles = []
    try:
        import json
        for folder in os.listdir(base_path):
            if folder.startswith("Profile") or folder == "Default":
                prefs = os.path.join(base_path, folder, "Preferences")
                if os.path.exists(prefs):
                    try:
                        with open(prefs, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            name = data.get('profile', {}).get('name', '')
                            if not name:
                                name = folder
                            profiles.append({
                                "folder": folder,
                                "name": name,
                                "mtime": os.path.getmtime(prefs)
                            })
                    except Exception:
                        pass
    except Exception:
        pass
    # Sort by mtime descending
    profiles.sort(key=lambda x: x["mtime"], reverse=True)
    return profiles

