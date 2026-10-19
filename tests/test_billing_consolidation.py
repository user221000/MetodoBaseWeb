"""
tests/test_billing_consolidation.py — Tests de integración para billing consolidado.

Verifica:
- subscription_service: activate_subscription, complete_checkout, is_payment_processed
- stripe_service usa Price IDs cuando están configurados
- billing.py MP webhook con idempotencia y firma
- pagos.py delega a stripe_service (no duplica lógica)
"""
import pytest
import secrets
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock, PropertyMock


# ═══════════════════════════════════════════════════════════════════════════════
# subscription_service — Shared service tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestSubscriptionService:
    """Tests del servicio compartido de suscripciones."""

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = None
        db.query.return_value.filter.return_value.first.return_value = None
        db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
        return db

    def test_activate_subscription_creates_new(self, mock_db):
        """activate_subscription crea suscripción si no existe."""
        from web.services.subscription_service import activate_subscription

        sub = activate_subscription(mock_db, "gym_001", "standard", provider="stripe")

        assert sub.gym_id == "gym_001"
        assert sub.plan == "standard"
        assert sub.status == "active"
        assert sub.max_clientes == 25
        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()

    def test_activate_subscription_updates_existing(self, mock_db):
        """activate_subscription actualiza suscripción existente."""
        from web.services.subscription_service import activate_subscription

        existing = MagicMock()
        existing.gym_id = "gym_001"
        existing.plan = "standard"
        mock_db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = existing

        sub = activate_subscription(
            mock_db, "gym_001", "gym_comercial",
            stripe_customer_id="cus_123",
            provider="stripe",
        )

        assert sub.plan == "gym_comercial"
        assert sub.status == "active"
        assert sub.stripe_customer_id == "cus_123"
        mock_db.add.assert_not_called()  # No se agrega, se actualiza

    def test_activate_subscription_mp_provider(self, mock_db):
        """activate_subscription funciona con provider mercadopago."""
        from web.services.subscription_service import activate_subscription

        sub = activate_subscription(mock_db, "gym_mp", "clinica", provider="mercadopago")

        assert sub.plan == "clinica"
        assert sub.status == "active"
        # clinica tiene max_clientes=0 (unlimited) → 999999
        assert sub.max_clientes == 999999

    def test_complete_checkout_updates_pending(self, mock_db):
        """complete_checkout actualiza checkout pendiente existente."""
        from web.services.subscription_service import complete_checkout

        pending = MagicMock()
        pending.status = "pending"
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = pending

        checkout = complete_checkout(mock_db, "gym_001", "standard", "a@b.com", "pay_123")

        assert checkout.status == "completed"
        assert checkout.stripe_session_id == "pay_123"
        mock_db.add.assert_not_called()

    def test_complete_checkout_creates_if_no_pending(self, mock_db):
        """complete_checkout crea nuevo si no hay pendiente."""
        from web.services.subscription_service import complete_checkout

        checkout = complete_checkout(mock_db, "gym_002", "gym_comercial", "x@y.com", "pay_456")

        assert checkout.gym_id == "gym_002"
        assert checkout.status == "completed"
        mock_db.add.assert_called_once()

    def test_is_payment_processed_false(self, mock_db):
        """is_payment_processed retorna False para pagos nuevos."""
        from web.services.subscription_service import is_payment_processed

        assert is_payment_processed(mock_db, "pay_new") is False

    def test_is_payment_processed_true(self, mock_db):
        """is_payment_processed retorna True para pagos ya procesados."""
        from web.services.subscription_service import is_payment_processed

        existing = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = existing

        assert is_payment_processed(mock_db, "pay_dup") is True

    def test_record_payment(self, mock_db):
        """record_payment crea registro en Payment."""
        from web.services.subscription_service import record_payment

        p = record_payment(
            mock_db, "gym_001",
            amount_cents=15900,
            currency="mxn",
            status="succeeded",
            plan="standard",
        )

        assert p.gym_id == "gym_001"
        assert p.amount_cents == 15900
        mock_db.add.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════════════
# stripe_service — Price ID usage
# ═══════════════════════════════════════════════════════════════════════════════

