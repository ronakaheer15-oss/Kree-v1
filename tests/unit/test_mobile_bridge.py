import json
import time
import pytest
from pathlib import Path


# ---------------------------------------------------------------------------
# Tests for the extracted token-validation helper we'll create:
#   kree.mobile_bridge._validate_pwa_token(client_token, token_file) -> bool
# ---------------------------------------------------------------------------

def test_missing_token_file_denies_access(tmp_path):
    """No pwa_token.json must deny access, not grant it (Critical Issue #3)."""
    from kree.mobile_bridge import _validate_pwa_token

    token_file = tmp_path / "pwa_token.json"  # does not exist
    assert _validate_pwa_token("any-token", token_file) is False, (
        "A missing token file must not grant access. "
        "This is the auth bypass bug: 'no token file = first boot = auth_passed=True'."
    )


def test_empty_token_in_file_denies_access(tmp_path):
    """An empty token stored in the file must deny access."""
    from kree.mobile_bridge import _validate_pwa_token

    token_file = tmp_path / "pwa_token.json"
    token_file.write_text(json.dumps({"token": "", "expires": time.time() + 3600}))
    assert _validate_pwa_token("", token_file) is False


def test_valid_matching_token_grants_access(tmp_path):
    """A matching, non-expired token must grant access."""
    from kree.mobile_bridge import _validate_pwa_token

    secret = "valid-secret-token-abc123"
    token_file = tmp_path / "pwa_token.json"
    token_file.write_text(json.dumps({"token": secret, "expires": time.time() + 3600}))
    assert _validate_pwa_token(secret, token_file) is True


def test_wrong_token_denies_access(tmp_path):
    """A token that does not match the stored one must deny access."""
    from kree.mobile_bridge import _validate_pwa_token

    token_file = tmp_path / "pwa_token.json"
    token_file.write_text(json.dumps({"token": "correct-token", "expires": time.time() + 3600}))
    assert _validate_pwa_token("wrong-token", token_file) is False


def test_expired_token_denies_access(tmp_path):
    """An expired token must deny access even if it matches."""
    from kree.mobile_bridge import _validate_pwa_token

    secret = "expired-but-matching"
    token_file = tmp_path / "pwa_token.json"
    token_file.write_text(json.dumps({"token": secret, "expires": time.time() - 1}))
    assert _validate_pwa_token(secret, token_file) is False


def test_malformed_token_file_denies_access(tmp_path):
    """A corrupted token file must deny access, not crash or grant access."""
    from kree.mobile_bridge import _validate_pwa_token

    token_file = tmp_path / "pwa_token.json"
    token_file.write_text("NOT VALID JSON {{{{")
    assert _validate_pwa_token("any-token", token_file) is False
