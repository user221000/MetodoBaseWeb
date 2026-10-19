"""
Tests para web/observability/sentry_setup.py

Verifica:
- Inicialización con DSN vacío (no crashea)
- Filtrado de eventos (ValidationError, HTTPException, etc.)
- Filtrado de transacciones (/health, /metrics)
- set_user_context no crashea
- capture_business_error funciona
"""
import pytest
from unittest.mock import patch, MagicMock


class TestInitSentry:
    """Tests para init_sentry()."""

    def test_init_with_empty_dsn_does_not_initialize(self):
        """Con DSN vacío, Sentry no debe inicializarse."""
        from web.observability.sentry_setup import init_sentry
        
        with patch("web.observability.sentry_setup.sentry_sdk.init") as mock_init:
            init_sentry(dsn="", environment="test", traces_rate=0.1, profiles_rate=0.1)
            mock_init.assert_not_called()

    def test_init_with_dsn_initializes_sentry(self):
        """Con DSN válido, Sentry debe inicializarse."""
        from web.observability.sentry_setup import init_sentry
        
        with patch("web.observability.sentry_setup.sentry_sdk.init") as mock_init:
            init_sentry(
                dsn="https://test@sentry.io/123",
                environment="test",
                traces_rate=0.5,
                profiles_rate=0.2,
            )
            mock_init.assert_called_once()
            call_kwargs = mock_init.call_args.kwargs
            assert call_kwargs["dsn"] == "https://test@sentry.io/123"
            assert call_kwargs["environment"] == "test"
            assert call_kwargs["traces_sample_rate"] == 0.5
            assert call_kwargs["profiles_sample_rate"] == 0.2


class TestFilterEvents:
    """Tests para _filter_events()."""

    def test_filter_validation_error(self):
        """ValidationError debe ser filtrado (retorna None)."""
        from web.observability.sentry_setup import _filter_events
        
        event = {
            "exception": {
                "values": [{"type": "ValidationError", "value": "invalid"}]
            }
        }
        result = _filter_events(event, {})
        assert result is None

    def test_filter_request_validation_error(self):
        """RequestValidationError debe ser filtrado."""
        from web.observability.sentry_setup import _filter_events
        
        event = {
            "exception": {
                "values": [{"type": "RequestValidationError", "value": "bad request"}]
            }
        }
        result = _filter_events(event, {})
        assert result is None

    def test_filter_http_exception(self):
        """HTTPException debe ser filtrado."""
        from web.observability.sentry_setup import _filter_events
        
        event = {
            "exception": {
                "values": [{"type": "HTTPException", "value": "not found"}]
            }
        }
        result = _filter_events(event, {})
        assert result is None

    def test_filter_starlette_http_exception(self):
        """StarletteHTTPException debe ser filtrado."""
        from web.observability.sentry_setup import _filter_events
        
        event = {
            "exception": {
                "values": [{"type": "StarletteHTTPException", "value": "forbidden"}]
            }
        }
        result = _filter_events(event, {})
        assert result is None

    def test_filter_http_status_error(self):
        """HTTPStatusError debe ser filtrado."""
        from web.observability.sentry_setup import _filter_events
        
        event = {
            "exception": {
                "values": [{"type": "HTTPStatusError", "value": "bad gateway"}]
            }
        }
        result = _filter_events(event, {})
        assert result is None

    def test_pass_through_real_errors(self):
        """Errores reales (como RuntimeError) NO deben ser filtrados."""
        from web.observability.sentry_setup import _filter_events
        
        event = {
            "exception": {
                "values": [{"type": "RuntimeError", "value": "something broke"}]
            }
        }
        result = _filter_events(event, {})
        assert result == event

    def test_pass_through_event_without_exception(self):
        """Eventos sin excepción deben pasar."""
        from web.observability.sentry_setup import _filter_events
        
        event = {"message": "info log", "level": "info"}
        result = _filter_events(event, {})
        assert result == event


class TestFilterTransactions:
    """Tests para _filter_transactions()."""

    def test_filter_health_endpoint(self):
        """/health debe ser filtrado."""
        from web.observability.sentry_setup import _filter_transactions
        
        event = {"transaction": "/health"}
        result = _filter_transactions(event, {})
        assert result is None

    def test_filter_health_ready_endpoint(self):
        """/health/ready debe ser filtrado."""
        from web.observability.sentry_setup import _filter_transactions
        
        event = {"transaction": "/health/ready"}
        result = _filter_transactions(event, {})
        assert result is None

    def test_filter_metrics_endpoint(self):
        """/metrics debe ser filtrado."""
        from web.observability.sentry_setup import _filter_transactions
        
        event = {"transaction": "/metrics"}
        result = _filter_transactions(event, {})
        assert result is None

    def test_filter_alerts_endpoint(self):
        """/alerts debe ser filtrado."""
        from web.observability.sentry_setup import _filter_transactions
        
        event = {"transaction": "/alerts"}
        result = _filter_transactions(event, {})
        assert result is None

    def test_pass_through_api_endpoints(self):
        """Endpoints de API deben pasar."""
        from web.observability.sentry_setup import _filter_transactions
        
        event = {"transaction": "/api/clientes"}
        result = _filter_transactions(event, {})
        assert result == event

    def test_pass_through_web_endpoints(self):
        """Endpoints web deben pasar."""
        from web.observability.sentry_setup import _filter_transactions
        
        event = {"transaction": "/dashboard"}
        result = _filter_transactions(event, {})
        assert result == event


