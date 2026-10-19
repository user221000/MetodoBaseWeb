"""Relative first-party navigation values for external billing capabilities."""
from urllib.parse import urlsplit


def private_return_path(value):
    """Keep the configured origin authoritative; reject rather than repair."""
    if (not isinstance(value, str) or not 1 <= len(value) <= 500
            or not value.startswith("/") or value.startswith("//") or "\\" in value
            or any(ord(char) <= 32 or ord(char) == 127 for char in value)):
        raise ValueError("Return path must be a relative application path")
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc:
        raise ValueError("Return path must not supply an origin")
    return value
