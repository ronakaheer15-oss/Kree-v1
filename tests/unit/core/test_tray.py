from pathlib import Path

import pytest


pytest.importorskip("pystray")

from kree.core import tray


def test_tray_fallback_icon_is_cached(monkeypatch):
    tray._FALLBACK_ICONS.clear()
    calls = []

    def fake_create(color):
        calls.append(color)
        return object()

    monkeypatch.setattr(tray, "_create_fallback_icon", fake_create)

    first = tray._get_fallback_icon("gray")
    second = tray._get_fallback_icon("gray")

    assert first is second
    assert calls == ["gray"]


def test_load_icon_uses_fallback_for_missing_asset(monkeypatch):
    tray._FALLBACK_ICONS.clear()
    fallback = object()

    def fake_open(path):
        raise FileNotFoundError(path)

    monkeypatch.setattr(tray.Image, "open", fake_open)
    monkeypatch.setattr(tray, "_get_fallback_icon", lambda color: fallback)

    assert tray._load_icon(Path("missing.png"), "gray") is fallback
