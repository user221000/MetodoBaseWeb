"""Independent CLI parse failures must obey the documented opaque boundary."""
import json

import pytest

from web import billing_reconciliation_cli as cli


@pytest.mark.parametrize('option', ['--deadline-seconds', '--max-items'])
def test_invalid_typed_CLI_argument_is_not_reflected_and_returns_opaque64(option, capsys):
    marker = 'INERT-PRIVATE-OPERATOR-VALUE-7639'
    try:
        status = cli.main(['--manifest', 'not-opened', option, marker])
    except SystemExit as error:
        status = error.code
    output = capsys.readouterr()
    assert marker not in output.out + output.err
    assert status == 64 and json.loads(output.out) == {'code': 'reconciliation_invalid_input'}
    assert output.err == ''


def test_help_remains_available_without_importing_DB_or_reading_manifest(capsys):
    with pytest.raises(SystemExit) as result:
        cli.main(['--help'])
    assert result.value.code == 0
    output = capsys.readouterr()
    assert '--manifest' in output.out and output.err == ''
