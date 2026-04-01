# ══════════════════════════════════════════════════════════════════════════════
# MetodoBase Web — Dockerfile de producción
# Cache bust: 2026-04-01-v4-NOCACHE
# FORCE REBUILD: $(date +%s)
#
# Multi-stage build:
#   1. Instala dependencias web-only (sin PySide6, sin GUI)
#   2. Copia solo lo necesario para el servidor
#   3. Ejecuta con uvicorn como non-root user
#
# Build:   docker build -t metodobase-web .
# Run:     docker run -p 8000:8000 --env-file .env metodobase-web
# ══════════════════════════════════════════════════════════════════════════════

FROM python:3.12-slim AS base

# Cache buster - change this value to force rebuild
ARG CACHEBUST=20260401v4

# Prevenir bytecode + buffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# ── Stage 1: dependencias ────────────────────────────────────────────────────
FROM base AS deps

COPY requirements_web.txt .
RUN pip install --no-cache-dir -r requirements_web.txt

# ── Stage 2: app final ───────────────────────────────────────────────────────
FROM base AS runtime

# Copiar dependencias instaladas del stage anterior
COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# Copiar solo los módulos necesarios para el web server
COPY config/ config/
COPY core/ core/
COPY src/ src/
COPY api/ api/
COPY web/ web/
COPY utils/ utils/
COPY fonts/ fonts/

# Crear directorio para datos persistentes (incluye config y planes para evitar PermissionError)
RUN mkdir -p /data/registros /data/output /data/config /data/planes && \
    useradd --system --no-create-home appuser && \
    chown -R appuser:appuser /app /data

# Variables de entorno por defecto (overrideables en deploy)
ENV METODOBASE_ENV=production \
    METODOBASE_DATA_DIR=/data \
    PYTHONPATH=/app \
    PORT=8000

# Copiar entrypoint y asignar permisos
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Copiar Alembic config, migraciones y DB bootstrap
COPY alembic.ini /app/alembic.ini
COPY db_bootstrap.py /app/db_bootstrap.py

# Non-root user
USER appuser

# Health check para Docker / Railway
# Usa /health que ahora siempre retorna 200 (liveness)
# Railway debe usar /health/ready para readiness si quiere verificar BD
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/health')" || exit 1

EXPOSE ${PORT}

# Ejecutar — Railway usa releaseCommand para migraciones; Docker usa entrypoint
CMD ["/app/entrypoint.sh"]
