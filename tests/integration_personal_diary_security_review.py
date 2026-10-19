"""Independent real-PG identity race and session-affinity negatives."""
import pytest
from fastapi import HTTPException
from sqlalchemy import event, select
from sqlalchemy.orm import Session

from tests.integration_personal_diary_postgres import diary_pg, migration_database, DAY, NOW

pytestmark=pytest.mark.parametrize('migration_database',['postgresql'],indirect=True)


@pytest.mark.parametrize('revocation',['owner_role','inactive','pending'])
def test_identity_is_revalidated_after_account_lock_is_acquired(diary_pg,revocation):
    from web.database.models import Usuario,UserRole,PersonalDiaryDay
    from web.personal_diary_schemas import WaterOperation
    from web.services.personal_diary_persistence import patch_diary_day
    admin,app=diary_pg
    applied=[]
    def revoke_before_account_write(connection,cursor,statement,parameters,context,executemany):
        if applied or not statement.upper().startswith('UPDATE USUARIOS '):
            return
        applied.append(True)
        with Session(admin) as db:
            user=db.get(Usuario,'diary-person')
            if revocation=='owner_role':user.role=UserRole.OWNER
            elif revocation=='inactive':user.activo=False
            else:user.invitation_token='synthetic-review-pending'
            db.commit()
    event.listen(app,'before_cursor_execute',revoke_before_account_write)
    try:
        with Session(app) as db,pytest.raises(HTTPException) as failure:
            patch_diary_day(db,'diary-person',DAY,WaterOperation(operation='water',expected_version=0,water_ml=999),now=NOW)
    finally:
        event.remove(app,'before_cursor_execute',revoke_before_account_write)
    assert applied==[True]
    # Pending membership discovered after the lock is denied as personal scope;
    # the pre-lock identity branch uses 401. Both prevent the mutation.
    assert failure.value.status_code=={'owner_role':409,'inactive':401,'pending':403}[revocation]
    with Session(admin) as db:
        assert db.query(PersonalDiaryDay).count()==0


def test_committed_session_cannot_change_subject_for_diary_or_export(diary_pg):
    from web.database.models import PersonalDiaryDay
    from web.personal_diary_schemas import WaterOperation
    from web.services.personal_diary_persistence import patch_diary_day,read_diary_day
    from web.services.privacy_export import export_personal_data
    admin,app=diary_pg
    for subject,water in [('diary-person',123),('diary-other',789)]:
        with Session(app) as db:
            patch_diary_day(db,subject,DAY,WaterOperation(operation='water',expected_version=0,water_ml=water),now=NOW)
    with Session(app) as db:
        assert read_diary_day(db,'diary-person',DAY,now=NOW)['water_ml']==123
        db.commit()
        with pytest.raises(HTTPException) as denied:
            read_diary_day(db,'diary-other',DAY,now=NOW)
        assert denied.value.status_code==403
        db.rollback()
        with pytest.raises(HTTPException) as denied:
            export_personal_data(db,'diary-other')
        assert denied.value.status_code==403
        db.rollback()
        assert db.scalars(select(PersonalDiaryDay.user_id)).all()==['diary-person']
    with app.connect() as connection:
        assert connection.exec_driver_sql("SELECT current_setting('app.current_tenant',true)").scalar_one()==''
        assert connection.exec_driver_sql('SELECT count(*) FROM personal_diary_days').scalar_one()==0
    with Session(admin) as db:
        assert db.query(PersonalDiaryDay).count()==2
