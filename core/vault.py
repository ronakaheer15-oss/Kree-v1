import os
import json
import base64
import subprocess
import hashlib
from pathlib import Path

try:
    from cryptography.fernet import Fernet # type: ignore[import]
except ImportError:
    # If cryptography is not installed, fallback to plain text JSON to avoid breaking existing users during the transition.
    # The true deploy script will PIP install cryptography.
    Fernet = None

def get_machine_id() -> str:
    try:
        # Windows Native Hardware UUID (Ties the API Key encryption strictly to this specific motherboard)
        out = subprocess.check_output("wmic csproduct get uuid", shell=True, stderr=subprocess.DEVNULL).decode().split('\n')[1].strip()
        if out: 
            return out
    except Exception:
        pass
    
    # Fallback to User + PC combination if WMIC is restricted
    user = os.environ.get('USERNAME', 'kree_user')
    pc = os.environ.get('COMPUTERNAME', 'kree_pc')
    return f"{user}_{pc}"

def _get_fernet():
    if Fernet is None:
        return None
    hw_id = get_machine_id()
    # Hash the hardware ID to create a secure 32-byte AES key
    key_material = hashlib.sha256(hw_id.encode('utf-8')).digest()
    fernet_key = base64.urlsafe_b64encode(key_material)
    return Fernet(fernet_key)

def save_api_key(api_file_path: Path, api_key: str):
    f = _get_fernet()
    # Graceful fallback to plaintext JSON if cryptography is missing
    if f is None:
        os.makedirs(api_file_path.parent, exist_ok=True)
        with open(api_file_path, "w", encoding="utf-8") as file:
            json.dump({"gemini_api_key": api_key}, file, indent=4)
        return

    encrypted = f.encrypt(api_key.encode('utf-8'))
    os.makedirs(api_file_path.parent, exist_ok=True)
    with open(api_file_path, "wb") as file:
        file.write(encrypted)

def load_api_key(api_file_path: Path) -> str:
    if not api_file_path.exists():
        return ""
        
    with open(api_file_path, "rb") as file:
        raw_data = file.read()
    
    # Check if the file is the old unencrypted JSON format.
    # This allows a seamless auto-migration for existing users.
    try:
        if raw_data.startswith(b'{'):
            data = json.loads(raw_data.decode('utf-8'))
            key = data.get("gemini_api_key", "")
            if key:
                save_api_key(api_file_path, key) # Auto-upgrade to encrypted Vault format
            return key
    except Exception:
        pass
        
    f = _get_fernet()
    if f is None:
        print("[VAULT] CRITICAL: 'cryptography' library missing, unable to decrypt Vault.")
        return ""
        
    try:
        decrypted = f.decrypt(raw_data).decode('utf-8')
        return decrypted
    except Exception as e:
        print(f"[VAULT] Decryption Error: {e}")
        return ""

def _get_master_pin_path() -> Path:
    # Use the same config dir as api file
    base = Path(os.environ.get('APPDATA', os.path.expanduser('~'))) / ".kree" / "config"
    return base / "master_pin.hash"

def is_master_pin_set() -> bool:
    return _get_master_pin_path().exists()

def setup_master_pin(pin: str):
    hw_id = get_machine_id()
    # Salt the PIN with hardware ID and hash it
    salted_pin = f"{pin}::{hw_id}".encode('utf-8')
    pin_hash = hashlib.sha256(salted_pin).hexdigest()
    
    path = _get_master_pin_path()
    os.makedirs(path.parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        file.write(pin_hash)

def verify_master_pin(pin: str) -> bool:
    if not is_master_pin_set():
        return False
        
    hw_id = get_machine_id()
    salted_pin = f"{pin}::{hw_id}".encode('utf-8')
    pin_hash = hashlib.sha256(salted_pin).hexdigest()
    
    try:
        with open(_get_master_pin_path(), "r", encoding="utf-8") as file:
            saved_hash = file.read().strip()
        return pin_hash == saved_hash
    except Exception:
        return False

def encrypt_data(data: str) -> bytes:
    f = _get_fernet()
    if f is None:
        return data.encode('utf-8')
    return f.encrypt(data.encode('utf-8'))

def decrypt_data(raw_data: bytes) -> str:
    # If not encrypted (like old JSON memory), try decoding directly
    if raw_data.startswith(b'{') or raw_data.startswith(b'['):
        return raw_data.decode('utf-8')
        
    f = _get_fernet()
    if f is None:
        return raw_data.decode('utf-8', errors='ignore')
        
    try:
        return f.decrypt(raw_data).decode('utf-8')
    except Exception:
        # Fallback if somehow it's plaintext but not JSON
        return raw_data.decode('utf-8', errors='ignore')
