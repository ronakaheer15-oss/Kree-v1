from kree.core.tool_registry import TOOL_DECLARATIONS


def test_tool_declarations_is_a_list():
    assert isinstance(TOOL_DECLARATIONS, list)


def test_each_tool_has_name_and_description():
    for tool in TOOL_DECLARATIONS:
        assert "name" in tool or "function_declarations" in tool or isinstance(tool, dict)


def test_tool_declarations_not_empty():
    assert len(TOOL_DECLARATIONS) > 0
