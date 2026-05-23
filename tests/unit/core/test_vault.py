import pytest
from pathlib import Path
from unittest.mock import patch


def test_save_api_key_raises_when_cryptography_missing(tmp_path):
    """save_api_key must refuse to write plaintext when the cryptography library is absent (fail-closed)."""
    from kree.core import vault

    api_file = tmp_path / "api_keys.vault"

    with patch.object(vault, "Fernet", None):
        with pytest.raises(RuntimeError, match="cryptography"):
            vault.save_api_key(api_file, "super-secret-api-key")

    assert not api_file.exists(), "No file must be created when encryption is unavailable."


def test_save_api_key_does_not_write_plaintext_key(tmp_path):
    """Even if save_api_key somehow continues, the raw API key must never appear in plaintext in the file."""
    from kree.core import vault

    api_file = tmp_path / "api_keys.vault"
    secret = "MY_SECRET_GEMINI_KEY"

    with patch.object(vault, "Fernet", None):
        try:
            vault.save_api_key(api_file, secret)
        except (RuntimeError, Exception):
            pass  # Expected — an error is the correct outcome

    if api_file.exists():
        contents = api_file.read_text(encoding="utf-8", errors="replace")
        assert secret not in contents, "API key must never be stored in plaintext."


def test_encrypt_data_raises_when_cryptography_missing():
    """encrypt_data must not silently return raw bytes when cryptography is absent."""
    from kree.core import vault

    with patch.object(vault, "Fernet", None):
        with pytest.raises(RuntimeError, match="cryptography"):
            vault.encrypt_data("sensitive data")


def test_decrypt_data_raises_when_cryptography_missing_for_non_json_payload():
    from kree.core import vault

    with patch.object(vault, "Fernet", None):
        with pytest.raises(RuntimeError, match="cryptography"):
            vault.decrypt_data(b"encrypted-secret")


def test_master_pin_uses_pbkdf2_and_verifies(tmp_path, monkeypatch):
    from kree.core import vault

    pin_path = tmp_path / "master_pin.hash"
    monkeypatch.setattr(vault, "_get_master_pin_path", lambda: pin_path)
    monkeypatch.setattr(vault, "get_machine_id", lambda: "machine")

    vault.setup_master_pin("123456")
    stored = pin_path.read_text(encoding="utf-8")

    assert stored.startswith("pbkdf2_sha256$")
    assert vault.verify_master_pin("123456") is True
    assert vault.verify_master_pin("000000") is False
