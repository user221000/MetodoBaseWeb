"""Replay only the failing PostgreSQL query criterion with additive plan output."""
from pathlib import Path

original=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-history30-final-base-test-20261019.py')
source=original.read_text(encoding='utf-8')
start=source.index('directory=ROOT/')
end=source.index('paths=subprocess.check_output',start)
source=source[:start]+source[end:]
source=source.replace("OUT=TEMP/'metodobase-history30-final-base-test-20261019'", "OUT=TEMP/'metodobase-history30-query-diagnostic-20261019'")
source=source.replace("'tests/integration_personal_history_index_migrations.py','tests/integration_personal_history_ordered_query.py',", "'tests/integration_personal_history_ordered_query.py','-k','postgresql',")
exec(compile(source,str(original)+'::query-only-additive-diagnostic','exec'),globals())
