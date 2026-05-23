from collections import Counter


def test_tool_declarations_have_unique_names():
    from kree.core.tool_registry import TOOL_DECLARATIONS

    names = [tool["name"] for tool in TOOL_DECLARATIONS]
    duplicates = [name for name, count in Counter(names).items() if count > 1]

    assert duplicates == []
