"""Read-only payment history contract; unknown legacy refund amounts stay null."""
from datetime import datetime, timezone
from typing import Annotated

from pydantic import BaseModel, Field, StrictInt, field_serializer

MinorAmount = Annotated[StrictInt, Field(ge=0)]


class PaymentHistoryItem(BaseModel):
    id: StrictInt
    amount_cents: MinorAmount = Field(description="Importe original en unidades menores de la moneda.")
    currency: str
    status: str = Field(description="Incluye partially_refunded y refunded; conserva estados históricos.")
    plan: str | None
    created_at: datetime | None
    stripe_invoice_id: str | None
    refund_amount_cents: MinorAmount | None = Field(description="Total acumulado observado en el proveedor; null significa desconocido.")
    net_amount_cents: MinorAmount | None = Field(description="Original menos devolución conocida; no incluye comisiones ni acredita abono bancario.")
    refund_observed_at: datetime | None = Field(description="Instante UTC de observación del proveedor, distinto de la fecha de abono bancario.")

    @field_serializer('created_at', 'refund_observed_at')
    def serialize_utc(self, value):
        if value is None:
            return None
        aware = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
        return aware.astimezone(timezone.utc).isoformat()


class PaymentHistoryResponse(BaseModel):
    payments: list[PaymentHistoryItem]
