"""Public links use the configured origin, never request Host/Origin headers."""
from urllib.parse import urlsplit, urlunsplit


def public_origin(settings=None):
    if settings is None:
        from web.settings import get_settings
        settings = get_settings()
    value = getattr(settings, "BASE_URL", "")
    try:
        if not isinstance(value, str) or any(ord(char) < 33 or ord(char) == 127 for char in value):
            raise ValueError("Invalid public origin")
        parsed = urlsplit(value)
        if (not parsed.hostname or parsed.username or parsed.password
                or parsed.path not in {"", "/"} or parsed.query or parsed.fragment
                or "\\" in parsed.netloc or "%" in parsed.netloc
                or parsed.scheme not in {"https", "http"}
                or (parsed.scheme == "http" and (getattr(settings, "is_production", False)
                    or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}))):
            raise ValueError("Invalid public origin")
        _ = parsed.port
        return urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("Public origin configuration is invalid") from None
