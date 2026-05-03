import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


@pytest.fixture()
def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


@pytest.fixture()
def tmp_config_dir(tmp_path: Path) -> Path:
    """Temporary config directory pre-populated with required JSON stubs."""
    cfg = tmp_path / "config"
    cfg.mkdir()
    (cfg / "api_keys.json").write_text('{"gemini_api_key": "test-key"}')
    (cfg / "audio_settings.json").write_text('{"tts_speed": 1.0, "wake_word": "hey kree"}')
    return cfg


@pytest.fixture()
def mock_gemini(monkeypatch):
    """Patch google.genai so no real API calls are made."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"goal": "test", "steps": [{"step": 1, "tool": "web_search", "description": "search", "parameters": {"query": "test"}, "critical": true}]}'
    mock_client.models.generate_content.return_value = mock_response

    with patch("google.genai.Client", return_value=mock_client):
        yield mock_client


@pytest.fixture()
def mock_vault(monkeypatch):
    """Patch kree.core.vault so memory tests don't require encryption keys."""
    with patch("kree.core.vault.encrypt_data", side_effect=lambda s: s.encode()), \
         patch("kree.core.vault.decrypt_data", side_effect=lambda b: b.decode()):
        yield
