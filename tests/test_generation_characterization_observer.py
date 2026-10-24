"""Pure observers: no application/core/PDF/SDK/database imports or operations."""
import asyncio
import ast
from contextlib import asynccontextmanager, contextmanager
import inspect
from pathlib import Path
import sys
import threading
from types import SimpleNamespace

import pytest

from tests.performance.generation_observer import (
    CURRENT, PARENT, CaptureRejected, Patches, Recorder, quantiles,
)


@pytest.fixture(scope="session", autouse=True)
def database_schema():
    """This module exercises only stdlib callbacks, never a database fixture."""
    yield


@pytest.fixture(autouse=True)
def isolated_database():
    """No application fixture is required for the pure observer."""
    yield


def recorder(**kwargs):
    return Recorder(maximum_generations=kwargs.pop("generations", 2),
                    maximum_object_bytes=kwargs.pop("bytes", 64), **kwargs)


def test_delegation_preserves_identity_arguments_result_and_single_call():
    seen, after, result, argument = [], [], object(), object()
    def original(value, *, option):
        seen.append((value, option))
        return result
    observed = recorder()
    with observed.sample("one", {"cell": 0}) as row:
        assert observed.wrap("core", original, after=after.append)(argument, option=argument) is result
        assert seen == [(argument, argument)]
        assert after == [result]
    assert [span["name"] for span in row.spans] == ["core"]
    assert row.spans[0]["error_class"] is None
    assert CURRENT.get() is None and PARENT.get() is None


def test_original_exception_object_propagates_and_context_is_restored():
    failure, calls, after = ValueError("synthetic"), [], []
    def original():
        calls.append(1)
        raise failure
    observed = recorder()
    with pytest.raises(ValueError) as caught:
        with observed.sample("failed", {}) as row:
            observed.wrap("render", original, after=after.append)()
    assert caught.value is failure and calls == [1]
    assert after == []
    assert row.spans[0]["error_class"] == "ValueError"
    assert CURRENT.get() is None and PARENT.get() is None


def test_nested_spans_have_one_parent_and_no_cross_sample_context():
    observed = recorder()
    with observed.sample("outer", {}) as first:
        with observed.span("parent"):
            with observed.span("child"):
                pass
    parent = next(row for row in first.spans if row["name"] == "parent")
    child = next(row for row in first.spans if row["name"] == "child")
    assert child["parent"] == parent["id"] and parent["parent"] is None
    with observed.sample("next", {}) as second:
        with observed.span("another"):
            pass
    assert second.spans[0]["parent"] is None
    assert len({row["id"] for row in first.spans + second.spans}) == 3


def test_real_to_thread_keeps_sample_and_delegates_once():
    observed, calls = recorder(), []
    def actual(value):
        calls.append((value, CURRENT.get().identifier, threading.get_ident()))
        return value
    parent_thread = threading.get_ident()
    async def run():
        with observed.sample("thread", {}) as row:
            delegated = observed.to_thread(asyncio.to_thread, {actual})
            result = await delegated(actual, 7)
            return result, row
    result, row = asyncio.run(run())
    assert result == 7 and len(calls) == 1
    assert calls[0][1] == "thread" and calls[0][2] != parent_thread
    assert row.counters["executor_starts"] == 1
    worker = next(span for span in row.spans if span["name"] == "executor.worker")
    waiting = next(span for span in row.spans if span["name"] == "executor.await")
    assert worker["parent"] == waiting["id"]
    assert CURRENT.get() is None and PARENT.get() is None


def test_thread_failure_preserves_exception_and_does_not_retry():
    observed, calls, failure = recorder(), [], RuntimeError("synthetic worker")
    def actual():
        calls.append(1)
        raise failure
    async def run():
        with observed.sample("thread-error", {}):
            return await observed.to_thread(asyncio.to_thread, {actual})(actual)
    with pytest.raises(RuntimeError) as caught:
        asyncio.run(run())
    assert caught.value is failure and calls == [1]
    assert CURRENT.get() is None


def test_same_real_lock_is_used_once_and_is_released():
    observed, lock, calls = recorder(), threading.Lock(), []
    def factory(tenant, client):
        calls.append((tenant, client))
        return lock
    with observed.sample("locked", {}) as row:
        proxy = observed.lock_factory(factory)("synthetic-tenant", "synthetic-client")
        assert proxy.original is lock
        assert proxy.acquire(timeout=.1) is True and lock.locked()
        proxy.release()
    assert not lock.locked() and calls == [("synthetic-tenant", "synthetic-client")]
    assert sum(span["name"] == "client_lock.acquire" for span in row.spans) == 1
    assert row.counters["client_lock_held_ns"] >= 0


