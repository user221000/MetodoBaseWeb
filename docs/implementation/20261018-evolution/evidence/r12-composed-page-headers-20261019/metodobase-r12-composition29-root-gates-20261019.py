"""Actual backend/UI-shell composition29 plus privacy/history/recovery guards."""
from pathlib import Path

original=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-history30-final-base-test-20261019.py')
source=original.read_text(encoding='utf-8')
start=source.index('directory=ROOT/');end=source.index('paths=subprocess.check_output',start)
source=source[:start]+source[end:]
source=source.replace("ROOT=Path('F:/mb-hidx-20261019')", "ROOT=Path('F:/mb-r12-full29-20261019')")
source=source.replace("OUT=TEMP/'metodobase-history30-final-base-test-20261019'", "OUT=TEMP/'metodobase-r12-composition29-root-gates-20261019'")
source=source.replace("assert head.startswith('aa9c3b8')", "assert head=='b8d0b8fe86188486084cc7178703477fa70ad7b3'")
source=source.replace('from web.database.alembic.history_index_contract_v1 import expected_history_index\n','')
needle="'tests/integration_personal_history_index_migrations.py','tests/integration_personal_history_ordered_query.py',"
assert source.count(needle)==1
modules=['tests/test_client_link_contract_before.py','tests/test_client_link_boundaries.py',
    'tests/integration_client_link_services.py','tests/integration_client_link_http.py',
    'tests/integration_client_link_service_races.py','tests/integration_client_link_publication_cas.py',
    'tests/test_r12_ui_pages.py','tests/test_privacy_export.py','tests/test_privacy_export_review.py',
    'tests/test_security_middleware.py','tests/test_recovery_method_headers.py',
    'tests/test_personal_history_pagination.py','tests/test_personal_history_cursor.py',
    'tests/test_history_headers_followup.py','tests/test_history_error_boundary.py']
source=source.replace(needle,','.join(repr(name) for name in modules)+',')
source=source.replace('Actual SQLite and owned synthetic PostgreSQL with real restricted role for history SQL. No latency/SLO, API29 acceptance or MAIN integration claim.', 'Actual composed29 backend plus UI shell, privacy/history/recovery tests, SQLite and owned synthetic PG with real restricted role. No browser, independent security acceptance, latency/SLO or MAIN integration claim.')
exec(compile(source,str(original)+'::composition29-root-focal','exec'),globals())
