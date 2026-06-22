import json
import base64
import uuid
import threading
from datetime import datetime
import hashlib
import hmac
import secrets
from cryptography.fernet import Fernet
from typing import Optional
from kree.core.runtime import VAULT_DIR
USERS_FILE = VAULT_DIR / "users.json"
PBKDF2_ITERATIONS = 200_000
FERNET_KDF_SALT = b"kree.auth_manager.fernet.v1"
_auth_lock = threading.RLock()

def _ensure_file():
    if not USERS_FILE.exists():
        USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
        USERS_FILE.write_text(json.dumps({"users": {}}, indent=2), encoding="utf-8")

def _load_data() -> dict:
    with _auth_lock:
        _ensure_file()
        try:
            return json.loads(USERS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {"users": {}}

def _save_data(data: dict):
    with _auth_lock:
        USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = USERS_FILE.with_suffix(f"{USERS_FILE.suffix}.tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.replace(USERS_FILE)

def hash_string(text: str) -> str:
    """Return a salted PBKDF2 hash record for passwords and PINs."""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        text.encode("utf-8"),
        salt.encode("ascii"),
        PBKDF2_ITERATIONS,
    ).hex()
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest}"


def _verify_hash(text: str, stored_hash: str) -> bool:
    stored_hash = stored_hash or ""
    if stored_hash.startswith("pbkdf2_sha256$"):
        try:
            _, iterations_text, salt, expected = stored_hash.split("$", 3)
            digest = hashlib.pbkdf2_hmac(
                "sha256",
                text.encode("utf-8"),
                salt.encode("ascii"),
                int(iterations_text),
            ).hex()
            return hmac.compare_digest(digest, expected)
        except Exception:
            return False

    legacy = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return hmac.compare_digest(legacy, stored_hash)

def derive_key(password: str, salt: bytes = FERNET_KDF_SALT) -> bytes:
    """Derive encryption key FROM the user's password."""
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
        dklen=32,
    )


def _derive_legacy_key(password: str) -> bytes:
    return hashlib.sha256(password.encode('utf-8')).digest()

def encrypt_api_key(api_key: str, password: str, salt: bytes = FERNET_KDF_SALT) -> str:
    """Encrypt API key based on the user password."""
    key = base64.urlsafe_b64encode(derive_key(password, salt))
    return Fernet(key).encrypt(api_key.encode('utf-8')).decode('utf-8')

def decrypt_api_key(encrypted: str, password: str, salt: bytes = FERNET_KDF_SALT) -> str:
    """Decrypt the API key when needed using the password."""
    for raw_key in (derive_key(password, salt), _derive_legacy_key(password)):
        key = base64.urlsafe_b64encode(raw_key)
        try:
            return Fernet(key).decrypt(encrypted.encode('utf-8')).decode('utf-8')
        except Exception:
            continue
    raise ValueError("Invalid password or encrypted API key.")

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
        salt_bytes = secrets.token_bytes(16)
        user_record = {
            "user_id": user_id,
            "handle": handle,
            "display_name": display_name or handle,
            "email": email,
            "password_hash": hash_string(password),
            "pin_hash": None,
            "encrypted_api_key": None,
            "encryption_salt": salt_bytes.hex(),
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
        target_user = None
        for uid, udata in users.items():
            if udata.get("handle") == identifier or udata.get("email") == identifier:
                target_user = udata
                break
                
        if not target_user:
            return {"ok": False, "message": "Invalid handle or email."}
            
        if not _verify_hash(password, target_user.get("password_hash", "")):
            return {"ok": False, "message": "Invalid password."}
            
        safe_user = {k: v for k,v in target_user.items() if not k.endswith('_hash') and not k.startswith('encrypted_')}
        
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
            
        if not _verify_hash(pin, users[user_id].get("pin_hash", "")):
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
            user_rec = users[user_id]
            salt_hex = user_rec.get("encryption_salt")
            if not salt_hex:
                salt_bytes = secrets.token_bytes(16)
                salt_hex = salt_bytes.hex()
                user_rec["encryption_salt"] = salt_hex
            else:
                salt_bytes = bytes.fromhex(salt_hex)

            enc_key = encrypt_api_key(raw_api_key, raw_password, salt_bytes)
            user_rec["encrypted_api_key"] = enc_key
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
            salt_hex = user.get("encryption_salt")
            salt_bytes = bytes.fromhex(salt_hex) if salt_hex else FERNET_KDF_SALT
            return decrypt_api_key(user["encrypted_api_key"], raw_password, salt_bytes)
        except Exception:
            return None
            
    @staticmethod
    def mark_login_complete(user_id: str):
        data = _load_data()
        users = data.get("users", {})
        if user_id in users:
            users[user_id]["is_first_login"] = False
            _save_data(data)
