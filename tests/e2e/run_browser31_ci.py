"""Execute the maintained offline browser-session criteria and verify their map.

Historical JWT-Storage reports are never converted into successful current cases.
Native browser and independent QA acceptance remain separate gates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAP = ROOT / 'docs/implementation/20261018-evolution/SESION_NAVEGADOR_R31_CI_MAP.json'


def digest(path: Path) -> str:
    """Hash exact source bytes; never print source or credentials."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def execute(output: Path, node: str) -> dict:
    """Keep raw diagnostics private and publish only exact current case outcomes."""
    mapping = json.loads(MAP.read_text(encoding='utf8'))
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    private = output / 'private'
    private.mkdir(mode=0o700)
    env = os.environ.copy()
    env['NODE_OPTIONS'] = '--require="' + (ROOT / 'tests/e2e/browser_offline31.cjs').as_posix() + '"'
    source_checks = []
    for item in mapping['historical_sources'].values():
        source_checks.append(digest(ROOT / item['path']) == item['sha256'])
    commands, rows, outcomes = [], [], {}
    for command in mapping['current_commands']:
        argv = [node, *command['argv'][1:]]
        key = command['key']
        expected = command['expected_cases']
        source_ok = digest(ROOT / command['argv'][1]) == command['source_sha256']
        if key.startswith('compat.'):
            source_ok = source_ok and digest(ROOT / ('tests/e2e/' + key[7:] + '.cjs')) == command['legacy_source_sha256']
        if key.startswith('export.'):
            source_ok = source_ok and digest(ROOT / ('tests/e2e/' + key[7:] + '.cjs')) == command['legacy_source_sha256']
        result = subprocess.run(argv, cwd=ROOT, env=env, capture_output=True, timeout=60, check=False)
        (private / (key + '.stdout.raw')).write_bytes(result.stdout)
        (private / (key + '.stderr.raw')).write_bytes(result.stderr)
        valid = source_ok and result.returncode == 0
        command_rows = []
        try:
            report = json.loads(result.stdout)
            actual = report['results']
            valid = (valid and type(report['total']) is int and type(report['passed']) is int
                     and report['total'] == report['passed'] == len(actual) == len(expected))
            for previous, current in zip(expected, actual, strict=True):
                label = str(current.get('case', current.get('name', current.get('code', ''))))
                passed = current.get('passed') is True and label == previous['name']
                valid = valid and passed
                command_rows.append({'case': previous['nodeid'], 'passed': passed})
        except (KeyError, TypeError, ValueError):
            valid = False
        if not valid or len(command_rows) != len(expected):
            command_rows = [{'case': item['nodeid'], 'passed': False} for item in expected]
        rows.extend(command_rows)
        outcomes.update({item['case']: item['passed'] for item in command_rows})
        commands.append({'key': key, 'exit': result.returncode, 'source_exact': source_ok,
                         'current_cases': len(expected), 'passed': bool(valid)})
        (private / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n', encoding='utf8')
    obligations = all(all(outcomes.get(ref) is True for ref in item['current_nodeids'])
                      for item in mapping['case_obligations'])
    valid = all(source_checks) and all(item['passed'] for item in commands) and obligations
    report = {
        'scope': 'Owned current offline criteria only. Historical cases are preserved and mapped, '
                 'not retroactively marked PASS. Native browser and independent QA gates '
                 'must pass separately before global CI acceptance.',
        'map_sha256': digest(MAP), 'historical_sources_exact': all(source_checks),
        'case_obligations_verified': len(mapping['case_obligations']) if obligations else 0,
        'commands': commands, 'passed': sum(row['passed'] for row in rows),
        'total': len(rows), 'results': rows, 'accepted_owned_scope': valid,
    }
    (output / 'current-browser31.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
    if not valid:
        raise ValueError('Current mapped frontend criteria failed; raw diagnostics retained privately')
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--node', default=shutil.which('node') or 'node')
    args = parser.parse_args()
    try:
        report = execute(args.output, args.node)
    except (OSError, ValueError, subprocess.SubprocessError):
        print('Current browser-session gate failed; inspect its private diagnostics.', file=sys.stderr)
        return 1
    print(json.dumps({'commands': len(report['commands']), 'passed': report['passed'],
                      'total': report['total'], 'mapped_obligations': report['case_obligations_verified'],
                      'scope': 'owned offline frontend criteria only'}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
