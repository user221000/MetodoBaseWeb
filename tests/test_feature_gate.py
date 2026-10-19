"""
tests/test_feature_gate.py — Tests para el servicio de feature gating.

Cubre:
- PlanFeatures dataclass y PLAN_FEATURES dict
- get_plan_features() utility
- FeatureGate class con limits y checks
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from web.services.feature_gate import (
    PlanFeatures,
    PLAN_FEATURES,
    TRIAL_PLAN_FEATURES,
    TRIAL_DAYS,
    get_plan_features,
    get_all_plans,
    FeatureGate,
)


class TestPlanFeatures:
    """Tests para PlanFeatures dataclass."""
    
    def test_plan_features_dataclass_has_all_fields(self):
        """PlanFeatures tiene todos los campos requeridos."""
        features = PlanFeatures(
            plan_name="Test",
            max_clientes=100,
            max_planes_por_mes=50,
            max_registros_diarios=25,
            max_planes_por_cliente_dia=1,
            can_export_excel=True,
            can_export_pdf=True,
            can_bulk_export=True,
            can_custom_branding=False,
            can_custom_templates=False,
            can_multi_user=False,
            max_team_members=1,
            can_api_access=True,
            can_webhooks=False,
            support_level="email",
            can_food_preferences=False,
            price_mxn=29,
            stripe_price_id="price_test",
        )
        assert features.plan_name == "Test"
        assert features.max_clientes == 100
        assert features.can_export_excel is True
    
    def test_all_plans_defined(self):
        """Todos los planes esperados están definidos."""
        expected_plans = ["free", "standard", "gym_comercial", "clinica"]
        for plan in expected_plans:
            assert plan in PLAN_FEATURES, f"Plan {plan} not defined"
    
    def test_free_plan_limits(self):
        """Plan free tiene límites correctos."""
        free = PLAN_FEATURES["free"]
        assert free.max_clientes == 10
        assert free.can_export_excel is False
        assert free.price_mxn == 0
        assert free.stripe_price_id is None
    
    def test_standard_plan_limits(self):
        """Plan standard tiene límites correctos."""
        standard = PLAN_FEATURES["standard"]
        assert standard.max_clientes == 25
        assert standard.can_export_excel is True
        assert standard.can_api_access is True
        assert standard.can_multi_user is False
        assert standard.price_mxn == 159
    
    def test_gym_comercial_plan_limits(self):
        """Plan gym_comercial tiene límites correctos."""
        pro = PLAN_FEATURES["gym_comercial"]
        assert pro.max_clientes == 75
        assert pro.max_planes_por_mes == 0  # Unlimited
        assert pro.can_custom_branding is True
        assert pro.can_webhooks is True
        assert pro.price_mxn == 479
    
    def test_clinica_plan_unlimited(self):
        """Plan clínica tiene sin límites."""
        clinica = PLAN_FEATURES["clinica"]
        assert clinica.max_clientes == 0  # Unlimited
        assert clinica.max_planes_por_mes == 0  # Unlimited
        assert clinica.max_team_members == 0  # Unlimited
        assert clinica.can_multi_user is True
        assert clinica.support_level == "priority"


class TestGetPlanFeatures:
    """Tests para get_plan_features utility."""
    
    def test_get_plan_features_valid_plan(self):
        """Obtiene features para plan válido."""
        features = get_plan_features("standard")
        assert features.plan_name == "Standard"
        assert features.max_clientes == 25
    
    def test_get_plan_features_invalid_plan(self):
        """Plan inválido retorna free."""
        features = get_plan_features("invalid_plan")
        assert features == PLAN_FEATURES["free"]
    
    def test_get_all_plans_returns_copy(self):
        """get_all_plans retorna copia, no referencia."""
        plans = get_all_plans()
        assert len(plans) == 5
        # Modificar copia no afecta original
        plans["test"] = PlanFeatures(
            plan_name="Test", max_clientes=1, max_planes_por_mes=1,
            max_registros_diarios=0, max_planes_por_cliente_dia=0,
            can_export_excel=False, can_export_pdf=False, can_bulk_export=False,
            can_custom_branding=False, can_custom_templates=False,
            can_multi_user=False, max_team_members=1,
            can_api_access=False, can_webhooks=False,
            support_level="none", can_food_preferences=False,
            price_mxn=0, stripe_price_id=None,
        )
        assert "test" not in PLAN_FEATURES


class TestTrialSettings:
    """Tests para configuración de trial."""
    
    def test_trial_days_defined(self):
        """TRIAL_DAYS está definido."""
        assert TRIAL_DAYS == 14
    
    def test_trial_uses_standard_features(self):
        """Trial usa features de standard."""
        assert TRIAL_PLAN_FEATURES == PLAN_FEATURES["standard"]


class TestFeatureGateBasic:
    """Tests básicos para FeatureGate."""
    
    def test_feature_gate_initialization(self):
        """FeatureGate se inicializa correctamente."""
        mock_db = MagicMock()
        gate = FeatureGate(mock_db, "gym_123")
        assert gate.gym_id == "gym_123"
        assert gate.db is mock_db
    
    def test_plan_without_subscription_is_free(self):
        """Sin suscripción, plan es free."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        gate = FeatureGate(mock_db, "gym_123")
        assert gate.plan == "free"
    
    def test_plan_with_subscription_returns_plan(self):
        """Con suscripción, retorna el plan correcto."""
        mock_db = MagicMock()
        mock_sub = MagicMock(current_period_end=None, trial_end=None)
        mock_sub.plan = "gym_comercial"
        mock_sub.status = "active"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_sub
        
        gate = FeatureGate(mock_db, "gym_123")
        assert gate.plan == "gym_comercial"
    
    def test_is_trial_false_when_active(self):
        """is_trial es False cuando status es active."""
        mock_db = MagicMock()
        mock_sub = MagicMock(current_period_end=None, trial_end=None)
        mock_sub.plan = "standard"
        mock_sub.status = "active"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_sub
        
        gate = FeatureGate(mock_db, "gym_123")
        assert gate.is_trial is False
    
    def test_is_trial_true_when_trialing(self):
        """is_trial es True cuando status es trialing."""
        mock_db = MagicMock()
        mock_sub = MagicMock(current_period_end=None, trial_end=None)
        mock_sub.plan = "standard"
        mock_sub.status = "trialing"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_sub
        
        gate = FeatureGate(mock_db, "gym_123")
        assert gate.is_trial is True


