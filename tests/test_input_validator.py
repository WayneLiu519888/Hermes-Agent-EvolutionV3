import pytest
from evolution.security.input_validator import InputValidator


def test_validate_tool_name_valid():
    r = InputValidator.validate_tool_name("my_tool-01")
    assert r.valid


def test_validate_tool_name_invalid():
    r = InputValidator.validate_tool_name("")
    assert not r.valid


def test_sanitize_error():
    msg = InputValidator.sanitize_error_message(Exception("/home/user/secret/config.yaml"))
    assert "/home/user/" not in msg
