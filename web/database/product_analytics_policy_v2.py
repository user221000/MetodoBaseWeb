"""Revision38 invoker guards and FORCE RLS, installed only by migrations.

Recipient access is limited to origin/publication facts of their active link.
INSERT capabilities also require the exact durable source under R12 policies.
"""
import re

from sqlalchemy import text

from web.database.product_analytics_schema_v2 import TABLE


def _predicates():
    same = "x.owner_id=NEW.owner_id AND x.context=NEW.context AND x.client_id IS NEW.client_id"
    latest = "COALESCE((SELECT x.origin FROM product_analytics_facts x WHERE " + same + " AND x.event_type='origin_declared' ORDER BY x.source_version DESC LIMIT 1),'unknown')"
    plan = "EXISTS(SELECT 1 FROM planes_generados p WHERE CAST(p.id AS TEXT)=NEW.source_id AND p.gym_id=NEW.owner_id AND (NEW.context='personal' OR p.id_cliente=NEW.client_id))"
    linked = "EXISTS(SELECT 1 FROM client_account_links l WHERE l.id=NEW.source_id AND l.gym_id=NEW.owner_id AND l.client_id=NEW.client_id AND l.status='active' AND l.version=NEW.source_version AND l.accepted_at IS NOT NULL)"
    pub = "EXISTS(SELECT 1 FROM client_plan_publications p WHERE p.id=NEW.source_id AND p.gym_id=NEW.owner_id AND p.client_id=NEW.client_id AND p.publication_version=NEW.source_version AND p.status="
    inherited_plan = "COALESCE((SELECT x.origin FROM product_analytics_facts x JOIN client_plan_publications p ON CAST(p.source_plan_id AS TEXT)=x.source_id AND p.gym_id=x.owner_id AND p.client_id=x.client_id WHERE " + same + " AND p.id=NEW.source_id AND x.event_type='plan_saved' AND x.source_version=1),'unknown')"
    inherited_pub = "COALESCE((SELECT x.origin FROM product_analytics_facts x WHERE " + same + " AND x.event_type='plan_assignment_published' AND x.source_id=NEW.source_id AND x.source_version=1),'unknown')"
    declaration = "(NEW.event_type='origin_declared' AND NEW.source_id=COALESCE(NEW.client_id,NEW.owner_id) AND NEW.source_version=COALESCE((SELECT max(x.source_version) FROM product_analytics_facts x WHERE " + same + " AND x.event_type='origin_declared'),0)+1)"
    saved = "(NEW.event_type='plan_saved' AND NEW.source_version=1 AND " + plan + " AND NEW.origin=" + latest + ")"
    accepted = "(NEW.event_type='client_link_accepted' AND " + linked + " AND NEW.origin=" + latest + ")"
    published = "(NEW.event_type='plan_assignment_published' AND NEW.source_version=1 AND " + pub + "'published') AND NEW.origin=" + inherited_plan + ")"
    withdrawn = "(NEW.event_type='plan_assignment_withdrawn' AND " + pub + "'withdrawn') AND NEW.origin=" + inherited_pub + ")"
    served = "(NEW.event_type='assigned_plan_http200' AND " + pub + "'published') AND NEW.origin=" + inherited_pub + ")"
    account = "EXISTS(SELECT 1 FROM usuarios u WHERE u.id=NEW.owner_id AND u.activo AND u.deleted_at IS NULL AND u.invitation_token IS NULL AND ((NEW.context='gym' AND u.tipo='gym' AND u.role='OWNER' AND u.team_gym_id IS NULL) OR (NEW.context='personal' AND u.role IN ('ADMIN','NUTRIOLOGO','VIEWER') AND (u.tipo='usuario' OR u.team_gym_id IS NOT NULL))))"
    return account + " AND (" + " OR ".join((declaration, saved, accepted, published, withdrawn, served)) + ")"


