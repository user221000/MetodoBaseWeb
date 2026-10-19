"""Check exact middleware composition after scoped R12 private500 candidate."""
from pathlib import Path

original=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-r12-composition29-root-gates-20261019.py')
source=original.read_text(encoding='utf-8')
start=source.index('modules=[');end=source.index("source=source.replace(needle",start)
modules=['tests/integration_client_link_http.py::test_privacy_headers_survive_wrong_method_and_missing_page',
    'tests/test_security_middleware.py','tests/test_recovery_method_headers.py',
    'tests/test_history_headers_followup.py','tests/test_history_error_boundary.py']
source=source[:start]+'modules='+repr(modules)+'\n'+source[end:]
source=source.replace("OUT=TEMP/'metodobase-r12-composition29-root-gates-20261019'", "OUT=TEMP/'metodobase-r12-private500-composition-focal-20261019'")
source=source.replace("assert head=='b8d0b8fe86188486084cc7178703477fa70ad7b3'", "assert head=='9d0c5c469aa261f027f5ca7c413f477c9e521206'")
exec(compile(source,str(original)+'::private500-composition-focal','exec'),globals())
