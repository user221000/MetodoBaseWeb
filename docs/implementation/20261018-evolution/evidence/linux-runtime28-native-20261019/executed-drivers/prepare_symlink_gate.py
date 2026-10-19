from pathlib import Path
import hashlib, io, json, os, re, subprocess, tarfile

LAB = Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
BASE = LAB / 'evidence/runtime28-native-20261019'
OUT = BASE / 'symlink-gate'
OUT.mkdir(exist_ok=False)
REPO = Path(r'F:\MetodoBaseWeb-image-security-20261019')
HEAD = 'bc365c13b9af9e24129a56b4068059a67bb3afa0'
env = {k: v for k, v in os.environ.items() if not k.upper().startswith('GIT_')}
env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull, GIT_ATTR_NOSYSTEM='1', GIT_NO_REPLACE_OBJECTS='1', GIT_OPTIONAL_LOCKS='0')
git = ['git', '--no-optional-locks', '-c', 'core.fsmonitor=false', '-c', 'core.hooksPath=' + os.devnull, '-C', str(REPO)]
def blob(ref, path):
    return subprocess.check_output(git + ['show', ref + ':' + path], env=env)
test_path = 'tests/test_object_storage.py'
case = blob(HEAD, test_path)
main_ref = subprocess.check_output(git + ['rev-parse', 'b59c99f'], env=env).decode().strip()
assert len(main_ref) == 40 and main_ref.startswith('b59c99f')
assert blob(main_ref, test_path) == case
expected = {}
for path in ['web/storage/local.py', 'web/storage/objects.py']:
    data = blob(HEAD, path)
    assert data == blob(main_ref, path)
    expected['/app/' + path] = hashlib.sha256(data).hexdigest()
runner = r'''from pathlib import Path
import hashlib,importlib.metadata,json,os,subprocess,sys,tempfile,xml.etree.ElementTree as ET
assert sys.platform=='linux' and os.getuid()==999
expected=EXPECTED
actual={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in expected}
assert actual==expected
assert hashlib.sha256(Path('/qa/tests/test_object_storage.py').read_bytes()).hexdigest()==TEST_SHA
with tempfile.TemporaryDirectory(prefix='symlink28-preflight-') as root:
 p=Path(root);(p/'outside').mkdir();(p/'link').symlink_to(p/'outside',target_is_directory=True)
 assert (p/'link').is_symlink() and (p/'link').resolve()==p/'outside'
toolenv=os.environ.copy()
toolenv.update(PYTHONPATH='/qa/tools:/app',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTHONDONTWRITEBYTECODE='1')
command=[sys.executable,'-B','-m','pytest','-q','-p','no:cacheprovider','--noconftest','-c','/dev/null',
 '--basetemp=/tmp/pytest-symlink28','--junitxml=/tmp/symlink28.xml',
 '/qa/tests/test_object_storage.py::test_symlink_cannot_redirect_a_private_document']
p=subprocess.run(command,env=toolenv,cwd='/qa')
xml=Path('/tmp/symlink28.xml').read_bytes();tree=ET.fromstring(xml)
cases=tree.findall('.//testcase');assert len(cases)==1
assert not tree.findall('.//skipped') and not tree.findall('.//failure') and not tree.findall('.//error')
assert p.returncode==0
print('SYMLINK28_RESULT '+json.dumps({'exit':p.returncode,'testcases':len(cases),'skipped':0,'failures':0,'errors':0,
 'exact_case':'test_symlink_cannot_redirect_a_private_document','source_hashes':actual,'test_sha256':TEST_SHA,
 'real_linux_symlink_preflight':True,'junit_xml':xml.decode(),'junit_sha256':hashlib.sha256(xml).hexdigest(),
 'scope':'Exact committed storage unit gate against code in the frozen image. --noconftest excludes unrelated global database fixtures; this is not PostgreSQL, application-startup or production-settings validation.'}),flush=True)
'''.replace('EXPECTED', repr(expected)).replace('TEST_SHA', repr(hashlib.sha256(case).hexdigest()))
compile(runner, 'symlink28-runner', 'exec')
members = {'tests/test_object_storage.py': case, 'runner.py': runner.encode()}
for p in sorted((BASE / 'pytest-tools/unpacked').rglob('*')):
    if p.is_file():
        assert not p.is_symlink() and not (getattr(p.lstat(), 'st_file_attributes', 0) & 0x400)
        members['tools/' + p.relative_to(BASE / 'pytest-tools/unpacked').as_posix()] = p.read_bytes()
manifest = {p: {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()} for p, data in members.items()}
assert len(manifest) == len({p.casefold() for p in manifest})
stream = io.BytesIO()
with tarfile.open(fileobj=stream, mode='w', format=tarfile.PAX_FORMAT) as archive:
    for name, data in sorted(members.items()):
        item = tarfile.TarInfo(name);item.size=len(data);item.mode=0o444;item.mtime=0
        archive.addfile(item, io.BytesIO(data))
tar = stream.getvalue()
header = json.dumps({'files': manifest}, sort_keys=True, separators=(',', ':')).encode() + b'\n'
frame = header + tar
(OUT / 'qa.transport').write_bytes(frame)
(OUT / 'files.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
report = {'image_source': HEAD, 'main_test_reference': main_ref,
          'test_file': test_path, 'test_sha256': hashlib.sha256(case).hexdigest(),
          'test_and_storage_modules_identical_between_image_source_and_main_reference': True,
          'expected_storage_source_sha256': expected, 'file_count': len(manifest),
          'frame': {'bytes': len(frame), 'sha256': hashlib.sha256(frame).hexdigest()},
          'tar': {'bytes': len(tar), 'sha256': hashlib.sha256(tar).hexdigest()},
          'scope': 'Prepared exact existing Linux storage symlink gate with separately pinned pure-Python pytest tools. No database fixtures, product code changes, image install or startup.'}
(OUT / 'preparation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, indent=2))