class TestSetUserContext:
    """Tests para set_user_context()."""

    def test_set_user_context_does_not_crash(self):
        """set_user_context no debe crashear con datos válidos."""
        from web.observability.sentry_setup import set_user_context
        
        with patch("web.observability.sentry_setup.sentry_sdk.set_user") as mock_set:
            # No debe lanzar excepción
            set_user_context(user_id="123", gym_id="456", role="owner")
            
            mock_set.assert_called_once_with({
                "id": "123",
                "gym_id": "456",
                "role": "owner",
            })

    def test_set_user_context_with_empty_values(self):
        """set_user_context no debe crashear con valores vacíos."""
        from web.observability.sentry_setup import set_user_context
        
        with patch("web.observability.sentry_setup.sentry_sdk.set_user") as mock_set:
            set_user_context(user_id="", gym_id="", role="")
            mock_set.assert_called_once()


class TestCaptureBusinessError:
    """Tests para capture_business_error()."""

    def test_capture_business_error_sends_message(self):
        """capture_business_error debe enviar mensaje a Sentry."""
        from web.observability.sentry_setup import capture_business_error
        
        with patch("web.observability.sentry_setup.sentry_sdk.capture_message") as mock_capture:
            with patch("web.observability.sentry_setup.sentry_sdk.push_scope"):
                capture_business_error("Plan generation failed")
                mock_capture.assert_called_once_with("Plan generation failed", level="error")

    def test_capture_business_error_with_extra_context(self):
        """capture_business_error debe setear contexto extra."""
        from web.observability.sentry_setup import capture_business_error
        
        mock_scope = MagicMock()
        
        with patch("web.observability.sentry_setup.sentry_sdk.capture_message"):
            with patch("web.observability.sentry_setup.sentry_sdk.push_scope") as mock_push:
                mock_push.return_value.__enter__ = MagicMock(return_value=mock_scope)
                mock_push.return_value.__exit__ = MagicMock(return_value=False)
                
                capture_business_error(
                    "Cliente sin plan",
                    extra={"cliente_id": "abc", "gym_id": "xyz"}
                )
                
                # Verificar que se setearon los extras
                assert mock_scope.set_extra.call_count == 2


class TestWithSentryContext:
    """Tests para with_sentry_context dependency."""

    def test_with_sentry_context_sets_user_and_returns_usuario(self):
        """with_sentry_context debe setear contexto y retornar usuario."""
        import asyncio
        from web.auth_deps import with_sentry_context
        
        mock_usuario = {
            "id": "user-123",
            "team_gym_id": "gym-456",
            "role": "trainer",
        }
        
        with patch("web.auth_deps.get_usuario_actual", return_value=mock_usuario):
            with patch("web.observability.sentry_setup.set_user_context") as mock_set:
                result = asyncio.run(
                    with_sentry_context(mock_usuario)
                )
                
                assert result == mock_usuario
                mock_set.assert_called_once_with(
                    user_id="user-123",
                    gym_id="gym-456",
                    role="trainer",
                )

    def test_with_sentry_context_uses_id_when_no_team_gym_id(self):
        """Si no hay team_gym_id, debe usar id como gym_id."""
        import asyncio
        from web.auth_deps import with_sentry_context
        
        mock_usuario = {
            "id": "owner-789",
            "role": "owner",
        }
        
        with patch("web.auth_deps.get_usuario_actual", return_value=mock_usuario):
            with patch("web.observability.sentry_setup.set_user_context") as mock_set:
                result = asyncio.run(
                    with_sentry_context(mock_usuario)
                )
                
                mock_set.assert_called_once_with(
                    user_id="owner-789",
                    gym_id="owner-789",  # Fallback a id
                    role="owner",
                )


class TestFilteredExceptionsConstant:
    """Tests para la constante FILTERED_EXCEPTIONS."""

    def test_filtered_exceptions_contains_expected_types(self):
        """FILTERED_EXCEPTIONS debe contener los tipos esperados."""
        from web.observability.sentry_setup import FILTERED_EXCEPTIONS
        
        expected = {
            "ValidationError",
            "RequestValidationError",
            "HTTPException",
            "StarletteHTTPException",
            "HTTPStatusError",
        }
        assert FILTERED_EXCEPTIONS == expected