def test_generation_and_object_budgets_refuse_before_original_effect():
    observed, effects = recorder(generations=1, bytes=3), []
    def generate():
        effects.append("generation")
    def put(store, descriptor, data, *, owner_id):
        effects.append(bytes(data))
    with observed.sample("bound", {}):
        delegated = observed.wrap("generation", generate, before=observed.generation)
        delegated()
        with pytest.raises(CaptureRejected):
            delegated()
        upload = observed.wrap("PUT", put, before=observed.put)
        upload(None, None, b"abc", owner_id="synthetic")
        with pytest.raises(CaptureRejected):
            upload(None, None, b"x", owner_id="synthetic")
    assert effects == ["generation", b"abc"]
    assert observed.generations == 1 and observed.object_bytes == 3


def test_only_first_generation_of_process_is_labelled_first():
    observed = recorder()
    with observed.sample("cell-a", {"cell": 0}) as first:
        observed.generation()
    with observed.sample("cell-b", {"cell": 1}) as second:
        observed.generation()
    assert first.labels["generation_process_phase"] == "first_generation"
    assert second.labels["generation_process_phase"] == "subsequent_generation"


def test_admission_deadline_refuses_before_delegate_effect(monkeypatch):
    observed, calls = recorder(deadline=10.0), []
    monkeypatch.setattr("tests.performance.generation_observer.time.monotonic", lambda: 10.0)
    with observed.sample("expired", {}), pytest.raises(CaptureRejected):
        observed.wrap("generation", lambda: calls.append(1), before=observed.generation)()
    assert calls == [] and observed.generations == 0


