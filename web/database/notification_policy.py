"""Revision36 invoker-only guards. GUC is context, never proof of a caller."""
from sqlalchemy import text,event
from web.database.notification_schema_v1 import TABLES,PREFERENCES,FACTS,OUTBOX,ATTEMPTS

_TRANSITIONS={
    "pending":("leased","suppressed"),"leased":("leased","sending","retry_wait","suppressed"),
    "sending":("accepted","retry_wait","failed","uncertain"),
    "retry_wait":("leased","suppressed"),"uncertain":("suppressed",),
}
_IMMUTABLE=("id","user_id","context","created_at","purpose","channel","preference_id","fact_id","source_hash","contact_hash","contact_version","request_key","request_hash")


def _same():
    return " AND ".join("NEW."+c+" IS OLD."+c for c in _IMMUTABLE)


def _transitions():
    return " OR ".join("(OLD.state='"+old+"' AND NEW.state IN ("+",".join("'"+s+"'" for s in new)+"))" for old,new in _TRANSITIONS.items())


def sqlite_statements():
    statements=[]
    for table in (PREFERENCES,FACTS,ATTEMPTS):
        for operation in ("UPDATE","DELETE"):
            statements.append("CREATE TRIGGER r36_"+table+"_"+operation.lower()+" BEFORE "+operation+" ON "+table+" BEGIN SELECT RAISE(ABORT,'Notification history is append only'); END")
    statements.append("CREATE TRIGGER r36_outbox_delete BEFORE DELETE ON "+OUTBOX+" BEGIN SELECT RAISE(ABORT,'Notification history requires reviewed restore'); END")
    account="EXISTS(SELECT 1 FROM usuarios WHERE id=NEW.user_id AND activo AND deleted_at IS NULL AND invitation_token IS NULL AND session_version BETWEEN 0 AND 2147483647)"
    exclude_account="EXISTS(SELECT 1 FROM usuarios WHERE id=NEW.user_id AND deleted_at IS NULL AND invitation_token IS NULL AND session_version BETWEEN 0 AND 2147483647 AND notification_contact_version=NEW.contact_version AND (NOT NEW.enabled OR activo))"
    eligible="EXISTS(SELECT 1 FROM usuarios u WHERE u.id=NEW.user_id AND ((NEW.context='gym' AND u.tipo='gym' AND u.role='OWNER' AND u.team_gym_id IS NULL) OR (NEW.context='personal' AND u.role IN ('ADMIN','NUTRIOLOGO','VIEWER') AND (u.tipo='usuario' OR u.team_gym_id IS NOT NULL) AND (u.team_gym_id IS NULL OR EXISTS(SELECT 1 FROM usuarios p WHERE p.id=u.team_gym_id AND p.activo AND p.deleted_at IS NULL AND p.invitation_token IS NULL AND p.tipo='gym' AND p.role='OWNER' AND p.team_gym_id IS NULL)))))"
    statements.append("CREATE TRIGGER r36_preference_insert BEFORE INSERT ON "+PREFERENCES+" WHEN NOT "+exclude_account+
        " OR NEW.version<>COALESCE((SELECT max(version) FROM notification_preferences WHERE user_id=NEW.user_id AND context=NEW.context AND purpose=NEW.purpose),0)+1 OR (NEW.enabled AND NOT "+eligible+
        ") OR (NOT NEW.enabled AND NOT EXISTS(SELECT 1 FROM notification_preferences WHERE user_id=NEW.user_id AND context=NEW.context AND purpose=NEW.purpose)) BEGIN SELECT RAISE(ABORT,'Notification preference scope denied'); END")
    mapping="EXISTS(SELECT 1 FROM provider_subject_associations a JOIN subscriptions s ON s.id=NEW.subscription_id AND s.gym_id=NEW.user_id AND s.provider=NEW.provider WHERE a.provider=NEW.provider AND a.resource_type=NEW.resource_type AND a.resource_id=NEW.resource_id AND a.subject_id=NEW.user_id AND ((NEW.provider='stripe' AND NEW.resource_type='subscription' AND s.stripe_subscription_id=NEW.resource_id) OR (NEW.provider='mercadopago' AND NEW.resource_type='payment' AND s.provider_payment_id=NEW.resource_id)))"
    statements.append("CREATE TRIGGER r36_fact_insert BEFORE INSERT ON "+FACTS+" WHEN NOT "+account+" OR NOT "+eligible+" OR NOT "+mapping+
        " OR NEW.version<>COALESCE((SELECT max(version) FROM notification_billing_facts WHERE user_id=NEW.user_id AND context=NEW.context),0)+1 BEGIN SELECT RAISE(ABORT,'Notification fact source denied'); END")
    source="EXISTS(SELECT 1 FROM notification_preferences p JOIN notification_billing_facts f ON f.id=NEW.fact_id AND f.user_id=p.user_id AND f.context=p.context JOIN usuarios u ON u.id=p.user_id AND u.notification_contact_version=p.contact_version WHERE p.id=NEW.preference_id AND p.user_id=NEW.user_id AND p.context=NEW.context AND p.purpose=NEW.purpose AND p.enabled AND p.contact_hash=NEW.contact_hash AND p.contact_version=NEW.contact_version AND f.source_hash=NEW.source_hash AND p.version=(SELECT max(x.version) FROM notification_preferences x WHERE x.user_id=p.user_id AND x.context=p.context AND x.purpose=p.purpose))"
    statements.append("CREATE TRIGGER r36_outbox_insert BEFORE INSERT ON "+OUTBOX+" WHEN NOT "+account+" OR NOT "+eligible+" OR NOT "+source+" OR NEW.state<>'pending' OR NEW.version<>1 OR NEW.attempt_count<>0 OR NEW.lease_hash IS NOT NULL OR NEW.lease_until IS NOT NULL OR NEW.sending_at IS NOT NULL OR NEW.exclude_hash IS NOT NULL BEGIN SELECT RAISE(ABORT,'Notification outbox source denied'); END")
    statements.append("CREATE TRIGGER r36_outbox_update BEFORE UPDATE ON "+OUTBOX+" WHEN NOT ("+_same()+") OR NEW.version<>OLD.version+1 OR NOT ("+_transitions()+") OR NEW.attempt_count<>OLD.attempt_count+CASE WHEN NEW.state='sending' THEN 1 ELSE 0 END BEGIN SELECT RAISE(ABORT,'Notification state transition denied'); END")
    statements.append("CREATE TRIGGER r36_attempt_insert BEFORE INSERT ON "+ATTEMPTS+" WHEN NEW.sequence<>COALESCE((SELECT max(sequence) FROM notification_attempts WHERE outbox_id=NEW.outbox_id),0)+1 OR NOT EXISTS(SELECT 1 FROM notification_outbox o WHERE o.id=NEW.outbox_id AND o.user_id=NEW.user_id AND o.context=NEW.context AND o.version=NEW.fence AND o.attempt_count=NEW.attempt_no) BEGIN SELECT RAISE(ABORT,'Notification attempt fence denied'); END")
    return statements


