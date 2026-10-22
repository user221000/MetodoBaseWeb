"""Keep all11 original safety criteria; adapt only complete mock diagnostics.

The original six function code objects, assertions and parameter marks remain
literal. Production scanners are never mocked by this test-only transport.
"""
import hashlib
import json
from pathlib import Path
from types import FunctionType

from tests import test_secret_scan_safety as original

SOURCE_SHA256 = {"7e7a274c33e7c305e6b2324e90c34358bbf775f465548693d6d7dd806873e474",
                 "ff229d7c7bec9cab6006de51922353a66a9cc164d2f2634891afbddb08b86624"}


def scenario(*args, **kwargs):
    scanner, report, canary = original._scenario(*args, **kwargs)
    tmp_path, monkeypatch = args[:2]
    private = tmp_path / "scanner-private-evidence"
    private.mkdir()
    # The test basetemp is already privately owned. No actual host scanner or
    # ACL command belongs to this mocked I/O scenario.
    monkeypatch.setattr(scanner, "_private_evidence", lambda requested: private)
    mocked_run = scanner.subprocess.run

    def complete_mock(command, **options):
        reply = mocked_run(command, **options)
        if command[0] != "git" and command[1] != "version" and reply.returncode in {0, 1}:
            raw = Path(command[command.index("--report-path") + 1])
            count = len(json.loads(raw.read_bytes()))
            last = f"WRN leaks found: {count}" if count else "INF no leaks found"
            reply.stdout = b""
            reply.stderr = "6:47PM INF scanned ~37 bytes (37 bytes) in 1ms\n6:47PM " + last + "\n"
        return reply

    monkeypatch.setattr(scanner.subprocess, "run", complete_mock)
    return scanner, report, canary


def export():
    if hashlib.sha256(Path(original.__file__).read_bytes()).hexdigest() not in SOURCE_SHA256:
        raise ValueError("The original scanner safety source differs; assertions cannot be transported")
    namespace = dict(vars(original))
    namespace["_scenario"] = scenario
    exported = {}
    for name, value in vars(original).items():
        if name.startswith("test_") and isinstance(value, FunctionType):
            copy = FunctionType(value.__code__, namespace, name, value.__defaults__, value.__closure__)
            copy.__kwdefaults__ = value.__kwdefaults__
            copy.__dict__.update(value.__dict__)
            copy.__doc__ = value.__doc__
            copy.__annotations__ = dict(value.__annotations__)
            exported[name] = copy
    if len(exported) != 6:
        raise ValueError("The complete original six scanner safety functions differ")
    return exported
