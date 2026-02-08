"""
Tests for error codes utility functions.

Tests:
- get_error_code
- get_error_description
- get_error_message
- get_error_category
- get_all_error_codes
- validate_error_code
"""
import pytest
from src.Utils.error_codes import (
    get_error_code,
    get_error_description,
    get_error_message,
    get_error_category,
    get_all_error_codes,
    validate_error_code,
    ERROR_CODES
)


def test_get_error_code_valid():
    """Test that get_error_code returns UUID for valid error codes"""
    code = get_error_code("INVALID_EMAIL")
    assert code is not None
    assert isinstance(code, str)
    # Should be a UUID format
    assert len(code) == 36  # UUID string length
    assert code.count('-') == 4


def test_get_error_code_invalid():
    """Test that get_error_code returns input for invalid codes"""
    invalid_code = "NONEXISTENT_ERROR"
    result = get_error_code(invalid_code)
    assert result == invalid_code


def test_get_error_code_stable():
    """Test that error codes are stable (same UUID for same code)"""
    code1 = get_error_code("INVALID_EMAIL")
    code2 = get_error_code("INVALID_EMAIL")
    assert code1 == code2, "Error codes should be stable"


def test_get_error_description():
    """Test that get_error_description returns description"""
    description = get_error_description("INVALID_EMAIL")
    assert description is not None
    assert isinstance(description, str)
    assert len(description) > 0


def test_get_error_message():
    """Test that get_error_message returns short message"""
    message = get_error_message("INVALID_EMAIL")
    assert message is not None
    assert isinstance(message, str)
    assert len(message) > 0


def test_get_error_category():
    """Test that get_error_category returns category"""
    category = get_error_category("INVALID_EMAIL")
    assert category is not None
    assert isinstance(category, str)
    assert category in ["validation", "authentication", "authorization", "not_found", "constraint", "concurrency", "business_logic"]


def test_get_all_error_codes():
    """Test that get_all_error_codes returns all codes"""
    all_codes = get_all_error_codes()
    assert isinstance(all_codes, dict)
    assert len(all_codes) > 0
    assert "INVALID_EMAIL" in all_codes


def test_validate_error_code_valid():
    """Test that validate_error_code returns True for valid codes"""
    assert validate_error_code("INVALID_EMAIL") is True


def test_validate_error_code_invalid():
    """Test that validate_error_code returns False for invalid codes"""
    assert validate_error_code("NONEXISTENT_ERROR") is False


def test_all_error_codes_have_uuid():
    """Test that all error codes have UUID"""
    for code_name, code_data in ERROR_CODES.items():
        assert "uuid" in code_data, f"Error code {code_name} should have UUID"
        uuid_str = code_data["uuid"]
        assert isinstance(uuid_str, str)
        assert len(uuid_str) == 36  # UUID string length


def test_all_error_codes_have_message():
    """Test that all error codes have message"""
    for code_name, code_data in ERROR_CODES.items():
        assert "message" in code_data, f"Error code {code_name} should have message"
        assert isinstance(code_data["message"], str)
        assert len(code_data["message"]) > 0
