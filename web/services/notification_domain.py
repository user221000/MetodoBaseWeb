"""Bounded, inert R27 values. Facts never grant rights or imply causality."""
from dataclasses import dataclass,asdict
from datetime import datetime,timedelta,timezone
import hashlib,json,re

UUID=re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\Z")
PURPOSES=("account_period_end","confirmed_payment_issue")
FRESHNESS=timedelta(minutes=15)
LEASE=timedelta(seconds=60)
EXCLUDE_TTL=timedelta(days=30)
MAX_VERSION=2147483647


def instant(now=None):
    value=datetime.now(timezone.utc) if now is None else now
    if not isinstance(value,datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Aware clock required")
    return value.astimezone(timezone.utc)


def aware(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def naive(value):return instant(value).replace(tzinfo=None)


def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")


def digest(value):return hashlib.sha256(canonical(value)).hexdigest()


def request_hash(user,context,method,path,body):
    return digest({"user":user,"context":context,"method":method,"path":path,"body":body})


def contact_hash(email):
    from web.account_values import normalize_account_email
    return digest({"purpose":"notification_contact36","email":normalize_account_email(email)})


def secret_hash(purpose,token):
    return hashlib.sha256((purpose+"\0"+token).encode("ascii")).hexdigest()


@dataclass(frozen=True)
class BillingSnapshot:
    provider:str
    resource_type:str
    resource_id:str
    invoice_id:str|None
    subscription_status:str
    invoice_status:str
    currency:str
    amount_due:int
    amount_paid:int
    amount_remaining:int
    paid:bool
    refunded:bool
    period_start:datetime|None
    period_end:datetime|None
    due_at:datetime|None

    def validate(self):
        if self.provider not in {"stripe","mercadopago"} or self.resource_type not in {"subscription","payment"}:
            raise ValueError("Unreviewed source")
        if not isinstance(self.resource_id,str) or not 1<=len(self.resource_id)<=255:
            raise ValueError("Invalid source identity")
        if self.invoice_id is not None and (not isinstance(self.invoice_id,str) or not 1<=len(self.invoice_id)<=255):
            raise ValueError("Invalid invoice identity")
        if self.subscription_status not in {"active","canceled","past_due","trialing","unpaid","incomplete","incomplete_expired","paused","unknown"} or self.invoice_status not in {"unknown","open","paid","void","uncollectible"}:
            raise ValueError("Unknown source state")
        if self.currency!="mxn" or any(type(v) is not int or not 0<=v<=2147483647 for v in (self.amount_due,self.amount_paid,self.amount_remaining)):
            raise ValueError("Invalid money unit")
        if type(self.paid) is not bool or type(self.refunded) is not bool:
            raise ValueError("Invalid payment flags")
        if (self.period_start is None)!=(self.period_end is None):raise ValueError("Partial period")
        for value in (self.period_start,self.period_end,self.due_at):
            if value is not None:instant(value)
        if self.period_start is not None and self.period_start>=self.period_end:raise ValueError("Invalid period")
        if self.paid and (self.amount_remaining!=0 or self.invoice_status!="paid" or self.amount_paid<=0):raise ValueError("Contradictory paid fact")
        if self.provider=="mercadopago" and self.invoice_status in {"open","uncollectible"}:raise ValueError("A single payment is not an invoice")
        return self

    def fingerprint(self):
        data=asdict(self.validate())
        for key in ("period_start","period_end","due_at"):
            if data[key] is not None:data[key]=instant(data[key]).isoformat()
        # No observed_at/fresh_until/now: repeated observation is the same fact.
        return digest(data)


def qualifies(fact,purpose,now):
    now=instant(now)
    if fact is None or aware(fact.created_at)>now or aware(fact.fresh_until)<=now:return False
    if fact.subscription_status in {"canceled","paused","incomplete","incomplete_expired","unknown"} or fact.refunded:return False
    if purpose=="account_period_end":
        return fact.period_end is not None and fact.paid and fact.subscription_status=="active" and now<aware(fact.period_end)<=now+timedelta(days=7)
    if purpose=="confirmed_payment_issue":
        return (fact.provider=="stripe" and fact.invoice_id is not None and fact.invoice_status=="open"
            and fact.subscription_status in {"past_due","unpaid"} and not fact.paid and fact.amount_remaining>0
            and fact.due_at is not None and aware(fact.due_at)<now)
    return False


@dataclass(frozen=True)
class SendResult:
    kind:str
    provider_id:str|None=None

    def validate(self):
        if self.kind not in {"accepted","not_sent_retryable","not_sent_terminal","uncertain"}:raise ValueError("Invalid transport outcome")
        if self.kind=="accepted" and (not isinstance(self.provider_id,str) or not self.provider_id.strip() or len(self.provider_id)>256):raise ValueError("Invalid provider acknowledgement")
        if self.kind!="accepted" and self.provider_id is not None:raise ValueError("Unexpected acknowledgement")
        return self


class DisabledPort:
    """No inherited email configuration silently enables a reminder worker."""
    enabled=False
    def read_billing(self,*_args):raise RuntimeError("Notification billing port disabled")
    def send(self,*_args):raise RuntimeError("Notification sending port disabled")
