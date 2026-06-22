import pytest
from kree.actions.math_helper import calculate

def test_calculate_basic():
    assert calculate("2 + 2") == "4"
    assert calculate("10 - 3") == "7"
    assert calculate("4 * 5") == "20"
    assert calculate("20 / 4") == "5"

def test_calculate_advanced():
    assert calculate("2 ** 3") == "8"
    assert calculate("10 % 3") == "1"
    assert calculate("-(5 + 5)") == "-10"
    assert calculate("2 * (3 + 4)") == "14"

def test_calculate_zero_division():
    assert "division by zero" in calculate("1 / 0").lower()
    assert "modulo by zero" in calculate("1 % 0").lower()

def test_calculate_rejected():
    assert "error" in calculate("import os").lower()
    assert "error" in calculate("eval('1+1')").lower()
    assert "error" in calculate("x = 10").lower()
    assert "error" in calculate("open('test.txt')").lower()
