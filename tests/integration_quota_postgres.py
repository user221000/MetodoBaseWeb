"""PostgreSQL multi-process quota regressions on an owned synthetic schema.

Metadata creates a test-only concurrency schema; this module does not validate
Alembic, RLS or a deployment. Those have separate mandatory acceptance checks.
"""
import multiprocessing
import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
import uuid

import pytest

from tests.isolation import validate_postgres_test_url


def _quota_worker(url, action, output, loaded, release, acquired, started):
    """Use a separate process/connection; events control actual SQL interleaving."""
    from fastapi import HTTPException
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from web.database.models import UserSubscription
    from web.services.billing_integrity import get_individual_subscription
    from web.services.generation_quota import reserve_generation

    engine = create_engine(url, pool_size=1, max_overflow=0)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    paused = False

    def pause():
        nonlocal paused
        if not paused:
            paused = True
            loaded.set()
            if not release.wait(15):
                raise RuntimeError("Synthetic concurrency coordination timed out")

    if action == "read-existing":
        @event.listens_for(factory.class_, "loaded_as_persistent")
        def pause_loaded(session, instance):
            if isinstance(instance, UserSubscription):
                pause()

    @event.listens_for(engine, "after_cursor_execute")
    def record_sql(connection, cursor, statement, parameters, context, executemany):
        normalized = statement.lower()
        if action == "read-absent" and "from user_subscriptions" in normalized:
            pause()
        if action.startswith("reserve") and normalized.lstrip().startswith("update usuarios"):
            acquired.set()

    try:
        if action.startswith("reserve-parallel"):
            release.wait(10)
        started.set()
        with factory() as db:
            if action.startswith("reserve"):
                reservation = reserve_generation(db, "quota-person", action)
                output.put(("accepted", reservation.id))
            else:
                get_individual_subscription(db, "quota-person")
                db.commit()
                output.put(("read", "committed"))
    except HTTPException as exc:
        output.put(("denied", exc.status_code))
    except Exception as exc:
        output.put(("error", type(exc).__name__))
    finally:
        engine.dispose()


@pytest.fixture
def quota_database():
    import psycopg2
    from psycopg2 import sql
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from web.database.models import Base, Usuario, UserRole

    admin_url = os.environ["METODOBASE_TEST_MIGRATOR_URL"]
    app_url = os.environ["METODOBASE_TEST_POSTGRES_URL"]
    validate_postgres_test_url(admin_url)
    validate_postgres_test_url(app_url)
    parsed = urlsplit(admin_url)
    app_parts = urlsplit(app_url)
    assert (parsed.hostname, parsed.port) == (app_parts.hostname, app_parts.port)
    name = "metodobase_test_quota_" + uuid.uuid4().hex[:12]
    admin = psycopg2.connect(admin_url.replace("postgresql+psycopg2://", "postgresql://", 1))
    admin.autocommit = True
    with admin.cursor() as cursor:
        cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    database_admin = urlunsplit(parsed._replace(path="/" + name))
    database_app = urlunsplit(app_parts._replace(path="/" + name))
    engine = create_engine(database_admin)
    Base.metadata.create_all(engine)
    with psycopg2.connect(database_admin.replace("postgresql+psycopg2://", "postgresql://", 1)) as db, db.cursor() as cursor:
        role = sql.Identifier(app_parts.username)
        cursor.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(role))
        cursor.execute(sql.SQL("GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO {}").format(role))
        cursor.execute(sql.SQL("GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA public TO {}").format(role))
    with Session(engine) as db:
        db.add(Usuario(id="quota-person", email="quota@example.test", nombre="Synthetic", tipo="usuario",
                       role=UserRole.VIEWER, password_hash="unused-synthetic", activo=True))
        db.commit()
    try:
        yield database_app, engine
    finally:
        engine.dispose()
        with admin.cursor() as cursor:
            assert name.startswith("metodobase_test_quota_")
            cursor.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))
        admin.close()


def _join_owned(processes):
    for process in processes:
        process.join(15)
        if process.is_alive():
            process.terminate()
            process.join(5)
            pytest.fail("Owned synthetic worker timed out")
        assert process.exitcode == 0


def test_last_credit_accepts_only_one_of_three_processes(quota_database):
    from sqlalchemy.orm import Session
    from web.database.models import UserSubscription, GenerationReservation
    from web.services.billing_integrity import current_quota_period
    url, engine = quota_database
    with Session(engine) as db:
        db.add(UserSubscription(user_id="quota-person", plan="starter", max_planes_mes=1,
                               planes_usados_mes=0, mes_actual=current_quota_period()))
        db.commit()
    context = multiprocessing.get_context("spawn")
    output = context.Queue()
    barrier = context.Barrier(3)
    processes = [context.Process(target=_quota_worker, args=(url, f"reserve-parallel-{index}", output,
                    context.Event(), barrier, context.Event(), context.Event())) for index in range(3)]
    for process in processes:
        process.start()
    _join_owned(processes)
    outcomes = [output.get(timeout=5)[0] for _ in processes]
    assert outcomes.count("accepted") == 1
    assert outcomes.count("denied") == 2
    with Session(engine) as db:
        assert db.query(UserSubscription).one().planes_usados_mes == 1
        assert db.query(GenerationReservation).count() == 1


@pytest.mark.parametrize("projection_exists", [True, False])
def test_subscription_get_cannot_erase_or_collide_with_reserved_credit(quota_database, projection_exists):
    from sqlalchemy.orm import Session
    from web.database.models import UserSubscription, GenerationReservation
    from web.services.billing_integrity import current_quota_period
    url, engine = quota_database
    if projection_exists:
        with Session(engine) as db:
            db.add(UserSubscription(user_id="quota-person", plan="starter", max_planes_mes=1,
                                   planes_usados_mes=1, mes_actual="2000-01"))
            db.commit()
    context = multiprocessing.get_context("spawn")
    loaded, release, acquired, started = context.Event(), context.Event(), context.Event(), context.Event()
    output = context.Queue()
    reader = context.Process(target=_quota_worker, args=(url, "read-existing" if projection_exists else "read-absent", output, loaded, release, acquired, context.Event()))
    writer = context.Process(target=_quota_worker, args=(url, "reserve-concurrent", output, loaded, release, acquired, started))
    reader.start()
    try:
        assert loaded.wait(10), "Reader never reached the real projection query"
        writer.start()
        assert started.wait(10), "Writer never reached the database operation"
        # Before the fix, the writer acquires the unprotected account and commits
        # while the reader holds its old snapshot. With serialization it waits.
        if acquired.wait(3):
            writer.join(10)
            assert not writer.is_alive()
        release.set()
        _join_owned([reader, writer])
    finally:
        release.set()
        for process in (reader, writer):
            if process.pid and process.is_alive():
                process.terminate()
                process.join(5)
    outcomes = sorted(output.get(timeout=5)[0] for _ in range(2))
    assert outcomes == ["accepted", "read"]
    with Session(engine) as db:
        projection = db.query(UserSubscription).one()
        assert projection.mes_actual == current_quota_period()
        assert projection.planes_usados_mes == 1
        assert db.query(GenerationReservation).count() == 1
