"""
web/middleware/metrics.py — Métricas de latencia y monitoreo de requests.

Recolecta métricas de:
- Latencia de requests (p50, p95, p99)
- Conteo de requests por endpoint
- Errores por código de estado
- Tiempos de respuesta por ruta

Uso:
    from web.middleware import MetricsMiddleware, get_metrics_summary
    
    app.add_middleware(MetricsMiddleware)
    
    # Obtener métricas
    @app.get("/metrics")
    async def metrics():
        return get_metrics_summary()

Configuración via ENV:
    METRICS_ENABLED=true
    METRICS_HISTORY_SIZE=1000
"""

import os
import time
import logging
import statistics
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Optional
from threading import Lock

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import BaseRoute

logger = logging.getLogger(__name__)
_METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "TRACE", "CONNECT"})


# ── Configuración ────────────────────────────────────────────────────────────

METRICS_ENABLED = os.getenv("METRICS_ENABLED", "true").lower() == "true"
METRICS_HISTORY_SIZE = int(os.getenv("METRICS_HISTORY_SIZE", "1000"))


# ── Estructuras de Datos ─────────────────────────────────────────────────────

@dataclass
class RequestMetric:
    """Métrica individual de una request."""
    timestamp: float
    path: str
    method: str
    status_code: int
    latency_ms: float


@dataclass
class EndpointStats:
    """Estadísticas agregadas por endpoint."""
    path: str
    total_requests: int = 0
    total_errors: int = 0  # status >= 400
    latencies: deque = field(default_factory=lambda: deque(maxlen=METRICS_HISTORY_SIZE))
    status_codes: dict = field(default_factory=lambda: defaultdict(int))
    last_request: Optional[float] = None
    
    def add_request(self, latency_ms: float, status_code: int):
        """Registra una request."""
        self.total_requests += 1
        self.latencies.append(latency_ms)
        self.status_codes[status_code] += 1
        self.last_request = time.time()
        
        if status_code >= 400:
            self.total_errors += 1
    
    def get_percentiles(self) -> dict:
        """Calcula percentiles de latencia."""
        if not self.latencies:
            return {"p50": 0, "p95": 0, "p99": 0, "avg": 0, "min": 0, "max": 0}
        
        sorted_latencies = sorted(self.latencies)
        n = len(sorted_latencies)
        
        def percentile(p: int) -> float:
            idx = int(n * p / 100)
            return sorted_latencies[min(idx, n - 1)]
        
        return {
            "p50": round(percentile(50), 2),
            "p95": round(percentile(95), 2),
            "p99": round(percentile(99), 2),
            "avg": round(statistics.mean(self.latencies), 2),
            "min": round(min(self.latencies), 2),
            "max": round(max(self.latencies), 2),
        }
    
    def to_dict(self) -> dict:
        """Convierte a diccionario para serialización."""
        percentiles = self.get_percentiles()
        return {
            "path": self.path,
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "error_rate": round(self.total_errors / max(1, self.total_requests) * 100, 2),
            "latency_ms": percentiles,
            "status_codes": dict(self.status_codes),
            "last_request": datetime.fromtimestamp(self.last_request, tz=timezone.utc).isoformat() if self.last_request else None,
        }


# ── Metrics Store ────────────────────────────────────────────────────────────

