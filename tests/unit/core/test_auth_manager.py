def test_auth_manager_module_importable():
    from kree.core import auth_manager
    assert auth_manager is not None


def test_auth_manager_has_public_functions():
    import inspect
    from kree.core import auth_manager
    public = [n for n, _ in inspect.getmembers(auth_manager, inspect.isfunction)
              if not n.startswith("_")]
    assert len(public) > 0, "auth_manager exposes no public functions"
