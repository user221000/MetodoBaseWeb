"""Bounded instrumentation; importing this module uses the standard library only.

Wrappers delegate once and preserve results/exceptions. Application imports occur
only inside install_application_hooks(), after the explicit driver's isolation.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from functools import wraps
import hashlib
import inspect
import json
import math
from pathlib import Path
import threading
import time


CURRENT = ContextVar("generation_characterization_sample", default=None)
PARENT = ContextVar("generation_characterization_parent", default=None)


class CaptureRejected(RuntimeError):
    """A technical capture bound or integrity condition failed."""


@dataclass
class Sample:
    identifier: str
    labels: dict
    spans: list = field(default_factory=list)
    counters: dict = field(default_factory=dict)
    facts: dict = field(default_factory=dict)
    errors: list = field(default_factory=list)
    lock: object = field(default_factory=threading.RLock, repr=False)

    def counter(self, name, amount=1):
        with self.lock:
            self.counters[name] = self.counters.get(name, 0) + amount

    def snapshot(self):
        with self.lock:
            return {"sample": self.identifier, "labels": dict(self.labels),
                    "spans": [dict(row) for row in self.spans],
                    "counters": dict(self.counters), "facts": dict(self.facts),
                    "capture_errors": list(self.errors)}


def quantiles(values):
    values = sorted(values)
    if not values:
        return {"n": 0}
    return {"n": len(values), "min": values[0],
            "p50": values[math.ceil(.50 * len(values)) - 1],
            "p95": values[math.ceil(.95 * len(values)) - 1], "max": values[-1],
            "method": "nearest_rank", "SLO": None}


class Recorder:
    def __init__(self, *, maximum_generations, maximum_object_bytes,
                 clock=time.perf_counter_ns, cpu_clock=time.thread_time_ns, deadline=None):
        if (type(maximum_generations) is not int or not 1 <= maximum_generations <= 100
                or type(maximum_object_bytes) is not int
                or not 1 <= maximum_object_bytes <= 64 * 1024**2):
            raise CaptureRejected("Explicit bounded generation/object budget required")
        self.maximum_generations = maximum_generations
        self.maximum_object_bytes = maximum_object_bytes
        self.clock, self.cpu_clock = clock, cpu_clock
        self.deadline = deadline
        self.lock = threading.Lock()
        self.generations = self.object_bytes = self.sequence = 0

    @contextmanager
    def sample(self, identifier, labels):
        if CURRENT.get() is not None:
            raise CaptureRejected("Nested HTTP sample rejected")
        row = Sample(identifier, dict(labels))
        token, parent = CURRENT.set(row), PARENT.set(None)
        try:
            yield row
        finally:
            PARENT.reset(parent)
            CURRENT.reset(token)

    @contextmanager
    def span(self, name):
        row = CURRENT.get()
        if row is None:
            yield
            return
        with self.lock:
            self.sequence += 1
            identifier = self.sequence
        started, cpu = self.clock(), self.cpu_clock()
        parent = PARENT.get()
        token = PARENT.set(identifier)
        error_class = None
        try:
            yield
        except BaseException as error:
            error_class = type(error).__name__
            raise
        finally:
            ended, cpu_ended = self.clock(), self.cpu_clock()
            PARENT.reset(token)
            with row.lock:
                row.spans.append({"id": identifier, "parent": parent, "name": name,
                                  "start_ns": started, "end_ns": ended,
                                  "elapsed_ns": ended - started,
                                  "thread_CPU_ns": cpu_ended - cpu,
                                  "thread_id": threading.get_ident(), "error_class": error_class})

    def wrap(self, name, original, *, before=None, after=None):
        @wraps(original)
        def delegated(*args, **kwargs):
            with self.span(name):
                if before is not None and CURRENT.get() is not None:
                    before(*args, **kwargs)
                result = original(*args, **kwargs)
            if after is not None and CURRENT.get() is not None:
                after(result)
            return result
        return delegated

    def rendered(self, result):
        # Both approved renderers return the completed PDF path, or None on
        # their existing failure path. Do not turn None into a synthetic PDF.
        if result is None:
            return
        with self.span("observer.closed_renderer_readback"):
            with Path(result).open("rb") as source:
                size = source.seek(0, 2)
                source.seek(0)
                if not 0 < size <= self.maximum_object_bytes:
                    raise CaptureRejected("Closed renderer output exceeds object budget")
                pdf_sha = hashlib.file_digest(source, "sha256").hexdigest()
            row = CURRENT.get()
            with row.lock:
                if "rendered_PDF" in row.facts:
                    raise CaptureRejected("More than one renderer output for a generation")
                row.facts["rendered_PDF"] = {"bytes": size, "sha256": pdf_sha}

    def generation(self, *args, **kwargs):
        del args, kwargs
        with self.lock:
            if self.deadline is not None and time.monotonic() >= self.deadline:
                raise CaptureRejected("Admission deadline exhausted before core")
            if self.generations >= self.maximum_generations:
                raise CaptureRejected("Generation budget exhausted before core")
            self.generations += 1
            ordinal = self.generations
        CURRENT.get().counter("generation_calls")
        # Only the first actual generation of this process can be cold.
        CURRENT.get().labels["generation_process_phase"] = "first_generation" if ordinal == 1 else "subsequent_generation"

    def core_inputs(self, *args, **kwargs):
        del args
        catalogue = kwargs.get("catalogo")
        if catalogue is None:
            raise CaptureRejected("Real constructor catalogue snapshot absent")
        # Hash the actual effective catalogue names/exclusions, not the caller's
        # labels. No catalogue or health values are published in the row.
        names, excluded = sorted(catalogue.alimentos), sorted(catalogue.excluidos)
        encoded = lambda value: json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf8")
        row = CURRENT.get()
        with row.lock:
            if "core_catalogue" in row.facts:
                raise CaptureRejected("Multiple constructor catalogues for one generation")
            row.facts["core_catalogue"] = {"food_count": len(names), "excluded_count": len(excluded),
                "names_sha256": hashlib.sha256(encoded(names)).hexdigest(),
                "excluded_sha256": hashlib.sha256(encoded(excluded)).hexdigest()}

    def put(self, store, descriptor, data, *, owner_id):
        del store, descriptor, owner_id
        with self.lock:
            if self.object_bytes + len(data) > self.maximum_object_bytes:
                raise CaptureRejected("Object byte budget exhausted before PUT")
            self.object_bytes += len(data)
        CURRENT.get().counter("PUT_attempted_bytes", len(data))

    def lock_factory(self, original):
        @wraps(original)
        def observed(*args, **kwargs):
            return ObservedLock(original(*args, **kwargs), self)
        return observed

    def to_thread(self, original, allowed):
        @wraps(original)
        async def delegated(function, /, *args, **kwargs):
            if function not in allowed or CURRENT.get() is None:
                return await original(function, *args, **kwargs)
            submitted = self.clock()
            row = CURRENT.get()

            @wraps(function)
            def start(*inner_args, **inner_kwargs):
                if CURRENT.get() is not row:
                    raise CaptureRejected("Executor ContextVar correlation lost")
                row.counter("executor_starts")
                row.counter("executor_handoff_ns", self.clock() - submitted)
                with self.span("executor.worker"):
                    return function(*inner_args, **inner_kwargs)
            with self.span("executor.await"):
                return await original(start, *args, **kwargs)
        return delegated

    def mail_sink(self, *args, **kwargs):
        del args, kwargs
        row = CURRENT.get()
        if row is None:
            raise CaptureRejected("Uncorrelated mail transport rejected")
        row.counter("mail_transport_suppressed")
        return False


class ObservedLock:
    """Proxy for the SAME real lock; no new synchronization or retry policy."""
    def __init__(self, original, recorder):
        self.original, self.recorder, self.started = original, recorder, None

    def acquire(self, *args, **kwargs):
        with self.recorder.span("client_lock.acquire"):
            acquired = self.original.acquire(*args, **kwargs)
        if acquired:
            self.started = self.recorder.clock()
        return acquired

    def release(self):
        try:
            return self.original.release()
        finally:
            row = CURRENT.get()
            if row is not None and self.started is not None:
                row.counter("client_lock_held_ns", self.recorder.clock() - self.started)
            self.started = None


class Patches:
    def __init__(self):
        self.rows = []

    def set(self, owner, name, replacement):
        own = name in vars(owner)
        raw = inspect.getattr_static(owner, name)
        setattr(owner, name, replacement)
        self.rows.append((owner, name, own, raw))

    def callable(self, owner, name, recorder, label, *, before=None, after=None):
        raw = inspect.getattr_static(owner, name)
        if isinstance(raw, classmethod):
            replacement = classmethod(recorder.wrap(label, raw.__func__, before=before, after=after))
        elif isinstance(raw, staticmethod):
            replacement = staticmethod(recorder.wrap(label, raw.__func__, before=before, after=after))
        else:
            replacement = recorder.wrap(label, getattr(owner, name), before=before, after=after)
        self.set(owner, name, replacement)

    def close(self):
        failures = []
        while self.rows:
            owner, name, own, raw = self.rows.pop()
            try:
                if own:
                    setattr(owner, name, raw)
                else:
                    delattr(owner, name)
            except BaseException as error:
                failures.append(type(error).__name__)
        if failures:
            raise CaptureRejected("Instrumentation restoration failed")

    def __enter__(self):
        return self

    def __exit__(self, kind, error, traceback):
        try:
            self.close()
        except BaseException:
            if error is None:
                raise
            row = CURRENT.get()
            if row is not None:
                row.errors.append("instrumentation_restoration_failed")
        return False


@contextmanager
def install_application_hooks(recorder):
    """Called only inside the isolated application child; no fake business work."""
    import asyncio
    from sqlalchemy.orm import Session
    from api.routes import planes as api_planes
    from web.routes import planes as web_planes
    from web.services import generation_quota, gym_generation_quota, plan_generation
    from web.services import private_objects, plan_documents, email_service
    from web.database import repository
    from web.storage.local import LocalObjectStore
    from core.generador_planes import ConstructorPlanNuevo
    from core.generador_opciones import ConstructorPlanConOpciones
    from core.exportador_opciones import GeneradorPDFConOpciones
    from web.pdf import PDFGenerator

    with Patches() as patches:
        for owner, method, label in (
            (gym_generation_quota, "reserve_gym_generation", "quota.gym.reserve"),
            (gym_generation_quota, "lock_gym_account", "quota.gym.account_lock"),
            (gym_generation_quota, "complete_gym_generation", "quota.gym.complete"),
            (generation_quota, "reserve_generation", "quota.individual.reserve"),
            (generation_quota, "_lock_account", "quota.individual.account_lock"),
            (generation_quota, "finish_generation", "quota.individual.finish"),
            (plan_generation, "_build_plan", "generation.build"),
            (private_objects, "publish_pending_object", "object.publish_pending"),
            (private_objects, "mark_object_ready", "object.stage_ready"),
            (repository, "registrar_plan", "plan.stage"),
            (Session, "commit", "transaction.commit"),
            (Session, "flush", "transaction.flush"),
            (LocalObjectStore, "read", "object.local.read"),
            (plan_documents, "read_plan_pdf", "object.authorized_PDF_read"),
        ):
            patches.callable(owner, method, recorder, label)
        patches.callable(ConstructorPlanNuevo, "construir", recorder, "core.menu_fijo", before=recorder.core_inputs)
        patches.callable(ConstructorPlanConOpciones, "construir", recorder, "core.opciones", before=recorder.core_inputs)
        patches.callable(PDFGenerator, "generar_plan", recorder, "render.menu_fijo", after=recorder.rendered)
        patches.callable(GeneradorPDFConOpciones, "generar", recorder, "render.opciones", after=recorder.rendered)
        patches.callable(plan_generation, "generate_plan", recorder, "generation", before=recorder.generation)
        patches.callable(LocalObjectStore, "put", recorder, "object.local.PUT", before=recorder.put)
        patches.set(plan_generation, "_client_lock", recorder.lock_factory(plan_generation._client_lock))
        patches.set(asyncio, "to_thread", recorder.to_thread(asyncio.to_thread,
                    {web_planes._generar_plan_sync, api_planes._generar_plan_sync}))
        patches.set(email_service, "send_plan_generated", recorder.mail_sink)
        yield
