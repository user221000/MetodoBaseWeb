"""Container startup must stop on migration failure before serving requests."""
import os
from pathlib import Path
import shutil
import subprocess


def _bash():
    if os.name == "nt":
        path = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Git/bin/bash.exe"
        assert path.is_file(), "Git Bash is required for the Windows entrypoint contract"
        return str(path)
    path = shutil.which("bash")
    assert path, "bash is required for the entrypoint contract"
    return path


def test_migration_failure_is_fatal_before_server_start(tmp_path):
    entrypoint = Path(__file__).resolve().parents[1] / "entrypoint.sh"
    # Git Bash accepts CRLF scripts on Windows. Linux execve includes CR in
    # the shebang interpreter name, so its actual bytes must remain portable.
    assert entrypoint.read_bytes().startswith(b"#!/bin/bash\n")
    syntax = subprocess.run([_bash(), "-n", str(entrypoint)], capture_output=True, timeout=15)
    assert syntax.returncode == 0, "entrypoint must be valid LF Bash code"
    fake_python = tmp_path / "python"
    fake_python.write_text('#!/bin/sh\nif [ "$1" = "db_bootstrap.py" ]; then exit 73; fi\nprintf "server-started"\n',
        encoding="utf-8", newline="\n")
    fake_python.chmod(0o700)
    # No inherited shell startup file, provider settings or database URL.
    environment = {key: os.environ[key] for key in ("SYSTEMROOT", "WINDIR", "TEMP", "TMP") if key in os.environ}
    environment["PATH"] = str(tmp_path)
    process = subprocess.run([_bash(), str(entrypoint)], env=environment,
        capture_output=True, timeout=15)
    assert process.returncode == 73
    assert b"server-started" not in process.stdout
