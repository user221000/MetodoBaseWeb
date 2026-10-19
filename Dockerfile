# ══════════════════════════════════════════════════════════════════════════════
# MetodoBase Web — Dockerfile de producción
# Candidato local 2026-10-18: lock con hashes y base fijada por digest.
#
# Multi-stage build:
#   1. Instala dependencias web-only (sin PySide6, sin GUI)
#   2. Copia solo lo necesario para el servidor
#   3. Ejecuta con uvicorn como non-root user
#
# Build:   docker build -t metodobase-web .
# Run:     docker run -p 8000:8000 --env-file .env metodobase-web
# ══════════════════════════════════════════════════════════════════════════════

FROM python:3.12.13-slim@sha256:229a2c5bfa27522db7815ea81f9bed70af17ccb9de9fc7ad142b1877b5830d36 AS base

# Both dependency and runtime stages inherit the verified installer upgrade.
# Pin its wheel independently; application locks and Windows environments stay separate.
COPY requirements-container-bootstrap.lock /usr/local/share/metodobase/requirements-container-bootstrap.lock
RUN python -m pip --isolated install --no-cache-dir --require-hashes --only-binary=:all: \
    --index-url https://pypi.org/simple -r /usr/local/share/metodobase/requirements-container-bootstrap.lock

# Prevenir bytecode + buffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# ── Stage 1: dependencias ────────────────────────────────────────────────────
FROM base AS deps

COPY requirements_web.lock .
RUN pip install --no-cache-dir --require-hashes -r requirements_web.lock

# ── Stage 2: app final ───────────────────────────────────────────────────────
FROM base AS runtime

# Copiar dependencias instaladas del stage anterior
COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# Asset version used by existing templates.
COPY web/.build_version /tmp/web_build_version

# Copiar solo los módulos necesarios para el web server
COPY config/ config/
COPY core/ core/
COPY src/ src/
COPY api/ api/
COPY web/ web/
COPY utils/ utils/
COPY static/ static/
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
# Readiness returns non-success when the database cannot serve requests.
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8000') + '/health/ready', timeout=5)" || exit 1

EXPOSE ${PORT}

# Railway uses preDeployCommand; standalone Docker migrates via entrypoint.
CMD ["/app/entrypoint.sh"]