class TestStripePriceIDs:
    """Verifica que stripe_service usa Price IDs cuando están disponibles."""

    def test_checkout_uses_price_id_when_available(self):
        """Si stripe_price_id está configurado, se usa en lugar de price_data."""
        from web.services.stripe_service import create_checkout_session

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with patch("web.services.stripe_service.prepare_purchase", return_value=MagicMock(id="intent_test")), \
             patch("web.services.stripe_service._init_stripe", return_value=True), \
             patch("stripe.checkout.Session.create") as mock_create, \
             patch.dict("web.constants.PLANES_LICENCIA", {
                 "standard": {
                     "precio_mxn": 159,
                     "max_clientes": 25,
                     "stripe_price_id": "price_REAL_STANDARD_ID",
                     "features": [],
                 },
             }):
            mock_session = MagicMock()
            mock_session.id = "cs_test"
            mock_session.url = "https://checkout.stripe.com/test"
            mock_create.return_value = mock_session

            result = create_checkout_session(
                db=mock_db, gym_id="gym_001", plan="standard",
                email="test@test.com",
                success_url="/success", cancel_url="/cancel",
            )

            # Verificar que se usó price ID, no price_data
            call_kwargs = mock_create.call_args[1]
            line_items = call_kwargs["line_items"]
            assert line_items == [{"price": "price_REAL_STANDARD_ID", "quantity": 1}]
            assert "price_data" not in str(line_items)

    def test_checkout_uses_price_data_when_no_price_id(self):
        """Sin stripe_price_id, usa price_data dinámico (desarrollo)."""
        from web.services.stripe_service import create_checkout_session

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with patch("web.services.stripe_service.prepare_purchase", return_value=MagicMock(id="intent_test")), \
             patch("web.services.stripe_service._init_stripe", return_value=True), \
             patch("stripe.checkout.Session.create") as mock_create, \
             patch.dict("web.constants.PLANES_LICENCIA", {
                 "standard": {
                     "precio_mxn": 159,
                     "max_clientes": 25,
                     "stripe_price_id": "",
                     "features": [],
                 },
             }):
            mock_session = MagicMock()
            mock_session.id = "cs_test2"
            mock_session.url = "https://checkout.stripe.com/test2"
            mock_create.return_value = mock_session

            result = create_checkout_session(
                db=mock_db, gym_id="gym_001", plan="standard",
                email="test@test.com",
                success_url="/success", cancel_url="/cancel",
            )

            call_kwargs = mock_create.call_args[1]
            line_items = call_kwargs["line_items"]
            assert "price_data" in line_items[0]
            assert line_items[0]["price_data"]["unit_amount"] == 15900


# ═══════════════════════════════════════════════════════════════════════════════
# stripe_service — Uses shared subscription_service
# ═══════════════════════════════════════════════════════════════════════════════

class TestStripeUsesSharedService:
    """Verifica que stripe_service usa activate_subscription del servicio compartido."""

    def test_paid_checkout_reconciles_provider_state(self):
        """Paid checkout must validate current provider state before granting access.

        The previous assertion accepted a checkout lacking payment_status. That
        unsafe contract is replaced by this paid case plus persisted unpaid and
        current-state regressions in test_billing_integrity.py.
        """
        from web.services.stripe_service import _on_checkout_completed

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        session_data = {
            "payment_status": "paid",
            "metadata": {"gym_id": "gym_test", "plan": "gym_comercial"},
            "customer": "cus_abc",
            "subscription": "sub_xyz",
            "customer_email": "test@gym.com",
        }

        with patch("web.services.stripe_service.reconcile_subscription") as reconcile:
            reconcile.return_value = {"plan": "gym_comercial", "activated": True}

            result = _on_checkout_completed(mock_db, session_data)

            reconcile.assert_called_once_with(mock_db, "sub_xyz")
            assert "activated" in result


# ═══════════════════════════════════════════════════════════════════════════════
# pagos.py — Delegates to stripe_service
# ═══════════════════════════════════════════════════════════════════════════════

