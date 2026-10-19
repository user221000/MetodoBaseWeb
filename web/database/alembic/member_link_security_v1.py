"""Revision29 helper/trigger vocabulary, without altering historical signatures."""
from sqlalchemy import text


def member_link_security_signature(connection):
    if connection.dialect.name == 'sqlite':
        return {'dialect':'sqlite','triggers':[list(row) for row in connection.execute(text(
            "SELECT name,tbl_name,sql FROM sqlite_master WHERE type='trigger' AND name LIKE 'r12_%' ORDER BY name"))]}
    if connection.dialect.name != 'postgresql':
        raise RuntimeError('Member linking requires a reviewed database dialect')
    functions=connection.execute(text("""
        SELECT p.proname,pg_get_function_identity_arguments(p.oid),pg_get_function_result(p.oid),
               p.prosecdef,p.proconfig,p.provolatile,p.proparallel,p.proacl::text,p.prosrc,l.lanname
        FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
        JOIN pg_language l ON l.oid=p.prolang
        WHERE n.nspname=current_schema() AND p.proname LIKE 'r12_%'
        ORDER BY p.proname,pg_get_function_identity_arguments(p.oid)
    """)).all()
    triggers=connection.execute(text("""
        SELECT c.relname,t.tgname,t.tgenabled,t.tgdeferrable,t.tginitdeferred,
               pg_get_triggerdef(t.oid,false)
        FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid
        WHERE c.relnamespace=current_schema()::regnamespace AND NOT t.tgisinternal AND t.tgname LIKE 'r12_%'
        ORDER BY c.relname,t.tgname
    """)).all()
    return {'dialect':'postgresql','functions':[list(row) for row in functions],
            'triggers':[list(row) for row in triggers]}
