"""Body-only bounded evidence; neither a subject nor a local actor is input."""
from pydantic import Field
from web.routes.mfa import Factor, Input, Proof


class LinkStart(Factor):
    password: str = Field(min_length=1, max_length=128)
    google_credential: str = Field(min_length=1, max_length=16384)


class LinkConfirm(Input):
    intent: Proof
    confirm: bool


class Unlink(Factor):
    password: str = Field(min_length=1, max_length=128)
    identity_id: str = Field(pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    expected_version: int = Field(ge=1, le=2147483647)
