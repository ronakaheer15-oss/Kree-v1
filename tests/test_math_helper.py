import pytest
from kree.actions.math_helper import calculate

@pytest.mark.parametrize("expr, expected", [
    ("2 + 2", "4"),
    ("10 - 3", "7"),
    ("4 * 5", "20"),
    ("20 / 4", "5"),
    ("2 ** 3", "8"),
    ("10 % 3", "1"),
    ("-(5 + 5)", "-10"),
    ("2 * (3 + 4)", "14"),
    ("1 / 0", "Error: Division by zero"),
    ("import os", "Error: "),
    ("eval('1+1')", "Error: Unsupported syntax: Call"),
])
def test_math_helper(expr, expected):
    res = calculate(expr)
    assert expected in res or res == expected
