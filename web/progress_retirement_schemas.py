"""Purpose-limited withdrawal requests. No identity or grant is accepted."""
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    field_validator,
    model_validator,
)

from web.account_values import normalize_account_email
from web.personal_progress_schemas import MAX_VERSION, uuid_text


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Primary(Input):
    method: Literal["password", "google"]
    email: str | None = Field(None, min_length=1, max_length=255)
    password: str | None = Field(None, min_length=1, max_length=128)
    google_credential: str | None = Field(None, min_length=1, max_length=16384)

    @model_validator(mode="after")
    def evidence(self):
        if self.method == "password":
            if not self.email or not self.password or self.google_credential is not None:
                raise ValueError("Password proof required")
            if len(self.password.encode("utf-8")) > 72:
                raise ValueError("Password input bound")
            self.email = normalize_account_email(self.email)
            if not self.email or any(ord(char) < 32 or ord(char) == 127 for char in self.email):
                raise ValueError("Account input bound")
        elif self.email is not None or self.password is not None or self.google_credential is None:
            raise ValueError("One primary method")
        return self


class Factor(Input):
    code: str | None = Field(None, pattern=r"^[0-9]{6}$")
    recovery_code: str | None = Field(None, pattern=r"^[A-Za-z0-9_-]{22}$")

    @model_validator(mode="after")
    def one(self):
        if (self.code is None) == (self.recovery_code is None):
            raise ValueError("One factor proof")
        return self


class Request(Input):
    primary: Primary
    factor: Factor | None = None


class Metadata(Request):
    limit: Annotated[StrictInt, Field(ge=1, le=100)] = 50
    after: str | None = None
    _cursor = field_validator("after")(lambda value: uuid_text(value) if value is not None else None)


class Withdrawal(Request):
    link_id: str
    expected_consent_id: str
    expected_version: Annotated[StrictInt, Field(ge=1, le=MAX_VERSION)]
    _ids = field_validator("link_id", "expected_consent_id")(uuid_text)
