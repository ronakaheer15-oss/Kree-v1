import json
import datetime

from kree._paths import PROJECT_ROOT
BASE_DIR = PROJECT_ROOT
MEMORY_FILE = BASE_DIR / "memory" / "kree_memory.json"
MAX_TURNS = 100

def load_memory() -> list:
    if not MEMORY_FILE.exists():
        return []
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_turn(user_text: str, kree_text: str, tools=None):
    if not user_text and not kree_text: return
    memory = load_memory()
    memory.append({
        "timestamp": str(datetime.datetime.now()),
        "user": user_text,
        "kree": kree_text,
        "tools": tools or []
    })
    
    # Cap size
    memory = memory[-MAX_TURNS:]
    
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2, ensure_ascii=False)

def detect_patterns(memory: list) -> str:
    """Analyze chat history to detect usage patterns to organically suggest actions."""
    if not memory: return ""
    
    # Example pattern detection: frequently opened apps
    opens = []
    for t in memory:
        u_text = str(t.get("user", "")).lower()
        if "open" in u_text or "launch" in u_text:
            opens.append(u_text)
            
    if opens:
        # Just a basic signature for now
        if any("chrome" in o for o in opens):
            return "User frequently opens Chrome at the start of sessions."
        if any("spotify" in o for o in opens):
            return "User frequently requests Spotify."
    return ""

def get_memory_summary() -> str:
    memory = load_memory()
    if not memory: return "No prior conversational history."
    
    recent = memory[-10:]
    lines = []
    for t in recent:
        lines.append(f"User: {t.get('user', '')}")
        lines.append(f"Kree: {t.get('kree', '')}")
        if t.get('tools'):
            lines.append(f"Tools Executed: {', '.join(t['tools'])}")
        lines.append("---")
        
    summary = "\n".join(lines)
    
    # Inject pattern intelligence
    patterns = detect_patterns(memory)
    intel = f"\n[BEHAVIORAL PATTERNS DETECTED]\n{patterns}\n" if patterns else ""
    
    return f"[RECENT CONVERSATION HISTORY]\n{summary}{intel}"
