import re
from typing import Any

NAME_MAX_LENGTH = 255
TITLE_MAX_LENGTH = 255


def normalize_string(v: Any) -> str:
    """Strip whitespace and ensure string is non-empty."""
    if not isinstance(v, str):
        raise ValueError("Field must be a valid string")
    cleaned = v.strip()
    if not cleaned:
        raise ValueError("Field cannot be empty or only whitespace")
    return cleaned


def normalize_email(v: Any) -> str:
    """Normalize email to lower case after validation."""
    if not isinstance(v, str):
        raise ValueError("Email must be a valid string")
    return v.strip().lower()
