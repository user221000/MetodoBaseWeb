"""Frozen v1 PostgreSQL policy/flag/helper snapshot vocabulary for migrations."""
from sqlalchemy import text


def tenant_security_signature(connection) -> dict:
    """Read the actual policy/flag/helper contract without changing protection."""
    if connection.dialect.name != "postgresql":
        return {"dialect": connection.dialect.name}
    tables = connection.execute(text("""
        SELECT relname,relrowsecurity,relforcerowsecurity FROM pg_class
        WHERE relnamespace=current_schema()::regnamespace AND relkind='r'
          AND relname <> 'alembic_version' ORDER BY relname
    """)).all()
    policies = connection.execute(text("""
        SELECT tablename,policyname,permissive,roles::text,cmd,qual,with_check
        FROM pg_policies WHERE schemaname=current_schema()
        ORDER BY tablename,policyname
    """)).all()
    helpers = connection.execute(text("""
        SELECT p.prosecdef,p.proconfig,p.prosrc,l.lanname
        FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
        JOIN pg_language l ON l.oid=p.prolang
        WHERE n.nspname=current_schema() AND p.proname='set_tenant'
          AND pg_get_function_identity_arguments(p.oid)='tenant_id text'
    """)).all()
    return {"dialect": "postgresql", "tables": [list(row) for row in tables],
        "policies": [list(row) for row in policies],
        "set_tenant": [[row[0], row[1], " ".join(row[2].split()), row[3]] for row in helpers]}

