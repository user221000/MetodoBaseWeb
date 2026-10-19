"""Replay R12 private headers after page mounting, with wrong-method control."""
from pathlib import Path

original=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-r12-composition29-root-gates-20261019.py')
source=original.read_text(encoding='utf-8')
start=source.index('modules=[');end=source.index("source=source.replace(needle",start)
source=source[:start]+"modules=['tests/integration_client_link_http.py','-k','privacy_headers_survive_wrong_method_and_missing_page']\n"+source[end:]
source=source.replace("OUT=TEMP/'metodobase-r12-composition29-root-gates-20261019'", "OUT=TEMP/'metodobase-r12-composed-page-focal-20261019'")
exec(compile(source,str(original)+'::composed-page28headers','exec'),globals())
