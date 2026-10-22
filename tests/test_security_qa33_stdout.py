"""Valid summary records cannot authorize additional scanner stdout."""
import pytest

from scripts import scan_secrets as scanner
from tests.test_security_qa33_scanner_completion import CANARY, FULL, scenario


def test_unexpected_stdout_is_refused_even_with_two_valid_completion_records(tmp_path, monkeypatch, capsys):
    report, _ = scenario(tmp_path, monkeypatch, stderr=FULL + "6:47PM WRN leaks found: 1\n")
    mocked = scanner.subprocess.run

    def extra_output(command, **options):
        reply = mocked(command, **options)
        if command[0] != "git" and command[1] != "version":
            reply.stdout = CANARY.encode()
        return reply

    monkeypatch.setattr(scanner.subprocess, "run", extra_output)
    with pytest.raises(RuntimeError, match="output withheld") as failure:
        scanner.main()
    captured = capsys.readouterr()
    assert CANARY not in str(failure.value) + captured.out + captured.err
    assert not report.exists()
