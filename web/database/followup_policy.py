"""Revision34 append-only events, atomic projection and tenant-only RLS.

These invoker triggers enforce relational/state invariants, not an authenticated
actor signature. The shared SQL app role can set a GUC; route authorization must
still reload the actor and apply the assignee predicate on every operation.
"""
from sqlalchemy import text
from web.database.followup_schema_v1 import SNAPSHOT, IMMUTABLE


def _actor():
    return """EXISTS(SELECT 1 FROM usuarios a JOIN usuarios g ON g.id=NEW.gym_id
        WHERE a.id=NEW.actor_id AND a.activo AND a.deleted_at IS NULL AND a.invitation_token IS NULL
        AND a.session_version BETWEEN 0 AND 2147483647 AND a.session_version=CAST(a.session_version AS INTEGER)
        AND lower(a.role) = NEW.actor_role AND g.activo AND g.deleted_at IS NULL
        AND g.session_version BETWEEN 0 AND 2147483647 AND g.session_version=CAST(g.session_version AS INTEGER)
        AND g.invitation_token IS NULL AND g.tipo='gym' AND g.role='OWNER' AND g.team_gym_id IS NULL
        AND ((a.id=g.id AND a.role='OWNER' AND a.tipo='gym' AND a.team_gym_id IS NULL)
          OR (a.team_gym_id=g.id AND a.role IN ('ADMIN','NUTRIOLOGO'))))"""


def _assignee():
    return """(NEW.assignee_id IS NULL OR EXISTS(SELECT 1 FROM usuarios a WHERE a.id=NEW.assignee_id
        AND a.activo AND a.deleted_at IS NULL AND a.invitation_token IS NULL
        AND a.session_version BETWEEN 0 AND 2147483647 AND a.session_version=CAST(a.session_version AS INTEGER)
        AND ((a.id=NEW.gym_id AND a.role='OWNER' AND a.tipo='gym' AND a.team_gym_id IS NULL)
          OR (a.team_gym_id=NEW.gym_id AND a.role IN ('ADMIN','NUTRIOLOGO')))))"""


def _source(equal):
    return f"""EXISTS(SELECT 1 FROM clientes c WHERE c.id_cliente=NEW.client_id AND c.gym_id=NEW.gym_id
        AND c.activo AND c.deleted_at IS NULL AND c.fecha_fin_suscripcion {equal} NEW.membership_end)
        AND NEW.plan_count=(SELECT count(*) FROM planes_generados p WHERE p.gym_id=NEW.gym_id
            AND p.id_cliente=NEW.client_id AND p.deleted_at IS NULL)
        AND NEW.last_plan_at {equal} (SELECT max(p.fecha_generacion) FROM planes_generados p
            WHERE p.gym_id=NEW.gym_id AND p.id_cliente=NEW.client_id AND p.deleted_at IS NULL)"""


def _projection(equal):
    return "EXISTS(SELECT 1 FROM followup_task_events e WHERE e.id=NEW.current_event_id AND e.task_id=NEW.id AND " + " AND ".join(
        f"e.{field} {equal} NEW.{field}" for field in SNAPSHOT) + ")"


def _qualifies(clock, cutoff):
    return f"""((NEW.cause='no_saved_plan' AND NEW.plan_count=0)
        OR (NEW.cause='plan_date_missing' AND NEW.plan_count>0 AND NEW.last_plan_at IS NULL)
        OR (NEW.cause='no_plan_in_window' AND NEW.plan_count>0 AND NEW.last_plan_at IS NOT NULL AND NEW.last_plan_at<{cutoff})
        OR (NEW.cause='membership_date_passed' AND NEW.membership_end IS NOT NULL AND NEW.membership_end<{clock}))"""


def _immutable(equal):
    return " AND ".join(f"NEW.{field} {equal} OLD.{field}" for field in ("id", *IMMUTABLE))


def _projection_insert():
    names = ["id", *SNAPSHOT, "current_event_id"]
    values = ["NEW.task_id", *("NEW."+c for c in SNAPSHOT), "NEW.id"]
    return "INSERT INTO followup_tasks("+",".join(names)+") VALUES("+",".join(values)+");"


