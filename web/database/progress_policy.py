"""Revision32 append-only consent and explicit measurement provenance guards.

No source-reading function, SECURITY DEFINER or actor-as-GUC signature exists.
The existing tenant context remains a backend-selected RLS boundary.
"""
from sqlalchemy import text

PROVENANCE_CHECK = "CAST(source_kind AS TEXT) IN (CAST('legacy_unverified' AS TEXT),CAST('self_reported' AS TEXT)) AND version BETWEEN 1 AND 2147483647"
SELF_REPORT_CHECK = "source_kind = 'legacy_unverified' OR (record_key IS NOT NULL AND measured_on IS NOT NULL AND recorded_by_id IS NOT NULL AND recorded_by_id = gym_id AND recorded_at IS NOT NULL AND updated_at IS NOT NULL AND (peso_kg IS NOT NULL OR grasa_corporal_pct IS NOT NULL OR masa_magra_kg IS NOT NULL) AND (peso_kg IS NULL OR peso_kg BETWEEN 20 AND 300) AND (grasa_corporal_pct IS NULL OR grasa_corporal_pct BETWEEN 3 AND 60) AND (masa_magra_kg IS NULL OR (masa_magra_kg > 0 AND masa_magra_kg <= 300)))"


def postgres_sql():
    return r"""
CREATE FUNCTION public.r25_account(identity text) RETURNS boolean LANGUAGE sql STABLE SECURITY INVOKER SET search_path=pg_catalog AS $$
 SELECT EXISTS(SELECT 1 FROM public.usuarios u WHERE u.id=identity AND u.activo AND u.deleted_at IS NULL
 AND u.invitation_token IS NULL AND u.role IN ('OWNER','ADMIN','NUTRIOLOGO','VIEWER')) $$;
CREATE FUNCTION public.r25_personal(identity text) RETURNS boolean LANGUAGE sql STABLE SECURITY INVOKER SET search_path=pg_catalog AS $$
 SELECT EXISTS(SELECT 1 FROM public.usuarios u WHERE u.id=identity AND u.activo AND u.deleted_at IS NULL
 AND u.invitation_token IS NULL AND u.role IN ('ADMIN','NUTRIOLOGO','VIEWER')
 AND (u.tipo='usuario' OR u.team_gym_id IS NOT NULL)
 AND (u.team_gym_id IS NULL OR public.r12_canonical_gym(u.team_gym_id))) $$;
CREATE FUNCTION public.r25_guard_measurement() RETURNS trigger LANGUAGE plpgsql VOLATILE SECURITY INVOKER SET search_path=pg_catalog AS $$
 BEGIN
 IF NEW.source_kind='legacy_unverified' THEN
  IF NEW.record_key IS NOT NULL OR NEW.measured_on IS NOT NULL OR NEW.recorded_by_id IS NOT NULL OR NEW.recorded_at IS NOT NULL OR NEW.updated_at IS NOT NULL OR NEW.withdrawn_at IS NOT NULL OR NEW.version<>1
   OR (TG_OP='UPDATE' AND OLD.source_kind<>'legacy_unverified') THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='R25 legacy provenance denied'; END IF;
  RETURN NEW;
 END IF;
 IF NEW.gym_id IS DISTINCT FROM NULLIF(current_setting('app.current_tenant',true),'') OR public.r25_personal(NEW.gym_id) IS NOT TRUE THEN RAISE EXCEPTION USING ERRCODE='42501',MESSAGE='R25 measurement subject denied'; END IF;
 PERFORM 1 FROM public.usuarios WHERE id=NEW.gym_id FOR UPDATE NOWAIT;
 PERFORM 1 FROM public.clientes WHERE gym_id=NEW.gym_id AND id_cliente=NEW.id_cliente AND activo AND deleted_at IS NULL FOR SHARE;
 IF NOT FOUND OR NEW.measured_on>(clock_timestamp() AT TIME ZONE 'America/Mexico_City')::date THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='R25 measurement source denied'; END IF;
 IF TG_OP='INSERT' THEN
  IF NEW.version<>1 OR NEW.withdrawn_at IS NOT NULL THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='R25 initial version denied'; END IF;
  NEW.recorded_at=clock_timestamp() AT TIME ZONE 'UTC'; NEW.updated_at=NEW.recorded_at; NEW.fecha=NEW.recorded_at;
 ELSE
  IF OLD.source_kind<>'self_reported' OR OLD.withdrawn_at IS NOT NULL OR NEW.version<>OLD.version+1
   OR (NEW.id,NEW.gym_id,NEW.id_cliente,NEW.record_key,NEW.recorded_by_id,NEW.recorded_at,NEW.fecha,NEW.notas) IS DISTINCT FROM (OLD.id,OLD.gym_id,OLD.id_cliente,OLD.record_key,OLD.recorded_by_id,OLD.recorded_at,OLD.fecha,OLD.notas)
   THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='R25 immutable measurement denied'; END IF;
  NEW.updated_at=clock_timestamp() AT TIME ZONE 'UTC';
  IF NEW.withdrawn_at IS NOT NULL THEN NEW.withdrawn_at=NEW.updated_at; END IF;
 END IF;
 RETURN NEW; END $$;
CREATE TRIGGER r25_measurement BEFORE INSERT OR UPDATE ON public.client_progress FOR EACH ROW EXECUTE FUNCTION public.r25_guard_measurement();
ALTER TABLE public.progress_consents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.progress_consents FORCE ROW LEVEL SECURITY;
CREATE POLICY r25_consent_select ON public.progress_consents FOR SELECT USING(user_id=NULLIF(current_setting('app.current_tenant',true),'') OR gym_id=NULLIF(current_setting('app.current_tenant',true),''));
CREATE POLICY r25_consent_insert ON public.progress_consents FOR INSERT WITH CHECK(user_id=NULLIF(current_setting('app.current_tenant',true),'') AND ((event='grant' AND public.r25_personal(user_id)) OR (event='withdraw' AND public.r25_account(user_id))));
CREATE POLICY r25_consent_lock ON public.progress_consents FOR UPDATE USING(user_id=NULLIF(current_setting('app.current_tenant',true),'') OR gym_id=NULLIF(current_setting('app.current_tenant',true),'')) WITH CHECK(false);
CREATE FUNCTION public.r25_guard_consent() RETURNS trigger LANGUAGE plpgsql VOLATILE SECURITY INVOKER SET search_path=pg_catalog AS $$
 DECLARE prior public.progress_consents; linked public.client_account_links;
 BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION USING ERRCODE='42501',MESSAGE='R25 consent is append only'; END IF;
 IF current_setting('transaction_isolation')<>'read committed' OR NEW.user_id IS DISTINCT FROM NULLIF(current_setting('app.current_tenant',true),'') OR public.r25_account(NEW.user_id) IS NOT TRUE OR (NEW.event='grant' AND public.r25_personal(NEW.user_id) IS NOT TRUE) THEN RAISE EXCEPTION USING ERRCODE='42501',MESSAGE='R25 consent subject denied'; END IF;
 PERFORM 1 FROM public.usuarios WHERE id=NEW.user_id FOR UPDATE NOWAIT;
 SELECT * INTO prior FROM public.progress_consents WHERE link_id=NEW.link_id ORDER BY version DESC LIMIT 1;
 IF NEW.version<>COALESCE(prior.version,0)+1 OR NEW.version>2147483647 THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='R25 consent version denied'; END IF;
 IF NEW.event='withdraw' THEN
  IF prior.id IS NULL OR prior.event<>'grant' OR (NEW.link_id,NEW.gym_id,NEW.client_id,NEW.user_id,NEW.link_version,NEW.protocol,NEW.source_profile_id,NEW.share_weight,NEW.share_body_fat,NEW.share_lean_mass,NEW.share_completion,NEW.from_date,NEW.through_date)
   IS DISTINCT FROM (prior.link_id,prior.gym_id,prior.client_id,prior.user_id,prior.link_version,prior.protocol,prior.source_profile_id,prior.share_weight,prior.share_body_fat,prior.share_lean_mass,prior.share_completion,prior.from_date,prior.through_date)
   THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='R25 withdrawal scope denied'; END IF;
 ELSE
  SELECT * INTO linked FROM public.client_account_links WHERE id=NEW.link_id AND user_id=NEW.user_id AND gym_id=NEW.gym_id AND client_id=NEW.client_id AND status='active' AND version=NEW.link_version FOR SHARE;
  IF linked.id IS NULL OR public.r12_canonical_gym(NEW.gym_id) IS NOT TRUE THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='R25 grant source denied'; END IF;
  IF NEW.source_profile_id IS NOT NULL THEN
   PERFORM 1 FROM public.clientes WHERE gym_id=NEW.user_id AND id_cliente=NEW.source_profile_id AND activo AND deleted_at IS NULL FOR SHARE;
   IF NOT FOUND THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='R25 personal profile denied'; END IF;
  END IF;
 END IF;
 NEW.created_at=clock_timestamp() AT TIME ZONE 'UTC'; RETURN NEW;
 END $$;
CREATE TRIGGER r25_consent_append BEFORE INSERT OR UPDATE OR DELETE ON public.progress_consents FOR EACH ROW EXECUTE FUNCTION public.r25_guard_consent();
"""


