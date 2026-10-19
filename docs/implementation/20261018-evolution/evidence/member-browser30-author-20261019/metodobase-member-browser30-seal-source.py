"""Seal the separate current30 fixture without changing historical assertions."""
import ast
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile

ROOT=Path('F:/mb-member-browser30-20261019')
OUT=ROOT/'docs/implementation/20261018-evolution/evidence/member-browser30-author-20261019'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
original={}
with zipfile.ZipFile(OUT/'before29-exact.zip') as archive:
    for name in archive.namelist():original[name]=archive.read(name).decode().replace('\r\n','\n')
new={name:(ROOT/name).read_text(encoding='utf8') for name in original}
name='tests/e2e/member_link_browser.cjs'
changes=[
    ('/* Actual browser -> actual29 API/PG. No page.route fulfilments or API doubles. */',
     '/* Actual browser -> actual30 schema/PG, unchanged business29. No API doubles. */'),
    ('Actual Chrome/HTTP/restricted-PostgreSQL29 integration; mail filesystem double only.',
     'Actual Chrome/HTTP/restricted-PostgreSQL30 integration of unchanged R12 business29; mail filesystem double only.'),
    ('head:meta.head,report,','head:meta.head,executed_revision:meta.executed_revision,report,'),
]
inverse=new[name]
for before,after in reversed(changes):
    assert inverse.count(after)==1
    inverse=inverse.replace(after,before)
assert inverse==original[name]
criteria=lambda raw:[line for line in raw.splitlines() if line.lstrip().startswith('await criterion(')]
assert len(criteria(original[name]))==len(criteria(new[name]))==16
assert criteria(original[name])==criteria(new[name])
def function(source,name):
    return next(node for node in ast.parse(source).body if isinstance(node,ast.FunctionDef) and node.name==name)
manager='tests/e2e/run_member_link_browser.py'
for name in ['publish','validate_closure','listener_closed']:
    assert ast.dump(function(original[manager],name),include_attributes=False)==ast.dump(function(new[manager],name),include_attributes=False)
units='tests/test_member_browser_gate.py'
old_functions=[node.name for node in ast.parse(original[units]).body if isinstance(node,ast.FunctionDef)]
for name in old_functions:
    if name!='marker':
        assert ast.dump(function(original[units],name),include_attributes=False)==ast.dump(function(new[units],name),include_attributes=False)
before_cases=list(ET.parse(OUT/'before29-units.xml').iter('testcase'))
after_cases=list(ET.parse(OUT/'after30-units.xml').iter('testcase'))
assert len(before_cases)==29 and len(after_cases)==50
assert all(case.find(tag) is None for case in before_cases+after_cases for tag in ['failure','error','skipped'])
sys.path.insert(0,str(ROOT))
from web.database.schema_control import expected_head
assert expected_head()=='20261019_personal_history_index'
proof={
    'base':'3a760a0cd5fc88b427f8e828d58f9e110015c00c',
    'browser_inverse_entire_source_exact_after_only_three_comment_scope_metadata_substitutions':True,
    'browser_criteria_lines_identical_git_lf':True,'browser_criteria_count':16,
    'browser_metadata_changes':changes,
    'manager_publish_closure_listener_ast_identical':True,
    'all_original_unit_functions_except_positive_marker_ast_identical':True,
    'original_unit_cases':29,'current_unit_cases':50,
    'static_before':{'historical_fixture_asserted_expected_head':'20261019_client_account_links',
                     'current_migration_graph_head':expected_head(),
                     'classification':'Static metadata/graph mismatch only; no before browser or database failure is claimed.'},
    'public_allowlist_unchanged_count':10,
}
(OUT/'criteria-preservation.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8')
quality=subprocess.run([sys.executable,'-m','ruff','check','--select','F,E9',
    'tests/e2e/member_link_postgres_server.py','tests/e2e/run_member_link_browser.py',
    'tests/e2e/normalize_member_link_report.py','tests/test_member_browser_gate.py'],cwd=ROOT,capture_output=True)
(OUT/'quality.log').write_bytes(quality.stdout+quality.stderr)
assert quality.returncode==0
node=subprocess.run(['C:/Program Files/nodejs/node.exe','--check','tests/e2e/member_link_browser.cjs'],cwd=ROOT,capture_output=True)
(OUT/'node-syntax.log').write_bytes(node.stdout+node.stderr)
assert node.returncode==0
pip=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True)
(OUT/'pip-check.log').write_bytes(pip.stdout+pip.stderr)
assert pip.returncode==0
packages=sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions())
assert len(packages)==89
(OUT/'packages.json').write_text(json.dumps(packages,indent=2)+'\n',encoding='utf8')
for name in ['metodobase-member-browser30-prepare.py','metodobase-member-browser30-seal-source.py']:
    (OUT/name).write_bytes((Path('C:/Users/Consu/AppData/Local/Temp')/name).read_bytes())
sources={name:{'raw_sha256':sha((ROOT/name).read_bytes()),'git_lf_sha256':sha((ROOT/name).read_bytes().replace(b'\r\n',b'\n'))} for name in original}
proof_files={p.relative_to(ROOT).as_posix():sha(p.read_bytes()) for p in OUT.rglob('*') if p.is_file()}
freeze={'base':proof['base'],'sources':sources,'proof_raw_sha256':proof_files,
        'before29_unit_cases_passed':29,'after30_unit_cases_passed':50,'browser_criteria_unchanged':16,
        'runtime_browser_pending':True,'independent_review_pending':True,
        'proof_attributes':'Local .gitattributes * -text from creation; every committed proof blob must equal raw bytes.'}
(OUT/'source-freeze.json').write_text(json.dumps(freeze,indent=2)+'\n',encoding='utf8')
print(json.dumps({'source_freeze_raw_sha256':sha((OUT/'source-freeze.json').read_bytes()),'sources':sources}))
