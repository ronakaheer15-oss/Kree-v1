def test_llm_gateway_module_importable():
    from kree.core import llm_gateway
    assert llm_gateway is not None


def test_llm_gateway_has_expected_interface():
    import inspect
    from kree.core import llm_gateway
    members = dir(llm_gateway)
    callables = [m for m in members if not m.startswith("_") and callable(getattr(llm_gateway, m))]
    assert len(callables) > 0, "llm_gateway exposes no public callables"
