"""Close independent R29 acceptance; preserve both product red and QA harness errors."""
import hashlib
import json
from pathlib import Path

ROOT = Path(r'F:\MetodoBaseWeb-landing-20261019')
OUT = Path(__file__).resolve().parent
HEAD = '55f72149e7e05d032b5a865c664fb13070eb3df6'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf8'))


def save(name, data):
    with (OUT / name).open('x', encoding='utf8') as stream:
        json.dump(data, stream, indent=2); stream.write('\n')


prior = load(OUT / 'partial-manifest.json')
assert all(sha(OUT / path) == value for path, value in prior['files'].items())
author_http = load(OUT / 'author12/summary.json')
assert author_http['junit'] == {'tests': 12, 'failures': 0, 'errors': 0, 'skipped': 0}
negative = load(OUT / 'own-dynamic-with-composition/source.json')
positive = load(OUT / 'period55-after/summary.json')
assert negative['junit'] == {'tests': 2, 'failures': 2, 'errors': 0, 'skipped': 0}
assert positive['junit'] == {'tests': 2, 'failures': 0, 'errors': 0, 'skipped': 0}
assert positive['original_criterion_and_red_evidence_unchanged']
author = load(OUT / 'browser55-first/author-browser/report.json')
first_own = load(OUT / 'browser55-first/own-browser/report.json')
navigation = load(OUT / 'browser55-navigation-final/own-browser/report.json')
assert author['passed'] and len(author['checks']) == 8 and len(author['screens']) == 4 and author['pageErrors'] == []
assert first_own['passed'] is False and len(first_own['checks']) == 2 and first_own['pageErrors'] == []
assert navigation['passed'] and len(navigation['checks']) == 1 and navigation['pageErrors'] == []
assert navigation['nextTabBypassesHeader']['main'] == 'contenido'
assert navigation['nextTabBypassesHeader']['outline'] >= 2
for name in author['screens']:
    screen = load(OUT / 'browser55-first/author-browser' / (name + '.json'))
    assert screen['violations'] == [] and screen['overflow'] is False
guards = []
for name in ['browser55-first', 'browser55-navigation', 'browser55-navigation-final']:
    closed = load(OUT / name / 'owned-process-close.json')
    assert closed['listener_gone'] and closed['owned_port_free'] and closed['foreign_ports_fingerprints_unchanged']
    before = load(OUT / name / 'before.json'); after = load(OUT / name / 'after.json')
    assert before == after and before['head'] == HEAD
    for path in (OUT / name).rglob('network-guard.json'):
        guard = load(path); assert guard['maxRedirects'] == 0 and guard['exactOrigin'] == 'http://127.0.0.1:8793'
        guards.append({'path': path.relative_to(OUT).as_posix(), 'blocked_external_attempts': guard['blockedOtherOrigins']})
(OUT / 'harness-final.py.txt').write_bytes((OUT.parent / 'run_public_history_browser_review.py').read_bytes())
save('final-summary.json', {
    'decision': 'Accepted scoped independent R29 QA at55. No product issue remains from this review; publication/integration are separate coordinator steps.',
    'head': HEAD, 'author12_http_head': 'ad541ae6b8a7de18719c08b6584b5fdb47018e6c',
    'validation': {'author_http': 12, 'independent_runtime_catalog_negatives_before': 2,
                   'same_independent_catalog_criteria_after_passed': 2,
                   'author_browser_groups': 8, 'own_browser_groups': 3,
                   'own_browser_group_distribution': '2 passed before harness-only stop; remaining navigation group passed on fresh fixture. Author8 ran once.',
                   'author_full_document_axe_screens': 4, 'author_overflow_and_pageerrors': 0},
    'sources': {'initial_http': 756, 'period_fix_http': 764, 'each_browser': 755,
                'packages': 89, 'readonly_browser_dependencies': 146,
                'all_phase_photos_stable': True, 'pip_checks_zero': True},
    'catalog': {'business_free': {'clients': 10, 'per_client_per_day': 1, 'total_per_day': 10, 'per_month': 20},
                'personal_starter_monthly_plans': 1, 'personal_pro_monthly_plans': 5,
                'personal_pro_centavos': 7900, 'currency': 'MXN',
                'note_fix': 'Neutral note refers to amount/currency/period shown in each actual catalog card; no invented annual support or tax assumption.',
                'dynamic_criterion_sha256': sha(OUT / 'test_landing_dynamic_review.py.txt')},
    'browser_checks': author['checks'] + first_own['checks'] + navigation['checks'],
    'preservation_and_worker_provenance': {'proof_sha256': sha(OUT / 'preservation.json'),
        'preserved_runtime_catalog_schema_auth_and_ci_sources': 13,
        'registration_change': 'Exactly one initialization line; other auth/submit/Storage bytes unchanged.',
        'orphan': 'Unmounted duplicate retired, exact RAW copy outside deliverable and original Git blob verified; checkout neighbor unchanged.',
        'worker': 'Public excerpt matches preserved actual breakfast options; PDF ZIP entry matches exact external RAW bytes and valid startxref. No worker regeneration claim from this QA.',
        'pdf_bytes': 3605631, 'pdf_sha256': 'a60d08d48bc000c95776b505d0517f3c23eda26ffd292d4ef46a09b9ec93fb19'},
    'retained_harness_errata': [
        'First external-Temp Python run lacked the root conftest and had2 setup errors. Explicit -p conftest fixed only composition; original criterion bytes unchanged and product2red then2green preserved.',
        'Initial browser control demanded activeElement.id=contenido. Actual native skip keeps BODY active but the next Tab correctly bypasses header into main CTA, with3px visible focus. A positive baseline without skip stays at header; both outcomes are observed.',
        'Remaining navigation control initially selected h2 although data section uses h3. Final control follows aria-labelledby=data-title and verifies a real nonempty heading. No product edits for either browser harness correction; all original records retained.'
    ],
    'network_guards': guards,
    'owned_processes': 'All three own8793 listener/launcher pairs closed with exact fingerprints and port absence; unrelated8776/8777/8780/8781/8784 fingerprints unchanged.',
    'visual_review': '1440px final landing screenshot inspected: both audience CTAs, all separated business/personal prices and limits, labeled synthetic example, neutral period note and factual data section match tested rendering.',
    'scope': 'Real unauthenticated local HTTP with isolated metadata-only SQLite, closed origin/maxRedirects0 and no form submission/provider. No PG/load/broad suite, clinical guidance, purchase, publication or recovery28 integration claim.',
    'no_product_ci_author_edits_or_commits': True,
})
files = {path.relative_to(OUT).as_posix(): sha(path) for path in sorted(OUT.rglob('*')) if path.is_file()}
save('final-manifest.json', {'files': files, 'count': len(files), 'scope': 'All independent prefix files, including product red and harness-error records; excludes this manifest.'})
print(json.dumps({'summary_sha256': sha(OUT / 'final-summary.json'),
                  'manifest_sha256': sha(OUT / 'final-manifest.json'), 'files': len(files)}))
