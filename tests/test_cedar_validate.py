import pytest
from app.cedar_validate import validate_cedar_policy, CedarValidationError

VALID_POLICY = b'permit(principal == User::"alice", action == Action::"view", resource == Photo::"vacation.jpg");'


def test_valid_policy_is_accepted():
    text = validate_cedar_policy(VALID_POLICY)
    assert "permit" in text


def test_invalid_syntax_is_rejected():
    with pytest.raises(CedarValidationError, match="Invalid Cedar policy syntax"):
        validate_cedar_policy(b"this is not cedar { garbage")


def test_empty_file_is_rejected():
    with pytest.raises(CedarValidationError, match="empty"):
        validate_cedar_policy(b"")


def test_non_utf8_is_rejected():
    with pytest.raises(CedarValidationError, match="not valid UTF-8"):
        validate_cedar_policy(b"\xff\xfe\x00\x01")