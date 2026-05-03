import os
import json
import base64
import uuid
from datetime import datetime
import hashlib
from pathlib import Path
from cryptography.fernet import Fernet
from typing import Dict, Any, Optional

def _get_base_dir() -> Path:
    import sys
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR = _get_base_dir()
USERS_FILE = BASE_DIR / "memory" / "users.json"

def _ensure_file():
    if not USERS_FILE.exists():
        USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
        USERS_FILE.write_text(json.dumps({"users": {}}, indent=2), encoding="utf-8")

def _load_data() -> dict:
    _ensure_file()
    try:
        return json.loads(USERS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"users": {}}

def _save_data(data: dict):
    USERS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

def hash_string(text: str) -> str:
    """Basic SHA256 hashing for passwords and pins (with a fixed salt or just direct for local usage)."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def derive_key(password: str) -> bytes:
    """Derive encryption key FROM the user's password."""
    # Using SHA256 digest to create a 32-byte key suitable for Fernet
    return hashlib.sha256(password.encode('utf-8')).digest()

def encrypt_api_key(api_key: str, password: str) -> str:
    """Encrypt API key based on the user password."""
    key = base64.urlsafe_b64encode(derive_key(password))
    return Fernet(key).encrypt(api_key.encode('utf-8')).decode('utf-8')

def decrypt_api_key(encrypted: str, password: str) -> str:
    """Decrypt the API key when needed using the password."""
    key = base64.urlsafe_b64encode(derive_key(password))
    return Fernet(key).decrypt(encrypted.encode('utf-8')).decode('utf-8')

class AuthManager:
    @staticmethod
    def get_user_count() -> int:
        data = _load_data()
        return len(data.get("users", {}))
        
    @staticmethod
    def create_user(handle: str, password: str, email: str = "", display_name: str = "") -> dict:
        data = _load_data()
        users = data.get("users", {})
        
        # Check uniqueness of handle
        for uid, udata in users.items():
            if udata.get("handle") == handle:
                return {"ok": False, "message": "Handle already exists."}
                
        user_id = str(uuid.uuid4())
        user_record = {
            "user_id": user_id,
            "handle": handle,
            "display_name": display_name or handle,
            "email": email,
            "password_hash": hash_string(password),
            "pin_hash": None,
            "encrypted_api_key": None,
            "is_first_login": True,
            "created_at": datetime.now().isoformat()
        }
        
        users[user_id] = user_record
        data["users"] = users
        _save_data(data)
        
        # Strip secrets from return value
        safe_user = {k: v for k,v in user_record.items() if not k.endswith('_hash') and not k.startswith('encrypted_')}
        return {"ok": True, "user": safe_user, "message": "Account created successfully.", "next_stage": "pin_setup"}

    @staticmethod
    def sign_in_user(identifier: str, password: str) -> dict:
        data = _load_data()
        users = data.get("users", {})
        pass_hash = hash_string(password)
        
        target_user = None
        for uid, udata in users.items():
            if udata.get("handle") == identifier or udata.get("email") == identifier:
                target_user = udata
                break
                
        if not target_user:
            return {"ok": False, "message": "Invalid handle or email."}
            
        if target_user.get("password_hash") != pass_hash:
            return {"ok": False, "message": "Invalid password."}
            
        safe_user = {k: v for k,v in target_user.items() if not k.endswith('_hash') and not k.startswith('encrypted_')}
        is_first = target_user.get("is_first_login", False)
        
        # Check what needs to be configured still
        if not target_user.get("pin_hash"):
            return {"ok": True, "user": safe_user, "next_stage": "pin_setup", "message": "Please set up your PIN."}
            
        if not target_user.get("encrypted_api_key"):
            return {"ok": True, "user": safe_user, "next_stage": "api_setup", "message": "Please provide an API key."}
            
        # If everything is setup, go to pin verification to unlock the session
        return {"ok": True, "user": safe_user, "next_stage": "pin_verify", "message": "Please verify your PIN to continue."}

    @staticmethod
    def set_user_pin(user_id: str, pin: str) -> dict:
        data = _load_data()
        users = data.get("users", {})
        if user_id not in users:
            return {"ok": False, "message": "User not found."}
            
        users[user_id]["pin_hash"] = hash_string(pin)
        _save_data(data)
        
        # Decide next stage
        api_key = users[user_id].get("encrypted_api_key")
        next_stage = "api_setup" if not api_key else "complete"
        return {"ok": True, "message": "PIN updated.", "next_stage": next_stage}

    @staticmethod
    def verify_user_pin(user_id: str, pin: str) -> dict:
        data = _load_data()
        users = data.get("users", {})
        if user_id not in users:
            return {"ok": False, "message": "User not found."}
            
        if users[user_id].get("pin_hash") != hash_string(pin):
            return {"ok": False, "message": "Incorrect PIN."}
            
        api_key = users[user_id].get("encrypted_api_key")
        next_stage = "api_setup" if not api_key else "complete"
        return {"ok": True, "message": "PIN verified.", "next_stage": next_stage}
        
    @staticmethod
    def save_user_api_key(user_id: str, raw_api_key: str, raw_password: str) -> dict:
        data = _load_data()
        users = data.get("users", {})
        if user_id not in users:
            return {"ok": False, "message": "User not found."}
            
        try:
            enc_key = encrypt_api_key(raw_api_key, raw_password)
            users[user_id]["encrypted_api_key"] = enc_key
            _save_data(data)
            return {"ok": True, "message": "API Key secured."}
        except Exception as e:
            return {"ok": False, "message": f"Encryption failed: {e}"}

    @staticmethod
    def get_user_api_key(user_id: str, raw_password: str) -> Optional[str]:
        data = _load_data()
        user = data.get("users", {}).get(user_id)
        if not user or not user.get("encrypted_api_key"):
            return None
        try:
            return decrypt_api_key(user["encrypted_api_key"], raw_password)
        except Exception:
            return None
            
    @staticmethod
    def mark_login_complete(user_id: str):
        data = _load_data()
        users = data.get("users", {})
        if user_id in users:
            users[user_id]["is_first_login"] = False
            _save_data(data)