def install(connection):
    if connection.dialect.name=="sqlite":
        connection.exec_driver_sql("CREATE TRIGGER r36_contact_epoch_initial BEFORE INSERT ON usuarios WHEN NEW.notification_contact_version<>0 BEGIN SELECT RAISE(ABORT,'Notification contact epoch must start at zero'); END")
        connection.exec_driver_sql("CREATE TRIGGER r36_contact_epoch_guard BEFORE UPDATE ON usuarios WHEN typeof(NEW.notification_contact_version)<>'integer' OR NEW.notification_contact_version<OLD.notification_contact_version OR NEW.notification_contact_version>OLD.notification_contact_version+1 OR NEW.notification_contact_version>2147483647 OR (NEW.email IS NOT OLD.email AND OLD.notification_contact_version=2147483647) BEGIN SELECT RAISE(ABORT,'Notification contact epoch transition denied'); END")
        connection.exec_driver_sql("CREATE TRIGGER r36_contact_email_change AFTER UPDATE OF email ON usuarios WHEN NEW.email IS NOT OLD.email BEGIN UPDATE usuarios SET notification_contact_version=OLD.notification_contact_version+1 WHERE id=NEW.id; END")
        for statement in sqlite_statements():connection.exec_driver_sql(statement)
        return
    if connection.dialect.name!="postgresql":raise RuntimeError("Unreviewed notification dialect")
    connection.exec_driver_sql("""CREATE FUNCTION public.r36_contact_epoch() RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog AS $$ BEGIN IF TG_OP='INSERT' THEN IF NEW.notification_contact_version IS DISTINCT FROM 0 THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Notification contact epoch must start at zero'; END IF; RETURN NEW; END IF; IF NEW.notification_contact_version IS NULL OR NEW.notification_contact_version<OLD.notification_contact_version OR NEW.notification_contact_version::bigint>OLD.notification_contact_version::bigint+1 THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Notification contact epoch transition denied'; END IF; IF NEW.email IS DISTINCT FROM OLD.email THEN IF OLD.notification_contact_version=2147483647 THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Notification contact epoch exhausted'; END IF; NEW.notification_contact_version=OLD.notification_contact_version+1; END IF; RETURN NEW; END $$""")
    connection.exec_driver_sql("CREATE TRIGGER r36_contact_epoch_guard BEFORE INSERT OR UPDATE ON public.usuarios FOR EACH ROW EXECUTE FUNCTION public.r36_contact_epoch()")
    for table in TABLES:
        connection.exec_driver_sql("ALTER TABLE public."+table+" ENABLE ROW LEVEL SECURITY")
        connection.exec_driver_sql("ALTER TABLE public."+table+" FORCE ROW LEVEL SECURITY")
        connection.exec_driver_sql("CREATE POLICY r36_owner ON public."+table+" USING (user_id=NULLIF(current_setting('app.current_tenant',true),'')) WITH CHECK (user_id=NULLIF(current_setting('app.current_tenant',true),''))")
    connection.exec_driver_sql("CREATE POLICY r36_exclude_read ON public.notification_outbox FOR SELECT USING (exclude_protocol=1 AND exclude_purpose='notification_exclude' AND exclude_hash IS NOT NULL AND exclude_hash=NULLIF(current_setting('app.notification_exclude_digest',true),'') AND exclude_expires_at>(clock_timestamp() AT TIME ZONE 'UTC'))")
    connection.exec_driver_sql("""CREATE FUNCTION public.r36_immutable() RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog AS $$ BEGIN RAISE EXCEPTION USING ERRCODE='42501',MESSAGE='Notification history is append only'; END $$""")
    for table in (PREFERENCES,FACTS,ATTEMPTS):
        connection.exec_driver_sql("CREATE TRIGGER r36_"+table+"_immutable BEFORE UPDATE OR DELETE ON public."+table+" FOR EACH ROW EXECUTE FUNCTION public.r36_immutable()")
    connection.exec_driver_sql("CREATE TRIGGER r36_outbox_delete BEFORE DELETE ON public.notification_outbox FOR EACH ROW EXECUTE FUNCTION public.r36_immutable()")
    # Compile equivalent closed SQLite predicates to invoker trigger guards.
    # Literal table names/columns are module constants, never caller input.
    for name,statement in enumerate(sqlite_statements()[7:],1):
        table=statement.split(" ON ",1)[1].split(" WHEN ",1)[0]
        operation="UPDATE" if " BEFORE UPDATE " in statement else "INSERT"
        predicate=statement.split(" WHEN ",1)[1].split(" BEGIN SELECT RAISE",1)[0]
        predicate=predicate.replace("NEW.enabled AND", "NEW.enabled AND")
        # IS comparison on immutable scalar columns has SQL NULL-safe semantics.
        import re
        predicate=re.sub(r"NEW\.([a-z_]+) IS OLD\.([a-z_]+)",r"NEW.\1 IS NOT DISTINCT FROM OLD.\2",predicate)
        # All table references are explicitly public; the function path is closed.
        for target in ("provider_subject_associations","subscriptions","usuarios",*TABLES):
            predicate=re.sub(r"(?<![.\w])"+target+r"\b","public."+target,predicate)
        function="r36_guard_"+str(name)
        connection.exec_driver_sql("CREATE FUNCTION public."+function+"() RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog AS $$ BEGIN IF current_setting('transaction_isolation')<>'read committed' THEN RAISE EXCEPTION USING ERRCODE='25000',MESSAGE='Notification mutations require read committed'; END IF; PERFORM id FROM public.usuarios WHERE id=NEW.user_id FOR UPDATE NOWAIT; IF ("+predicate+") IS NOT FALSE THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Notification transition or source denied'; END IF; RETURN NEW; END $$")
        connection.exec_driver_sql("CREATE TRIGGER "+function+" BEFORE "+operation+" ON public."+table+" FOR EACH ROW EXECUTE FUNCTION public."+function+"()")


