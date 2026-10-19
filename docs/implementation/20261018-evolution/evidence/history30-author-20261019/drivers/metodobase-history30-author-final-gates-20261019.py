"""Run final migration/query criteria and existing96 HTTP/cursor regressions."""
from pathlib import Path

original=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-history30-final-base-test-20261019.py')
source=original.read_text(encoding='utf-8')
start=source.index('directory=ROOT/')
end=source.index('paths=subprocess.check_output',start)
source=source[:start]+source[end:]
source=source.replace("OUT=TEMP/'metodobase-history30-final-base-test-20261019'", "OUT=TEMP/'metodobase-history30-author-final-gates-20261019'")
needle="'tests/integration_personal_history_index_migrations.py','tests/integration_personal_history_ordered_query.py',"
assert source.count(needle)==1
source=source.replace(needle,needle+"\n    'tests/test_personal_history_pagination.py','tests/test_personal_history_cursor.py','tests/test_history_headers_followup.py','tests/test_history_error_boundary.py',")
exec(compile(source,str(original)+'::final16plus96','exec'),globals())
