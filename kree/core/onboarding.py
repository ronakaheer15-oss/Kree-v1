import platform
import os
import shutil

def is_first_launch() -> bool:
    import kree.core.user_profile as up
    profile = up.get_user_profile()
    return not bool(profile.get("name"))

def find_chrome_profile() -> str:
    # Auto-detect profile directory
    sys_os = platform.system()
    base_path = ""
    
    if sys_os == "Windows":
        base_path = os.path.expanduser(r"~\AppData\Local\Google\Chrome\User Data")
    elif sys_os == "Darwin":
        base_path = os.path.expanduser("~/Library/Application Support/Google/Chrome")
    else:
        base_path = os.path.expanduser("~/.config/google-chrome")
        
    if not os.path.exists(base_path):
        return "Default"
        
    # Pick the most recently modified profile folder or one matching the user's name
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
                            name = data.get('profile', {}).get('name', 'Unknown')
                            profiles.append((folder, name, os.path.getmtime(prefs)))
                    except Exception: pass
    except Exception: pass
    
    if not profiles:
        return "Default"
        
    # Sort by recent usage
    profiles.sort(key=lambda x: x[2], reverse=True)
    return profiles[0][0] # Return the folder name of the most recently used profile

async def first_time_setup(live_session):
    print("[JARVIS] 🌱 First Time Setup Sequence Initiated")
    try:
        await live_session.send(
            input="[SYSTEM OVERRIDE] We are initiating first time setup. Introduce yourself warmly as Kree, explain that you need to get to know them, and ask them for their name."
        )
        
        # Determine background info automatically
        sys_os = platform.system()
        chrome_exe = shutil.which("chrome") or shutil.which("google-chrome") or "Chrome execution not found"
        chrome_prof = find_chrome_profile()
        
        import kree.core.user_profile as up
        up.update_user_profile({
            "os": sys_os,
            "browser": chrome_exe,
            "browser_profile": chrome_prof
        })
        
    except Exception as e:
        print(f"[JARVIS] ⚠️ Onboarding fail: {e}")
