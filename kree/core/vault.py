import os
import json
import base64
import subprocess
import hashlib
import hmac
import secrets
import threading
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

import sys
import ctypes
import ctypes.wintypes

class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", ctypes.wintypes.DWORD),
                ("pbData", ctypes.POINTER(ctypes.c_byte))]

def _dpapi_encrypt(data: bytes) -> bytes | None:
    if sys.platform != "win32":
        return None
    try:
        blob_in = DATA_BLOB(len(data), ctypes.cast(ctypes.c_char_p(data), ctypes.POINTER(ctypes.c_byte)))
        blob_out = DATA_BLOB()
        CRYPTPROTECT_UI_FORBIDDEN = 0x1
        if ctypes.windll.crypt32.CryptProtectData(
                ctypes.byref(blob_in), None, None, None, None, CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(blob_out)
        ):
            result = ctypes.string_at(blob_out.pbData, blob_out.cbData)
            ctypes.windll.kernel32.LocalFree(blob_out.pbData)
            return b"DPAPI" + result
    except Exception as e:
        logger.error(f"DPAPI encrypt failed: {e}")
    return None

def _dpapi_decrypt(data: bytes) -> bytes | None:
    if sys.platform != "win32" or not data.startswith(b"DPAPI"):
        return None
    try:
        raw_data = data[5:]
        blob_in = DATA_BLOB(len(raw_data), ctypes.cast(ctypes.c_char_p(raw_data), ctypes.POINTER(ctypes.c_byte)))
        blob_out = DATA_BLOB()
        CRYPTPROTECT_UI_FORBIDDEN = 0x1
        if ctypes.windll.crypt32.CryptUnprotectData(
                ctypes.byref(blob_in), None, None, None, None, CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(blob_out)
        ):
            result = ctypes.string_at(blob_out.pbData, blob_out.cbData)
            ctypes.windll.kernel32.LocalFree(blob_out.pbData)
            return result
    except Exception as e:
        logger.error(f"DPAPI decrypt failed: {e}")
    return None

_vault_lock = threading.RLock()

try:
    from cryptography.fernet import Fernet # type: ignore[import]
except ImportError:
    # If cryptography is not installed, fallback to plain text JSON to avoid breaking existing users during the transition.
    # The true deploy script will PIP install cryptography.
    Fernet = None

_REGISTRY_GUID_CACHE = None
_WMIC_UUID_CACHE = None
_ENV_FALLBACK_ID_CACHE = None

def _get_registry_guid() -> str | None:
    global _REGISTRY_GUID_CACHE
    if _REGISTRY_GUID_CACHE is not None:
        return _REGISTRY_GUID_CACHE or None
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Cryptography",
        ) as key:
            guid, _ = winreg.QueryValueEx(key, "MachineGuid")
            if guid and guid.strip():
                _REGISTRY_GUID_CACHE = guid.strip()
                return _REGISTRY_GUID_CACHE
    except Exception as e:
        logger.debug(f"Failed to get Registry MachineGuid: {e}")
    _REGISTRY_GUID_CACHE = ""
    return None

def _get_wmic_uuid() -> str | None:
    global _WMIC_UUID_CACHE
    if _WMIC_UUID_CACHE is not None:
        return _WMIC_UUID_CACHE or None
    try:
        out = subprocess.check_output(
            "wmic csproduct get uuid", shell=True, stderr=subprocess.DEVNULL
        ).decode().split('\n')[1].strip()
        if out:
            _WMIC_UUID_CACHE = out
            return out
    except Exception as e:
        logger.debug(f"Failed to get WMIC UUID: {e}")
    _WMIC_UUID_CACHE = ""
    return None

def _get_env_fallback_id() -> str:
    global _ENV_FALLBACK_ID_CACHE
    if _ENV_FALLBACK_ID_CACHE is not None:
        return _ENV_FALLBACK_ID_CACHE
    user = os.environ.get('USERNAME', 'kree_user')
    pc = os.environ.get('COMPUTERNAME', 'kree_pc')
    _ENV_FALLBACK_ID_CACHE = f"{user}_{pc}"
    return _ENV_FALLBACK_ID_CACHE