def test_closed_renderer_readback_matches_result_and_is_separate_from_render(tmp_path):
    import hashlib
    observed, payload = recorder(bytes=64), b"%PDF-synthetic-observer-only"
    path = tmp_path / "synthetic.pdf"
    path.write_bytes(payload)
    with observed.sample("render", {}) as row:
        assert observed.wrap("render.synthetic", lambda: path, after=observed.rendered)() is path
    assert row.facts["rendered_PDF"] == {"bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
    proof = next(span for span in row.spans if span["name"] == "observer.closed_renderer_readback")
    render = next(span for span in row.spans if span["name"] == "render.synthetic")
    assert proof["parent"] is None and proof["start_ns"] >= render["end_ns"]


def test_descriptors_and_inherited_method_restore_after_exception():
    class Base:
        def method(self, value):
            return value
    class Example(Base):
        @classmethod
        def class_method(cls, value):
            return cls, value
        @staticmethod
        def static_method(value):
            return value
    observed = recorder()
    original_class = inspect.getattr_static(Example, "class_method")
    original_static = inspect.getattr_static(Example, "static_method")
    with pytest.raises(ValueError):
        with Patches() as changes, observed.sample("restore", {}):
            changes.callable(Example, "class_method", observed, "classmethod")
            changes.callable(Example, "static_method", observed, "staticmethod")
            changes.callable(Example, "method", observed, "inherited")
            assert Example.class_method(3) == (Example, 3)
            assert Example.static_method(4) == 4 and Example().method(5) == 5
            raise ValueError("synthetic")
    assert inspect.getattr_static(Example, "class_method") is original_class
    assert inspect.getattr_static(Example, "static_method") is original_static
    assert "method" not in vars(Example)


def test_restoration_attempts_all_owners_even_when_one_fails():
    class Refusing:
        def __init__(self):
            object.__setattr__(self, "method", "old")
            object.__setattr__(self, "refuse", False)
        def __setattr__(self, name, value):
            if name == "method" and self.refuse:
                raise RuntimeError("synthetic restore refusal")
            object.__setattr__(self, name, value)
    other, refusing = SimpleNamespace(method="old"), Refusing()
    changes = Patches()
    changes.set(other, "method", "new")
    changes.set(refusing, "method", "new")
    refusing.refuse = True
    with pytest.raises(CaptureRejected):
        changes.close()
    assert other.method == "old" and changes.rows == []


def test_percentiles_always_retain_sample_count_without_SLO():
    row = quantiles([9, 1, 5])
    assert row["n"] == 3 and row["p50"] == 5 and row["p95"] == 9
    assert row["SLO"] is None and quantiles([])["n"] == 0


@pytest.mark.parametrize("value", [True, 0, 101, 1.0])
def test_generation_budget_requires_exact_bounded_integer(value):
    with pytest.raises(CaptureRejected):
        recorder(generations=value)


@pytest.mark.parametrize("late_failure", [None, "original_lifespan", "restoration"])
def test_closed_receipt_is_published_only_after_actual_lifespan_and_restoration_exit(
        late_failure, monkeypatch, tmp_path):
    """Exercise the driver's literal lifespan AST, never import an application."""
    source = Path(__file__).parent / "performance/characterize_generation_http.py"
    tree = ast.parse(source.read_text(encoding="utf8"))
    serve = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "serve")
    actual = next(node for node in serve.body if isinstance(node, ast.AsyncFunctionDef) and node.name == "lifespan")
    events, writes = [], []
    failure = RuntimeError("synthetic late exit")

    @asynccontextmanager
    async def original_lifespan(app):
        del app
        yield
        events.append("original_lifespan_exit")
        if late_failure == "original_lifespan":
            raise failure

    @contextmanager
    def hooks(observed):
        del observed
        yield
        events.append("hooks_exit")

    close = Patches.close
    def close_patches(changes):
        close(changes)
        events.append("patches_restored")
        if late_failure == "restoration":
            raise failure
    monkeypatch.setattr(Patches, "close", close_patches)
    # The only imported non-stdlib module in this extracted function is our
    # pure observer. This explicit inert stub prevents importing the PG module.
    monkeypatch.setitem(sys.modules, "tests.billing13_legacy_apply37_pg_contract",
                        SimpleNamespace(windows_process_identity=lambda pid: (1, Path("E:/synthetic-python.exe"))))
    pool = SimpleNamespace(_do_get=lambda: None, size=lambda: 1, _max_overflow=0, timeout=lambda: 30)
    engine = SimpleNamespace(pool=pool, dispose=lambda: events.append("dispose"))
    class LocalStore:
        root = tmp_path / "metodobase-test-data"
    def endpoint():
        pass
    endpoint.__module__ = "web.routes.planes"
    app = SimpleNamespace(routes=[SimpleNamespace(path="/api/generar-plan", methods={"POST"}, endpoint=endpoint)])
    args = SimpleNamespace(output=tmp_path, factory="web", nonce="synthetic", ready=tmp_path / "ready.json")
    def write_json(path, value):
        if path.name.endswith("-observer-closed.json"):
            assert events[-3:] == ["hooks_exit", "patches_restored", "original_lifespan_exit"]
        writes.append((path.name, value))
    space = {"asynccontextmanager": asynccontextmanager, "original_lifespan": original_lifespan,
        "get_engine": lambda: engine, "verify_runtime_schema": lambda *a, **k: None,
        "get_object_store": lambda: LocalStore(), "LocalObjectStore": LocalStore,
        "contract": {"expected_schema_revision": "synthetic-observer-revision"},
        "args": args, "recorder": recorder(), "install_application_hooks": hooks,
        "event": SimpleNamespace(listen=lambda *a: None, remove=lambda *a: None),
        "sql_before": object(), "sql_after": object(), "checkout": object(), "checkin": object(),
        "application": app, "os": SimpleNamespace(getpid=lambda: 101, getppid=lambda: 100),
        "sys": SimpleNamespace(argv=["synthetic"]), "write_json": write_json,
        "active": {"pool": 0, "ASGI": 0, "HTTP": 0}, "maximum_http": 10,
        "CaptureRejected": CaptureRejected}
    exec(compile(ast.Module(body=[actual], type_ignores=[]), str(source), "exec"), space)
    async def exercise():
        async with space["lifespan"](app):
            events.append("request")
    if late_failure is None:
        asyncio.run(exercise())
        assert [name for name, value in writes if name.endswith("-observer-closed.json")] == ["web-observer-closed.json"]
    else:
        with pytest.raises(RuntimeError) as caught:
            asyncio.run(exercise())
        assert caught.value is failure
        assert not any(name.endswith("-observer-closed.json") for name, value in writes)
    assert "dispose" in events and "patches_restored" in events
