"""Integration test: memory read/write cycle through the full memory stack."""
import json
import pytest
from unittest.mock import patch
from pathlib import Path


@pytest.fixture()
def isolated_memory(tmp_path, monkeypatch):
    """Point the memory manager at a temp dir with no encryption."""
    mem_file = tmp_path / "long_term.json"
    monkeypatch.setattr("kree.memory.memory_manager.MEMORY_PATH", mem_file)
    with patch("kree.core.vault.encrypt_data", side_effect=lambda s: s.encode()), \
         patch("kree.core.vault.decrypt_data", side_effect=lambda b: b.decode()), \
         patch("kree.core.security.scrub_pii", side_effect=lambda x: x):
        yield mem_file


@pytest.mark.integration
def test_update_memory_persists_to_disk(isolated_memory):
    from kree.memory.memory_manager import update_memory, load_memory

    update_memory({"identity": {"name": "Bob"}})
    loaded = load_memory()

    assert loaded["identity"]["name"]["value"] == "Bob"


@pytest.mark.integration
def test_update_memory_is_idempotent(isolated_memory):
    from kree.memory.memory_manager import update_memory, load_memory

    update_memory({"identity": {"name": "Bob"}})
    update_memory({"identity": {"name": "Bob"}})
    loaded = load_memory()

    assert loaded["identity"]["name"]["value"] == "Bob"


@pytest.mark.integration
def test_format_memory_for_prompt_uses_saved_data(isolated_memory):
    from kree.memory.memory_manager import update_memory, load_memory, format_memory_for_prompt

    update_memory({"identity": {"name": "Carol", "city": "London"}})
    mem = load_memory()
    prompt_text = format_memory_for_prompt(mem)

    assert "Carol" in prompt_text
    assert "London" in prompt_text
