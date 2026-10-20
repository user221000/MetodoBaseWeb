"""Additive37 contact evidence. These fields never grant authentication."""
from sqlalchemy import CheckConstraint, Column, Integer, String

from web.database.utc_datetime import UTCDateTime

NAMES = (
    "email_verified_at", "email_verified_contact_version", "email_verification_hash",
    "email_verification_issued_at", "email_verification_expires_at",
    "email_verification_session_version", "email_verification_contact_version",
)


def columns():
    return (
        Column(NAMES[0], UTCDateTime, nullable=True),
        Column(NAMES[1], Integer, CheckConstraint(
            "(email_verified_at IS NULL AND email_verified_contact_version IS NULL) OR "
            "(email_verified_at IS NOT NULL AND email_verified_contact_version IS NOT NULL AND "
            "email_verified_contact_version BETWEEN 0 AND 2147483647 AND "
            "email_verified_contact_version = CAST(email_verified_contact_version AS INTEGER))",
            name="ck_usuario_verified_email_state"), nullable=True),
        Column(NAMES[2], String(64), nullable=True),
        Column(NAMES[3], UTCDateTime, nullable=True),
        Column(NAMES[4], UTCDateTime, nullable=True),
        Column(NAMES[5], Integer, nullable=True),
        Column(NAMES[6], Integer, CheckConstraint(
            "(email_verification_hash IS NULL AND email_verification_issued_at IS NULL AND "
            "email_verification_expires_at IS NULL AND email_verification_session_version IS NULL AND "
            "email_verification_contact_version IS NULL) OR (email_verification_hash IS NOT NULL AND "
            "length(email_verification_hash) = 64 AND email_verification_issued_at IS NOT NULL AND "
            "email_verification_expires_at IS NOT NULL AND email_verification_expires_at > email_verification_issued_at AND "
            "email_verification_session_version IS NOT NULL AND email_verification_session_version BETWEEN 0 AND 2147483647 AND "
            "email_verification_session_version = CAST(email_verification_session_version AS INTEGER) AND "
            "email_verification_contact_version IS NOT NULL AND email_verification_contact_version BETWEEN 0 AND 2147483647 AND "
            "email_verification_contact_version = CAST(email_verification_contact_version AS INTEGER))",
            name="ck_usuario_email_verification_state"), nullable=True),
    )
