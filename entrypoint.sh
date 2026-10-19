#!/bin/bash
set -e

echo "=== MetodoBase: Container starting (BUILD v7-TEMPLATECOMPAT) ==="
echo "  RAILWAY_ENVIRONMENT: ${RAILWAY_ENVIRONMENT:-'(not set)'}"
echo "  METODOBASE_ENV: ${METODOBASE_ENV:-'(not set)'}"
echo "  PORT: ${PORT:-'(not set)'}"
echo "  DATABASE_URL: ${DATABASE_URL:+'(configured)'}"
echo "  WEB_SECRET_KEY: ${WEB_SECRET_KEY:+'(configured)'}"
echo "  SENTRY_DSN: ${SENTRY_DSN:+'(configured)'}"

# Railway runs the blocking pre-deploy command before new workers start.
if [ -z "$RAILWAY_ENVIRONMENT" ]; then
    echo "=== MetodoBase: Ejecutando migraciones Alembic ==="
    python db_bootstrap.py
else
    echo "=== MetodoBase: Migraciones gestionadas por Railway preDeployCommand ==="
fi

echo "=== MetodoBase: Iniciando servidor (BUILD v7-TEMPLATECOMPAT) en 0.0.0.0:${PORT:-8000} ==="
exec python web/main_web.py --no-browser
