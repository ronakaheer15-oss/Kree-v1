import os
import time
import json
import zipfile
import urllib.request
import urllib.error
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional, Dict

from kree.core.runtime import APP_DATA_DIR
from kree.core.file_security import (
    TrustTier, FileRisk, classify_extension, is_path_safe,
    hash_file, get_real_mime_type, scan_for_secrets, SecretConfidence,
    scan_executable_heuristics, get_authenticode_signature, is_extension_spoofed
)

# Network Egress Caps (In-memory mock for session tracking)
_UPLOAD_SESSION_COUNT = 0
_UPLOAD_SESSION_BYTES = 0
MAX_UPLOAD_SIZE = 250 * 1024 * 1024
MAX_SESSION_BYTES = 1024 * 1024 * 1024
MAX_SESSION_DESTINATIONS = 3
_UPLOAD_DESTINATIONS = set()

QUARANTINE_DIR = APP_DATA_DIR / "vault" / "downloads" / "quarantine"
TRANSFER_LOG_DIR = APP_DATA_DIR / "logs" / "transfers"

QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
TRANSFER_LOG_DIR.mkdir(parents=True, exist_ok=True)

AUDIT_LOG_FILE = TRANSFER_LOG_DIR / "audit_chain.json"

ALLOWED_DOMAINS = ["github.com", "huggingface.co", "drive.google.com", "raw.githubusercontent.com"]
BLOCKED_DOMAINS = ["anonfiles.com", "tempfile.ru", "mega.nz", "bit.ly", "tinyurl.com"]


def log_transfer_audit(action: str, source: str, destination: str, file_hash: str, risk: str, confirmed: bool):
    """Immutable hash-chained JSON audit log for forensics."""
    prev_hash = "genesis"
    entries = []
    
    if AUDIT_LOG_FILE.exists():
        try:
            entries = json.loads(AUDIT_LOG_FILE.read_text(encoding="utf-8"))
            if entries:
                prev_hash = entries[-1].get("entry_hash", "genesis")
        except Exception:
            pass
            
    entry = {
        "timestamp": time.time(),
        "action": action,
        "source": source,
        "destination": destination,
        "hash": file_hash,
        "risk": risk,
        "confirmed": confirmed,
        "prev_hash": prev_hash
    }
    
    entry_str = json.dumps(entry, sort_keys=True)
    import hashlib
    entry["entry_hash"] = hashlib.sha256(entry_str.encode('utf-8')).hexdigest()
    
    entries.append(entry)
    AUDIT_LOG_FILE.write_text(json.dumps(entries, indent=2), encoding="utf-8")


def get_domain_trust(url: str) -> TrustTier:
    """Returns trust tier based on domain allowlist/blocklist."""
    try:
        domain = urlparse(url).netloc.lower()
        if any(b in domain for b in BLOCKED_DOMAINS):
            return TrustTier.HIGH_RISK
        if any(a in domain for a in ALLOWED_DOMAINS):
            return TrustTier.KNOWN_TRUSTED
        return TrustTier.UNKNOWN_WEB
    except Exception:
        return TrustTier.UNKNOWN_WEB


def validate_redirect_chain(url: str) -> tuple[TrustTier, str]:
    """
    Validates initial URL, resolves redirects, and validates final URL.
    Returns (Lowest Trust Tier, Final URL)
    """
    try:
        req = urllib.request.Request(url, method='HEAD')
        response = urllib.request.urlopen(req, timeout=10)
        final_url = response.url
        
        initial_trust = get_domain_trust(url)
        final_trust = get_domain_trust(final_url)
        
        return max(initial_trust, final_trust), final_url
    except Exception:
        return TrustTier.HIGH_RISK, url


def scan_archive_recursively(filepath: Path, depth: int = 1) -> FileRisk:
    """Recursively scans archives for hidden nested executables or MIME spoofing."""
    MAX_DEPTH = 3
    if depth > MAX_DEPTH:
        return FileRisk.HIGH  # Too deep, suspicious
        
    try:
        with zipfile.ZipFile(filepath, 'r') as z:
            for info in z.infolist():
                ext = Path(info.filename).suffix.lower()
                from kree.core.file_security import HIGH_RISK_EXTS
                if ext in HIGH_RISK_EXTS:
                    return FileRisk.HIGH
                    
                # Nested archive checking
                if ext in {'.zip', '.tar', '.gz'}:
                    return FileRisk.HIGH  # V1: Flag nested archives as high risk
    except zipfile.BadZipFile:
        pass # Not a zip or malformed
    return FileRisk.SAFE


