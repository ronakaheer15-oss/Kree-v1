def test_auth_manager_module_importable():
    from kree.core import auth_manager
    assert auth_manager is not None


def test_auth_manager_has_public_functions():
    import inspect
    from kree.core import auth_manager
    public = [n for n, _ in inspect.getmembers(auth_manager, inspect.isfunction)
              if not n.startswith("_")]
    assert len(public) > 0, "auth_manager exposes no public functions"


def test_auth_manager_hashes_are_salted_and_verifiable():
    from kree.core import auth_manager

    first = auth_manager.hash_string("secret")
    second = auth_manager.hash_string("secret")

    assert first != second
    assert first.startswith("pbkdf2_sha256$")
    assert auth_manager._verify_hash("secret", first) is True
    assert auth_manager._verify_hash("wrong", first) is False


def test_auth_manager_saves_users_atomically_and_signs_in(tmp_path, monkeypatch):
    from kree.core import auth_manager

    users_file = tmp_path / "users.json"
    monkeypatch.setattr(auth_manager, "USERS_FILE", users_file)

    result = auth_manager.AuthManager.create_user("alice", "correct horse battery staple")
    assert result["ok"] is True

    stored = users_file.read_text(encoding="utf-8")
    assert "pbkdf2_sha256$" in stored
    assert not users_file.with_suffix(".json.tmp").exists()
    assert auth_manager.AuthManager.sign_in_user("alice", "correct horse battery staple")["ok"] is True
    assert auth_manager.AuthManager.sign_in_user("alice", "wrong password")["ok"] is False
