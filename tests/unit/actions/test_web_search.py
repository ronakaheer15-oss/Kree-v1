def test_web_search_module_importable():
    from kree.actions import web_search
    assert web_search is not None


def test_web_search_action_callable():
    from kree.actions.web_search import web_search
    assert callable(web_search)
