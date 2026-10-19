"""Private author replay of immutable SEC20, or maintained primary header probes."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path('F:/mb-mfa31-parent-canonical-20261019')
HERE = Path(__file__).parent
ORIGINAL = Path('C:/Users/Consu/AppData/Local/Temp/metodobase-mfa31-security-full-20261019')
OUT = ROOT / 'docs/implementation/20261018-evolution/evidence/backend-mfa31-parent-canonical'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def photograph():
    names = subprocess.check_output(['git', '--no-replace-objects', 'ls-files', '-co', '--exclude-standard', '-z'], cwd=ROOT).decode().split('\0')[:-1]
    return {name: sha((ROOT / name).read_bytes()) for name in sorted(set(names))
            if not name.startswith('docs/') and (ROOT / name).is_file()}


def packages():
    return sorted((item.metadata['Name'], item.version) for item in importlib.metadata.distributions())


def main():
    label = sys.argv[1]
    assert label in {'before', 'after', 'maintained-after', 'actor-before', 'maintained-final', 'security-final'}
    if not OUT.exists():
        OUT.mkdir()
        (OUT / '.gitattributes').write_bytes(b'* -text\n')
        test = (ORIGINAL / 'test_parent_scope.py').read_bytes()
        assert sha(test) == '4d0d35179c3ef1bc10f2023a4a6ac67d6310f09d597ddbc6adfaa4a154ed385f'
        runner = (ORIGINAL / 'run_full.py').read_bytes()
        runner = runner.replace(b'test_full_review.py', b'test_parent_scope.py')
        (OUT / 'security-test_parent_scope.py').write_bytes(test)
        (OUT / 'security-run_full-original.py').write_bytes(runner)
        adapted = runner.replace(b'F:/mb-mfa-sec', ROOT.as_posix().encode())
        assert adapted != runner
        (OUT / 'security-run_full-own-root.py').write_bytes(adapted)
        for name in ['before', 'after']:
            folder = HERE / name
            folder.mkdir()
            (folder / 'test_parent_scope.py').write_bytes(test)
            (folder / 'run_full.py').write_bytes(adapted)
        for name in ['mfa_service.py', 'mfa_actions.py']:
            (OUT / (name + '-before-RAW.py')).write_bytes((ROOT / 'web/services' / name).read_bytes())
    assert not (OUT / (label + '.log')).exists()
    before, package_before = photograph(), packages()
    maintained = label in {'maintained-after', 'actor-before', 'maintained-final'}
    if maintained:
        xml_path = HERE / (label + '.xml')
        command = [sys.executable, '-X', 'utf8', '-B', 'tests/run_isolated.py',
                   'tests/test_mfa31_parent_canonical.py', '-q', '--tb=short', '--junitxml=' + str(xml_path)]
        if label == 'actor-before':
            command += ['-k', 'test_actor_empty_invitation']
    else:
        if label == 'security-final':
            folder = HERE / label
            folder.mkdir()
            for name in ['test_parent_scope.py', 'run_full.py']:
                (folder / name).write_bytes((HERE / 'after' / name).read_bytes())
        command = [sys.executable, '-X', 'utf8', '-B', str(HERE / label / 'run_full.py')]
        xml_path = HERE / label / 'full.xml'
    result = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=300)
    raw, xml = result.stdout + result.stderr, xml_path.read_bytes()
    assert b'otpauth://' not in raw and re.search(rb'[A-Za-z0-9_-]+\.[0-9a-fA-F]{64}', raw) is None
    (OUT / (label + '.log')).write_bytes(raw)
    (OUT / (label + '.xml')).write_bytes(xml)
    cases = list(ET.fromstring(xml).iter('testcase'))
    after, package_after = photograph(), packages()
    report = {'label': label, 'exit': result.returncode, 'cases': len(cases),
              'failures': sum(case.find('failure') is not None for case in cases),
              'errors': sum(case.find('error') is not None for case in cases),
              'skips': sum(case.find('skipped') is not None for case in cases),
              'source_files': len(before), 'sources_quiet': before == after,
              'packages': len(package_before), 'packages_quiet': package_before == package_after,
              'stdout_sha256': sha(raw), 'xml_sha256': sha(xml)}
    for suffix, value in [('summary', report), ('source-before', before), ('source-after', after),
                          ('packages-before', package_before), ('packages-after', package_after)]:
        with (OUT / (label + '-' + suffix + '.json')).open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(json.dumps(value, indent=2) + '\n')
    if not maintained:
        origins = (HERE / label / 'origins.json').read_bytes()
        assert json.loads(origins)['source_root'] == str(ROOT)
        (OUT / (label + '-origins.json')).write_bytes(origins)
    print(json.dumps(report))
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
