"""Real boto3 parameter/StreamingBody contracts with botocore Stubber, no service.

This explicit integration target requires the dedicated SDK environment. It
does not claim an object provider, container replacement or production bucket.
"""
import base64
from io import BytesIO

import boto3
from botocore.response import StreamingBody
from botocore.stub import Stubber
import pytest

from tests.isolation import block_external_sockets, prepare_environment
from web.storage.objects import ObjectAccessDenied, ObjectConflict, ObjectUnavailable, describe
from web.storage.s3 import S3ObjectStore

prepare_environment(discard_inherited=True)
block_external_sockets()


@pytest.fixture
def s3_case():
    client = boto3.client("s3", endpoint_url="http://127.0.0.1:1", region_name="us-east-1",
                          aws_access_key_id="synthetic", aws_secret_access_key="synthetic")
    data = b"%PDF-1.7\nsynthetic-private-plan\n%%EOF"
    descriptor = describe("gym-a", "plan_pdf", data, "application/pdf")
    with Stubber(client) as stub:
        yield S3ObjectStore(client, "private-test-bucket"), stub, descriptor, data
        stub.assert_no_pending_responses()
    client.close()


def put_parameters(descriptor, data):
    return dict(Bucket="private-test-bucket", Key=descriptor.key, Body=data,
        ContentType="application/pdf", ContentLength=len(data), IfNoneMatch="*",
        ChecksumSHA256=base64.b64encode(bytes.fromhex(descriptor.sha256)).decode("ascii"),
        Metadata={"sha256": descriptor.sha256, "kind": "plan_pdf"})


def test_sdk_immutable_put_and_verified_download_contract(s3_case):
    store, stub, descriptor, data = s3_case
    stub.add_response("put_object", {}, put_parameters(descriptor, data))
    stub.add_response("get_object", {"Body": StreamingBody(BytesIO(data), len(data)), "ContentLength": len(data)},
                      {"Bucket": store.bucket, "Key": descriptor.key})
    store.put(descriptor, data, owner_id="gym-a")
    assert store.read(descriptor, owner_id="gym-a") == data


@pytest.mark.parametrize("operation", ["put", "read", "delete"])
def test_other_owner_is_denied_before_any_sdk_request(s3_case, operation):
    store, _, descriptor, data = s3_case
    with pytest.raises(ObjectAccessDenied):
        if operation == "put":
            store.put(descriptor, data, owner_id="gym-b")
        else:
            getattr(store, operation)(descriptor, owner_id="gym-b")


def test_storage_error_is_sanitized_without_local_fallback(s3_case):
    store, stub, descriptor, data = s3_case
    stub.add_client_error("put_object", "AccessDenied", "untrusted transport detail", 403,
                          expected_params=put_parameters(descriptor, data))
    with pytest.raises(ObjectUnavailable) as error:
        store.put(descriptor, data, owner_id="gym-a")
    assert "untrusted" not in str(error.value)


@pytest.mark.parametrize("same", [True, False])
def test_existing_object_retry_verifies_bytes_and_never_overwrites(s3_case, same):
    store, stub, descriptor, data = s3_case
    stub.add_client_error("put_object", "PreconditionFailed", "already exists", 412,
                          expected_params=put_parameters(descriptor, data))
    existing = data if same else data.replace(b"synthetic", b"altered--")
    stub.add_response("get_object", {"Body": StreamingBody(BytesIO(existing), len(existing)), "ContentLength": len(existing)},
                      {"Bucket": store.bucket, "Key": descriptor.key})
    if same:
        store.put(descriptor, data, owner_id="gym-a")
    else:
        with pytest.raises(ObjectConflict):
            store.put(descriptor, data, owner_id="gym-a")


def test_downloaded_corruption_is_rejected(s3_case):
    store, stub, descriptor, data = s3_case
    corrupted = data.replace(b"synthetic", b"altered--")
    stub.add_response("get_object", {"Body": StreamingBody(BytesIO(corrupted), len(corrupted)), "ContentLength": len(corrupted)},
                      {"Bucket": store.bucket, "Key": descriptor.key})
    with pytest.raises(ObjectUnavailable):
        store.read(descriptor, owner_id="gym-a")
