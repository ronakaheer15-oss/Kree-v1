def test_file_controller_module_importable():
    from kree.actions import file_controller
    assert file_controller is not None


def test_file_controller_action_callable():
    from kree.actions.file_controller import file_controller
    assert callable(file_controller)
