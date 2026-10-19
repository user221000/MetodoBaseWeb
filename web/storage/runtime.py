"""Compose the configured private store once per immutable configuration."""
from functools import lru_cache
from pathlib import Path

from web.storage.configuration import ObjectStoreConfiguration, build_object_store


def storage_configuration(settings) -> ObjectStoreConfiguration:
    """Translate settings without consulting SDK profiles or ambient endpoints."""
    return ObjectStoreConfiguration(
        backend=settings.OBJECT_STORAGE_BACKEND,
        production=settings.is_production,
        local_root=Path(settings.OBJECT_STORAGE_LOCAL_ROOT) if settings.OBJECT_STORAGE_LOCAL_ROOT else None,
        bucket=settings.OBJECT_STORAGE_S3_BUCKET,
        region=settings.OBJECT_STORAGE_S3_REGION,
        endpoint=settings.OBJECT_STORAGE_S3_ENDPOINT or None,
        access_key=settings.OBJECT_STORAGE_S3_ACCESS_KEY,
        secret_key=settings.OBJECT_STORAGE_S3_SECRET_KEY,
        session_token=settings.OBJECT_STORAGE_S3_SESSION_TOKEN or None,
    )


@lru_cache(maxsize=4)
def _configured_store(configuration):
    return build_object_store(configuration)


def get_object_store():
    from web.settings import get_settings
    return _configured_store(storage_configuration(get_settings()))
