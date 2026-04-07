"""
utils/auth.py
-------------
Simple API-key authentication.

Valid keys are loaded from the VALID_API_KEYS environment variable
(comma-separated) or fall back to a hard-coded development key.

Usage:
    from utils.auth import verify_api_key
    verify_api_key(x_api_key)   # raises HTTPException(401) if invalid
"""

import logging
import os

from fastapi import HTTPException

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Load valid keys from environment (comma-separated list)
# Default includes a dev key so the project runs out of the box.
# ---------------------------------------------------------------------------
_raw_keys = os.getenv("VALID_API_KEYS", "dev-key-12345,test-key-67890")
VALID_API_KEYS: set[str] = {k.strip() for k in _raw_keys.split(",") if k.strip()}

logger.info("Auth module loaded. %d valid API key(s) configured.", len(VALID_API_KEYS))


def verify_api_key(api_key: str) -> None:
    """
    Validates the provided API key.

    Raises:
        HTTPException(401): when the key is missing or not recognised.
    """
    if not api_key or api_key.strip() not in VALID_API_KEYS:
        logger.warning("Unauthorised request — invalid API key provided.")
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key. Pass a valid key in the X-API-Key header.",
        )
