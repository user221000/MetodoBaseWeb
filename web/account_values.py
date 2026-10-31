"""Existing account identity semantics and policy for newly chosen passwords."""

import re
import unicodedata

from web.password_blocklist import contains_password

# NIST 63B-4 single-factor minimum for every newly chosen credential.
MIN_NEW_PASSWORD_CHARS = 15


def normalize_account_email(value: str) -> str:
    """Preserve lower(), never merge Unicode/provider aliases with casefold."""
    return value.strip().lower()


def validate_registration_email(value: str) -> str:
    """Check a new account address without merging provider aliases or IDNs."""
    if not isinstance(value, str):
        raise ValueError("Email inválido.")  # noqa: TRY004 -- public registration uses ValueError
    email = normalize_account_email(value)
    if (not email or len(email) > 255 or email.count("@") != 1
            or any(char.isspace() or unicodedata.category(char).startswith("C") for char in email)):
        raise ValueError("Email inválido.")
    local, domain = email.split("@")
    if (not local or not domain or len(local.encode("utf-8")) > 64
            or local.startswith(".") or local.endswith(".") or ".." in local
            or any(ord(char) < 128 and char not in "abcdefghijklmnopqrstuvwxyz0123456789.!#$%&'*+-/=?^_`{|}~" for char in local)):
        raise ValueError("Email inválido.")
    try:
        labels = [label.encode("idna").decode("ascii") for label in domain.split(".")]
    except UnicodeError:
        raise ValueError("Email inválido.") from None
    ascii_domain = ".".join(labels)
    if (len(local.encode("utf-8")) + 1 + len(ascii_domain) > 254 or len(ascii_domain) > 253
            or any(not re.fullmatch(r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?", label) for label in labels)):
        raise ValueError("Email inválido.")
    return email


def validate_registration_name(value: str, *, required: bool = True) -> str:
    """Match persisted name limits before opening a session or hashing a secret."""
    if not isinstance(value, str):
        raise ValueError("Nombre inválido.")  # noqa: TRY004 -- public registration uses ValueError
    name = value.strip()
    if ((required and not name) or len(name) > 150
            or any(unicodedata.category(char) == "Cc" or 0xD800 <= ord(char) <= 0xDFFF for char in name)):
        raise ValueError("Nombre inválido.")
    return name


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
