"""Independent preservation audit of immutable R34 71+49 commits."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import re
import subprocess
import zipfile

ROOT = Path(r'F:\MetodoBaseWeb-history-ui-20261019')
OUT = Path(__file__).resolve().parent
BASE = '5c9e09723a2de2e40a4de7488c7af918fd51422f'
FEATURE = '71e2481ce37d64a244ae1fba3754ebfeba1d0a0d'
FINAL = '49eb44124d36a0d0aeaf732d7f720d969f1d517c'


def frozen(commit, path):
    return subprocess.check_output(['git', 'show', commit + ':' + path], cwd=ROOT).decode('utf8')


def functions(source):
    return {node.name: node for node in ast.parse(source).body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}


def dump(node):
    return ast.dump(node, include_attributes=False)


path = 'web/routes/usuario.py'
old, new = functions(frozen(BASE, path)), functions(frozen(FINAL, path))
assert old.keys() == new.keys()
assert [name for name in old if dump(old[name]) != dump(new[name])] == ['historial_planes']
assert dump(old['descargar_pdf_usuario']) == dump(new['descargar_pdf_usuario'])

path = 'api/app.py'
old_api = ast.parse(frozen(BASE, path)); new_api = ast.parse(frozen(FINAL, path))
removed = []


class RemoveOnlyFocalMount(ast.NodeTransformer):
    def visit_ImportFrom(self, node):
        if node.module == 'web.routes.usuario':
            assert [(alias.name, alias.asname) for alias in node.names] == [('historial_planes', None)]
            removed.append('canonical handler import')
            return None
        return node

    def visit_Expr(self, node):
        if (isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute)
                and node.value.func.attr == 'add_api_route' and node.value.args
                and isinstance(node.value.args[0], ast.Constant)
                and node.value.args[0].value == '/api/usuario/historial'):
            assert dump(node.value.args[1]) == dump(ast.Name(id='historial_planes', ctx=ast.Load()))
            keywords = {keyword.arg: ast.literal_eval(keyword.value) for keyword in node.value.keywords}
            assert keywords == {'methods': ['GET'], 'tags': ['Usuario Individual']}
            removed.append('exact GET focal mount')
            return None
        return self.generic_visit(node)


assert dump(old_api) == dump(RemoveOnlyFocalMount().visit(copy.deepcopy(new_api)))
assert removed == ['canonical handler import', 'exact GET focal mount']
api_old, api_new = frozen(BASE, 'web/static/js/api.js'), frozen(FINAL, 'web/static/js/api.js')
pattern = r'    historial:.*?\n    descargarPlan:'
old_helper = re.search(pattern, api_old, re.S)
new_helper = re.search(pattern, api_new, re.S)
assert old_helper and new_helper
assert api_new[:new_helper.start()] + old_helper.group() + api_new[new_helper.end():] == api_old

query_name = 'test_query_is_readonly_limit_plus_one_without_count_or_plan_json'
first = functions(frozen(FEATURE, 'tests/test_personal_history_pagination.py'))[query_name]
last = functions(frozen(FINAL, 'tests/test_personal_history_pagination.py'))[query_name]
first_asserts = [dump(node) for node in ast.walk(first) if isinstance(node, ast.Assert)]
last_asserts = [dump(node) for node in ast.walk(last) if isinstance(node, ast.Assert)]
assert len(first_asserts) == 7 and first_asserts == last_asserts

preserved = []
for path in ['web/services/generation_quota.py', 'web/auth.py', 'web/auth_deps.py',
             'web/database/models.py', 'web/database/schema_control.py', 'web/database/tenant_policy.py',
             'web/routes/personal_diary.py', 'web/services/personal_diary_service.py',
             'web/services/personal_diary_persistence.py', 'web/routes/privacy.py',
             'web/services/privacy_export.py', 'web/services/plan_documents.py',
             'web/static/js/usuario-plan-operacion.js', 'web/static/js/usuario-diario.js',
             'web/static/js/usuario-privacidad.js', 'web/static/js/auth-guard.js',
             '.github/workflows/ci.yml', 'tests/e2e/personal_diary.cjs']:
    original, current = frozen(BASE, path), frozen(FINAL, path)
    assert original == current, path
    preserved.append({'path': path, 'lf_sha256': hashlib.sha256(current.encode()).hexdigest()})

archives = []
for directory in ['history-pagination', 'history-headers-followup']:
    prefix = 'docs/implementation/20261018-evolution/evidence/' + directory
    manifest = json.loads(frozen(FINAL, prefix + '/source-freeze.json'))
    archive_path = ROOT / manifest['raw_source_archive']['path']
    archive_sha = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    assert archive_sha == manifest['raw_source_archive']['sha256']
    with zipfile.ZipFile(archive_path) as archive:
        for path, expected in manifest['sources'].items():
            data = archive.read(path)
            assert hashlib.sha256(data).hexdigest() == expected['raw_sha256']
            assert hashlib.sha256(data.replace(b'\r\n', b'\n')).hexdigest() == expected['lf_sha256']
        archives.append({'path': str(archive_path.relative_to(ROOT)).replace('\\', '/'),
                         'sha256': archive_sha, 'tested_owned_sources': len(manifest['sources']),
                         'raw_and_lf_owned_sources_validated': True})

proof = {'base': BASE, 'feature': FEATURE, 'header_followup': FINAL,
         'only_usuario_function_changed': 'historial_planes', 'exact_personal_pdf_reader_ast_unchanged': True,
         'api_only_canonical_handler_import_and_exact_get_mount': True,
         'api_js_only_history_helper_changed': True,
         'original_explain_assertions_unchanged': 7,
         'preserved_runtime_schema_auth_quota_diary_privacy_ci_and_old_driver': preserved,
         'original_raw_source_archives': archives,
         'scope': 'Static independent frozen-commit preservation only. 500-response header issue remains a separate open security gate; no integration/performance claim.'}
with (OUT / 'preservation.json').open('x', encoding='utf8') as stream:
    json.dump(proof, stream, indent=2)
    stream.write('\n')
print(json.dumps({'historical_runtime_sources_unchanged': len(preserved),
                  'sql_assertions_unchanged': 7, 'raw_archives': len(archives)}))
