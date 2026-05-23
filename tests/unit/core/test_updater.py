def test_legacy_updater_does_not_force_process_exit(monkeypatch, tmp_path):
    from kree.core import updater

    package = tmp_path / "update.zip"
    package.write_bytes(b"zip")
    called = {}

    def fake_apply_update(path):
        called["path"] = path
        return {"ok": True}

    monkeypatch.setattr("kree.core.update_service.apply_update", fake_apply_update)
    monkeypatch.setattr(updater.os, "_exit", lambda code: (_ for _ in ()).throw(AssertionError("os._exit called")))

    assert updater.run_installer_and_exit(str(package)) is True
    assert called["path"] == str(package)
