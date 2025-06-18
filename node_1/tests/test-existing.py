import pytest
from test_script import calculate_discount


def test_calculate_discount_basic():
    '''Test basic discount calculation'''
    result = calculate_discount(100.0, 20)
    assert result == (80.0, 20.0)


def test_calculate_discount_zero():
    '''Test zero discount'''
    result = calculate_discount(50.0, 0)
    assert result == (50.0, 0.0)