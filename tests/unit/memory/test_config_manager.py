def test_config_manager_importable():
    from kree.memory import config_manager
    assert config_manager is not None


def test_load_audio_settings_returns_dict(tmp_path, monkeypatch):
    import json
    cfg = tmp_path / "audio_settings.json"
    cfg.write_text(json.dumps({"tts_speed": 1.2}))
    monkeypatch.setattr("kree.memory.config_manager.CONFIG_DIR", tmp_path)
    from kree.memory.config_manager import load_audio_settings
    result = load_audio_settings()
    assert isinstance(result, dict)
