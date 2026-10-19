from pathlib import Path
source=(Path(__file__).parent/'run_full.py').read_text('utf-8')
source=source.replace('test_full_review.py','test_parent_scope.py').replace("/'full.xml'","/'parent-scope.xml'").replace("/'origins.json'","/'parent-origins.json'")
exec(compile(source,__file__,'exec'))