class TestFeatureGateLimits:
    """Tests para límites de FeatureGate."""
    
    def test_get_remaining_clients_unlimited_plan(self):
        """Plan ilimitado retorna 999999."""
        mock_db = MagicMock()
        mock_sub = MagicMock(current_period_end=None, trial_end=None)
        mock_sub.plan = "clinica"
        mock_sub.status = "active"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_sub
        
        gate = FeatureGate(mock_db, "gym_123")
        remaining = gate.get_remaining_clients()
        assert remaining == 999999
    
    def test_get_remaining_clients_with_limit(self):
        """Calcula correctamente clientes restantes."""
        mock_db = MagicMock()
        mock_sub = MagicMock(current_period_end=None, trial_end=None)
        mock_sub.plan = "standard"  # max 25
        mock_sub.status = "active"
        
        # Setup query chain for subscription
        sub_query = MagicMock()
        sub_query.filter.return_value.first.return_value = mock_sub
        
        # Setup query chain for client count (15 clients)
        client_query = MagicMock()
        client_query.filter.return_value.count.return_value = 15
        
        def query_side_effect(model):
            if model.__name__ == "Subscription":
                return sub_query
            return client_query
        
        mock_db.query.side_effect = query_side_effect
        
        gate = FeatureGate(mock_db, "gym_123")
        remaining = gate.get_remaining_clients()
        assert remaining == 10  # 25 - 15


