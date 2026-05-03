"""Integration test: user command flows through planner → executor → action result.

All external API calls (Gemini, Playwright) are mocked at the network boundary.
"""
import json
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture()
def fake_api_config(tmp_path):
    cfg = tmp_path / "api_keys.json"
    cfg.write_text(json.dumps({"gemini_api_key": "test-key"}))
    return cfg


def _make_gemini_mock(plan_json: str):
    client = MagicMock()
    resp = MagicMock()
    resp.text = plan_json
    client.models.generate_content.return_value = resp
    return client


@pytest.mark.integration
def test_planner_returns_valid_plan_for_web_search_goal(fake_api_config, monkeypatch):
    monkeypatch.setattr("kree.agent.planner.API_CONFIG_PATH", fake_api_config)
    plan_json = json.dumps({
        "goal": "what is the weather in London",
        "steps": [
            {"step": 1, "tool": "web_search", "description": "weather London",
             "parameters": {"query": "weather London today"}, "critical": True}
        ]
    })
    mock_client = _make_gemini_mock(plan_json)
    with patch("google.genai.Client", return_value=mock_client):
        from kree.agent.planner import create_plan
        plan = create_plan("what is the weather in London")

    assert plan["steps"][0]["tool"] == "web_search"
    assert "London" in plan["steps"][0]["parameters"]["query"]


@pytest.mark.integration
def test_planner_blocks_generated_code_tool(fake_api_config, monkeypatch):
    monkeypatch.setattr("kree.agent.planner.API_CONFIG_PATH", fake_api_config)
    bad_plan = json.dumps({
        "goal": "run a script",
        "steps": [
            {"step": 1, "tool": "generated_code", "description": "do something",
             "parameters": {}, "critical": True}
        ]
    })
    mock_client = _make_gemini_mock(bad_plan)
    with patch("google.genai.Client", return_value=mock_client):
        from kree.agent.planner import create_plan
        plan = create_plan("run a script")

    assert all(s["tool"] != "generated_code" for s in plan["steps"])


@pytest.mark.integration
def test_sanitizer_blocks_dangerous_commands_before_executor():
    from kree.core.sanitizer import sanitize_command
    commands = ["rm -rf /tmp", "format c:", "del /s /q C:\\Windows", "wipe disk"]
    for cmd in commands:
        text, err = sanitize_command(cmd)
        assert text is None, f"Expected '{cmd}' to be blocked"
        assert err is not None
