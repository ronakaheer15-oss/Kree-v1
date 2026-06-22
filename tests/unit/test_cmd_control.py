import pytest
from unittest.mock import MagicMock
from kree.actions import cmd_control

def test_ask_gemini_dependency_injection():
    mock_llm = MagicMock()
    mock_llm.generate_content.return_value.text = "mock_command /run"
    
    result = cmd_control._ask_gemini("do something", llm_client=mock_llm)
    assert result == "mock_command /run"
    
    mock_llm.generate_content.assert_called_once()
    assert "Convert this request to a single Windows CMD command." in mock_llm.generate_content.call_args[0][0]

def test_cmd_injection_blocked():
    safe, reason = cmd_control._is_safe("echo test & rm -rf /")
    assert safe is False
    assert "Blocked" in reason
    
    safe, reason = cmd_control._is_safe("ping google.com")
    assert safe is True
