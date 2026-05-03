import json
from unittest.mock import MagicMock, patch
import pytest
from kree.agent.planner import create_plan, _fallback_plan


def _make_mock_client(response_text: str):
    client = MagicMock()
    response = MagicMock()
    response.text = response_text
    client.models.generate_content.return_value = response
    return client


VALID_PLAN_JSON = json.dumps({
    "goal": "search the web",
    "steps": [
        {"step": 1, "tool": "web_search", "description": "search", "parameters": {"query": "test"}, "critical": True}
    ]
})


def test_create_plan_returns_dict_with_steps(tmp_path, monkeypatch):
    (tmp_path / "api_keys.json").write_text('{"gemini_api_key": "k"}')
    monkeypatch.setattr("kree.agent.planner.API_CONFIG_PATH", tmp_path / "api_keys.json")

    mock_client = _make_mock_client(VALID_PLAN_JSON)
    with patch("google.genai.Client", return_value=mock_client):
        plan = create_plan("search the web")

    assert "steps" in plan
    assert len(plan["steps"]) >= 1
    assert plan["steps"][0]["tool"] == "web_search"


def test_create_plan_falls_back_on_json_error(tmp_path, monkeypatch):
    (tmp_path / "api_keys.json").write_text('{"gemini_api_key": "k"}')
    monkeypatch.setattr("kree.agent.planner.API_CONFIG_PATH", tmp_path / "api_keys.json")

    mock_client = _make_mock_client("not valid json {{{{")
    with patch("google.genai.Client", return_value=mock_client):
        plan = create_plan("some goal")

    assert "steps" in plan
    assert plan["steps"][0]["tool"] == "web_search"


def test_fallback_plan_wraps_goal_in_web_search():
    plan = _fallback_plan("find the weather")
    assert plan["goal"] == "find the weather"
    assert plan["steps"][0]["tool"] == "web_search"
    assert "find the weather" in plan["steps"][0]["parameters"]["query"]


def test_generated_code_tool_is_replaced(tmp_path, monkeypatch):
    (tmp_path / "api_keys.json").write_text('{"gemini_api_key": "k"}')
    monkeypatch.setattr("kree.agent.planner.API_CONFIG_PATH", tmp_path / "api_keys.json")

    bad_plan = json.dumps({
        "goal": "run code",
        "steps": [{"step": 1, "tool": "generated_code", "description": "do something", "parameters": {}, "critical": True}]
    })
    mock_client = _make_mock_client(bad_plan)
    with patch("google.genai.Client", return_value=mock_client):
        plan = create_plan("run code")

    assert all(s["tool"] != "generated_code" for s in plan["steps"])
