"""Resume equal public projections, keeping the intentionally sensitive canary source private."""
from pathlib import Path

original=Path('E:/MetodoBaseWorkspace/evidence/backend-ci57-pytest-bootstrap-20261022-seal.py')
source=original.read_text(encoding='utf8')
source=source.replace("    with (PUBLIC/name).open('xb') as stream:stream.write(b)",
    "    if (PUBLIC/name).exists():\n        assert (PUBLIC/name).read_bytes()==b\n        return\n    with (PUBLIC/name).open('xb') as stream:stream.write(b)")
source=source.replace("write('seal.py',Path(__file__).read_bytes())", "write('seal-v2.py',Path(__file__).read_bytes())")
source=source.replace("write('test_ci_image57_offline.before.py.RAW',original)",
    "# Before source remains private: its old negative canary contains an intentionally rejected otpauth literal.")
exec(compile(source,str(original),'exec'))