def _projection_update():
    return "UPDATE followup_tasks SET " + ",".join(f"{c}=NEW.{c}" for c in SNAPSHOT) + ",current_event_id=NEW.id WHERE id=NEW.task_id AND gym_id=NEW.gym_id;"


def _transition(prior):
    return f"""((NEW.kind='created' AND NEW.version=1 AND NEW.status='open' AND NEW.created_by=NEW.actor_id
        AND NEW.created_at=NEW.updated_at AND NOT EXISTS(SELECT 1 FROM followup_tasks t WHERE t.id=NEW.task_id))
        OR (NEW.kind<>'created' AND EXISTS(SELECT 1 FROM followup_tasks t WHERE t.id=NEW.task_id
          AND t.gym_id=NEW.gym_id AND t.status='open' AND t.version<2147483647 AND NEW.version=t.version+1
          AND ((NEW.kind='updated' AND NEW.status='open' AND (NEW.next_step<>t.next_step OR NEW.assignee_id {prior} t.assignee_id))
            OR (NEW.kind='completed' AND NEW.status='completed' AND NEW.completed_by=NEW.actor_id
                AND NEW.assignee_id IS NOT NULL AND NEW.assignee_id=t.assignee_id AND NEW.next_step=t.next_step)
            OR (NEW.kind='cancelled' AND NEW.status='cancelled' AND NEW.cancelled_by=NEW.actor_id
                AND NEW.assignee_id {('IS' if prior == 'IS NOT' else 'IS NOT DISTINCT FROM')} t.assignee_id AND NEW.next_step=t.next_step)))))"""


def install(connection):
    if connection.dialect.name == "sqlite":
        _sqlite(connection)
    elif connection.dialect.name == "postgresql":
        _postgres(connection)
    else:
        raise RuntimeError("Unsupported task ledger dialect")


def _sqlite(c):
    c.exec_driver_sql("""CREATE TRIGGER r34_event_preserve_update BEFORE UPDATE ON followup_task_events
        BEGIN SELECT RAISE(ABORT,'Follow-up event is append only'); END""")
    c.exec_driver_sql("""CREATE TRIGGER r34_event_preserve_delete BEFORE DELETE ON followup_task_events
        BEGIN SELECT RAISE(ABORT,'Follow-up event requires reviewed purge'); END""")
    c.exec_driver_sql(f"""CREATE TRIGGER r34_event_authorize BEFORE INSERT ON followup_task_events BEGIN
        SELECT CASE WHEN NOT ({_actor()}) THEN RAISE(ABORT,'Follow-up actor denied') END;
        SELECT CASE WHEN NEW.kind<>'cancelled' AND NOT ({_assignee()}) THEN RAISE(ABORT,'Follow-up assignee denied') END;
        SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM clientes WHERE id_cliente=NEW.client_id AND gym_id=NEW.gym_id AND activo AND deleted_at IS NULL)
            THEN RAISE(ABORT,'Follow-up client denied') END;
        SELECT CASE WHEN NOT ({_transition('IS NOT')}) THEN RAISE(ABORT,'Follow-up transition denied') END;
        SELECT CASE WHEN NEW.kind='created' AND NOT ({_source('IS')}) THEN RAISE(ABORT,'Follow-up source changed') END;
        SELECT CASE WHEN NEW.kind='created' AND NOT ({_qualifies("strftime('%Y-%m-%d %H:%M:%f','now')", "strftime('%Y-%m-%d %H:%M:%f','now','-30 days')")}) THEN RAISE(ABORT,'Follow-up cause absent') END;
        SELECT CASE WHEN NEW.actor_role='nutriologo' AND (NEW.kind<>'completed' OR NEW.assignee_id IS NOT NEW.actor_id)
            THEN RAISE(ABORT,'Follow-up assigned operation denied') END;
        END""")
    c.exec_driver_sql(f"""CREATE TRIGGER r34_task_insert BEFORE INSERT ON followup_tasks BEGIN
        SELECT CASE WHEN NEW.version<>1 OR NEW.status<>'open' OR NOT ({_projection('IS')})
            THEN RAISE(ABORT,'Follow-up projection requires exact event') END; END""")
    c.exec_driver_sql(f"""CREATE TRIGGER r34_task_update BEFORE UPDATE ON followup_tasks BEGIN
        SELECT CASE WHEN OLD.status<>'open' OR NEW.version<>OLD.version+1 OR NEW.updated_at<OLD.updated_at OR NOT ({_immutable('IS')})
            OR NOT ({_projection('IS')}) THEN RAISE(ABORT,'Follow-up projection is immutable') END; END""")
    c.exec_driver_sql("""CREATE TRIGGER r34_task_delete BEFORE DELETE ON followup_tasks BEGIN
        SELECT RAISE(ABORT,'Follow-up task requires reviewed purge'); END""")
    c.exec_driver_sql(f"""CREATE TRIGGER r34_event_create AFTER INSERT ON followup_task_events WHEN NEW.kind='created'
        BEGIN {_projection_insert()} END""")
    c.exec_driver_sql(f"""CREATE TRIGGER r34_event_apply AFTER INSERT ON followup_task_events WHEN NEW.kind<>'created'
        BEGIN {_projection_update()} END""")


