"""Readonly diagnostic photographs; no dependency installation or application I/O."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import subprocess
import sys


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def photograph(root, task, label, profile, node, chrome, dependencies):
    private = task / "private"
    source = {}
    for command in (["git", "ls-files", "-z"], ["git", "ls-files", "--others", "--exclude-standard", "-z"]):
        names = subprocess.check_output(command, cwd=root).decode().split("\0")
        for name in names:
            path = root / name
            if name and not name.startswith("docs/") and path.is_file():
                source[name] = digest(path)
    packages, installed = [], {}
    for distribution in importlib.metadata.distributions():
        packages.append([distribution.metadata["Name"], distribution.version])
        for item in distribution.files or []:
            path = Path(distribution.locate_file(item)).resolve()
            if path.is_file() and path.suffix not in {".pyc", ".pyo"}:
                installed[str(path)] = digest(path)
    config = json.loads(profile.read_bytes())
    pg_bin = Path(config["METODOBASE_TEST_PG_BIN"])
    value = {
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        "source": source, "packages": sorted(packages), "installed": installed,
        "python": {"path": sys.executable, "sha256": digest(sys.executable)},
        "Python_base": {"path": sys._base_executable, "sha256": digest(sys._base_executable)},
        "profile_sha256": digest(profile),
        "PG_tools": {name: digest(pg_bin / name) for name in ("pg_dump.exe", "pg_restore.exe")},
        "node": {"path": str(node), "sha256": digest(node)},
        "chrome": {"path": str(chrome), "sha256": digest(chrome)},
        "node_files": {path.relative_to(dependencies).as_posix(): digest(path)
                       for path in sorted(dependencies.rglob("*")) if path.is_file()},
        "external_private_helpers": {path.name: digest(path) for path in task.glob("*.py")},
    }
    target = private / (label + "-full.json")
    with target.open("xb") as output:
        output.write((json.dumps(value, indent=2) + "\n").encode())
    return value


def pipcheck(root, task, label):
    result = subprocess.run([sys.executable, "-m", "pip", "check"], cwd=root, capture_output=True)
    for name, content in (("stdout", result.stdout), ("stderr", result.stderr)):
        with (task / "private" / (label + "-pip." + name)).open("xb") as output:
            output.write(content)
    assert result.returncode == 0
    return 0