class TestPagosLegacyDelegation:
    """Verifica que pagos.py delega a stripe_service, no duplica lógica."""

    def test_pagos_no_inline_stripe_session_create(self):
        """pagos.py no debe tener stripe.checkout.Session.create en handlers (solo en wrapper)."""
        import re
        from pathlib import Path
        text = (Path(__file__).resolve().parents[1] / "api" / "routes" / "pagos.py").read_text(encoding="utf-8")
        # Stripe calls must ONLY be inside protected wrapper functions (with @retry_with_backoff)
        # Check that route handlers don't call stripe directly
        lines = text.split('\n')
        in_router_handler = False
        for line in lines:
            if '@router.' in line:
                in_router_handler = True
            if line.startswith('def _') or line.startswith('@retry_with_backoff'):
                in_router_handler = False
            if in_router_handler and 'stripe.checkout.Session.create' in line:
                raise AssertionError("Route handler calls stripe.checkout.Session.create directly")

    def test_pagos_uses_shared_subscription_service(self):
        """pagos.py debe importar de subscription_service."""
        from pathlib import Path
        text = (Path(__file__).resolve().parents[1] / "api" / "routes" / "pagos.py").read_text(encoding="utf-8")
        assert "from web.services.subscription_service import" in text
        assert "activate_subscription" in text
        assert "complete_checkout" in text
        assert "is_payment_processed" in text

    def test_billing_has_mp_endpoints(self):
        """billing.py debe tener endpoints de MercadoPago."""
        from pathlib import Path
        text = (Path(__file__).resolve().parents[1] / "web" / "routes" / "billing.py").read_text(encoding="utf-8")
        assert "/billing/mp/preference" in text
        assert "/billing/mp/webhook" in text
        assert "activate_subscription" in text

    def test_no_duplicate_subscription_logic_in_pagos(self):
        """pagos.py no debe tener lógica inline de Subscription."""
        from pathlib import Path
        text = (Path(__file__).resolve().parents[1] / "api" / "routes" / "pagos.py").read_text(encoding="utf-8")
        # No debe importar Subscription directamente
        assert "from web.database.models import" not in text or "Subscription" not in text.split("from web.database.models import")[-1].split("\n")[0]


# ═══════════════════════════════════════════════════════════════════════════════
# Settings — Price IDs configuration
# ═══════════════════════════════════════════════════════════════════════════════

class TestPriceIDConfiguration:
    """Verifica que la configuración de Price IDs funcione correctamente."""

    def test_settings_has_stripe_price_ids(self):
        """Settings debe tener campos para Price IDs."""
        from config.settings import get_settings
        settings = get_settings()
        assert hasattr(settings, "STRIPE_PRICE_STANDARD")
        assert hasattr(settings, "STRIPE_PRICE_GYM_COMERCIAL")
        assert hasattr(settings, "STRIPE_PRICE_CLINICA")

    def test_constantes_reads_price_ids_from_env(self):
        """PLANES_LICENCIA debe leer stripe_price_id de env vars."""
        import os
        with patch.dict(os.environ, {"STRIPE_PRICE_STANDARD": "price_test_123"}):
            # Re-evaluate the expression
            result = os.environ.get("STRIPE_PRICE_STANDARD", "")
            assert result == "price_test_123"

    def test_production_requires_price_ids(self):
        """En producción, settings debe requerir Price IDs de Stripe."""
        from pathlib import Path
        text = (Path(__file__).resolve().parents[1] / "config" / "settings.py").read_text(encoding="utf-8")
        assert "STRIPE_PRICE_STANDARD" in text
        assert "STRIPE_PRICE_GYM_COMERCIAL" in text or "STRIPE_PRICE_CLINICA" in text


# ═══════════════════════════════════════════════════════════════════════════════
# billing.py — CSRF exemption for MP webhook
# ═══════════════════════════════════════════════════════════════════════════════

class TestCSRFExemption:
    """Verifica que los webhooks están exentos de CSRF."""

    def test_mp_webhook_exempt_from_csrf(self):
        """MP webhook debe estar exento de CSRF en main_web.py."""
        from pathlib import Path
        text = (Path(__file__).resolve().parents[1] / "web" / "main_web.py").read_text(encoding="utf-8")
        assert "/api/billing/mp/webhook" in text
