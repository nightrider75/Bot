"""Platform authentication configuration routes.

This module provides API endpoints for reading HTTP Basic Auth credentials.
Auth credentials are configured via environment variables (AUTH_USERNAME and AUTH_PASSWORD).
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from bot.config import settings

router = APIRouter()


class AuthConfigResponse(BaseModel):
    """Response model for auth configuration."""

    username: str = Field(
        ..., description="Current username from environment variables"
    )
    password: str = Field(..., description="Current password (masked for security)")


@router.get("/auth", response_model=AuthConfigResponse)
async def get_auth_config_endpoint():
    """Get current platform auth configuration.

    Returns the current username and a masked password indication.
    Credentials are loaded from environment variables (AUTH_USERNAME and AUTH_PASSWORD).
    """
    try:
        username = settings.auth_username
        password = settings.auth_password
        # Don't expose the actual password, just indicate it's set
        return AuthConfigResponse(
            username=username,
            password="***" if password else "",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve auth config: {str(e)}",
        )
