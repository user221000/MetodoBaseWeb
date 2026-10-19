"""Explicit storage composition without credential discovery or fallback writes.

The application supplies validated environment values at startup. Constructing a
client does not create/discover a bucket or upload data. A deployment must
provision the private destination and its permissions separately.
"""
from dataclasses import dataclass, field
from ipaddress import ip_address
from pathlib import Path
import re
from urllib.parse import urlsplit

from web.storage.local import LocalObjectStore
from web.storage.objects import ObjectUnavailable
from web.storage.s3 import S3ObjectStore

_APPLICATION_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class ObjectStoreConfiguration:
    """One explicitly configured destination; credentials are omitted from repr.

    Local storage requires an absolute private root, including development.
    Production S3 accepts HTTPS only. Development HTTP is restricted to an
    explicit loopback endpoint. No provider credentials are read by this module.
    """
    backend: str
    production: bool = False
    local_root: Path | None = None
    bucket: str = ""
    region: str = ""
    endpoint: str | None = field(default=None, repr=False)
    access_key: str = field(default="", repr=False)
    secret_key: str = field(default="", repr=False)
    session_token: str | None = field(default=None, repr=False)

    def validate(self) -> None:
        if self.backend == "local":
            if self.local_root is None or not Path(self.local_root).is_absolute():
                raise ValueError("Private object storage requires an absolute local root")
            resolved = Path(self.local_root).resolve()
            public_roots = (_APPLICATION_ROOT / "static", _APPLICATION_ROOT / "web" / "static")
            if resolved == Path(resolved.anchor) or any(resolved.is_relative_to(root.resolve()) for root in public_roots):
                raise ValueError("Private object storage cannot use a public or filesystem root")
            if self.bucket or self.region or self.endpoint or self.access_key or self.secret_key or self.session_token:
                raise ValueError("Local object storage cannot include S3 configuration")
            return
        if self.backend != "s3":
            raise ValueError("Private object storage backend is not configured")
        if self.local_root is not None:
            raise ValueError("S3 object storage cannot include a local fallback")
        if (not isinstance(self.bucket, str) or not re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", self.bucket)
                or ".." in self.bucket or ".-" in self.bucket or "-." in self.bucket):
            raise ValueError("Private object storage requires an explicit bucket")
        if not isinstance(self.region, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,62}", self.region):
            raise ValueError("Private object storage requires an explicit region")
        if not isinstance(self.access_key, str) or not self.access_key or not isinstance(self.secret_key, str) or not self.secret_key:
            raise ValueError("Private object storage requires explicit credentials")
        if self.session_token is not None and (not isinstance(self.session_token, str) or not self.session_token):
            raise ValueError("Invalid private object storage session configuration")
        if self.endpoint is not None:
            self._validate_endpoint()

    def _validate_endpoint(self) -> None:
        message = "Private object storage endpoint must be HTTPS without credentials or overrides"
        try:
            parsed = urlsplit(self.endpoint)
            if (not parsed.hostname or parsed.username is not None or parsed.password is not None
                    or parsed.path not in {"", "/"} or parsed.query or parsed.fragment
                    or parsed.port == 0 or any(char.isspace() for char in self.endpoint)):
                raise ValueError(message)
            if parsed.scheme == "https":
                return
            if parsed.scheme == "http" and not self.production:
                host = parsed.hostname
                if host == "localhost" or ip_address(host).is_loopback:
                    return
        except (ValueError, TypeError, AttributeError):
            pass
        raise ValueError(message)


def build_object_store(configuration: ObjectStoreConfiguration):
    """Build a private adapter with bounded SDK retries and explicit credentials.

    Invalid configuration fails before SDK construction or directory creation.
    S3 errors never create or select a local store. Callers retain their intent
    descriptor to reconcile ambiguous publication failures.
    """
    configuration.validate()
    if configuration.backend == "local":
        return LocalObjectStore(configuration.local_root)
    try:
        from boto3.session import Session
        from botocore.config import Config

        session = Session(aws_access_key_id=configuration.access_key,
            aws_secret_access_key=configuration.secret_key,
            aws_session_token=configuration.session_token, region_name=configuration.region)
        client = session.client("s3", endpoint_url=configuration.endpoint,
            config=Config(region_name=configuration.region, signature_version="s3v4",
                connect_timeout=3, read_timeout=10,
                retries={"mode": "standard", "total_max_attempts": 2},
                s3={"addressing_style": "path"}, ignore_configured_endpoint_urls=True))
    except Exception:
        raise ObjectUnavailable("Private object storage client unavailable") from None
    return S3ObjectStore(client, configuration.bucket)
