"""S3-compatible adapter with immutable writes and authorized bounded reads.

The composition root supplies a configured SDK client and private bucket. This
module neither discovers credentials nor creates a bucket or paid resources.
"""
import base64

from web.storage.objects import (
    ObjectConflict, ObjectDescriptor, ObjectUnavailable, authorize, verify,
)


class S3ObjectStore:
    def __init__(self, client, bucket: str):
        if not bucket or not isinstance(bucket, str):
            raise ValueError("An explicit private bucket is required")
        self.client, self.bucket = client, bucket

    def put(self, descriptor: ObjectDescriptor, data: bytes, *, owner_id: str) -> None:
        authorize(descriptor, owner_id)
        verify(descriptor, data)
        try:
            self.client.put_object(Bucket=self.bucket, Key=descriptor.key, Body=data,
                ContentType=descriptor.content_type, ContentLength=descriptor.byte_size,
                ChecksumSHA256=base64.b64encode(bytes.fromhex(descriptor.sha256)).decode("ascii"),
                Metadata={"sha256": descriptor.sha256, "kind": descriptor.kind},
                IfNoneMatch="*")
        except Exception as error:
            code = getattr(error, "response", {}).get("Error", {}).get("Code")
            if code in {"PreconditionFailed", "412"}:
                try:
                    self.read(descriptor, owner_id=owner_id)
                    return
                except ObjectUnavailable:
                    raise ObjectConflict("Immutable private object differs") from None
            raise ObjectUnavailable("Private object write unavailable") from None

    def read(self, descriptor: ObjectDescriptor, *, owner_id: str) -> bytes:
        authorize(descriptor, owner_id)
        stream = None
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=descriptor.key)
            stream = response["Body"]
            if response["ContentLength"] != descriptor.byte_size:
                raise ObjectUnavailable("Private object size differs")
            data = stream.read(descriptor.byte_size + 1)
            return verify(descriptor, data)
        except ObjectUnavailable:
            raise
        except Exception:
            raise ObjectUnavailable("Private object read unavailable") from None
        finally:
            if stream is not None:
                try:
                    stream.close()
                except Exception:
                    raise ObjectUnavailable("Private object stream cleanup unavailable") from None

    def delete(self, descriptor: ObjectDescriptor, *, owner_id: str) -> None:
        authorize(descriptor, owner_id)
        try:
            self.client.delete_object(Bucket=self.bucket, Key=descriptor.key)
        except Exception:
            raise ObjectUnavailable("Private object deletion unavailable") from None
