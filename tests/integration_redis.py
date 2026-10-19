"""Real Redis Lua, expiration and shared-worker gates; invoked explicitly in CI.

Requires METODOBASE_TEST_REDIS_URL at loopback:56379/15. Each case records
only its UUID-owned keys and deletes only those keys. No shared DB reset.
"""
import asyncio
from contextlib import asynccontextmanager
import multiprocessing
import os
import queue
import time
import uuid

import pytest

from tests.isolation import validate_redis_test_url

pytestmark = pytest.mark.redis


@pytest.fixture
def redis_endpoint():
    import redis

    url = os.environ.get("METODOBASE_TEST_REDIS_URL", "")
    if not url:
        pytest.fail("Redis integration requires explicit METODOBASE_TEST_REDIS_URL")
    validate_redis_test_url(url)
    client = redis.Redis.from_url(url, decode_responses=True,
                                 socket_connect_timeout=2, socket_timeout=2)
    assert client.ping(), "Dedicated Redis did not answer PING"
    prefix = "metodobase:test:" + uuid.uuid4().hex + ":"
    keys = set()

    def owned_key(suffix):
        key = prefix + suffix
        keys.add(key)
        return key

    try:
        yield url, client, owned_key
    finally:
        if keys:
            client.delete(*keys)
        client.close()


@asynccontextmanager
async def _production_counter(url):
    import redis.asyncio as redis
    import web.rate_limiter_redis as limiter

    client = redis.Redis.from_url(url, decode_responses=True,
                                 socket_connect_timeout=2, socket_timeout=2)
    previous = limiter._redis_pool
    limiter._redis_pool = client
    try:
        yield limiter
    finally:
        limiter._redis_pool = previous
        await client.aclose()


def test_fixed_window_rejection_does_not_extend_ttl_and_expiry_reopens(redis_endpoint):
    url, client, key_for = redis_endpoint
    key = key_for("short-window")

    async def check():
        async with _production_counter(url) as limiter:
            assert (await limiter._is_allowed_redis(key, 1, 3))[0]
            initial_ttl = client.pttl(key)
            assert 2500 <= initial_ttl <= 3000
            await asyncio.sleep(1.1)
            allowed, info = await limiter._is_allowed_redis(key, 1, 3)
            remaining_ttl = client.pttl(key)
            assert not allowed and info["remaining"] == 0
            assert 0 < remaining_ttl <= initial_ttl - 900
            assert 1 <= info["retry_after"] <= 3
            await asyncio.sleep(remaining_ttl / 1000 + 0.15)
            allowed, info = await limiter._is_allowed_redis(key, 1, 3)
            assert allowed and info["remaining"] == 0
            assert client.get(key) == "1"

    asyncio.run(check())


def test_long_login_window_and_missing_ttl_are_repaired(redis_endpoint):
    url, client, key_for = redis_endpoint
    key = key_for("legacy-counter-without-expiration")
    client.set(key, 5)
    assert client.ttl(key) == -1

    async def check():
        async with _production_counter(url) as limiter:
            allowed, info = await limiter._is_allowed_redis(key, 5, 900)
            assert not allowed
            assert 895 <= client.ttl(key) <= 900
            assert 895 <= info["retry_after"] <= 900

    asyncio.run(check())


def _worker_attempts(url, key, barrier, result_queue):
    """One distinct worker process with its own Redis connection pool."""
    try:
        from tests.isolation import block_external_sockets, prepare_environment
        prepare_environment(discard_inherited=True)
        block_external_sockets()

        async def check():
            async with _production_counter(url) as limiter:
                await limiter._redis_pool.ping()
                barrier.wait(timeout=40)
                results = await asyncio.gather(*(
                    limiter._is_allowed_redis(key, 7, 30) for _ in range(8)))
                return sum(allowed for allowed, _ in results)

        result_queue.put({"accepted": asyncio.run(check())})
    except Exception as error:
        result_queue.put({"error": type(error).__name__})


def test_four_processes_share_one_atomic_limit(redis_endpoint):
    url, client, key_for = redis_endpoint
    key = key_for("four-workers")
    context = multiprocessing.get_context("spawn")
    barrier = context.Barrier(4)
    result_queue = context.Queue()
    workers = [context.Process(target=_worker_attempts,
               args=(url, key, barrier, result_queue)) for _ in range(4)]
    try:
        for worker in workers:
            worker.start()
        deadline = time.monotonic() + 55
        for worker in workers:
            worker.join(timeout=max(0, deadline - time.monotonic()))
        assert all(not worker.is_alive() and worker.exitcode == 0 for worker in workers)
        results = []
        for _ in workers:
            try:
                results.append(result_queue.get(timeout=2))
            except queue.Empty:
                pytest.fail("Redis worker did not report its result")
        assert all("error" not in result for result in results), results
        assert sum(result["accepted"] for result in results) == 7
        assert client.get(key) == "32"
        assert 1 <= client.ttl(key) <= 30
    finally:
        for worker in workers:
            if worker.is_alive():
                worker.terminate()
            worker.join(timeout=5)
        result_queue.close()


def test_login_dependency_shares_account_across_ips_without_storing_email(redis_endpoint, monkeypatch):
    """Two app instances use the actual dependency and Redis decision function."""
    from fastapi import Depends, FastAPI
    from fastapi.testclient import TestClient
    from types import SimpleNamespace
    import web.middleware.rate_limiter as dependency_module
    import web.rate_limiter_redis as redis_module

    url, client, key_for = redis_endpoint
    monkeypatch.setattr(dependency_module, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr("web.settings.get_settings", lambda: SimpleNamespace(
        REDIS_URL=url, SECRET_KEY="synthetic-test-only-secret", TRUSTED_PROXY_COUNT=0))
    production_check = redis_module.check_rate_limit

    async def namespaced_check(key, *args, **kwargs):
        async with _production_counter(url):
            return await production_check(key_for(key), *args, **kwargs)

    monkeypatch.setattr(redis_module, "check_rate_limit", namespaced_check)
    dependency = dependency_module.rate_limit_dependency(2, 900, account_field="email")

    def app():
        application = FastAPI()

        @application.post("/login", dependencies=[Depends(dependency)])
        async def login():
            return {"accepted": True}

        return application

    with TestClient(app(), client=("127.0.0.2", 40001)) as first, TestClient(
            app(), client=("127.0.0.3", 40002)) as second:
        assert first.post("/login", json={"email": " Synthetic@Example.invalid "}).status_code == 200
        assert second.post("/login", json={"email": "synthetic@example.invalid"}).status_code == 200
        response = second.post("/login", json={"email": "SYNTHETIC@example.invalid"})
        assert response.status_code == 429
        assert 895 <= int(response.headers["Retry-After"]) <= 900
        assert second.post("/login", json={"email": "different@example.invalid"}).status_code == 429
    account_key = key_for("rl:dependency:/login:2:900:account:")
    # Enumerate only this case's prefix; cleanup still targets exact owned keys.
    account_keys = list(client.scan_iter(match=account_key + "*"))
    assert len(account_keys) == 1
    assert "synthetic" not in account_keys[0].lower() and "@" not in account_keys[0]
    assert 895 <= client.ttl(account_keys[0]) <= 900
