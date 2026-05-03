import json

from kree._paths import PROJECT_ROOT
BASE_DIR = PROJECT_ROOT
CONFIG_FILE = BASE_DIR / "core" / "automations_config.json"

DEFAULT_CONFIG = {
    "chains": {
        "work session": [
            {"narration": "Opening your workspace, sir.", "action": "open_app", "target": "code"},
            {"narration": "Pulling up Notion.", "action": "browser_control", "url": "https://notion.so"},
            {"narration": "Starting focus music.", "action": "open_app", "target": "spotify"}
        ],
        "gaming session": [
            {"narration": "Launching Discord.", "action": "open_app", "target": "discord"},
            {"narration": "Opening Steam.", "action": "open_app", "target": "steam"},
            {"narration": "Game mode active.", "action": "computer_settings", "setting": "dnd"}
        ]
    },
    "trigger_automations": {
        "code": "You opened Visual Studio Code. Shall I load your last project?",
        "chrome": "Chrome is open. Want me to check your calendar?",
        "spotify": "Resuming your last playlist."
    },
    "scheduled_tasks": [
        {"time": "09:00", "narration": "Good morning sir, here is your daily briefing.", "macro": "briefing"},
        {"time": "23:00", "narration": "Wrapping up sir, doing a system save.", "macro": "shutdown"}
    ]
}

def load_automations() -> dict:
    if not CONFIG_FILE.exists():
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return DEFAULT_CONFIG

def get_chain(chain_name: str) -> list:
    cfg = load_automations()
    return cfg.get("chains", {}).get(chain_name, [])

def get_app_trigger(app_name: str) -> str:
    cfg = load_automations()
    # Extremely basic partial match
    for k, v in cfg.get("trigger_automations", {}).items():
        if k.lower() in app_name.lower():
            return v
    return ""
