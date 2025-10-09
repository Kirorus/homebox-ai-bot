"""
Simple test to verify testing setup works
"""

import pytest


def test_basic_functionality():
    """Test that basic functionality works"""
    assert 1 + 1 == 2
    assert "hello" in "hello world"


def test_string_operations():
    """Test string operations"""
    text = "HomeBox AI Bot"
    assert len(text) == 14
    assert "AI" in text
    assert text.lower() == "homebox ai bot"


def test_list_operations():
    """Test list operations"""
    items = ["apple", "banana", "orange"]
    assert len(items) == 3
    assert "apple" in items
    assert items[0] == "apple"


@pytest.mark.parametrize("input_val,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
    (0, 0),
])
def test_parametrized_doubling(input_val, expected):
    """Test parametrized doubling function"""
    result = input_val * 2
    assert result == expected


def test_exception_handling():
    """Test exception handling"""
    def divide(a, b):
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b
    
    # Test normal case
    result = divide(10, 2)
    assert result == 5
    
    # Test exception case
    with pytest.raises(ValueError, match="Cannot divide by zero"):
        divide(10, 0)