class MetricsStore:
    """
    Almacén de métricas en memoria.
    
    Para producción con múltiples instancias, considerar:
    - Prometheus + Grafana
    - Datadog
    - New Relic
    - CloudWatch
    """
    
    def __init__(self):
        self._endpoints: dict[str, EndpointStats] = defaultdict(lambda: EndpointStats(path=""))
        self._lock = Lock()
        self._start_time = time.time()
        self._total_requests = 0
        self._total_errors = 0
        
        # Historial global para alertas
        self._recent_requests: deque[RequestMetric] = deque(maxlen=METRICS_HISTORY_SIZE)
        self._recent_errors: deque[RequestMetric] = deque(maxlen=100)
    
    def record(self, metric: RequestMetric):
        """Registra una métrica de request."""
        with self._lock:
            self._total_requests += 1
            self._recent_requests.append(metric)
            
            # The middleware supplies only a declared route or one fixed fallback.
            normalized_path = metric.path
            
            endpoint = self._endpoints[normalized_path]
            endpoint.path = normalized_path
            endpoint.add_request(metric.latency_ms, metric.status_code)
            
            if metric.status_code >= 400:
                self._total_errors += 1
                self._recent_errors.append(metric)
    
    def get_summary(self) -> dict:
        """Obtiene resumen de todas las métricas."""
        from web.rate_limiter_redis import get_rate_limit_status
        with self._lock:
            uptime = time.time() - self._start_time
            
            # Calcular latencias globales
            all_latencies = []
            for endpoint in self._endpoints.values():
                all_latencies.extend(endpoint.latencies)
            
            global_percentiles = {"p50": 0, "p95": 0, "p99": 0, "avg": 0}
            if all_latencies:
                sorted_latencies = sorted(all_latencies)
                n = len(sorted_latencies)
                global_percentiles = {
                    "p50": round(sorted_latencies[int(n * 0.50)], 2),
                    "p95": round(sorted_latencies[int(n * 0.95)], 2),
                    "p99": round(sorted_latencies[int(n * 0.99)], 2),
                    "avg": round(statistics.mean(all_latencies), 2),
                }
            
            # Top endpoints más lentos
            slowest = sorted(
                self._endpoints.values(),
                key=lambda e: e.get_percentiles()["p95"],
                reverse=True
            )[:5]
            
            # Endpoints con más errores
            most_errors = sorted(
                self._endpoints.values(),
                key=lambda e: e.total_errors,
                reverse=True
            )[:5]
            
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "uptime_seconds": round(uptime, 0),
                "total_requests": self._total_requests,
                "total_errors": self._total_errors,
                "error_rate_percent": round(self._total_errors / max(1, self._total_requests) * 100, 2),
                "requests_per_second": round(self._total_requests / max(1, uptime), 2),
                "global_latency_ms": global_percentiles,
                "rate_limit_backend": get_rate_limit_status(),
                "endpoints": {
                    path: stats.to_dict()
                    for path, stats in sorted(self._endpoints.items())
                },
                "slowest_endpoints": [e.to_dict() for e in slowest],
                "most_error_endpoints": [e.to_dict() for e in most_errors if e.total_errors > 0],
            }
    
    def get_recent_errors(self, limit: int = 10) -> list[dict]:
        """Obtiene errores recientes para debugging."""
        with self._lock:
            return [
                {
                    "timestamp": datetime.fromtimestamp(m.timestamp, tz=timezone.utc).isoformat(),
                    "path": m.path,
                    "method": m.method,
                    "status_code": m.status_code,
                    "latency_ms": m.latency_ms,
                }
                for m in list(self._recent_errors)[-limit:]
            ]
    
    def check_alerts(self) -> list[dict]:
        """
        Verifica condiciones de alerta.
        
        Returns:
            Lista de alertas activas.
        """
        alerts = []
        summary = self.get_summary()
        
        # Alerta: Latencia p95 > 500ms
        if summary["global_latency_ms"]["p95"] > 500:
            alerts.append({
                "type": "high_latency",
                "severity": "warning",
                "message": f"Latencia p95 alta: {summary['global_latency_ms']['p95']}ms",
                "threshold": 500,
                "current": summary["global_latency_ms"]["p95"],
            })
        
        # Alerta: Latencia p99 > 1000ms
        if summary["global_latency_ms"]["p99"] > 1000:
            alerts.append({
                "type": "critical_latency",
                "severity": "critical",
                "message": f"Latencia p99 crítica: {summary['global_latency_ms']['p99']}ms",
                "threshold": 1000,
                "current": summary["global_latency_ms"]["p99"],
            })
        
        # Alerta: Error rate > 5%
        if summary["error_rate_percent"] > 5:
            alerts.append({
                "type": "high_error_rate",
                "severity": "critical",
                "message": f"Tasa de errores alta: {summary['error_rate_percent']}%",
                "threshold": 5,
                "current": summary["error_rate_percent"],
            })
        
        # Alerta: Endpoint específico con errores altos
        for endpoint in summary["most_error_endpoints"]:
            if endpoint["error_rate"] > 10 and endpoint["total_requests"] > 10:
                alerts.append({
                    "type": "endpoint_errors",
                    "severity": "warning",
                    "message": f"Endpoint {endpoint['path']} con {endpoint['error_rate']}% errores",
                    "endpoint": endpoint["path"],
                    "error_rate": endpoint["error_rate"],
                })
        
        return alerts


