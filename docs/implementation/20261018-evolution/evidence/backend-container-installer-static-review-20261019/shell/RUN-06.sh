mkdir -p /data/registros /data/output /data/config /data/planes && \
    useradd --system --no-create-home appuser && \
    chown -R appuser:appuser /app /data
