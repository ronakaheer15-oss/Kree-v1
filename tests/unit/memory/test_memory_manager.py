import json
import pytest
from unittest.mock import patch
from kree.memory.memory_manager import (
    _empty_memory,
    _recursive_update,
    format_memory_for_prompt,
)


def test_empty_memory_has_required_keys():
    mem = _empty_memory()
    assert set(mem.keys()) == {"identity", "preferences", "relationships", "notes"}


def test_recursive_update_adds_new_key():
    target = _empty_memory()
    _recursive_update(target["identity"], {"name": "Alice"})
    assert target["identity"]["name"]["value"] == "Alice"


def test_recursive_update_skips_none_values():
    target = {"key": {"value": "existing"}}
    changed = _recursive_update(target, {"key": None})
    assert not changed
    assert target["key"]["value"] == "existing"


def test_recursive_update_skips_empty_strings():
    target = {}
    changed = _recursive_update(target, {"name": "   "})
    assert not changed


def test_recursive_update_truncates_long_values():
    target = {}
    with patch("kree.core.security.scrub_pii", side_effect=lambda x: x):
        long_val = "x" * 400
        _recursive_update(target, {"note": long_val})
    value = target["note"]["value"]
    assert len(value) <= 305  # 300 chars + ellipsis


def test_format_memory_for_prompt_returns_empty_on_empty():
    result = format_memory_for_prompt({})
    assert result == ""


def test_format_memory_for_prompt_includes_name():
    mem = {
        "identity": {"name": {"value": "Alice"}},
        "preferences": {},
        "relationships": {},
        "notes": {}
    }
    result = format_memory_for_prompt(mem)
    assert "Alice" in result
    assert result.startswith("[USER MEMORY]")
