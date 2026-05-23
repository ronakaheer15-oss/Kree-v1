import asyncio
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


class _DummyWriter:
    def __init__(self):
        self.data = bytearray()
        self.closed = False
        self.peername = ("127.0.0.1", 55555)

    def write(self, payload):
        self.data.extend(payload)

    async def drain(self):
        return None

    def close(self):
        self.closed = True

    def get_extra_info(self, name):
        if name == "peername":
            return self.peername
        return None


def _reader_with(payload: bytes) -> asyncio.StreamReader:
    reader = asyncio.StreamReader()
    reader.feed_data(payload)
    reader.feed_eof()
    return reader


async def _handle_payload(bridge, payload: bytes, writer: _DummyWriter):
    reader = _reader_with(payload)
    await bridge.handle_client(reader, writer)


def _run_bridge(bridge, payload: bytes, writer: _DummyWriter):
    asyncio.run(_handle_payload(bridge, payload, writer))


def _websocket_request(*, authorization: str = "") -> bytes:
    headers = [
        "GET / HTTP/1.1",
        "Host: 127.0.0.1:8443",
        "Upgrade: websocket",
        "Connection: Upgrade",
        "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==",
        "Sec-WebSocket-Version: 13",
    ]
    if authorization:
        headers.append(f"Authorization: {authorization}")
    return ("\r\n".join(headers) + "\r\n\r\n").encode("ascii")


def _masked_frame(opcode: int, payload: bytes = b"") -> bytes:
    mask = b"\x01\x02\x03\x04"
    length = len(payload)
    if length >= 126:
        raise AssertionError("test helper only supports short frames")
    masked = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
    return bytes([0x80 | opcode, 0x80 | length]) + mask + masked


def _masked_json(payload: dict) -> bytes:
    return _masked_frame(0x1, json.dumps(payload).encode("utf-8"))


def test_browser_pwa_auth_frame_is_allowed_after_upgrade(tmp_path, monkeypatch):
    from kree import mobile_bridge
    from kree.mobile_bridge import KreeMobileBridge

    secret = "valid-browser-token"
    token_file = tmp_path / "pwa_token.json"
    token_file.write_text(json.dumps({"token": secret, "expires": time.time() + 3600}))
    monkeypatch.setattr(mobile_bridge, "_get_pwa_token_file", lambda: token_file)

    connected = []
    bridge = KreeMobileBridge(on_connect_callback=lambda peer: connected.append(peer))
    writer = _DummyWriter()
    payload = (
        _websocket_request()
        + _masked_json({"type": "auth", "token": secret})
        + _masked_json({"type": "device_info", "os": "iOS", "agent": "test-browser"})
        + _masked_frame(0x8)
    )

    _run_bridge(bridge, payload, writer)

    response = bytes(writer.data)
    assert b"HTTP/1.1 101 Switching Protocols" in response
    assert b"HTTP/1.1 403 Forbidden" not in response
    assert connected == [writer.peername]
    assert writer.closed is True
    assert writer not in bridge.clients


def test_browser_pwa_invalid_first_auth_frame_closes_after_upgrade(tmp_path, monkeypatch):
    from kree import mobile_bridge
    from kree.mobile_bridge import KreeMobileBridge

    token_file = tmp_path / "pwa_token.json"
    token_file.write_text(json.dumps({"token": "correct-token", "expires": time.time() + 3600}))
    monkeypatch.setattr(mobile_bridge, "_get_pwa_token_file", lambda: token_file)

    connected = []
    bridge = KreeMobileBridge(on_connect_callback=lambda peer: connected.append(peer))
    writer = _DummyWriter()
    payload = (
        _websocket_request()
        + _masked_json({"type": "auth", "token": "wrong-token"})
        + _masked_frame(0x8)
    )

    _run_bridge(bridge, payload, writer)

    response = bytes(writer.data)
    assert b"HTTP/1.1 101 Switching Protocols" in response
    assert b"HTTP/1.1 403 Forbidden" not in response
    assert b"\x88" in response
    assert connected == []


def test_native_invalid_authorization_header_is_rejected_before_upgrade(tmp_path, monkeypatch):
    from kree import mobile_bridge
    from kree.mobile_bridge import KreeMobileBridge

    token_file = tmp_path / "pwa_token.json"
    token_file.write_text(json.dumps({"token": "correct-token", "expires": time.time() + 3600}))
    monkeypatch.setattr(mobile_bridge, "_get_pwa_token_file", lambda: token_file)

    bridge = KreeMobileBridge()
    writer = _DummyWriter()
    _run_bridge(bridge, _websocket_request(authorization="Bearer wrong-token"), writer)

    response = bytes(writer.data)
    assert b"HTTP/1.1 403 Forbidden" in response
    assert b"HTTP/1.1 101 Switching Protocols" not in response
