"""Existing account identity semantics and policy for newly chosen passwords."""

from web.password_blocklist import contains_password


def normalize_account_email(value: str) -> str:
    """Preserve lower(), never merge Unicode/provider aliases with casefold."""
    return value.strip().lower()


def validate_new_password(value: str) -> str:
    if not isinstance(value,str) or len(value)<12:
        raise ValueError('La contraseña debe tener al menos 12 caracteres.')
    try:
        encoded=value.encode('utf-8')
    except UnicodeError:
        raise ValueError('La contraseña contiene caracteres no válidos.') from None
    if len(encoded)>72:
        raise ValueError('La contraseña debe ocupar como máximo 72 bytes UTF-8.')
    if contains_password(encoded):
        raise ValueError('Esta contraseña es demasiado común. Elige otra contraseña o una frase larga y poco predecible.')
    return value
