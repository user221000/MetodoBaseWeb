"""Closed-by-default read/send adapters. Provider ACK is not mailbox delivery."""
from dataclasses import dataclass
from datetime import datetime,timezone
from html import escape
from web.services.notification_domain import BillingSnapshot,SendResult


@dataclass(frozen=True)
class BillingReference:
    user_id:str
    context:str
    subscription_id:int
    provider:str
    resource_type:str
    resource_id:str
    customer_id:str|None
    plan:str
    expected_amount:int
    database_status:str
    period_start:datetime|None
    period_end:datetime|None
    purchase_ref:str|None=None
    association_proof:str=""
    contact_version:int=0


def _time(value):
    if value is None:return None
    if type(value) is not int or value<=0:raise ValueError("Invalid provider instant")
    return datetime.fromtimestamp(value,timezone.utc)


def _number(value):
    if type(value) is not int or not 0<=value<=2147483647:raise ValueError("Invalid provider amount")
    return value


class ProviderReadPort:
    """Existing SDKs only; explicit construction does not enable the runtime."""
    def __init__(self,*,enabled=False):self.enabled=enabled is True

    def read_billing(self,reference):
        if not self.enabled:raise RuntimeError("Notification observation disabled")
        if reference.provider=="stripe":return self._stripe(reference)
        if reference.provider=="mercadopago":return self._mp(reference)
        raise ValueError("Unreviewed notification provider")

    def _stripe(self,reference):
        from web.services import stripe_service
        if not stripe_service._init_stripe():raise RuntimeError("Payment source unavailable")
        sdk=stripe_service.stripe
        subscription=sdk.Subscription.retrieve(reference.resource_id)
        if (subscription.get("id")!=reference.resource_id or subscription.get("customer")!=reference.customer_id):
            raise ValueError("Provider identity changed")
        invoice_ref=subscription.get("latest_invoice")
        invoice_id=invoice_ref.get("id") if isinstance(invoice_ref,dict) else invoice_ref
        if not isinstance(invoice_id,str) or not invoice_id:raise ValueError("Current invoice unavailable")
        invoice=sdk.Invoice.retrieve(invoice_id,expand=["charge"])
        invoice_sub=invoice.get("subscription") or ((invoice.get("parent") or {}).get("subscription_details") or {}).get("subscription")
        if invoice.get("id")!=invoice_id or invoice.get("customer")!=reference.customer_id or invoice_sub!=reference.resource_id:
            raise ValueError("Invoice identity changed")
        currency=invoice.get("currency")
        due,paid,remaining=(_number(invoice.get(name)) for name in ("amount_due","amount_paid","amount_remaining"))
        if currency!="mxn" or due!=reference.expected_amount:raise ValueError("Invoice amount mismatch")
        charge=invoice.get("charge")
        if isinstance(charge,str):charge=sdk.Charge.retrieve(charge)
        # Preserve the provider's assertion before combining it with state;
        # bool coercion must not turn paid=True/status=open into an unpaid fact.
        paid_flag=invoice.get("paid")
        if type(paid_flag) is not bool or (invoice.get("status")=="paid")!=paid_flag:
            raise ValueError("Contradictory invoice payment state")
        refunded=False
        if paid_flag:
            if (not isinstance(charge,dict) or charge.get("customer")!=reference.customer_id or charge.get("currency")!="mxn"
                    or charge.get("paid") is not True or charge.get("captured") is not True
                    or _number(charge.get("amount"))<paid):raise ValueError("Captured payment unavailable")
            refunded=charge.get("refunded") is True or _number(charge.get("amount_refunded"))>0
        elif isinstance(charge,dict):
            if charge.get("customer")!=reference.customer_id:raise ValueError("Charge identity changed")
            refunded=charge.get("refunded") is True or _number(charge.get("amount_refunded",0))>0
            if charge.get("paid") is True:raise ValueError("Contradictory invoice and charge")
        return BillingSnapshot("stripe","subscription",reference.resource_id,invoice_id,
            subscription.get("status"),invoice.get("status"),currency,due,paid,remaining,paid_flag,refunded,
            _time(subscription.get("current_period_start")),_time(subscription.get("current_period_end")),
            _time(invoice.get("due_date"))).validate()

    def _mp(self,reference):
        # An approved one-time payment has no invoice arrears semantics. A
        # canonical period must already exist; it is not invented from a date.
        from web.services import mercadopago_service as mp
        result=mp.get_sdk().payment().get(reference.resource_id)
        if not isinstance(result,dict) or result.get("status")!=200 or not isinstance(result.get("response"),dict):
            raise ValueError("MP observation unavailable")
        payment=result["response"]
        if (str(payment.get("id"))!=reference.resource_id or payment.get("currency_id")!="MXN"):
            raise ValueError("MP identity changed")
        if reference.purchase_ref is None or payment.get("external_reference")!=reference.purchase_ref:
            raise ValueError("MP purchase identity changed")
        from decimal import Decimal
        amount=Decimal(str(payment.get("transaction_amount")))*100
        if amount!=reference.expected_amount:raise ValueError("MP amount mismatch")
        approved=payment.get("status")=="approved"
        refunded=payment.get("status") in {"refunded","charged_back"} or Decimal(str(payment.get("transaction_amount_refunded",0)))>0
        return BillingSnapshot("mercadopago","payment",reference.resource_id,None,reference.database_status,
            "paid" if approved else "unknown","mxn",int(amount),int(amount) if approved else 0,0,
            approved,refunded,reference.period_start,reference.period_end,None).validate()


@dataclass(frozen=True)
class ReminderMessage:
    destination:str
    purpose:str
    account_url:str
    exclusion_url:str
    idempotency_key:str


class ResendReminderPort:
    """No retries or interpretation of SDK errors as definite non-delivery."""
    def __init__(self,*,enabled=False):self.enabled=enabled is True

    def send(self,message):
        if not self.enabled:raise RuntimeError("Reminder transport disabled")
        from web.settings import get_settings
        key=get_settings().RESEND_API_KEY
        if not key:return SendResult("not_sent_terminal")
        import resend
        resend.api_key=key
        title="Revisa el estado de tu pago" if message.purpose=="confirmed_payment_issue" else "Consulta el periodo de tu cuenta"
        body="<p>Hay información de tu propia suscripción para revisar en Método Base.</p>"
        body+='<p><a href="'+escape(message.account_url,quote=True)+'">Consultar mi cuenta</a></p>'
        body+='<p><a href="'+escape(message.exclusion_url,quote=True)+'">Excluir estos recordatorios</a></p>'
        try:
            response=resend.Emails.send({"from":"MetodoBase <no-reply@metodobase.app>","to":[message.destination],"subject":title,"html":body},
                {"idempotency_key":message.idempotency_key})
            identifier=response.get("id") if isinstance(response,dict) else None
            return SendResult("accepted",identifier).validate()
        except Exception:
            # A timeout, invalid ACK or SDK exception may follow acceptance.
            # No body, recipient, link or exception text is logged here.
            return SendResult("uncertain")