def _derive_fernet(hw_id: str):
    if Fernet is None:
        return None
    key_material = hashlib.sha256(hw_id.encode('utf-8')).digest()
    fernet_key = base64.urlsafe_b64encode(key_material)
    return Fernet(fernet_key)

_MACHINE_ID_CACHE = None

def get_machine_id() -> str:
    global _MACHINE_ID_CACHE
    if _MACHINE_ID_CACHE is not None:
        return _MACHINE_ID_CACHE

    # ── Strategy: Registry (stable) → WMIC (legacy compat) → Env vars (last resort) ──
    guid = _get_registry_guid()
    if guid:
        print("[VAULT] Machine ID source: Registry MachineGuid")
        _MACHINE_ID_CACHE = guid
        return guid
        
    uuid_str = _get_wmic_uuid()
    if uuid_str:
        print("[VAULT] Machine ID source: WMIC UUID (legacy)")
        _MACHINE_ID_CACHE = uuid_str
        return uuid_str
        
    print("[VAULT] WARNING: Machine ID source: Environment fallback (USERNAME_COMPUTERNAME)")
    val = _get_env_fallback_id()
    _MACHINE_ID_CACHE = val
    return val

def _get_fernet():
    if Fernet is None:
        return None
    hw_id = get_machine_id()
    # Hash the hardware ID to create a secure 32-byte AES key
    key_material = hashlib.sha256(hw_id.encode('utf-8')).digest()
    fernet_key = base64.urlsafe_b64encode(key_material)
    return Fernet(fernet_key)

def save_api_key(api_file_path: Path, api_key: str):
    with _vault_lock:
        os.makedirs(api_file_path.parent, exist_ok=True)
        
        # Try DPAPI first (Windows)
        dpapi_encrypted = _dpapi_encrypt(api_key.encode('utf-8'))
        if dpapi_encrypted:
            with open(api_file_path, "wb") as file:
                file.write(dpapi_encrypted)
            return

        # Fallback to Fernet
        f = _get_fernet()
        if f is None:
            raise RuntimeError(
                "Cannot save API key: the 'cryptography' library is not installed. "
                "Run `pip install cryptography` to enable encrypted vault storage."
            )

        encrypted = f.encrypt(api_key.encode('utf-8'))
        with open(api_file_path, "wb") as file:
            file.write(encrypted)

def load_api_key(api_file_path: Path) -> str:
    with _vault_lock:
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
        except Exception as e:
            logger.debug(f"Failed to parse API key file as unencrypted JSON: {e}")
            
        # Check DPAPI
        if raw_data.startswith(b"DPAPI"):
            decrypted = _dpapi_decrypt(raw_data)
            if decrypted:
                return decrypted.decode('utf-8')
            else:
                logger.error("[VAULT] DPAPI decryption failed for API key.")
                return ""
        
    if Fernet is None:
        print("[VAULT] CRITICAL: 'cryptography' library missing, unable to decrypt Vault.")
        return ""

    wmic_id = _get_wmic_uuid()
    reg_id = _get_registry_guid()
    env_id = _get_env_fallback_id()
    primary_id = get_machine_id()

    # 1. Attempt decryption using WMIC-derived key
    if wmic_id:
        f_wmic = _derive_fernet(wmic_id)
        if f_wmic:
            try:
                decrypted = f_wmic.decrypt(raw_data).decode('utf-8')
                print("[VAULT] Decrypted successfully using WMIC-derived key.")
                if primary_id != wmic_id:
                    try:
                        save_api_key(api_file_path, decrypted)
                        print("[VAULT] Automatically re-encrypted/migrated vault with preferred modern key.")
                    except Exception as me:
                        print(f"[VAULT] Migration save error: {me}")
                return decrypted
            except Exception:
                pass

    # 2. Attempt decryption using Registry MachineGuid-derived key
    if reg_id:
        f_reg = _derive_fernet(reg_id)
        if f_reg:
            try:
                decrypted = f_reg.decrypt(raw_data).decode('utf-8')
                print("[VAULT] Decrypted successfully using Registry MachineGuid-derived key.")
                if primary_id != reg_id:
                    try:
                        save_api_key(api_file_path, decrypted)
                        print("[VAULT] Automatically re-encrypted/migrated vault with preferred modern key.")
                    except Exception as me:
                        print(f"[VAULT] Migration save error: {me}")
                return decrypted
            except Exception:
                pass

    # 3. Attempt legacy USERNAME_COMPUTERNAME key
    f_env = _derive_fernet(env_id)
    if f_env:
        try:
            decrypted = f_env.decrypt(raw_data).decode('utf-8')
            print("[VAULT] Decrypted successfully using legacy USERNAME_COMPUTERNAME key.")
            if primary_id != env_id:
                try:
                    save_api_key(api_file_path, decrypted)
                    print("[VAULT] Automatically re-encrypted/migrated vault from legacy env key.")
                except Exception as me:
                    print(f"[VAULT] Migration save error: {me}")
            return decrypted
        except Exception:
            pass

    print("[VAULT] Decryption Error: All decryption key candidates failed.")
    return ""

