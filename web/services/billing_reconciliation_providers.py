"""Read-only, deadline-aware SDK capabilities for the administrative CLI.

Clients are local to each request; no global Stripe settings or SDK automatic
retries change. No create/update/cancel API is exposed by this adapter.
"""
import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

class RetryableRead(Exception):
    """The next periodic invocation may retry the same resource."""


@dataclass
class ReadBudget:
    seconds: float = 60.0
    max_reads: int = 300
    clock: object = time.monotonic
    reads: int = 0
    deadline: float = field(init=False)

    def __post_init__(self):
        if type(self.seconds) not in {int, float} or not 1 <= self.seconds <= 120:
            raise ValueError("Invalid reconciliation deadline")
        if type(self.max_reads) is not int or not 1 <= self.max_reads <= 300:
            raise ValueError("Invalid reconciliation read budget")
        self.deadline = self.clock() + self.seconds

    def admit_item(self):
        if self.clock() >= self.deadline or self.reads >= self.max_reads:
            raise RetryableRead("Reconciliation admission exhausted")

    def admit_read(self):
        remaining = self.deadline - self.clock()
        if remaining <= 0 or self.reads >= self.max_reads:
            raise RetryableRead("Reconciliation admission exhausted")
        self.reads += 1
        return float(min(5.0, remaining))


class ReadOnlyProviders:
    def __init__(self, budget, settings):
        self.budget = budget
        self.settings = settings

    def _stripe(self, operation, reference, params=None):
        import stripe

        timeout = self.budget.admit_read()
        if not self.settings.STRIPE_SECRET_KEY:
            raise RetryableRead("Provider unavailable")
        transport = None
        try:
            transport = stripe.http_client.RequestsClient(timeout=timeout)
            client = stripe.StripeClient(self.settings.STRIPE_SECRET_KEY,
                stripe_version="2024-06-20", http_client=transport, max_network_retries=0)
            service = client.checkout.sessions if operation == "checkout" else getattr(client, operation)
            return service.retrieve(reference, params or {}, options={"max_network_retries": 0})
        except Exception as error:  # noqa: BLE001 -- SDK errors can contain credentials/provider payloads.
            logger.warning("reconciliation_provider_unavailable class=%s", type(error).__name__)
            raise RetryableRead("Provider unavailable") from None
        finally:
            if transport is not None:
                try:
                    transport.close()
                except Exception as error:  # noqa: BLE001 -- failed owned transport cleanup is not a confirmed read.
                    logger.warning("reconciliation_provider_close_unavailable class=%s", type(error).__name__)
                    raise RetryableRead("Provider unavailable") from None

    def subscription(self, reference, *, expand):
        return self._stripe("subscriptions", reference, {"expand": expand})

    def charge(self, reference):
        return self._stripe("charges", reference)

    def checkout(self, reference):
        return self._stripe("checkout", reference)

    def _mp(self, operation, value):
        import mercadopago
        from mercadopago.config import RequestOptions

        timeout = self.budget.admit_read()
        if not self.settings.MERCADOPAGO_ACCESS_TOKEN:
            raise RetryableRead("Provider unavailable")
        try:
            options = RequestOptions(connection_timeout=timeout, max_retries=0)
            sdk = mercadopago.SDK(self.settings.MERCADOPAGO_ACCESS_TOKEN, request_options=options)
            return getattr(sdk.payment(), operation)(value, request_options=options)
        except Exception as error:  # noqa: BLE001 -- SDK errors can contain credentials/provider payloads.
            logger.warning("reconciliation_provider_unavailable class=%s", type(error).__name__)
            raise RetryableRead("Provider unavailable") from None

    def payment(self):
        # Minimal existing reconcile_payment SDK interface; no mutation ports.
        return self

    def get(self, payment_id):
        return self._mp("get", payment_id)

    def search(self, intent_id):
        return self._mp("search", {"external_reference": intent_id, "limit": 11, "offset": 0})