def sqlite_sql():
    # SQLite tests use the same service authorization; SQL guards additionally
    # enforce provenance/version/scope and append-only history without a GUC.
    return r"""
CREATE TRIGGER r25_measurement_insert BEFORE INSERT ON client_progress WHEN
 (NEW.source_kind='legacy_unverified' AND (NEW.record_key IS NOT NULL OR NEW.measured_on IS NOT NULL OR NEW.recorded_by_id IS NOT NULL OR NEW.recorded_at IS NOT NULL OR NEW.updated_at IS NOT NULL OR NEW.withdrawn_at IS NOT NULL OR NEW.version<>1))
 OR (NEW.source_kind='self_reported' AND (NEW.version<>1 OR NEW.withdrawn_at IS NOT NULL OR NOT EXISTS(SELECT 1 FROM clientes WHERE gym_id=NEW.gym_id AND id_cliente=NEW.id_cliente AND activo AND deleted_at IS NULL)))
 BEGIN SELECT RAISE(ABORT,'R25 measurement provenance denied'); END;
CREATE TRIGGER r25_measurement_update BEFORE UPDATE ON client_progress WHEN
 (OLD.source_kind='legacy_unverified' AND (NEW.source_kind<>OLD.source_kind OR NEW.record_key IS NOT NULL OR NEW.measured_on IS NOT NULL OR NEW.recorded_by_id IS NOT NULL OR NEW.recorded_at IS NOT NULL OR NEW.updated_at IS NOT NULL OR NEW.withdrawn_at IS NOT NULL OR NEW.version<>1))
 OR (OLD.source_kind='self_reported' AND (NEW.source_kind<>OLD.source_kind OR OLD.withdrawn_at IS NOT NULL OR NEW.version<>OLD.version+1 OR NEW.gym_id IS NOT OLD.gym_id OR NEW.id_cliente IS NOT OLD.id_cliente OR NEW.record_key IS NOT OLD.record_key OR NEW.recorded_by_id IS NOT OLD.recorded_by_id OR NEW.recorded_at IS NOT OLD.recorded_at OR NEW.fecha IS NOT OLD.fecha OR NEW.notas IS NOT OLD.notas))
 BEGIN SELECT RAISE(ABORT,'R25 immutable measurement denied'); END;
CREATE TRIGGER r25_consent_update BEFORE UPDATE ON progress_consents BEGIN SELECT RAISE(ABORT,'R25 consent is append only'); END;
CREATE TRIGGER r25_consent_delete BEFORE DELETE ON progress_consents BEGIN SELECT RAISE(ABORT,'R25 consent is append only'); END;
CREATE TRIGGER r25_consent_insert BEFORE INSERT ON progress_consents WHEN
 NOT EXISTS(SELECT 1 FROM usuarios WHERE id=NEW.user_id AND activo AND deleted_at IS NULL AND invitation_token IS NULL AND role IN ('OWNER','ADMIN','NUTRIOLOGO','VIEWER'))
 OR (NEW.event='grant' AND NOT EXISTS(SELECT 1 FROM usuarios u WHERE u.id=NEW.user_id AND u.role IN ('ADMIN','NUTRIOLOGO','VIEWER') AND (u.tipo='usuario' OR u.team_gym_id IS NOT NULL) AND (u.team_gym_id IS NULL OR EXISTS(SELECT 1 FROM usuarios p WHERE p.id=u.team_gym_id AND p.tipo='gym' AND p.role='OWNER' AND p.team_gym_id IS NULL AND p.activo AND p.deleted_at IS NULL AND p.invitation_token IS NULL))))
 OR NEW.version<>COALESCE((SELECT max(version) FROM progress_consents WHERE link_id=NEW.link_id),0)+1
 OR (NEW.event='grant' AND (NOT EXISTS(SELECT 1 FROM client_account_links l JOIN usuarios u ON u.id=l.gym_id WHERE l.id=NEW.link_id AND l.user_id=NEW.user_id AND l.gym_id=NEW.gym_id AND l.client_id=NEW.client_id AND l.status='active' AND l.version=NEW.link_version AND u.tipo='gym' AND u.role='OWNER' AND u.team_gym_id IS NULL AND u.activo AND u.deleted_at IS NULL AND u.invitation_token IS NULL)
 OR (NEW.source_profile_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM clientes WHERE gym_id=NEW.user_id AND id_cliente=NEW.source_profile_id AND activo AND deleted_at IS NULL))))
 OR (NEW.event='withdraw' AND NOT EXISTS(SELECT 1 FROM progress_consents p WHERE p.link_id=NEW.link_id AND p.version=NEW.version-1 AND p.event='grant' AND p.gym_id=NEW.gym_id AND p.client_id=NEW.client_id AND p.user_id=NEW.user_id AND p.link_version=NEW.link_version AND p.protocol=NEW.protocol AND p.source_profile_id IS NEW.source_profile_id AND p.share_weight=NEW.share_weight AND p.share_body_fat=NEW.share_body_fat AND p.share_lean_mass=NEW.share_lean_mass AND p.share_completion=NEW.share_completion AND p.from_date=NEW.from_date AND p.through_date IS NEW.through_date))
 BEGIN SELECT RAISE(ABORT,'R25 consent scope/version denied'); END;
"""


