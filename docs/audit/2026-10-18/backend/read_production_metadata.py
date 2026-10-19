"""Read only Railway/PostgreSQL schema audit; never prints credentials or rows.

Arguments: project UUID, PostgreSQL service UUID, application service UUID.
Needs authenticated railway.cmd and psycopg2. Does not link or mutate services.
"""
import json
import subprocess
import sys
from urllib.parse import urlparse

import psycopg2

def variables(project, service):
    process = subprocess.run(
        ["railway.cmd", "variable", "list", "-p", project, "-e", "production",
         "-s", service, "--json"], capture_output=True, text=True, timeout=20,
    )
    if process.returncode:
        raise RuntimeError("Railway variable read failed; raw output suppressed")
    return json.loads(process.stdout)

def main():
    project, postgres_service, app_service = sys.argv[1:]
    pg = variables(project, postgres_service)
    app = variables(project, app_service)
    public_url = pg.get("DATABASE_PUBLIC_URL")
    if not public_url:
        raise RuntimeError("Public database URL unavailable")
    parsed_app, parsed_pg = urlparse(app.get("DATABASE_URL", "")), urlparse(public_url)
    result = {
        "scope": "Read-only metadata; no business records queried",
        "app_database_username": parsed_app.username,
        "same_database_name_and_username": (
            parsed_app.username == parsed_pg.username and parsed_app.path == parsed_pg.path
        ),
    }
    conn = psycopg2.connect(public_url, connect_timeout=8, sslmode="require",
                            application_name="metodobase_metadata_readonly_audit")
    conn.set_session(readonly=True, autocommit=False)
    try:
        with conn.cursor() as cur:
            cur.execute("SET LOCAL statement_timeout = '5000ms'")
            cur.execute("SET LOCAL lock_timeout = '2000ms'")
            for name, query in [
                ("server_version", "SHOW server_version"),
                ("max_connections", "SHOW max_connections"),
                ("role", "SELECT current_user, rolsuper, rolbypassrls FROM pg_roles WHERE rolname=current_user"),
                ("rls_flags", "SELECT relname,relrowsecurity,relforcerowsecurity FROM pg_class JOIN pg_namespace ns ON ns.oid=relnamespace WHERE ns.nspname='public' AND relkind='r' ORDER BY relname"),
                ("rls_policies", "SELECT tablename,policyname,cmd,roles,qual,with_check FROM pg_policies WHERE schemaname='public' ORDER BY tablename,policyname"),
                ("subscription_constraints", "SELECT conname,pg_get_constraintdef(c.oid) FROM pg_constraint c JOIN pg_class t ON t.oid=c.conrelid JOIN pg_namespace n ON n.oid=t.relnamespace WHERE n.nspname='public' AND t.relname='subscriptions' ORDER BY conname"),
                ("alembic_version_present", "SELECT to_regclass('public.alembic_version') IS NOT NULL"),
            ]:
                cur.execute(query)
                result[name] = cur.fetchall()
            if result["alembic_version_present"][0][0]:
                cur.execute("SELECT version_num FROM public.alembic_version")
                result["alembic_version"] = cur.fetchall()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    finally:
        conn.rollback()
        conn.close()

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"error_type": type(exc).__name__, "details_suppressed": True}))
        sys.exit(1)
