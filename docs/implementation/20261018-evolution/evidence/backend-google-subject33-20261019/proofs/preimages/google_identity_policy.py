"""Revision33 control-plane integrity, with no RLS or definer impersonation.

The app role already owns authentication queries for Usuario, refresh tokens,
and hash-only MFA proofs. These two new tables follow that narrow control plane:
lookup by verified provider subject, or actor + opaque hash. GUCs never prove a
provider or password. DML users cannot rewrite or delete a primary association.
"""
from sqlalchemy import text


def install(connection):
    if connection.dialect.name == "sqlite":
        connection.exec_driver_sql("""CREATE TRIGGER r33_identity_immutable BEFORE UPDATE ON auth_external_identities
            WHEN NOT (NEW.id IS OLD.id AND NEW.user_id IS OLD.user_id AND NEW.issuer IS OLD.issuer
                AND NEW.subject IS OLD.subject AND NEW.created_at IS OLD.created_at AND NEW.version = OLD.version+1
                AND ((NEW.revoked_at IS NULL AND OLD.revoked_at IS NOT NULL) OR (NEW.revoked_at IS NOT NULL AND OLD.revoked_at IS NULL)))
            BEGIN SELECT RAISE(ABORT,'Authentication binding is immutable'); END""")
        connection.exec_driver_sql("CREATE TRIGGER r33_identity_preserve BEFORE DELETE ON auth_external_identities BEGIN SELECT RAISE(ABORT,'Authentication binding requires reviewed withdrawal'); END")
        connection.exec_driver_sql("""CREATE TRIGGER r33_intent_immutable BEFORE UPDATE ON google_link_intents
            WHEN NOT (NEW.token_hash IS OLD.token_hash AND NEW.user_id IS OLD.user_id
                AND NEW.issuer IS OLD.issuer AND NEW.subject IS OLD.subject AND NEW.purpose IS OLD.purpose
                AND NEW.access_hash IS OLD.access_hash AND NEW.session_version IS OLD.session_version
                AND NEW.generation IS OLD.generation AND NEW.created_at IS OLD.created_at
                AND NEW.expires_at IS OLD.expires_at AND OLD.consumed_at IS NULL AND NEW.consumed_at IS NOT NULL)
            BEGIN SELECT RAISE(ABORT,'Authentication intent is immutable'); END""")
        connection.exec_driver_sql("CREATE TRIGGER r33_intent_preserve BEFORE DELETE ON google_link_intents BEGIN SELECT RAISE(ABORT,'Authentication intent requires reviewed retention'); END")
        return
    connection.exec_driver_sql("""CREATE FUNCTION r33_identity_immutable() RETURNS trigger
        LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
        BEGIN
          IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'Authentication binding requires reviewed withdrawal' USING ERRCODE='42501'; END IF;
          IF (ROW(NEW.id,NEW.user_id,NEW.issuer,NEW.subject,NEW.created_at) IS NOT DISTINCT FROM ROW(OLD.id,OLD.user_id,OLD.issuer,OLD.subject,OLD.created_at)
              AND NEW.version=OLD.version+1 AND ((NEW.revoked_at IS NULL AND OLD.revoked_at IS NOT NULL)
                   OR (NEW.revoked_at IS NOT NULL AND OLD.revoked_at IS NULL))) IS NOT TRUE
          THEN RAISE EXCEPTION 'Authentication binding is immutable' USING ERRCODE='42501'; END IF;
          RETURN NEW;
        END $$""")
    connection.exec_driver_sql("CREATE TRIGGER r33_identity_immutable BEFORE UPDATE OR DELETE ON auth_external_identities FOR EACH ROW EXECUTE FUNCTION r33_identity_immutable()")
    connection.exec_driver_sql("""CREATE FUNCTION r33_intent_immutable() RETURNS trigger
        LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
        BEGIN
          IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'Authentication intent requires reviewed retention' USING ERRCODE='42501'; END IF;
          IF (ROW(NEW.token_hash,NEW.user_id,NEW.issuer,NEW.subject,NEW.purpose,NEW.access_hash,NEW.session_version,NEW.generation,NEW.created_at,NEW.expires_at)
              IS NOT DISTINCT FROM ROW(OLD.token_hash,OLD.user_id,OLD.issuer,OLD.subject,OLD.purpose,OLD.access_hash,OLD.session_version,OLD.generation,OLD.created_at,OLD.expires_at)
              AND OLD.consumed_at IS NULL AND NEW.consumed_at IS NOT NULL) IS NOT TRUE
          THEN RAISE EXCEPTION 'Authentication intent is immutable' USING ERRCODE='42501'; END IF;
          RETURN NEW;
        END $$""")
    connection.exec_driver_sql("CREATE TRIGGER r33_intent_immutable BEFORE UPDATE OR DELETE ON google_link_intents FOR EACH ROW EXECUTE FUNCTION r33_intent_immutable()")


def signature(connection):
    if connection.dialect.name == "sqlite":
        return {"dialect":"sqlite","triggers":[list(row) for row in connection.execute(text(
            "SELECT name,tbl_name,sql FROM sqlite_master WHERE type='trigger' AND name LIKE 'r33_%' ORDER BY name"))]}
    functions = connection.execute(text("""SELECT p.proname,pg_get_function_identity_arguments(p.oid),
        pg_get_function_result(p.oid),p.prosecdef,p.proconfig,p.provolatile,p.proparallel,p.proacl::text,p.prosrc,l.lanname
        FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace JOIN pg_language l ON l.oid=p.prolang
        WHERE n.nspname=current_schema() AND p.proname LIKE 'r33_%' ORDER BY p.proname""")).all()
    triggers = connection.execute(text("""SELECT c.relname,t.tgname,t.tgenabled,t.tgdeferrable,t.tginitdeferred,pg_get_triggerdef(t.oid,false)
        FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid WHERE c.relnamespace=current_schema()::regnamespace
        AND NOT t.tgisinternal AND t.tgname LIKE 'r33_%' ORDER BY c.relname,t.tgname""")).all()
    flags = connection.execute(text("""SELECT relname,relrowsecurity,relforcerowsecurity FROM pg_class
        WHERE relnamespace=current_schema()::regnamespace AND relname IN ('auth_external_identities','google_link_intents') ORDER BY relname""")).all()
    return {"dialect":"postgresql","functions":[list(row) for row in functions],"triggers":[list(row) for row in triggers],"control_plane":[list(row) for row in flags]}
