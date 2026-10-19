"""Revision31 personal-factor context, independent of professional tenant scope.

This capability selects only MFA secrets. Callers first prove the persisted
actor; no request field supplies this value. Every transaction shadows any
session-level residue with an empty LOCAL setting, including pool reuse.
"""
from sqlalchemy import event, text


def _clear(connection):
    connection.execute(text("SELECT set_config('app.mfa_actor', '', true)"))


def configure_mfa_engine(engine):
    if engine.dialect.name == "postgresql" and not event.contains(engine, "begin", _clear):
        event.listen(engine, "begin", _clear)
    return engine


def bind_mfa_actor(db, actor_id):
    if not isinstance(actor_id, str) or not actor_id or len(actor_id) > 36:
        raise ValueError("Verified MFA actor required")
    if db.get_bind().dialect.name == "postgresql":
        db.execute(text("SELECT set_config('app.mfa_actor', :actor, true)"), {"actor": actor_id})


def install_policies(connection):
    if connection.dialect.name != "postgresql":
        return
    for table in ("mfa_credentials", "mfa_recovery_codes"):
        connection.exec_driver_sql("CREATE POLICY mfa_actor_" + table + " ON " + table + " FOR ALL USING (user_id = NULLIF(current_setting('app.mfa_actor', true), '')) WITH CHECK (user_id = NULLIF(current_setting('app.mfa_actor', true), ''))")
        connection.exec_driver_sql("ALTER TABLE " + table + " ENABLE ROW LEVEL SECURITY")
        connection.exec_driver_sql("ALTER TABLE " + table + " FORCE ROW LEVEL SECURITY")
