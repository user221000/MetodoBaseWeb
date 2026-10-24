"""Existing account identity semantics and policy for newly chosen passwords."""

from web.password_blocklist import contains_password

# NIST 63B-4 single-factor minimum for every newly chosen credential.
MIN_NEW_PASSWORD_CHARS = 15


def normalize_account_email(value: str) -> str:
    """Preserve lower(), never merge Unicode/provider aliases with casefold."""
    return value.strip().lower()


def validate_new_password(value: str) -> str:
    """Validate a newly selected credential; existing login hashes are unaffected.

    Count Unicode code points without trimming or normalization. Preserve the
    current bcrypt 72-byte UTF-8 bound and fail closed on the blocklist.
    """
    if not isinstance(value,str) or len(value)<MIN_NEW_PASSWORD_CHARS:
        raise ValueError('La contraseña debe tener al menos 15 caracteres.')
    try:
        encoded=value.encode('utf-8')
    except UnicodeError:
        raise ValueError('La contraseña contiene caracteres no válidos.') from None
    if len(encoded)>72:
        raise ValueError('La contraseña debe ocupar como máximo 72 bytes UTF-8.')
    if contains_password(encoded):
        raise ValueError('Esta contraseña es demasiado común. Elige otra contraseña o una frase larga y poco predecible.')
    return value
