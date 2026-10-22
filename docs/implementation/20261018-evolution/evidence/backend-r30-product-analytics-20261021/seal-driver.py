from pathlib import Path
import ast
import os

original = Path(os.environ['TEMP'])/'metodobase-r30-seal.py'
source = original.read_text(encoding='utf8')
# Only repair the inverse harness: 'if' also occurs as a suffix of 'elif'.
source = source.replace("back.count(b'if product_analytics_api or ')==1", "back.count(b'\\n        if product_analytics_api or ')==1")
source = source.replace("'initial48':'48 pass, source/pip before-after not captured for that first run; no quiet claim retroactively added'", "'initial48':'48 pass, source/pip before-after not captured for that first run; no quiet claim retroactively added', 'seal_v1_erratum':'Inverse harness counted if inside elif; partial public projection preserved privately at partial-seal-v1, original driver retained; no product or test delta'")
ast.parse(source)
exec(compile(source,str(original),'exec'))
