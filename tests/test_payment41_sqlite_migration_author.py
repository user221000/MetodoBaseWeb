"""Genuine40/41 SQLite migrations, preserved rows, constraints and loss guard."""
from contextlib import contextmanager
import importlib

import pytest
from alembic import command
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError


@pytest.fixture(scope='session', autouse=True)
def database_schema():
    yield


@pytest.fixture(autouse=True)
def isolated_database():
    yield


@contextmanager
def migrated40():
    from web.database.schema_control import alembic_config
    engine = create_engine('sqlite://')
    try:
        with engine.connect() as connection:
            connection.exec_driver_sql('PRAGMA foreign_keys=OFF')
            connection.commit()
            config = alembic_config()
            config.attributes['connection'] = connection
            command.upgrade(config, '20261031_gym_equipment')
            connection.execute(text("INSERT INTO usuarios(id,email,password_hash,nombre,apellido,tipo,role,activo,fecha_registro) "
                "VALUES ('refund-owner','refund-owner@example.invalid','unused','Synthetic','','gym','OWNER',true,'2026-11-01')"))
            connection.execute(text("INSERT INTO payments(gym_id,amount_cents,currency,status,created_at) "
                "VALUES ('refund-owner',7900,'mxn','refunded','2026-11-01')"))
            connection.commit()
            yield engine, connection, config
    finally:
        engine.dispose()


def test_additive_upgrade_preserves_legacy_unknown_and_old_security_contract():
    from web.database.schema_control import verify_runtime_schema
    migration = importlib.import_module('web.database.alembic.versions.20261102_payment_refund_facts')
    with migrated40() as (engine, connection, config):
        old = migration.signature(connection)
        command.upgrade(config, 'head')
        command.upgrade(config, 'head')
        connection.commit()
        assert connection.execute(text('SELECT amount_cents,status,refund_amount_cents,refund_observed_at,stripe_charge_id FROM payments')).one() == (7900, 'refunded', None, None, None)
        current = migration.signature(connection)
        assert {k: v for k, v in old.items() if k != 'signature'} == {k: v for k, v in current.items() if k != 'signature'}
        assert connection.exec_driver_sql('PRAGMA foreign_key_check').all() == []
        verify_runtime_schema(engine)


@pytest.mark.parametrize('values', [
    {'refund': -1, 'status': 'partially_refunded', 'at': '2026-11-02', 'charge': 'ch_owned'},
    {'refund': 7901, 'status': 'refunded', 'at': '2026-11-02', 'charge': 'ch_owned'},
    {'refund': 1.5, 'status': 'partially_refunded', 'at': '2026-11-02', 'charge': 'ch_owned'},
    {'refund': 1, 'status': 'succeeded', 'at': '2026-11-02', 'charge': 'ch_owned'},
    {'refund': 7900, 'status': 'partially_refunded', 'at': '2026-11-02', 'charge': 'ch_owned'},
    {'refund': 1, 'status': 'partially_refunded', 'at': None, 'charge': 'ch_owned'},
    {'refund': None, 'status': 'succeeded', 'at': '2026-11-02', 'charge': None},
])
def test_real_database_rejects_impossible_amounts_and_partial_observations(values):
    with migrated40() as (_, connection, config):
        command.upgrade(config, 'head')
        connection.commit()
        with pytest.raises(IntegrityError):
            connection.execute(text('UPDATE payments SET refund_amount_cents=:refund,status=:status,refund_observed_at=:at,stripe_charge_id=:charge'), values)
        connection.rollback()
        assert connection.scalar(text('SELECT refund_amount_cents FROM payments')) is None


def test_downgrade_allows_unknowns_but_blocks_loss_of_observed_money():
    with migrated40() as (_, connection, config):
        command.upgrade(config, 'head')
        connection.commit()
        command.downgrade(config, '20261031_gym_equipment')
        connection.commit()
        assert connection.execute(text('SELECT amount_cents,status FROM payments')).one() == (7900, 'refunded')
        command.upgrade(config, 'head')
        connection.execute(text("UPDATE payments SET refund_amount_cents=100,status='partially_refunded',"
            "refund_observed_at='2026-11-02',stripe_charge_id='ch_owned'"))
        connection.commit()
        with pytest.raises(RuntimeError, match='data-preserving recovery'):
            command.downgrade(config, '20261031_gym_equipment')
        connection.rollback()
        assert connection.scalar(text('SELECT version_num FROM alembic_version')) == '20261102_payment_refund_facts'
        assert connection.scalar(text('SELECT refund_amount_cents FROM payments')) == 100
