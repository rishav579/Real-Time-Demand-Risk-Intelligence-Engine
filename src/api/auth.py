"""API Key authentication dependency for protecting sensitive endpoints."""

from typing import Optional
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from src.config.settings import get_settings

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: Optional[str] = Security(API_KEY_HEADER)) -> Optional[str]:
    """Verify incoming X-API-Key against configured server secret.

    If auth_enabled is False (development/testing default), requests pass through.
    If auth_enabled is True, missing or invalid API key raises HTTP 401 Unauthorized.
    """
    settings = get_settings()

    if not settings.auth_enabled:
        return api_key or "anonymous"

    if not api_key or api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key. Provide a valid 'X-API-Key' header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return api_key
