import pytest
from unittest.mock import MagicMock
import sys
import main

def test_registry_enumeration_uses_queryinfokey(monkeypatch):
    import winreg
    
    # Mock winreg behavior for check_chromium
    mock_queryinfokey = MagicMock(return_value=(2, 0, 0)) # 2 subkeys
    mock_enumkey = MagicMock(side_effect=["GUID-1", "GUID-2"])
    mock_openkey = MagicMock()
    
    # Simulate that the first GUID does not have a 'pv' value, but the second does
    mock_queryvalueex = MagicMock(side_effect=[OSError("Not found"), ("1.2.3.4", 1)])
    
    monkeypatch.setattr(winreg, "QueryInfoKey", mock_queryinfokey)
    monkeypatch.setattr(winreg, "EnumKey", mock_enumkey)
    monkeypatch.setattr(winreg, "OpenKey", mock_openkey)
    monkeypatch.setattr(winreg, "QueryValueEx", mock_queryvalueex)
    monkeypatch.setattr(winreg, "CloseKey", MagicMock())
    
    # Force platform to windows so the check actually runs
    monkeypatch.setattr("sys.platform", "win32")
    
    found, msg = main.check_chromium()
    
    assert found is True
    assert "Edge WebView2 Runtime v1.2.3.4 detected" in msg
    
    # Verify that the query info key optimization was actually used instead of while True
    mock_queryinfokey.assert_called()
    assert mock_enumkey.call_count == 2
