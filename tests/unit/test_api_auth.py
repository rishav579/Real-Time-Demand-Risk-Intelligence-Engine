"""Unit tests for API key verification and authentication policies."""

from fastapi import HTTPException
import pytest

from src.api.auth import verify_api_key
from src.config.settings import Settings, get_settings


def test_auth_disabled_allows_anonymous_requests(monkeypatch):
    """When auth_enabled is False, any request is allowed."""
    monkeypatch.setattr("src.api.auth.get_settings", lambda: Settings(auth_enabled=False))
    result = verify_api_key(api_key=None)
    assert result == "anonymous"


def test_auth_enabled_valid_key_succeeds(monkeypatch):
    """When auth_enabled is True, matching key passes verification."""
    monkeypatch.setattr(
        "src.api.auth.get_settings",
        lambda: Settings(auth_enabled=True, api_key="valid-test-key"),
    )
    result = verify_api_key(api_key="valid-test-key")
    assert result == "valid-test-key"


def test_auth_enabled_missing_key_raises_401(monkeypatch):
    """When auth_enabled is True, missing key raises HTTP 401."""
    monkeypatch.setattr(
        "src.api.auth.get_settings",
        lambda: Settings(auth_enabled=True, api_key="valid-test-key"),
    )
    with pytest.raises(HTTPException) as exc_info:
        verify_api_key(api_key=None)
    assert exc_info.value.status_code == 401
    assert "Invalid or missing API key" in exc_info.value.detail


def test_auth_enabled_invalid_key_raises_401(monkeypatch):
    """When auth_enabled is True, incorrect key raises HTTP 401."""
    monkeypatch.setattr(
        "src.api.auth.get_settings",
        lambda: Settings(auth_enabled=True, api_key="valid-test-key"),
    )
    with pytest.raises(HTTPException) as exc_info:
        verify_api_key(api_key="incorrect-key")
    assert exc_info.value.status_code == 401
    assert "Invalid or missing API key" in exc_info.value.detail
