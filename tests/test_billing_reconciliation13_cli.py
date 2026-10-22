"""CLI argument failures are opaque and stop before application imports or I/O."""
import builtins
import json

import pytest

from web import billing_reconciliation_cli as cli

MARKER = 'Synthetic-private-argument-value-2026'


def invoke_without_application_or_file_access(argv, monkeypatch):
    original_import = builtins.__import__
    def guarded_import(name, *args, **kwargs):
        if name.startswith(('web.services.', 'sqlalchemy', 'stripe', 'mercadopago')):
            pytest.fail('Argument processing imported the application or provider')
        return original_import(name, *args, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(builtins, '__import__', guarded_import)
        patch.setattr(cli.Path, 'open', lambda *_a, **_k: pytest.fail('Argument processing opened a file'))
        try:
            return cli.main(argv)
        except SystemExit as error:
            return error.code


@pytest.mark.parametrize('argv', [
    ['--manifest', 'not-opened', '--max-items', MARKER],
    ['--manifest', 'not-opened', '--deadline-seconds', MARKER],
    ['--manifest', 'not-opened', '--unknown-' + MARKER],
    ['--manifest', 'not-opened', '--cursor'],
    ['--cursor', MARKER],
], ids=['integer', 'float', 'unknown', 'missing-value', 'missing-required'])
def test_invalid_cli_arguments_are_fixed64_before_IO_or_application_import(argv, monkeypatch, capsys, caplog):
    assert invoke_without_application_or_file_access(argv, monkeypatch) == 64
    output = capsys.readouterr()
    assert json.loads(output.out) == {'code': 'reconciliation_invalid_input'}
    assert output.err == '' and MARKER not in output.out + output.err + caplog.text
    assert caplog.records == []


def test_help_remains_zero_with_usage_and_without_application_import_or_IO(monkeypatch, capsys, caplog):
    assert invoke_without_application_or_file_access(['--help'], monkeypatch) == 0
    output = capsys.readouterr()
    assert '--manifest' in output.out and output.err == '' and caplog.records == []
