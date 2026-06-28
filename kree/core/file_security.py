import os
import re
import math
import mimetypes
import hashlib
from enum import IntEnum
from pathlib import Path
from typing import Optional, List, Tuple

class TrustTier(IntEnum):
    USER_LOCAL = 1      # Tier 1: User-selected local files
    KNOWN_TRUSTED = 2   # Tier 2: Known trusted domains
    UNKNOWN_WEB = 3     # Tier 3: Unknown internet sources
    HIGH_RISK = 4       # Tier 4: Executables/scripts, known bad domains


class FileRisk(IntEnum):
    SAFE = 1
    MEDIUM = 2
    HIGH = 3


SAFE_EXTS = {'.txt', '.png', '.jpg', '.jpeg', '.pdf', '.csv', '.json', '.md'}
MEDIUM_EXTS = {'.zip', '.docx', '.xlsx', '.pptx', '.tar', '.gz'}
HIGH_RISK_EXTS = {'.exe', '.bat', '.ps1', '.dll', '.js', '.vbs', '.scr', '.msi', '.cmd', '.sh', '.py'}

BLOCKED_PATHS = [
    Path(os.environ.get("SystemRoot", r"C:\Windows")).resolve(),
    Path(os.environ.get("ProgramFiles", r"C:\Program Files")).resolve(),
    Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")).resolve(),
    Path(os.environ.get("APPDATA", r"C:\Users\Default\AppData\Roaming")).resolve() / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup",
]

def classify_extension(filepath: Path) -> FileRisk:
    ext = filepath.suffix.lower()
    if ext in HIGH_RISK_EXTS:
        return FileRisk.HIGH
    if ext in MEDIUM_EXTS:
        return FileRisk.MEDIUM
    if ext in SAFE_EXTS:
        return FileRisk.SAFE
    return FileRisk.MEDIUM # Default to medium for unknown types


def is_path_safe(target_path: Path, allowed_roots: Optional[List[Path]] = None) -> bool:
    """
    Validates that a path is safe for read/write.
    Checks for path traversal and explicitly blocks sensitive OS directories.
    """
    try:
        resolved = target_path.resolve(strict=False)
    except Exception:
        return False

    # Enforce allowed roots if provided (prevent "upload anything from C:\")
    if allowed_roots:
        is_in_root = any(
            resolved == root or root in resolved.parents
            for root in allowed_roots
        )
        if not is_in_root:
            return False

    # Enforce strict blocklists to prevent persistence/abuse
    for blocked in BLOCKED_PATHS:
        try:
            if resolved == blocked or blocked in resolved.parents:
                return False
        except Exception:
            continue
            
    return True


def get_real_mime_type(filepath: Path) -> str:
    """Gets the actual MIME type of the file, not just by extension."""
    try:
        import magic
        # use python-magic if installed
        mime = magic.from_file(str(filepath), mime=True)
        if mime:
            return mime
    except ImportError:
        pass
    except Exception:
        pass
        
    # Fallback if magic is unavailable
    mime, _ = mimetypes.guess_type(str(filepath))
    return mime or "application/octet-stream"


def is_extension_spoofed(filepath: Path) -> bool:
    """
    Detects if file content mismatches its extension (e.g. invoice.pdf.exe masked as pdf).
    """
    if not filepath.exists():
        return False
        
    real_mime = get_real_mime_type(filepath)
    declared_mime, _ = mimetypes.guess_type(str(filepath))
    
    # If python-magic determines it's executable but extension claims it's a PDF
    if "application/x-dosexec" in real_mime and filepath.suffix.lower() not in HIGH_RISK_EXTS:
        return True
        
    if "application/zip" in real_mime and filepath.suffix.lower() not in {'.zip', '.docx', '.xlsx', '.pptx', '.jar'}:
        return True

    return False


def calculate_entropy(data: bytes) -> float:
    """Calculates byte entropy to detect packed/encrypted payloads."""
    if not data:
        return 0.0
    entropy = 0.0
    length = len(data)
    for x in range(256):
        p_x = float(data.count(x)) / length
        if p_x > 0:
            entropy += - p_x * math.log(p_x, 2)
    return entropy


def hash_file(filepath: Path) -> str:
    """Returns SHA256 of a file."""
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()

def get_authenticode_signature(filepath: Path) -> dict:
    """
    Executes PowerShell Get-AuthenticodeSignature and returns the parsed JSON.
    Returns empty dict if unsigned or failed.
    """
    import subprocess
    import json
    
    if not filepath.exists() or filepath.suffix.lower() not in HIGH_RISK_EXTS:
        return {}
        
    cmd = [
        "powershell",
        "-NoProfile",
        "-Command",
        f"Get-AuthenticodeSignature '{filepath}' | ConvertTo-Json -Depth 3"
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
    except Exception:
        pass
    return {}


class SecretConfidence(IntEnum):
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

def scan_for_secrets(filepath: Path) -> SecretConfidence:
    """
    Scans a file for exposed secrets prior to upload.
    Returns confidence level.
    """
    if filepath.suffix.lower() in HIGH_RISK_EXTS or filepath.suffix.lower() in {'.pdf', '.zip'}:
        # Skip binary / large executable scans
        return SecretConfidence.NONE
        
    try:
        content = filepath.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        return SecretConfidence.NONE
        
    confidence = SecretConfidence.NONE
    
    # 1. Private Key Header (CRITICAL)
    if re.search(r"-----BEGIN (RSA|OPENSSH|DSA|EC|PGP) PRIVATE KEY-----", content):
        return SecretConfidence.CRITICAL
        
    # 2. Match .env structure (HIGH)
    if filepath.name == ".env" or re.search(r"(?im)^(AWS_ACCESS_KEY_ID|STRIPE_SECRET_KEY|DATABASE_URL|API_KEY)\s*=\s*['\"]?[a-zA-Z0-9_\-]+['\"]?$", content):
        return SecretConfidence.HIGH
        
    # 3. Looks like an API key in code (MEDIUM)
    if re.search(r"(?i)(api_key|secret_key|access_token|bearer)\s*[:=]\s*['\"][a-zA-Z0-9_\-]{16,}['\"]", content):
        confidence = max(confidence, SecretConfidence.MEDIUM)
        
    # 4. Suspicious generic patterns (LOW)
    if re.search(r"password\s*=\s*['\"][^'\"]+['\"]", content):
        confidence = max(confidence, SecretConfidence.LOW)
        
    return confidence


def scan_executable_heuristics(filepath: Path) -> List[str]:
    """
    Performs a lightweight static analysis of executables/scripts to find suspicious behavior markers.
    Returns a list of flagged behaviors.
    """
    flags = []
    if filepath.suffix.lower() not in HIGH_RISK_EXTS:
        return flags
        
    try:
        # Read the first 1MB for static strings
        with open(filepath, 'rb') as f:
            content = f.read(1024 * 1024).lower()
            
        if b"powershell" in content:
            flags.append("Imports PowerShell")
        if b"cmd.exe" in content:
            flags.append("Imports cmd.exe")
        if b"wininet.dll" in content or b"ws2_32.dll" in content or b"system.net.webclient" in content:
            flags.append("Imports Networking APIs")
        if b"software\\microsoft\\windows\\currentversion\\run" in content:
            flags.append("Contains Persistence Registry Keys")
            
    except Exception:
        pass
        
    return flags
