"""Same legacy21 and R12additional11 assertions use the shared additive DTO7."""
from pathlib import Path

original=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-r12-node-composition29-20261019.py')
source=original.read_text(encoding='utf-8')
start=source.index("modules=['auth_refresh'");end=source.index('results=[]',start)
source=source[:start]+"modules=['personal_export_controls','member_link_export']\n"+source[end:]
source=source.replace("out=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-r12-node-composition29-20261019')", "out=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-r12-node-export-focal-20261019')")
exec(compile(source,str(original)+'::legacy21plusR12controls','exec'),globals())