class TestFeatureGateChecks:
    """Tests para checks que lanzan HTTPException."""
    
    def test_check_can_create_client_unlimited(self):
        """Plan ilimitado siempre permite crear."""
        mock_db = MagicMock()
        mock_sub = MagicMock(current_period_end=None, trial_end=None)
        mock_sub.plan = "clinica"  # unlimited
        mock_sub.status = "active"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_sub
        
        gate = FeatureGate(mock_db, "gym_123")
        # Should not raise
        gate.check_can_create_client()
    
    def test_check_can_create_client_at_limit_raises_402(self):
        """En el límite, lanza HTTPException 402."""
        mock_db = MagicMock()
        mock_sub = MagicMock(current_period_end=None, trial_end=None)
        mock_sub.plan = "free"  # max 10
        mock_sub.status = "active"
        
        # Setup query chain
        sub_query = MagicMock()
        sub_query.filter.return_value.first.return_value = mock_sub
        
        client_query = MagicMock()
        client_query.filter.return_value.count.return_value = 10  # At limit
        
        def query_side_effect(model):
            if model.__name__ == "Subscription":
                return sub_query
            return client_query
        
        mock_db.query.side_effect = query_side_effect
        
        gate = FeatureGate(mock_db, "gym_123")
        
        with pytest.raises(HTTPException) as exc_info:
            gate.check_can_create_client()
        
        assert exc_info.value.status_code == 402
        assert exc_info.value.detail["error"] == "plan_limit_exceeded"
        assert exc_info.value.detail["current"] == 10
        assert exc_info.value.detail["limit"] == 10
    
    def test_check_can_create_client_below_limit_passes(self):
        """Debajo del límite, no lanza excepción."""
        mock_db = MagicMock()
        mock_sub = MagicMock(current_period_end=None, trial_end=None)
        mock_sub.plan = "free"  # max 10
        mock_sub.status = "active"
        
        # Setup query chain
        sub_query = MagicMock()
        sub_query.filter.return_value.first.return_value = mock_sub
        
        client_query = MagicMock()
        client_query.filter.return_value.count.return_value = 5  # Below limit
        
        def query_side_effect(model):
            if model.__name__ == "Subscription":
                return sub_query
            return client_query
        
        mock_db.query.side_effect = query_side_effect
        
        gate = FeatureGate(mock_db, "gym_123")
        # Should not raise
        gate.check_can_create_client()


class TestPlanFeatureValues:
    """Tests para verificar valores consistentes entre planes."""
    
    def test_plans_have_increasing_limits(self):
        """Planes tienen límites crecientes (excepto 0 = unlimited)."""
        plans_order = ["free", "standard", "gym_comercial", "clinica"]
        
        prev_max = 0
        for plan_name in plans_order:
            plan = PLAN_FEATURES[plan_name]
            if plan.max_clientes == 0:
                # Unlimited, skip comparison
                continue
            assert plan.max_clientes >= prev_max, f"{plan_name} should have >= limit than previous"
            prev_max = plan.max_clientes
    
    def test_plans_have_increasing_prices(self):
        """Planes tienen precios crecientes."""
        plans_order = ["free", "standard", "gym_comercial", "clinica"]
        
        prev_price = -1
        for plan_name in plans_order:
            plan = PLAN_FEATURES[plan_name]
            assert plan.price_mxn > prev_price, f"{plan_name} should cost more than previous"
            prev_price = plan.price_mxn
    
    def test_paid_plans_have_stripe_price_id(self):
        """Planes de pago tienen stripe_price_id configurado (via env var)."""
        paid_plans = ["standard", "gym_comercial", "clinica"]
        for plan_name in paid_plans:
            plan = PLAN_FEATURES[plan_name]
            assert plan.stripe_price_id is not None, f"{plan_name} missing stripe_price_id"
            # In test env, env vars may not be set (empty string).
            # In production, they must start with 'price_'.
            if plan.stripe_price_id:
                assert plan.stripe_price_id.startswith("price_"), f"{plan_name} has invalid price_id format"


class TestFeatureGateTrialBehavior:
    """Tests para comportamiento durante trial."""
    
    def test_trial_gets_standard_features(self):
        """Durante trial, obtiene features de standard."""
        mock_db = MagicMock()
        mock_sub = MagicMock(current_period_end=None, trial_end=None)
        mock_sub.plan = "standard"
        mock_sub.status = "trialing"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_sub
        
        gate = FeatureGate(mock_db, "gym_123")
        features = gate.features
        
        assert features == TRIAL_PLAN_FEATURES
        assert features.max_clientes == 25  # Standard limit
        assert features.can_export_excel is True
