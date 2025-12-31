"""HTTP Basic Authentication module for the bot orchestration system."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from bot.config import settings

security = HTTPBasic()


def get_current_username(
    credentials: Annotated[HTTPBasicCredentials, Depends(security)],
) -> str:
    """Verify HTTP Basic Auth credentials and return username if valid.

    Credentials are loaded from settings (environment variables).

    Args:
        credentials: HTTP Basic Auth credentials from the request

    Returns:
        The username if credentials are valid

    Raises:
        HTTPException: If credentials are invalid (401 Unauthorized)
    """

    if (
        credentials.username != settings.auth_username
        or credentials.password != settings.auth_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