# ── Singleton Store ──────────────────────────────────────────────────────────

_metrics_store: Optional[MetricsStore] = None


def get_metrics_store() -> MetricsStore:
    """Obtiene el store singleton."""
    global _metrics_store
    if _metrics_store is None:
        _metrics_store = MetricsStore()
    return _metrics_store


def get_metrics_summary() -> dict:
    """Obtiene resumen de métricas."""
    return get_metrics_store().get_summary()


def get_recent_errors(limit: int = 10) -> list[dict]:
    """Obtiene errores recientes."""
    return get_metrics_store().get_recent_errors(limit)


def check_alerts() -> list[dict]:
    """Verifica alertas activas."""
    return get_metrics_store().check_alerts()


# ── Middleware ───────────────────────────────────────────────────────────────

class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware para recolección de métricas de latencia.
    
    Args:
        app: Aplicación FastAPI
        enabled: Si las métricas están activas
        exclude_paths: Rutas a excluir de métricas
    """
    
    def __init__(
        self,
        app,
        enabled: bool = METRICS_ENABLED,
        exclude_paths: Optional[list[str]] = None,
    ):
        super().__init__(app)
        self.enabled = enabled
        self.exclude_paths = exclude_paths or ["/metrics", "/health", "/health/ready"]
        self.store = get_metrics_store()
        
        logger.info(f"MetricsMiddleware inicializado: enabled={enabled}")
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Procesa cada request midiendo latencia."""
        if not self.enabled:
            return await call_next(request)
        
        path = request.url.path
        if any(path.startswith(excluded) for excluded in self.exclude_paths):
            return await call_next(request)
        
        # Medir latencia
        start_time = time.perf_counter()
        
        # Obtener respuesta
        try:
            response = await call_next(request)
        except Exception:
            # The outer generic handler will emit 500. Preserve no exception,
            # traceback, body or concrete request identity in this store.
            self._record(request, start_time, 500)
            raise
        
        # Calcular latencia
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        self._record(request, start_time, response.status_code)

        # Agregar headers de timing
        response.headers["X-Response-Time"] = f"{latency_ms:.2f}ms"
        return response

    def _record(self, request: Request, start_time: float, status_code: int):
        """Record one completed or failed request with its declared route only."""
        latency_ms = (time.perf_counter() - start_time) * 1000
        # Never retain a concrete path, forwarded header or client address.
        # Router metadata is available only after a route has been resolved.
        route = request.scope.get("route")
        route_path = getattr(route, "path_format", None) if isinstance(route, BaseRoute) else None
        if not isinstance(route_path, str):
            route_path = getattr(route, "path", None) if isinstance(route, BaseRoute) else None
        if not isinstance(route_path, str):
            route_path = "/__unmatched__"
        
        metric = RequestMetric(
            timestamp=time.time(),
            path=route_path,
            method=request.method if request.method in _METHODS else "OTHER",
            status_code=status_code,
            latency_ms=round(latency_ms, 2),
        )
        
        self.store.record(metric)
