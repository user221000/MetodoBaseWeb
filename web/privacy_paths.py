"""Finite39 routes; private redirects never become admitted POSTs."""
import re

REQUESTS = "/api/account/privacy/requests"
PERSONAL_FACTS = "/api/account/privacy/personal-facts"
_REQUEST = re.compile(r"/api/account/privacy/requests/[0-9a-f]{32}")
_CLOSE = re.compile(r"/api/account/privacy/requests/[0-9a-f]{32}/close-account")


def is_privacy_close(path):
    return _CLOSE.fullmatch(path) is not None


def is_privacy_post(path):
    return path == REQUESTS or is_privacy_close(path)


def is_privacy_post_boundary(path):
    # Admission still checks the original path and refuses even one slash.
    return is_privacy_post(path[:-1] if path.endswith("/") else path)


def is_privacy_private(path):
    path = path[:-1] if path.endswith("/") else path
    return path in {REQUESTS, PERSONAL_FACTS} or _REQUEST.fullmatch(path) is not None or is_privacy_close(path)
