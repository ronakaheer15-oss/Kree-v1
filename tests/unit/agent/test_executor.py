def test_executor_module_importable():
    from kree.agent import executor
    assert executor is not None


def test_get_api_key_reads_from_config(tmp_path, monkeypatch):
    cfg = tmp_path / "api_keys.json"
    cfg.write_text('{"gemini_api_key": "abc123"}')
    monkeypatch.setattr("kree.agent.executor.API_CONFIG_PATH", cfg)
    from kree.agent.executor import _get_api_key
    assert _get_api_key() == "abc123"
