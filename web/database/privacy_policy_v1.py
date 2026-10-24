"""Self-only FORCE RLS and durable identity/CAS, with no definer bypass."""
from sqlalchemy import text
from web.database.privacy_schema_v1 import REQUESTS, ITEMS


def install(connection):
    rules = {
        REQUESTS: "NEW.id<>OLD.id OR NEW.subject_id<>OLD.subject_id OR NEW.idempotency_key<>OLD.idempotency_key OR NEW.intent<>OLD.intent OR NEW.created_at<>OLD.created_at OR (OLD.closed_at IS NOT NULL AND (NEW.closed_at IS NULL OR NEW.closed_at<>OLD.closed_at)) OR (OLD.policy_digest IS NOT NULL AND (NEW.policy_digest IS NULL OR NEW.policy_digest<>OLD.policy_digest OR NEW.policy_id<>OLD.policy_id OR NEW.policy_version<>OLD.policy_version))",
        ITEMS: "NEW.id<>OLD.id OR NEW.subject_id<>OLD.subject_id OR NEW.request_id<>OLD.request_id OR NEW.category<>OLD.category OR NEW.deleted_rows<OLD.deleted_rows",
    }
    for table, immutable in rules.items():
        guard = '(' + immutable + ') OR NEW.version<>OLD.version+1'
        if connection.dialect.name == 'sqlite':
            connection.exec_driver_sql('CREATE TRIGGER r39_' + table + '_update BEFORE UPDATE ON ' + table + ' WHEN ' + guard + " BEGIN SELECT RAISE(ABORT,'Privacy identity or CAS denied'); END")
            connection.exec_driver_sql('CREATE TRIGGER r39_' + table + '_delete BEFORE DELETE ON ' + table + " BEGIN SELECT RAISE(ABORT,'Privacy records require reviewed retention'); END")
        elif connection.dialect.name == 'postgresql':
            connection.exec_driver_sql('ALTER TABLE public.' + table + ' ENABLE ROW LEVEL SECURITY')
            connection.exec_driver_sql('ALTER TABLE public.' + table + ' FORCE ROW LEVEL SECURITY')
            own = "subject_id=NULLIF(current_setting('app.current_tenant',true),'')"
            connection.exec_driver_sql('CREATE POLICY r39_self ON public.' + table + ' FOR ALL USING (' + own + ') WITH CHECK (' + own + ')')
            pg_guard = guard.replace('<>', ' IS DISTINCT FROM ')
            connection.exec_driver_sql('CREATE FUNCTION public.r39_' + table + "() RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog AS $$ BEGIN IF TG_OP='DELETE' THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Privacy records require reviewed retention'; END IF; IF " + pg_guard + " THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Privacy identity or CAS denied'; END IF; RETURN NEW; END $$")
            connection.exec_driver_sql('CREATE TRIGGER r39_' + table + ' BEFORE UPDATE OR DELETE ON public.' + table + ' FOR EACH ROW EXECUTE FUNCTION public.r39_' + table + '()')
        else:
            raise RuntimeError('Unreviewed privacy dialect')


def uninstall(connection):
    if connection.dialect.name == 'postgresql':
        for table in (ITEMS, REQUESTS):
            connection.exec_driver_sql('DROP FUNCTION public.r39_' + table + '() CASCADE')


def signature(connection):
    if connection.dialect.name == 'sqlite':
        return {'dialect':'sqlite','triggers':[list(row) for row in connection.execute(text("SELECT name,tbl_name,sql FROM sqlite_master WHERE type='trigger' AND name LIKE 'r39_%' ORDER BY name"))]}
    if connection.dialect.name != 'postgresql':
        raise RuntimeError('Unreviewed privacy dialect')
    queries = {
        'flags': "SELECT relname,relrowsecurity,relforcerowsecurity FROM pg_class WHERE relnamespace=current_schema()::regnamespace AND relname IN ('privacy_requests','privacy_disposition_items') ORDER BY relname",
        'policies': "SELECT tablename,policyname,permissive,roles::text,cmd,qual,with_check FROM pg_policies WHERE schemaname=current_schema() AND tablename IN ('privacy_requests','privacy_disposition_items') ORDER BY tablename,policyname",
        'functions': "SELECT p.proname,pg_get_function_identity_arguments(p.oid),p.prosecdef,p.proconfig,p.prosrc FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname=current_schema() AND p.proname LIKE 'r39_%' ORDER BY p.proname",
        'triggers': "SELECT c.relname,t.tgname,pg_get_triggerdef(t.oid,false) FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid WHERE c.relnamespace=current_schema()::regnamespace AND NOT t.tgisinternal AND t.tgname LIKE 'r39_%' ORDER BY c.relname,t.tgname",
    }
    return {'dialect':'postgresql',**{name:[list(row) for row in connection.execute(text(query))] for name,query in queries.items()}}
