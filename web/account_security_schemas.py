"""Closed37 inputs; credential validation uses the canonical account policy."""
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from web.account_values import MIN_NEW_PASSWORD_CHARS, validate_new_password

Proof = Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{43}$")]


class Empty(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class EmailConfirmation(Empty):
    token: Proof


class PasswordChange(Empty):
    reauthentication_token: Proof
    new_password: str = Field(min_length=MIN_NEW_PASSWORD_CHARS, max_length=128)
    confirm_password: str = Field(min_length=MIN_NEW_PASSWORD_CHARS, max_length=128)
    code: str | None = Field(None, pattern=r"^[0-9]{6}$")
    recovery_code: str | None = Field(None, pattern=r"^[A-Za-z0-9_-]{22}$")

    @field_validator("new_password", "confirm_password")
    @classmethod
    def password_value(cls, value):
        return validate_new_password(value)

    @model_validator(mode="after")
    def confirmation(self):
        if self.new_password != self.confirm_password or (self.code is not None and self.recovery_code is not None):
            raise ValueError("Password confirmation and a single factor required")
        return self