def install(connection):
    if connection.dialect.name == "postgresql":
        connection.exec_driver_sql(postgres_sql())
    elif connection.dialect.name == "sqlite":
        # SQLAlchemy/DBAPI executes one trigger statement at a time, preserving
        # the outer migration transaction (executescript would commit it).
        import sqlite3
        statement = ""
        for line in sqlite_sql().splitlines(True):
            statement += line
            if sqlite3.complete_statement(statement):
                connection.exec_driver_sql(statement)
                statement = ""
        if statement.strip():
            raise RuntimeError("Incomplete R25 SQLite guard")
    else:
        raise RuntimeError("Unreviewed progress database dialect")


def signature(connection):
    if connection.dialect.name == "sqlite":
        return {"dialect":"sqlite","triggers":[list(row) for row in connection.execute(text("SELECT name,tbl_name,sql FROM sqlite_master WHERE type='trigger' AND name LIKE 'r25_%' ORDER BY name"))]}
    functions = connection.execute(text("SELECT p.proname,pg_get_function_identity_arguments(p.oid),pg_get_function_result(p.oid),p.prosecdef,p.proconfig,p.provolatile,p.proparallel,p.proacl::text,p.prosrc,l.lanname FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace JOIN pg_language l ON l.oid=p.prolang WHERE n.nspname=current_schema() AND p.proname LIKE 'r25_%' ORDER BY p.proname")).all()
    triggers = connection.execute(text("SELECT c.relname,t.tgname,t.tgenabled,t.tgdeferrable,t.tginitdeferred,pg_get_triggerdef(t.oid,false) FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid WHERE c.relnamespace=current_schema()::regnamespace AND NOT t.tgisinternal AND t.tgname LIKE 'r25_%' ORDER BY c.relname,t.tgname")).all()
    return {"dialect":"postgresql","functions":[list(row) for row in functions],"triggers":[list(row) for row in triggers]}
