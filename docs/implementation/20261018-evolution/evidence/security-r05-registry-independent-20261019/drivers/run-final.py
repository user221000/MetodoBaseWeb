from pathlib import Path
original=Path(r'C:/Users/Consu/AppData/Local/Temp/metodobase-sec-r05-classifier-peer-tests-20261019.py')
text=original.read_text(encoding='utf8')
assert 'tests17-summary.json' in text and 'pip17-before.raw.log' in text
text=text.replace('tests17','tests-final').replace('pip17','pip-final').replace('pytest-17','pytest-final')
exec(compile(text,str(original),'exec'))
