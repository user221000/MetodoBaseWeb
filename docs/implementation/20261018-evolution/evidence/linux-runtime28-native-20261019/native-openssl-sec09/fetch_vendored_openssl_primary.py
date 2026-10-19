from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib, json, urllib.request

LAB = Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
OUT = LAB / 'evidence/runtime28-native-20261019/vendored-openssl-primary'
OUT.mkdir(exist_ok=False)
prior = json.loads((LAB / 'evidence/os-audit-abd559a/triage-primary/openssl-backport-comparison.json').read_text())
ids = prior['upstream_359_cve_ids']
def fetch(key):
    url = 'https://openssl-library.org/news/secjson/' + key.lower() + '.json'
    with urllib.request.urlopen(url, timeout=60) as response:
        raw = response.read()
    record = json.loads(raw)
    assert record['cveMetadata']['cveId'] == key
    assert record['containers']['cna']['providerMetadata']['shortName'] == 'openssl'
    (OUT / (key + '.json')).write_bytes(raw)
    cna = record['containers']['cna']
    matches = [v for item in cna['affected'] for v in item['versions']
               if v.get('version') == '3.5.0' and v.get('lessThan') == '3.5.9' and v.get('status') == 'affected']
    assert matches, key
    return {'id': key, 'primary_url': url, 'raw_sha256': hashlib.sha256(raw).hexdigest(),
            'title': cna['title'], 'affected_35_range': matches,
            'installed_vendored_openssl': '3.5.8', 'version_in_affected_range': True,
            'primary_severity': cna.get('metrics', []),
            'fix_references': [r for r in cna.get('references', []) if '3.5.9' in r.get('name', '')],
            'reachability': 'OPEN: version match is not a demonstrated product path or exploit. Check architecture, protocol/API/build conditions per advisory.',
            'debian_backport_covers_this_vendored_binary': False}
with ThreadPoolExecutor(max_workers=4) as pool:
    rows = list(pool.map(fetch, ids))
report = {'fetched_utc': datetime.now(timezone.utc).isoformat(),
          'image_id': 'sha256:99c846bd28b0d464c837a72fc6340df1c9583834b2529c8bde18bd6d7544410c',
          'component': 'psycopg2-binary vendored libssl/libcrypto', 'installed_runtime_api_version': 'OpenSSL 3.5.8 25 Aug 2026',
          'primary_records': len(rows), 'rows': rows,
          'scope': 'Additional native-library version-range findings, separate from the 71 Debian identifiers and zero direct PyPI audit. No ignored or accepted exceptions; product exploitability pending.'}
(OUT / 'comparison.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'primary_records': len(rows), 'vendored_version_matches_affected_ranges': True,
                  'comparison_sha256': hashlib.sha256((OUT / 'comparison.json').read_bytes()).hexdigest()}))
