"""Exercise the real quality CLIs against isolated synthetic code, never imports.

Uses only stdlib plus the separately installed quality tools. No app/runtime,
database or provider configuration is imported. Invoked by the quality CI job.
"""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def main():
    from check_quality import SOURCES

    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="metodobase-quality-probe-") as temporary:
        target = Path(temporary)
        for directory in (*SOURCES, "tests"):
            (target / directory).mkdir()
        for name in ("check_quality.py", "bandit-reviewed-baseline.json"):
            shutil.copyfile(root / "tests" / name, target / "tests" / name)
        command = [sys.executable, "-X", "utf8", str(target / "tests/check_quality.py")]

        def run(mode):
            return subprocess.run([*command, mode], capture_output=True, text=True,
                                  encoding="utf-8", timeout=30)

        for filename in ("scripts/synthetic_probe.py", "api_server.py"):
            source = target / filename
            source.write_text("safe = 1\n", encoding="utf-8")
            assert run("lint").returncode == 0
            assert run("syntax").returncode == 0
            source.write_text("def probe():\n    return undefined_quality_canary\n", encoding="utf-8")
            result = run("lint")
            assert result.returncode != 0 and "F821" in result.stdout, result.stdout + result.stderr
            source.write_text("def broken(:\n", encoding="utf-8")
            result = run("syntax")
            assert result.returncode != 0 and "SyntaxError" in result.stderr, result.stdout + result.stderr
            source.write_text("import subprocess\ndef dangerous(command):\n    subprocess.run(command, shell=True)\n", encoding="utf-8")
            result = run("security")
            assert result.returncode != 0 and "B602" in result.stdout, result.stdout + result.stderr
            source.write_text("safe = 1\n", encoding="utf-8")
    print("Verified real F821, syntax and Bandit failures in scripts and root entrypoints; synthetic code was never executed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
