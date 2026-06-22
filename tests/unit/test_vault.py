import pytest
import os
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from kree.core import vault

def test_dpapi_encrypt_decrypt_success():
    data = "my_secret_key"
    encrypted = vault.encrypt_data(data)
    assert encrypted.startswith(b"DPAPI")
    decrypted = vault.decrypt_data(encrypted)
    assert decrypted == data

def test_fernet_fallback(monkeypatch):
    monkeypatch.setattr(vault, "_dpapi_encrypt", lambda x: None)
    monkeypatch.setattr(vault, "_dpapi_decrypt", lambda x: None)
    
    class FakeFernet:
        def __init__(self, key):
            pass
        def encrypt(self, data):
            return b"FERNET" + data
        def decrypt(self, data):
            return data[6:]
            
    monkeypatch.setattr(vault, "Fernet", FakeFernet)
    
    data = "my_secret_key"
    encrypted = vault.encrypt_data(data)
    assert not encrypted.startswith(b"DPAPI")
    assert encrypted.startswith(b"FERNET")
    
    decrypted = vault.decrypt_data(encrypted)
    assert decrypted == data

def test_save_load_api_key_dpapi():
    with tempfile.TemporaryDirectory() as tmpdir:
        api_file = Path(tmpdir) / "api.json"
        vault.save_api_key(api_file, "API_KEY_TEST")
        
        with open(api_file, "rb") as f:
            content = f.read()
            assert content.startswith(b"DPAPI")
            
        loaded = vault.load_api_key(api_file)
        assert loaded == "API_KEY_TEST"

def test_auto_migration_unencrypted_to_encrypted():
    with tempfile.TemporaryDirectory() as tmpdir:
        api_file = Path(tmpdir) / "api.json"
        with open(api_file, "w", encoding="utf-8") as f:
            f.write('{"gemini_api_key": "MIGRATION_KEY"}')
            
        loaded = vault.load_api_key(api_file)
        assert loaded == "MIGRATION_KEY"
        
        with open(api_file, "rb") as f:
            content = f.read()
            assert content.startswith(b"DPAPI")