def _get_master_pin_path() -> Path:
    from kree.core.runtime import VAULT_DIR
    return VAULT_DIR / "master_pin.hash"


def _get_unlock_trust_path() -> Path:
    from kree.core.runtime import VAULT_DIR
    return VAULT_DIR / "trusted_unlock.json"


MASTER_PIN_ITERATIONS = 200_000


def _hash_master_pin(pin: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    machine_id = get_machine_id()
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        f"{pin}::{machine_id}".encode("utf-8"),
        salt.encode("ascii"),
        MASTER_PIN_ITERATIONS,
    ).hex()
    return f"pbkdf2_sha256${MASTER_PIN_ITERATIONS}${salt}${digest}"


def _verify_master_pin_hash(pin: str, saved_hash: str) -> bool:
    if saved_hash.startswith("pbkdf2_sha256$"):
        try:
            _, iterations_text, salt, expected = saved_hash.split("$", 3)
            machine_id = get_machine_id()
            actual = hashlib.pbkdf2_hmac(
                "sha256",
                f"{pin}::{machine_id}".encode("utf-8"),
                salt.encode("ascii"),
                int(iterations_text),
            ).hex()
            return hmac.compare_digest(actual, expected)
        except Exception as e:
            logger.warning(f"Error verifying master PIN PBKDF2 hash: {e}")
            return False

    hw_id = get_machine_id()
    legacy = hashlib.sha256(f"{pin}::{hw_id}".encode("utf-8")).hexdigest()
    return hmac.compare_digest(legacy, saved_hash)

def is_master_pin_set() -> bool:
    return _get_master_pin_path().exists()

