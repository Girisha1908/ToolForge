import os
from typing import Optional

from fastapi import Header, HTTPException, status

API_KEY_HEADER_NAME = "X-ToolForge-Key"


def verify_api_key(x_toolforge_key: Optional[str] = Header(default=None, alias=API_KEY_HEADER_NAME)) -> None:
    """
    Lightweight shared-secret check for ToolForge's own API.

    If TOOLFORGE_API_KEY is unset (e.g. local dev), auth is disabled entirely so the
    existing dev workflow keeps working without configuration. When set, every protected
    request must present a matching X-ToolForge-Key header.
    """
    expected = os.environ.get("TOOLFORGE_API_KEY")
    if not expected:
        return

    if not x_toolforge_key or x_toolforge_key != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid API key.")
