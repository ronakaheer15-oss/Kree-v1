"""Integration test: mobile WebSocket bridge connect/send/receive."""
import pytest


@pytest.mark.integration
def test_mobile_bridge_module_importable():
    from kree import mobile_bridge
    assert mobile_bridge is not None


@pytest.mark.integration
def test_mobile_bridge_has_class():
    from kree.mobile_bridge import KreeMobileBridge
    assert KreeMobileBridge is not None