def install(connection):
    predicate = _predicates()
    if connection.dialect.name == "sqlite":
        for action in ("UPDATE", "DELETE"):
            connection.exec_driver_sql("CREATE TRIGGER r38_product_" + action.lower() + " BEFORE " + action + " ON " + TABLE + " BEGIN SELECT RAISE(ABORT,'Product facts are append only'); END")
        connection.exec_driver_sql("CREATE TRIGGER r38_product_source BEFORE INSERT ON " + TABLE + " WHEN NOT (" + predicate + ") OR typeof(NEW.source_version)<>'integer' OR NEW.occurred_at IS NOT CURRENT_TIMESTAMP BEGIN SELECT RAISE(ABORT,'Product fact source denied'); END")
        return
    if connection.dialect.name != "postgresql":
        raise RuntimeError("Unreviewed product analytics dialect")
    # Only the NULL-safe client scalar comparison differs between the dialects.
    predicate = predicate.replace("x.client_id IS NEW.client_id", "x.client_id IS NOT DISTINCT FROM NEW.client_id")
    for table in (TABLE, "usuarios", "clientes", "planes_generados", "client_account_links", "client_plan_publications"):
        predicate = re.sub(r"(?<![.\w])" + table + r"\b", "public." + table, predicate)
    connection.exec_driver_sql("ALTER TABLE public." + TABLE + " ENABLE ROW LEVEL SECURITY")
    connection.exec_driver_sql("ALTER TABLE public." + TABLE + " FORCE ROW LEVEL SECURITY")
    owner = "owner_id=NULLIF(current_setting('app.current_tenant',true),'')"
    recipient = "context='gym' AND EXISTS(SELECT 1 FROM public.client_account_links l WHERE l.gym_id=owner_id AND l.client_id=product_analytics_facts.client_id AND l.status='active' AND l.user_id=NULLIF(current_setting('app.current_tenant',true),'') AND public.r12_actor_valid())"
    connection.exec_driver_sql("CREATE POLICY r38_read ON public." + TABLE + " FOR SELECT USING (" + owner + " OR (event_type IN ('origin_declared','plan_assignment_published') AND " + recipient + "))")
    bound_recipient = "((event_type='client_link_accepted' AND EXISTS(SELECT 1 FROM public.client_account_links l WHERE l.id=source_id AND l.gym_id=owner_id AND l.client_id=product_analytics_facts.client_id AND l.user_id=NULLIF(current_setting('app.current_tenant',true),'') AND l.status='active')) OR (event_type='assigned_plan_http200' AND EXISTS(SELECT 1 FROM public.client_plan_publications p JOIN public.client_account_links l ON l.id=p.link_id AND l.gym_id=p.gym_id AND l.client_id=p.client_id WHERE p.id=source_id AND p.gym_id=owner_id AND p.client_id=product_analytics_facts.client_id AND p.status='published' AND l.user_id=NULLIF(current_setting('app.current_tenant',true),'') AND l.status='active')))"
    connection.exec_driver_sql("CREATE POLICY r38_append ON public." + TABLE + " FOR INSERT WITH CHECK (" + owner + " OR (" + bound_recipient + " AND " + recipient + "))")
    connection.exec_driver_sql("CREATE FUNCTION public.r38_immutable() RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog AS $$ BEGIN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Product facts are append only'; END $$")
    connection.exec_driver_sql("CREATE TRIGGER r38_product_immutable BEFORE UPDATE OR DELETE ON public." + TABLE + " FOR EACH ROW EXECUTE FUNCTION public.r38_immutable()")
    connection.exec_driver_sql("CREATE FUNCTION public.r38_source() RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog AS $$ BEGIN IF NEW.event_type='origin_declared' THEN PERFORM id FROM public.usuarios WHERE id=NEW.owner_id FOR UPDATE; IF NOT FOUND THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Product owner unavailable'; END IF; IF NEW.context='gym' THEN PERFORM id FROM public.clientes WHERE gym_id=NEW.owner_id AND id_cliente=NEW.client_id FOR UPDATE; IF NOT FOUND THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Product subject unavailable'; END IF; END IF; END IF; IF (" + predicate + ") IS NOT TRUE THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Product fact source denied'; END IF; NEW.occurred_at=clock_timestamp() AT TIME ZONE 'UTC'; RETURN NEW; END $$")
    connection.exec_driver_sql("CREATE TRIGGER r38_product_source BEFORE INSERT ON public." + TABLE + " FOR EACH ROW EXECUTE FUNCTION public.r38_source()")


def uninstall(connection):
    if connection.dialect.name == "postgresql":
        connection.exec_driver_sql("DROP FUNCTION public.r38_source() CASCADE")
        connection.exec_driver_sql("DROP FUNCTION public.r38_immutable() CASCADE")


def signature(connection):
    if connection.dialect.name == "sqlite":
        return {"dialect": "sqlite", "triggers": [list(r) for r in connection.execute(text("SELECT name,tbl_name,sql FROM sqlite_master WHERE type='trigger' AND name LIKE 'r38_%' ORDER BY name"))]}
    if connection.dialect.name != "postgresql":
        raise RuntimeError("Unreviewed product analytics dialect")
    functions = connection.execute(text("SELECT p.proname,pg_get_function_identity_arguments(p.oid),pg_get_function_result(p.oid),p.prosecdef,p.proconfig,p.provolatile,p.proparallel,p.proacl::text,p.prosrc,l.lanname FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace JOIN pg_language l ON l.oid=p.prolang WHERE n.nspname=current_schema() AND p.proname LIKE 'r38_%' ORDER BY p.proname")).all()
    triggers = connection.execute(text("SELECT c.relname,t.tgname,t.tgenabled,t.tgdeferrable,t.tginitdeferred,pg_get_triggerdef(t.oid,false) FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid WHERE c.relnamespace=current_schema()::regnamespace AND NOT t.tgisinternal AND t.tgname LIKE 'r38_%' ORDER BY c.relname,t.tgname")).all()
    flags = connection.execute(text("SELECT relname,relrowsecurity,relforcerowsecurity FROM pg_class WHERE relnamespace=current_schema()::regnamespace AND relname='product_analytics_facts'")).all()
    policies = connection.execute(text("SELECT tablename,policyname,permissive,roles::text,cmd,qual,with_check FROM pg_policies WHERE schemaname=current_schema() AND tablename='product_analytics_facts' ORDER BY policyname")).all()
    return {"dialect": "postgresql", "functions": [list(r) for r in functions], "triggers": [list(r) for r in triggers], "flags": [list(r) for r in flags], "policies": [list(r) for r in policies]}
