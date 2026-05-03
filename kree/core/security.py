import re
from pathlib import Path

# DESTRUCTIVE COMMANDS that require EXPLICIT User Confirmation
DESTRUCTIVE_PATTERNS = [
    r"\brm\s+-rf\b", r"\brmdir\s+/s\b", r"\bdel\s+/[fqs]",
    r"\bformat\b", r"\bdiskpart\b", r"\bfdisk\b",
    r"\bshutdown\b", r"\brestart-computer\b",
    r"\breg\s+delete\b", r"\bbcdedit\b",
]
_DESTRUCTIVE_RE = re.compile("|".join(DESTRUCTIVE_PATTERNS), re.IGNORECASE)

# SANDBOX: The AI is only allowed to modify files in this directory by default
WORKSPACE_NAME = "Kree_Workspace"

def get_workspace_path() -> Path:
    return Path.home() / "Documents" / WORKSPACE_NAME

def is_command_destructive(command: str) -> bool:
    """Returns True if the command matches a high-risk destructive pattern."""
    return bool(_DESTRUCTIVE_RE.search(command))

def is_path_safe(path: str | Path, allow_read_only: bool = True) -> bool:
    """
    Verifies if a file path is within the allowed Kree_Workspace sandbox.
    If allow_read_only is True, allows reading from anywhere but writing only to sandbox.
    """
    try:
        p = Path(path).resolve()
        workspace = get_workspace_path().resolve()
        
        # Ensure workspace exists
        if not workspace.exists():
            workspace.mkdir(parents=True, exist_ok=True)
            
        # Is the path inside the workspace?
        is_inside = str(p).startswith(str(workspace))
        
        # For Government-Grade security, we start by enforcing STRICT write access
        return is_inside
    except Exception:
        return False

def scrub_pii(text: str) -> str:
    """Masks sensitive data like Credit Cards, SSNs, and common password patterns."""
    if not isinstance(text, str):
        return text
        
    # Credit Cards (Simple pattern)
    text = re.sub(r"\b(?:\d[ -]*?){13,16}\b", "****-****-****-****", text)
    
    # SSN (USA format)
    text = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "***-**-****", text)
    
    # Email (Optional, but good for privacy)
    # text = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL]", text)
    
    # Potential Password patterns (Labels like "password: XYZ" or "pass: XYZ")
    text = re.sub(r"(?i)(password|pass|secret|key|token)[:=\s]+(\S+)", r"\1: ********", text)
    
    return text