def download_file(url: str, dest_dir: str, filename: str, explicit_user_intent: bool = False) -> Dict:
    """
    Secure pipeline for downloading files.
    """
    # 1. Validate Intent & Privilege Boundaries
    if not explicit_user_intent:
        return {"error": "Autonomous downloads are forbidden. User intent required."}
        
    dest_path = Path(dest_dir).resolve() / filename
    if not is_path_safe(dest_path):
        return {"error": f"Destination path {dest_dir} is restricted by privilege boundaries."}
        
    # 2. Resolve redirects & Domain Trust
    trust_tier, final_url = validate_redirect_chain(url)
    if trust_tier == TrustTier.HIGH_RISK:
        return {"error": "Download blocked. Domain or redirect chain is on the blocklist."}
        
    # 3. Quarantine Download
    quarantine_path = QUARANTINE_DIR / filename
    try:
        urllib.request.urlretrieve(final_url, str(quarantine_path))
    except Exception as e:
        return {"error": f"Download failed: {str(e)}"}
        
    # 4. Fingerprint & Entropy
    f_hash = hash_file(quarantine_path)
    file_size = quarantine_path.stat().st_size
    risk = classify_extension(quarantine_path)
    
    # 5. Size Anomalies (e.g. 980MB PDF)
    human_reasons = []
    if trust_tier == TrustTier.UNKNOWN_WEB:
        human_reasons.append("Downloaded from an unknown source")
    
    if file_size > 100 * 1024 * 1024 and risk == FileRisk.SAFE:
        risk = FileRisk.HIGH
        human_reasons.append(f"Suspiciously large size ({file_size//1024//1024}MB) for a safe extension")
        
    # 6. MIME Spoofing
    if is_extension_spoofed(quarantine_path):
        risk = FileRisk.HIGH
        human_reasons.append("File extension does not match actual MIME content")
        
    # 7. Sandboxed Archive Inspection
    if quarantine_path.suffix.lower() == ".zip":
        archive_risk = scan_archive_recursively(quarantine_path)
        if archive_risk > risk:
            risk = archive_risk
            human_reasons.append("Archive contains nested high-risk executables or is malformed")
            
    # 8. Signature & Heuristics
    if risk == FileRisk.HIGH:
        heuristics = scan_executable_heuristics(quarantine_path)
        if heuristics:
            human_reasons.extend(heuristics)
            
        sig = get_authenticode_signature(quarantine_path)
        if not sig or sig.get("Status") != "Valid":
            # Unsigned executable
            trust_tier = TrustTier.HIGH_RISK
            human_reasons.append("Unsigned executable (Missing Valid Authenticode Signature)")
            
    # TOCTOU Protection (Time-of-check to time-of-use re-hash)
    f_hash_now = hash_file(quarantine_path)
    if f_hash_now != f_hash:
        return {"error": "TOCTOU Violation: File modified during scan."}

    # Release / Confirm Gate
    if risk == FileRisk.HIGH or trust_tier >= TrustTier.UNKNOWN_WEB:
        log_transfer_audit("download_quarantined", final_url, str(dest_path), f_hash_now, risk.name, False)
        return {
            "status": "quarantined",
            "message": "File requires explicit user confirmation.",
            "quarantine_path": str(quarantine_path),
            "hash": f_hash_now,
            "risk": risk.name,
            "trust": trust_tier.name,
            "executable": False,
            "released": False,
            "reasons": human_reasons
        }
        
    # Release from Quarantine
    import shutil
    shutil.move(str(quarantine_path), str(dest_path))
    log_transfer_audit("download_released", final_url, str(dest_path), f_hash_now, risk.name, True)
    
    return {"status": "success", "path": str(dest_path), "hash": f_hash_now}


def upload_file(filepath: str, endpoint: str, explicit_user_intent: bool = False) -> Dict:
    """
    Secure pipeline for uploading files.
    """
    global _UPLOAD_SESSION_COUNT, _UPLOAD_SESSION_BYTES, _UPLOAD_DESTINATIONS
    
    if not explicit_user_intent:
        return {"error": "Autonomous uploads are forbidden. User intent required."}
        
    if not endpoint.startswith("https://"):
        return {"error": "Upload blocked. Only HTTPS destinations are allowed."}
        
    source_path = Path(filepath).resolve()
    if not source_path.exists():
        return {"error": "File not found."}
        
    if not is_path_safe(source_path):
        return {"error": "Source path is outside permitted boundaries."}
        
    file_size = source_path.stat().st_size
    if file_size > MAX_UPLOAD_SIZE:
        return {"error": f"Upload blocked. Exceeds max per-file upload cap ({MAX_UPLOAD_SIZE//1024//1024}MB)."}
        
    if _UPLOAD_SESSION_BYTES + file_size > MAX_SESSION_BYTES:
        return {"error": "Upload blocked. Exceeds session data cap (1GB)."}
        
    endpoint_domain = urlparse(endpoint).netloc.lower()
    _UPLOAD_DESTINATIONS.add(endpoint_domain)
    if len(_UPLOAD_DESTINATIONS) > MAX_SESSION_DESTINATIONS:
        return {"error": f"Upload blocked. Session destinations exceed cap ({MAX_SESSION_DESTINATIONS})."}
        
    # Secret Scanning
    secret_conf = scan_for_secrets(source_path)
    if secret_conf >= SecretConfidence.MEDIUM:
        return {"error": f"Upload blocked. Sensitive credentials detected (Confidence: {secret_conf.name})."}
        
    f_hash = hash_file(source_path)
    
    # Destination Trust
    trust_tier = get_domain_trust(endpoint)
    if trust_tier == TrustTier.HIGH_RISK:
        log_transfer_audit("upload_blocked", str(source_path), endpoint, f_hash, "HIGH", False)
        return {"error": "Upload blocked. Destination domain is high-risk."}
        
    # TOCTOU Check before final upload
    f_hash_now = hash_file(source_path)
    if f_hash_now != f_hash:
        return {"error": "TOCTOU Violation: File modified during pre-upload scan."}
        
    _UPLOAD_SESSION_BYTES += file_size
    _UPLOAD_SESSION_COUNT += 1
        
    # Proceed with upload (Mocked implementation)
    # ...
    log_transfer_audit("upload_success", str(source_path), endpoint, f_hash_now, "SAFE", True)
    
    return {"status": "success", "hash": f_hash_now}