def signature(connection):
    if connection.dialect.name=="sqlite":
        return {"dialect":"sqlite","triggers":[list(r) for r in connection.execute(text("SELECT name,tbl_name,sql FROM sqlite_master WHERE type='trigger' AND name LIKE 'r36_%' ORDER BY name"))]}
    functions=connection.execute(text("SELECT p.proname,pg_get_function_identity_arguments(p.oid),pg_get_function_result(p.oid),p.prosecdef,p.proconfig,p.provolatile,p.proparallel,p.proacl::text,p.prosrc,l.lanname FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace JOIN pg_language l ON l.oid=p.prolang WHERE n.nspname=current_schema() AND p.proname LIKE 'r36_%' ORDER BY p.proname")).all()
    triggers=connection.execute(text("SELECT c.relname,t.tgname,t.tgenabled,t.tgdeferrable,t.tginitdeferred,pg_get_triggerdef(t.oid,false) FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid WHERE c.relnamespace=current_schema()::regnamespace AND NOT t.tgisinternal AND t.tgname LIKE 'r36_%' ORDER BY c.relname,t.tgname")).all()
    flags=connection.execute(text("SELECT relname,relrowsecurity,relforcerowsecurity FROM pg_class WHERE relnamespace=current_schema()::regnamespace AND relkind='r' AND relname LIKE 'notification_%' ORDER BY relname")).all()
    policies=connection.execute(text("SELECT tablename,policyname,permissive,roles::text,cmd,qual,with_check FROM pg_policies WHERE schemaname=current_schema() AND tablename LIKE 'notification_%' ORDER BY tablename,policyname")).all()
    return {"dialect":"postgresql","functions":[list(r) for r in functions],"triggers":[list(r) for r in triggers],"flags":[list(r) for r in flags],"policies":[list(r) for r in policies]}


def _reset_begin(connection):
    connection.execute(text("SELECT set_config('app.notification_exclude_digest','',true)"))


def configure_engine(engine):
    """New purpose-local reset, including a prior session-level setting."""
    if engine.dialect.name=="postgresql" and not event.contains(engine,"begin",_reset_begin):
        event.listen(engine,"begin",_reset_begin)
