"""Independent R29 scope, catalog and exact synthetic worker/PDF provenance audit."""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import zipfile

ROOT = Path(r'F:\MetodoBaseWeb-landing-20261019')
OUT = Path(__file__).resolve().parent
BASE = '593127fd20fed139bcbc077e23b521c965aeeb53'
HEAD = '55f72149e7e05d032b5a865c664fb13070eb3df6'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def frozen(commit, path):
    return subprocess.check_output(['git', 'show', commit + ':' + path], cwd=ROOT)


def functions(source):
    return {node.name: ast.dump(node, include_attributes=False) for node in ast.parse(source).body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}


old, new = functions(frozen(BASE, 'web/routes/pages.py')), functions(frozen(HEAD, 'web/routes/pages.py'))
assert old.keys() == new.keys() and [name for name in old if old[name] != new[name]] == ['index']
before, after = frozen(BASE, 'web/templates/registro.html').decode(), frozen(HEAD, 'web/templates/registro.html').decode()
old_line = "if (params.get('tipo') === 'gym') setTipo('gym');"
new_line = "setTipo(params.get('tipo') === 'gym' ? 'gym' : 'usuario');"
assert before.count(old_line) == 1 and before.replace(old_line, new_line) == after
preserved = []
for path in ['core/plan_catalog.py', 'api/app.py', 'web/static/js/api.js', 'web/middleware/security_headers.py',
             'web/database/models.py', 'web/database/schema_control.py', 'web/routes/auth.py',
             'web/routes/usuario.py', 'web/services/generation_quota.py', 'web/services/plan_generation.py',
             'web/pages/checkout.html', '.github/workflows/ci.yml', 'tests/e2e/package-lock.json']:
    raw = frozen(HEAD, path); assert raw == frozen(BASE, path), path
    preserved.append({'path': path, 'lf_sha256': sha(raw)})

original_path = 'docs/implementation/20261018-evolution/evidence/landing/source-freeze.json'
manifest = json.loads(frozen(HEAD, original_path))
archive_path = ROOT / manifest['raw_source_archive']['path']
assert sha(archive_path.read_bytes()) == manifest['raw_source_archive']['sha256']
with zipfile.ZipFile(archive_path) as archive:
    for path, expected in manifest['sources'].items():
        data = archive.read(path)
        assert sha(data) == expected['raw_sha256'] and sha(data.replace(b'\r\n', b'\n')) == expected['lf_sha256']
    example_raw = archive.read('web/static/data/landing-example.json')
retired = manifest['retired']
orphan = Path(retired['external_raw_copy'])
assert orphan.is_file() and not orphan.resolve().is_relative_to(ROOT.resolve())
assert sha(orphan.read_bytes()) == retired['raw_sha256']
assert orphan.read_bytes().replace(b'\r\n', b'\n') == frozen(BASE, retired['path'])
assert subprocess.check_output(['git', 'rev-parse', BASE + ':' + retired['path']], cwd=ROOT, text=True).strip() == retired['git_blob']
assert not (ROOT / retired['path']).exists()

worker = ROOT / 'docs/implementation/20261018-evolution/evidence/landing/worker-example'
provenance = json.loads((worker / 'provenance.json').read_text(encoding='utf8'))
plan = json.loads((worker / 'generated-plan.json').read_text(encoding='utf8'))
example = json.loads((ROOT / 'web/static/data/landing-example.json').read_text(encoding='utf8'))
assert sha(example_raw) == provenance['public_excerpt_sha256']
assert example == json.loads(example_raw)
assert example['groups'] == [{'group': group, 'option': plan['desayuno'][group]['opciones'][0]}
                              for group in ['proteinas', 'carbohidratos', 'grasas']]
pdf_path = ROOT / manifest['pdf_proof']['archive']
assert sha(pdf_path.read_bytes()) == manifest['evidence'][manifest['pdf_proof']['archive']]
with zipfile.ZipFile(pdf_path) as archive:
    assert archive.namelist() == [manifest['pdf_proof']['entry']]
    pdf = archive.read(manifest['pdf_proof']['entry'])
assert sha(pdf) == manifest['pdf_proof']['raw_sha256'] == provenance['pdf_sha256']
assert len(pdf) == provenance['pdf_bytes'] and pdf.startswith(b'%PDF-')
match = re.search(rb'startxref\s+(\d+)\s+%%EOF\s*$', pdf)
assert match and pdf[int(match.group(1)):][:4] == b'xref'
external_pdf = Path(manifest['pdf_proof']['external_raw_copy'])
assert external_pdf.is_file() and external_pdf.read_bytes() == pdf
template = frozen(HEAD, 'web/templates/landing.html').decode()
assert not re.search(r'\b(?:IVA|impuestos|tax)\b', template, re.I)
proof = {'base': BASE, 'head': HEAD, 'pages_only_index_function_changed': True,
         'registration_only_exact_initialization_line_changed': True,
         'shared_catalog_api_auth_storage_models_ci_unchanged': preserved,
         'source_archive_sha256': sha(archive_path.read_bytes()), 'tested_raw_owned_sources_authenticated': len(manifest['sources']),
         'retired_orphan': {'external_raw_sha256': sha(orphan.read_bytes()), 'git_blob': retired['git_blob'],
                            'raw_copy_outside_deliverable_present': True, 'normalized_copy_matches_original_git': True,
                            'active_path_absent_and_checkout_neighbor_unchanged': True},
         'worker_provenance': {'public_excerpt_exactly_matches_three_actual_breakfast_options': True,
                               'raw_pdf_sha256': sha(pdf), 'pdf_bytes': len(pdf),
                               'pdf_exact_external_copy_matches_zip_and_startxref': True,
                               'scope': 'Preserved actual author worker/ASGI artifacts and builder inspected; generation procedure not repeated and no nutritional/clinical claim.'},
         'no_added_tax_text': True,
         'scope': 'Independent frozen source/provenance comparison. Runtime catalog and browser results are separate; no purchase, publication, external delivery or integration claim.'}
with (OUT / 'preservation.json').open('x', encoding='utf8') as stream:
    json.dump(proof, stream, indent=2); stream.write('\n')
print(json.dumps({'preserved_sources': len(preserved), 'pdf_bytes': len(pdf), 'public_excerpt_exact': True, 'orphan_raw_present': True}))
