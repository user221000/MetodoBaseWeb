"""
web/services/resilience.py — Circuit Breaker y Retry con backoff exponencial.

Protege llamadas a servicios externos (Stripe, MercadoPago) de:
- Fallos repetidos (circuit breaker)
- Errores transitorios (retry con backoff)
- Timeouts excesivos

Uso:
    from web.services.resilience import (
        CircuitBreaker, 
        retry_with_backoff,
        stripe_circuit,
        mercadopago_circuit,
    )
    
    # Con decorador
    @retry_with_backoff(max_retries=3, circuit=stripe_circuit)
    def create_checkout():
        ...
    
    # Manual
    result = stripe_circuit.call(stripe.checkout.Session.create, **params)
"""
import logging
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from functools import wraps
from threading import Lock
from typing import Any, Callable, Optional, Set, Type

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"      # Normal, cuenta fallos
    OPEN = "open"          # Bloqueando, fail fast
    HALF_OPEN = "half_open"  # Probando recuperación


class CircuitOpenError(Exception):
    """Excepción cuando el circuit breaker está abierto."""
    def __init__(self, name: str, retry_after: float):
        self.name = name
        self.retry_after = retry_after
        super().__init__(f"Circuit '{name}' is open. Retry after {retry_after:.1f}s")


@dataclass
class CircuitBreakerConfig:
    """Configuración del circuit breaker."""
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    half_open_max_calls: int = 1


class CircuitBreaker:
    """
    Implementación de Circuit Breaker pattern.
    
    Estados:
    - CLOSED: Normal, permite todas las llamadas, cuenta fallos
    - OPEN: Demasiados fallos, rechaza inmediatamente
    - HALF_OPEN: Después del timeout, permite una llamada de prueba
    """
    
    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._half_open_calls = 0
        self._lock = Lock()
    
    @property
    def state(self) -> CircuitState:
        """Estado actual, considerando auto-recovery."""
        with self._lock:
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                    logger.info("Circuit %s transitioning to HALF_OPEN", self.name)
            return self._state
    
    def _should_attempt_reset(self) -> bool:
        """Verifica si pasó el tiempo de recovery."""
        if not self._last_failure_time:
            return False
        elapsed = (datetime.now(timezone.utc) - self._last_failure_time).total_seconds()
        return elapsed >= self.config.recovery_timeout
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Ejecuta función protegida por el circuit breaker."""
        state = self.state
        
        if state == CircuitState.OPEN:
            retry_after = self.config.recovery_timeout
            if self._last_failure_time:
                elapsed = (datetime.now(timezone.utc) - self._last_failure_time).total_seconds()
                retry_after = max(0, self.config.recovery_timeout - elapsed)
            raise CircuitOpenError(self.name, retry_after)
        
        if state == CircuitState.HALF_OPEN:
            with self._lock:
                if self._half_open_calls >= self.config.half_open_max_calls:
                    raise CircuitOpenError(self.name, self.config.recovery_timeout)
                self._half_open_calls += 1
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure(e)
            raise
    
    def _on_success(self):
        """Callback en éxito."""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                logger.info("Circuit %s recovered, closing", self.name)
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._half_open_calls = 0
    
    def _on_failure(self, error: Exception):
        """Callback en fallo."""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = datetime.now(timezone.utc)
            
            if self._state == CircuitState.HALF_OPEN:
                logger.warning("Circuit %s failed in HALF_OPEN, reopening", self.name)
                self._state = CircuitState.OPEN
            elif self._failure_count >= self.config.failure_threshold:
                logger.error(
                    "Circuit %s opened after %d failures class=%s",
                    self.name, self._failure_count, type(error).__name__
                )
                self._state = CircuitState.OPEN
    
    def reset(self):
        """Reset manual del circuit breaker."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._half_open_calls = 0
            logger.info("Circuit %s manually reset", self.name)
    
    def get_status(self) -> dict:
        """Estado para monitoreo."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "failure_threshold": self.config.failure_threshold,
        }


# ── Retry with Backoff ────────────────────────────────────────────────────────

# Excepciones que disparan retry
RETRYABLE_EXCEPTIONS: Set[Type[Exception]] = {
    ConnectionError,
    TimeoutError,
    OSError,  # Includes network errors
}

# Status codes que disparan retry
RETRYABLE_STATUS_CODES = {500, 502, 503, 504, 429}


def is_retryable(error: Exception) -> bool:
    """Determina si un error es retryable."""
    # Excepciones de red
    if any(isinstance(error, exc) for exc in RETRYABLE_EXCEPTIONS):
        return True
    
    # Stripe API errors con status code retryable
    if hasattr(error, "http_status"):
        return error.http_status in RETRYABLE_STATUS_CODES
    
    # httpx errors
    if hasattr(error, "response") and hasattr(error.response, "status_code"):
        return error.response.status_code in RETRYABLE_STATUS_CODES
    
    return False


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 10.0,
    exponential_base: float = 2.0,
    jitter: float = 0.2,
    circuit: Optional[CircuitBreaker] = None,
):
    """
    Decorador para retry con backoff exponencial.
    
    Args:
        max_retries: Número máximo de reintentos
        initial_delay: Delay inicial en segundos
        max_delay: Delay máximo en segundos  
        exponential_base: Base para cálculo exponencial
        jitter: Variación aleatoria (±20% por defecto)
        circuit: CircuitBreaker opcional para integrar
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    if circuit:
                        return circuit.call(func, *args, **kwargs)
                    return func(*args, **kwargs)
                    
                except CircuitOpenError:
                    raise  # No reintentar si circuit está abierto
                    
                except Exception as e:
                    last_exception = e
                    
                    if not is_retryable(e):
                        raise  # Error no retryable
                    
                    if attempt == max_retries:
                        logger.error(
                            "%s failed after %d attempts class=%s",
                            func.__name__, max_retries + 1, type(e).__name__
                        )
                        raise
                    
                    # Calcular delay con backoff exponencial + jitter
                    delay = min(
                        initial_delay * (exponential_base ** attempt),
                        max_delay
                    )
                    jitter_range = delay * jitter
                    delay += random.uniform(-jitter_range, jitter_range)
                    
                    logger.warning(
                        "%s attempt %d failed, retrying in %.2fs class=%s",
                        func.__name__, attempt + 1, delay, type(e).__name__
                    )
                    time.sleep(delay)
            
            raise last_exception
        
        return wrapper
    return decorator


# ── Circuit Breakers predefinidos ─────────────────────────────────────────────

stripe_circuit = CircuitBreaker(
    "stripe",
    CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=30.0,
        half_open_max_calls=1,
    )
)

mercadopago_circuit = CircuitBreaker(
    "mercadopago", 
    CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=30.0,
        half_open_max_calls=1,
    )
)


# ── Helper Functions ──────────────────────────────────────────────────────────

def get_all_circuit_status() -> list[dict]:
    """Retorna estado de todos los circuit breakers para /health o métricas."""
    return [
        stripe_circuit.get_status(),
        mercadopago_circuit.get_status(),
    ]
