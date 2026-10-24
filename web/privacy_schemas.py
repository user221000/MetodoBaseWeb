"""Closed account privacy intent; no subject, gym or policy selected by clients."""
from typing import Literal
from pydantic import Field, model_validator
from web.account_security_schemas import Empty, Proof


class PrivacyRequestInput(Empty):
    idempotency_key: str = Field(pattern=r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
    intent: Literal['erase_personal_data']


class PrivacyClosureInput(Empty):
    expected_version: int = Field(ge=1,le=2147483647)
    confirmation: Literal['close_account']
    reauthentication_token: Proof
    code: str | None = Field(None,pattern=r'^[0-9]{6}$')
    recovery_code: str | None = Field(None,pattern=r'^[A-Za-z0-9_-]{22}$')

    @model_validator(mode='after')
    def one_factor(self):
        if self.code is not None and self.recovery_code is not None:
            raise ValueError('Only one current factor can be supplied')
        return self