def setup_master_pin(pin: str):
    path = _get_master_pin_path()
    os.makedirs(path.parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        file.write(_hash_master_pin(pin))

def verify_master_pin(pin: str) -> bool:
    if not is_master_pin_set():
        return False
        
    try:
        with open(_get_master_pin_path(), "r", encoding="utf-8") as file:
            saved_hash = file.read().strip()
        return _verify_master_pin_hash(pin, saved_hash)
    except Exception as e:
        logger.warning(f"Error verifying master PIN: {e}")
        return False


def remember_unlock_session(ttl_hours: int = 24) -> bool:
    if not is_master_pin_set():
        return False

    try:
        master_pin_hash = _get_master_pin_path().read_text(encoding="utf-8").strip()
        if not master_pin_hash:
            return False

        expires_at = datetime.now(timezone.utc) + timedelta(hours=max(1, int(ttl_hours)))
        machine_id = get_machine_id()
        signature = hashlib.sha256(
            f"{machine_id}::{expires_at.isoformat()}::{master_pin_hash}".encode("utf-8")
        ).hexdigest()
        payload = {
            "machine_id": machine_id,
            "expires_at": expires_at.isoformat(),
            "master_pin_hash": master_pin_hash,
            "signature": signature,
        }
        payload_str = json.dumps(payload, indent=2)
        encrypted_payload = encrypt_data(payload_str)
        path = _get_unlock_trust_path()
        os.makedirs(path.parent, exist_ok=True)
        with open(path, "wb") as file:
            file.write(encrypted_payload)
        return True
    except Exception as e:
        logger.warning(f"Error saving unlock session: {e}")
        return False


def is_unlock_trusted() -> bool:
    path = _get_unlock_trust_path()
    if not path.exists():
        return False

    try:
        raw_data = path.read_bytes()
        # Support both legacy plain JSON and encrypted JSON for fallback compatibility
        if raw_data.startswith(b'{'):
            payload = json.loads(raw_data.decode('utf-8'))
        else:
            payload = json.loads(decrypt_data(raw_data))

        if not isinstance(payload, dict):
            return False

        if not hmac.compare_digest(str(payload.get("machine_id") or ""), get_machine_id()):
            return False

        expires_at_raw = str(payload.get("expires_at") or "")
        expires_at = datetime.fromisoformat(expires_at_raw)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= datetime.now(timezone.utc):
            return False

        master_pin_hash = _get_master_pin_path().read_text(encoding="utf-8").strip()
        if not master_pin_hash or not hmac.compare_digest(master_pin_hash, str(payload.get("master_pin_hash") or "")):
            return False

        expected_signature = hashlib.sha256(
            f"{payload.get('machine_id')}::{expires_at.isoformat()}::{master_pin_hash}".encode("utf-8")
        ).hexdigest()
        return hmac.compare_digest(expected_signature, str(payload.get("signature") or ""))
    except Exception as e:
        logger.warning(f"Error verifying unlock session trust: {e}")
        return False


def clear_unlock_trust() -> None:
    path = _get_unlock_trust_path()
    try:
        if path.exists():
            path.unlink()
    except Exception as e:
        logger.warning(f"Error clearing unlock trust file: {e}")

def encrypt_data(data: str) -> bytes:
    # Prefer DPAPI
    dpapi_encrypted = _dpapi_encrypt(data.encode('utf-8'))
    if dpapi_encrypted:
        return dpapi_encrypted

    # Fallback to Fernet
    f = _get_fernet()
    if f is None:
        raise RuntimeError(
            "Cannot encrypt data: the 'cryptography' library is not installed. "
            "Run `pip install cryptography` to enable encrypted vault storage."
        )
    return f.encrypt(data.encode('utf-8'))

def decrypt_data(raw_data: bytes) -> str:
    # If DPAPI encrypted
    if raw_data.startswith(b"DPAPI"):
        decrypted = _dpapi_decrypt(raw_data)
        if decrypted:
            return decrypted.decode('utf-8')
        raise ValueError("DPAPI decryption failed for vault payload.")

    # If not encrypted (like old JSON memory), try decoding directly
    if raw_data.startswith(b'{') or raw_data.startswith(b'['):
        return raw_data.decode('utf-8')
        
    if Fernet is None:
        raise RuntimeError(
            "Cannot decrypt data: the 'cryptography' library is not installed. "
            "Run `pip install cryptography` to enable encrypted vault storage."
        )

    wmic_id = _get_wmic_uuid()
    reg_id = _get_registry_guid()
    env_id = _get_env_fallback_id()

    # 1. Attempt decryption using WMIC-derived key
    if wmic_id:
        f_wmic = _derive_fernet(wmic_id)
        if f_wmic:
            try:
                return f_wmic.decrypt(raw_data).decode('utf-8')
            except Exception:
                pass

    # 2. Attempt decryption using Registry MachineGuid-derived key
    if reg_id:
        f_reg = _derive_fernet(reg_id)
        if f_reg:
            try:
                return f_reg.decrypt(raw_data).decode('utf-8')
            except Exception:
                pass

    # 3. Attempt legacy USERNAME_COMPUTERNAME key
    f_env = _derive_fernet(env_id)
    if f_env:
        try:
            return f_env.decrypt(raw_data).decode('utf-8')
        except Exception:
            pass
        
    raise ValueError("Encrypted vault payload could not be decrypted.")
