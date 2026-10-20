"""Finite37 boundaries, including only their single-slash redirects."""
POSTS = frozenset({
    "/api/account/security/email/request", "/api/account/security/email/confirm",
    "/api/account/security/password",
})
PRIVATE = POSTS | frozenset({"/api/account/security", "/auth/verify-email"})


def is_account_security_private(path):
    return path in PRIVATE or (path.endswith("/") and path[:-1] in PRIVATE)


def is_account_security_post(path):
    return path in POSTS or (path.endswith("/") and path[:-1] in POSTS)
