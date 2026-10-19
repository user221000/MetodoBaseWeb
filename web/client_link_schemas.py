"""Strict R12 inputs; every identity, source snapshot and PDF is server-owned."""
from pydantic import BaseModel,ConfigDict,Field,StrictBool,field_validator,model_validator

from web.account_values import normalize_account_email

MAX_VERSION=2147483647


class LinkInput(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)


class InvitationIssue(LinkInput):
    recipient_email:str=Field(min_length=3,max_length=255)
    request_key:str=Field(min_length=1,max_length=128,pattern=r'^[A-Za-z0-9_.:-]+$')

    @field_validator('recipient_email')
    @classmethod
    def canonical_email(cls,value):
        result=normalize_account_email(value)
        if (len(result)>255 or result.count('@')!=1 or not all(result.split('@'))
                or any(ord(char)<33 or ord(char)==127 for char in result)):
            raise ValueError('Invalid recipient email')
        return result


class LinkVersion(LinkInput):
    expected_version:int=Field(ge=1,le=MAX_VERSION)


class InvitationToken(LinkInput):
    token:str=Field(min_length=43,max_length=43,pattern=r'^[A-Za-z0-9_-]{43}$')


class InvitationAccept(InvitationToken,LinkVersion):
    confirm:StrictBool

    @model_validator(mode='after')
    def explicit_confirmation(self):
        if self.confirm is not True:raise ValueError('Confirmation required')
        return self


class PlanPublication(LinkInput):
    plan_id:int=Field(gt=0,le=MAX_VERSION)
    expected_link_version:int=Field(ge=1,le=MAX_VERSION)
    expected_publication_version:int=Field(ge=0,le=MAX_VERSION)
    expected_publication_id:str|None=Field(...,min_length=36,max_length=36,
        pattern=r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')

    @model_validator(mode='after')
    def exact_observed_publication(self):
        if (self.expected_publication_id is None)!=(self.expected_publication_version==0):
            raise ValueError('Publication identity and version must describe the same observation')
        return self
