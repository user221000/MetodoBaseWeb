"""Persistent owner-only inventory and strict CAS/data bounds on owned SQLite."""
import json
from copy import deepcopy

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from core.gym_equipment_catalog import get_machine_catalog
from web.database.models import GymSettings, Usuario, UserRole
from web.routes.gym_equipment import InventoryUpdate
from web.services.gym_equipment import inventory_for_subject, save_inventory_for_subject


@pytest.fixture(scope='session',autouse=True)
def database_schema():
    # This module owns a two-table unit database; migration acceptance is
    # separately exercised against genuine39->40 databases in both dialects.
    yield


@pytest.fixture(autouse=True)
def isolated_database():
    yield


@pytest.fixture
def database(tmp_path):
    engine = create_engine('sqlite:///'+(tmp_path/'owned-inventory.sqlite').as_posix())
    Usuario.__table__.create(engine)
    GymSettings.__table__.create(engine)
    with Session(engine) as db:
        for identifier in ('inventory-owner-a','inventory-owner-b'):
            db.add(Usuario(id=identifier,email=identifier+'@example.invalid',nombre='Synthetic owner',
                           password_hash='not-a-login',tipo='gym',role=UserRole.OWNER,session_version=0))
        db.flush()
        for role in (UserRole.ADMIN,UserRole.NUTRIOLOGO,UserRole.VIEWER):
            db.add(Usuario(id='inventory-'+role.value,email='inventory-'+role.value+'@example.invalid',
                           nombre='Synthetic member',password_hash='not-a-login',tipo='usuario',role=role,
                           team_gym_id='inventory-owner-a',session_version=0))
        db.commit()
    yield engine
    engine.dispose()


def principal(db, identifier):
    row = db.get(Usuario,identifier)
    return {'id':row.id,'tipo':row.tipo,'role':row.role.value,
            'team_gym_id':row.team_gym_id,'session_version':row.session_version}


def test_get_is_read_only_and_unconfigured_differs_from_confirmed_empty(database):
    with Session(database) as db:
        actor = principal(db,'inventory-owner-a')
        first = inventory_for_subject(db,actor,'gym')
        assert first['configured'] is False and first['revision']==0 and first['machine_ids']==[]
        assert first['can_edit'] is True
        assert db.scalar(select(func.count()).select_from(GymSettings))==0
        saved = save_inventory_for_subject(db,actor,'gym',[],0)
        assert saved['configured'] is True and saved['revision']==1 and saved['machine_ids']==[]
    with Session(database) as fresh:
        actual = inventory_for_subject(fresh,principal(fresh,'inventory-owner-a'),'gym')
        assert actual==saved
        assert db.is_active


def test_save_is_visible_immediately_and_preserves_other_settings(database):
    selected = [r['id'] for r in get_machine_catalog()[:2]]
    with Session(database) as db:
        db.add(GymSettings(gym_id='inventory-owner-a',trial_days=77,trial_max_clients=19,
                           strict_mode=False,timezone='UTC',locale='en_US'))
        db.commit()
        actor = principal(db,'inventory-owner-a')
        answer = save_inventory_for_subject(db,actor,'gym',selected,0)
        assert answer['revision']==1 and answer['machine_ids']==sorted(selected)
    with Session(database) as fresh:
        row = fresh.scalar(select(GymSettings).where(GymSettings.gym_id=='inventory-owner-a'))
        assert (row.trial_days,row.trial_max_clients,row.strict_mode,row.timezone,row.locale)==(77,19,False,'UTC','en_US')
        payload = json.loads(row.training_equipment_json)
        assert payload=={'format_version':1,'revision':1,'machine_ids':sorted(selected)}
        assert inventory_for_subject(fresh,principal(fresh,'inventory-owner-b'),'gym')['configured'] is False