def _postgres(c):
    # SELECT role enums explicitly cast to TEXT; no reliance on enum coercion.
    actor = _actor().replace("lower(a.role)", "lower(a.role::text)")
    c.exec_driver_sql(f"""CREATE FUNCTION r34_event_guard() RETURNS trigger LANGUAGE plpgsql
        VOLATILE SECURITY INVOKER SET search_path=pg_catalog,public AS $$
        DECLARE hint public.followup_tasks; prior public.followup_tasks;
        BEGIN
          IF TG_OP<>'INSERT' THEN RAISE EXCEPTION USING ERRCODE='42501',MESSAGE='Follow-up event is append only'; END IF;
          IF NEW.gym_id IS DISTINCT FROM NULLIF(current_setting('app.current_tenant',true),'')
              OR ({actor}) IS NOT TRUE THEN RAISE EXCEPTION USING ERRCODE='42501',MESSAGE='Follow-up actor denied'; END IF;
          SELECT * INTO hint FROM public.followup_tasks WHERE id=NEW.task_id AND gym_id=NEW.gym_id;
          PERFORM 1 FROM public.usuarios WHERE id=ANY(ARRAY[NEW.actor_id,NEW.gym_id,NEW.assignee_id,hint.assignee_id]) ORDER BY id FOR UPDATE NOWAIT;
          IF ({actor}) IS NOT TRUE OR (NEW.kind<>'cancelled' AND ({_assignee()}) IS NOT TRUE)
              THEN RAISE EXCEPTION USING ERRCODE='42501',MESSAGE='Follow-up eligibility changed'; END IF;
          PERFORM 1 FROM public.clientes WHERE id_cliente=NEW.client_id AND gym_id=NEW.gym_id AND activo AND deleted_at IS NULL FOR SHARE NOWAIT;
          IF NOT FOUND THEN RAISE EXCEPTION USING ERRCODE='42501',MESSAGE='Follow-up client denied'; END IF;
          SELECT * INTO prior FROM public.followup_tasks WHERE id=NEW.task_id AND gym_id=NEW.gym_id FOR UPDATE NOWAIT;
          IF prior.assignee_id IS DISTINCT FROM hint.assignee_id THEN RAISE EXCEPTION USING ERRCODE='55P03',MESSAGE='Follow-up lock set changed'; END IF;
          IF ({_transition('IS DISTINCT FROM')}) IS NOT TRUE
              THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Follow-up transition denied'; END IF;
          IF NEW.kind='created' AND ({_source('IS NOT DISTINCT FROM')}) IS NOT TRUE
              THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Follow-up source changed'; END IF;
          IF NEW.kind='created' AND ({_qualifies("(clock_timestamp() AT TIME ZONE 'UTC')", "(clock_timestamp() AT TIME ZONE 'UTC') - interval '30 days'")}) IS NOT TRUE
              THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Follow-up cause absent'; END IF;
          IF NEW.actor_role='nutriologo' AND (NEW.kind<>'completed' OR NEW.assignee_id IS DISTINCT FROM NEW.actor_id)
              THEN RAISE EXCEPTION USING ERRCODE='42501',MESSAGE='Follow-up assigned operation denied'; END IF;
          RETURN NEW;
        END $$""")
    c.exec_driver_sql("CREATE TRIGGER r34_event_guard BEFORE INSERT OR UPDATE OR DELETE ON followup_task_events FOR EACH ROW EXECUTE FUNCTION r34_event_guard()")
    c.exec_driver_sql(f"""CREATE FUNCTION r34_task_guard() RETURNS trigger LANGUAGE plpgsql
        VOLATILE SECURITY INVOKER SET search_path=pg_catalog,public AS $$ BEGIN
          IF TG_OP='DELETE' THEN RAISE EXCEPTION USING ERRCODE='42501',MESSAGE='Follow-up task requires reviewed purge'; END IF;
          IF ({_projection('IS NOT DISTINCT FROM')}) IS NOT TRUE OR
            (TG_OP='INSERT' AND (NEW.version<>1 OR NEW.status<>'open')) OR
            (TG_OP='UPDATE' AND (OLD.status<>'open' OR NEW.version<>OLD.version+1 OR NEW.updated_at<OLD.updated_at OR ({_immutable('IS NOT DISTINCT FROM')}) IS NOT TRUE))
          THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Follow-up projection requires exact event'; END IF;
          RETURN NEW;
        END $$""")
    c.exec_driver_sql("CREATE TRIGGER r34_task_guard BEFORE INSERT OR UPDATE OR DELETE ON followup_tasks FOR EACH ROW EXECUTE FUNCTION r34_task_guard()")
    c.exec_driver_sql(f"""CREATE FUNCTION r34_event_apply() RETURNS trigger LANGUAGE plpgsql
        VOLATILE SECURITY INVOKER SET search_path=pg_catalog,public AS $$ BEGIN
          IF NEW.kind='created' THEN {_projection_insert()} ELSE {_projection_update()} END IF;
          RETURN NEW;
        END $$""")
    c.exec_driver_sql("CREATE TRIGGER r34_event_apply AFTER INSERT ON followup_task_events FOR EACH ROW EXECUTE FUNCTION r34_event_apply()")
    for table in ("followup_tasks", "followup_task_events"):
        c.exec_driver_sql(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        c.exec_driver_sql(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        c.exec_driver_sql(f"CREATE POLICY r34_tenant ON {table} FOR ALL USING (gym_id=NULLIF(current_setting('app.current_tenant',true),'')) WITH CHECK (gym_id=NULLIF(current_setting('app.current_tenant',true),''))")


def signature(c):
    if c.dialect.name == "sqlite":
        return {"dialect": "sqlite", "triggers": [list(r) for r in c.execute(text(
            "SELECT name,tbl_name,sql FROM sqlite_master WHERE type='trigger' AND name LIKE 'r34_%' ORDER BY name"))]}
    functions = c.execute(text("""SELECT p.proname,pg_get_function_identity_arguments(p.oid),pg_get_function_result(p.oid),
        p.prosecdef,p.proconfig,p.provolatile,p.proparallel,p.proacl::text,p.prosrc,l.lanname,
        p.proowner=(SELECT relowner FROM pg_class WHERE relnamespace=n.oid AND relname='followup_tasks')
        FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace JOIN pg_language l ON l.oid=p.prolang
        WHERE n.nspname=current_schema() AND p.proname LIKE 'r34_%' ORDER BY p.proname""")).all()
    triggers = c.execute(text("""SELECT c.relname,t.tgname,t.tgenabled,t.tgdeferrable,t.tginitdeferred,pg_get_triggerdef(t.oid,false)
        FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid WHERE c.relnamespace=current_schema()::regnamespace
        AND NOT t.tgisinternal AND t.tgname LIKE 'r34_%' ORDER BY c.relname,t.tgname""")).all()
    policies = c.execute(text("""SELECT c.relname,c.relrowsecurity,c.relforcerowsecurity,p.polname,p.polcmd,p.polpermissive,
        p.polroles::text,pg_get_expr(p.polqual,p.polrelid),pg_get_expr(p.polwithcheck,p.polrelid)
        FROM pg_class c JOIN pg_policy p ON p.polrelid=c.oid WHERE c.relnamespace=current_schema()::regnamespace
        AND c.relname IN ('followup_tasks','followup_task_events') ORDER BY c.relname,p.polname""")).all()
    return {"dialect": "postgresql", "functions": [list(r) for r in functions],
            "triggers": [list(r) for r in triggers], "policies": [list(r) for r in policies]}
