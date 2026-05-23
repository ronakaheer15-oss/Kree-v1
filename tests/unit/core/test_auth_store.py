def test_auth_store_creates_user_without_bootstrap_pin(tmp_path, monkeypatch):
    from kree.core import auth_store

    monkeypatch.setattr(auth_store, "AUTH_FILE", tmp_path / "user_auth.json")
    monkeypatch.setattr(auth_store, "USER_SECRETS_DIR", tmp_path / "user_secrets")
    monkeypatch.setattr(auth_store, "LEGACY_API_FILE", tmp_path / "api_keys.json")

    result = auth_store.create_user("alice", "correct horse battery staple")
    user_id = result["user"]["user_id"]
    raw = auth_store._load_state()["users"][0]

    assert result["next_stage"] == "pin_setup"
    assert auth_store.get_auth_state()["bootstrap_pin"] is None
    assert raw["pin_hash"] == ""
    assert auth_store.verify_user_pin(user_id, "143211")["ok"] is False


def test_auth_store_saves_user_api_key_only_to_user_secret(tmp_path, monkeypatch):
    from kree.core import auth_store

    monkeypatch.setattr(auth_store, "AUTH_FILE", tmp_path / "user_auth.json")
    monkeypatch.setattr(auth_store, "USER_SECRETS_DIR", tmp_path / "user_secrets")
    monkeypatch.setattr(auth_store, "LEGACY_API_FILE", tmp_path / "api_keys.json")
    monkeypatch.setattr(auth_store.vault, "save_api_key", lambda path, key: path.write_text(key, encoding="utf-8"))
    monkeypatch.setattr(auth_store.vault, "load_api_key", lambda path: path.read_text(encoding="utf-8") if path.exists() else "")

    user_id = auth_store.create_user("alice", "correct horse battery staple")["user"]["user_id"]
    auth_store.save_user_api_key(user_id, "secret")

    assert auth_store.get_user_secret_path(user_id).read_text(encoding="utf-8") == "secret"
    assert not auth_store.LEGACY_API_FILE.exists()