def test_stale_revision_cannot_overwrite_and_matching_revision_can_clear(database):
    machines = [get_machine_catalog()[0]['id']]
    with Session(database) as db:
        actor = principal(db,'inventory-owner-a')
        save_inventory_for_subject(db,actor,'gym',machines,0)
        with pytest.raises(HTTPException) as error:
            save_inventory_for_subject(db,actor,'gym',[],0)
        assert error.value.status_code==409
        assert inventory_for_subject(db,actor,'gym')['machine_ids']==machines
        cleared = save_inventory_for_subject(db,actor,'gym',[],1)
        assert cleared['revision']==2 and cleared['configured'] is True


@pytest.mark.parametrize('role',[UserRole.ADMIN,UserRole.NUTRIOLOGO,UserRole.VIEWER])
def test_members_read_same_inventory_but_never_save(database,role):
    with Session(database) as db:
        owner = principal(db,'inventory-owner-a')
        save_inventory_for_subject(db,owner,'gym',[get_machine_catalog()[0]['id']],0)
        actor = principal(db,'inventory-'+role.value)
        before = inventory_for_subject(db,actor,'gym')
        assert before['can_edit'] is False and before['revision']==1
        with pytest.raises(HTTPException) as error:
            save_inventory_for_subject(db,actor,'gym',[],1)
        assert error.value.status_code==403
        assert inventory_for_subject(db,actor,'gym')==before


def test_revoked_actor_or_parent_cannot_access(database):
    with Session(database) as db:
        owner = principal(db,'inventory-owner-a')
        member = principal(db,'inventory-'+UserRole.VIEWER.value)
        db.get(Usuario,'inventory-owner-a').activo=False
        db.commit()
        with pytest.raises(HTTPException) as error:
            inventory_for_subject(db,member,'gym')
        assert error.value.status_code==403
        with pytest.raises(HTTPException) as error:
            save_inventory_for_subject(db,owner,'gym',[],0)
        assert error.value.status_code==401
        assert db.scalar(select(func.count()).select_from(GymSettings))==0


def test_commit_failure_rolls_back_before_reporting_success(database,monkeypatch):
    with Session(database) as db:
        actor = principal(db,'inventory-owner-a')
        def fail():
            raise RuntimeError('Synthetic commit failure')
        monkeypatch.setattr(db,'commit',fail)
        with pytest.raises(RuntimeError):
            save_inventory_for_subject(db,actor,'gym',[],0)
    with Session(database) as fresh:
        assert fresh.scalar(select(func.count()).select_from(GymSettings))==0


@pytest.mark.parametrize('payload',[
    {'machine_ids':[],'expected_revision':True},
    {'machine_ids':[],'expected_revision':'0'},
    {'machine_ids':[],'expected_revision':0.0},
    {'machine_ids':[],'expected_revision':-1},
    {'machine_ids':[],'expected_revision':2147483647},
    {'machine_ids':['bad_id'],'expected_revision':0},
    {'machine_ids':['a'*65],'expected_revision':0},
    {'machine_ids':['leg-press','leg-press'],'expected_revision':0},
    {'machine_ids':['machine-'+str(i) for i in range(129)],'expected_revision':0},
    {'machine_ids':[],'expected_revision':0,'gym_id':'other'},
    {'machine_ids':[],'expected_revision':0,'trial_days':100},
])
def test_input_rejects_coercion_duplicates_identity_and_mass_assignment(payload):
    before = deepcopy(payload)
    with pytest.raises(ValidationError):
        InventoryUpdate.model_validate(payload)
    assert payload==before


@pytest.mark.parametrize('invalid',[
    '[]','{}','null','{"format_version":true,"revision":1,"machine_ids":[]}',
    '{"format_version":1,"revision":true,"machine_ids":[]}',
    '{"format_version":1,"revision":1,"machine_ids":["unknown-machine"]}',
])
def test_corrupt_inventory_fails_closed_instead_of_assuming_all_machines(database,invalid):
    with Session(database) as db:
        db.add(GymSettings(gym_id='inventory-owner-a',training_equipment_json=invalid))
        db.commit()
        with pytest.raises(HTTPException) as error:
            inventory_for_subject(db,principal(db,'inventory-owner-a'),'gym')
        assert error.value.status_code==503
