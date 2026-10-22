"""Separate PG27 runner; --plan-only is AST-only, no collection/SQL/services."""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import traceback
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.scan_secrets import _private_evidence
from tests.billing13_legacy_apply37_pg_contract import (
    MODULE,
    build_contract,
    check_generation,
    phase,
    private_workspace,
    require_ack,
    source_pins,
    temporary_root,
)
from tests.ci_web37.evidence import boundary_before_payload, seal, write


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--private', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--plan-only', action='store_true')
    parser.add_argument('--pg-profile', type=Path)
    parser.add_argument('--pg-generation', type=Path)
    parser.add_argument('--lease-ack', type=Path)
    args = parser.parse_args()
    workspace = private_workspace()
    temporary = temporary_root()
    if (any(not path.is_absolute() or not path.resolve().is_relative_to(workspace) or path.exists()
            for path in (args.private, args.output))
            or Path(tempfile.gettempdir()).resolve() != temporary):
        parser.error('Fresh private/output and exact process TEMP boundary are required')
    if not args.plan_only and any(path is None for path in (args.pg_profile, args.pg_generation, args.lease_ack)):
        parser.error('New explicit source/profile/generation-bound Root ACK is required')
    private = _private_evidence(args.private)
    acl = boundary_before_payload(private)
    before = source_pins()
    write(private / 'sources-before.json', before)
    value = phase()
    write(private / 'plan.json', value)
    result = {'accepted': False, 'scope': 'prepared_PG27_AST_only' if args.plan_only else 'separate_current37_PG27',
        'PostgreSQL_executed': False, 'case_count': 27, 'UUID_budget': 1,
        'legacy429_or53_replayed': False, 'Desktop': False, 'Chrome': False, 'VM': False, 'Redis': False,
        'real_provider_calls': False}
    leases = environment = quiet_before = pg_before = roles_before = pg_bin = None
    try:
        if args.plan_only:
            result['accepted'] = True
        else:
            from tests.ci_google33.run_postgres import photo, role_catalog
            from tests.ci_web37.pg_lease import profile
            from tests.ci_web37.reports import require_exact_junit
            from tests.ci_web37.run_postgres import audit_leases
            from tests.ci_web37.run_web import environment_photo, execute
            contract = build_contract(args.pg_profile, args.pg_generation)
            require_ack(args.lease_ack, contract)
            write(private / 'lease-contract.json', contract)
            environment = dict(os.environ, PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1', PYTHON_DOTENV_DISABLED='1')
            for key in list(environment):
                upper = key.upper()
                if (upper == 'DATABASE_URL' or upper.endswith('_DATABASE_URL') or upper.startswith(('AWS_', 'S3_', 'COVERAGE_'))
                        or any(name in upper for name in ('STRIPE', 'MERCADOPAGO', 'SMTP', 'RESEND', 'SENTRY', 'GOOGLE_CLIENT', 'OPENAI_API'))):
                    environment.pop(key, None)
            environment.update(profile(args.pg_profile, expected_sha256=contract['profile_sha256']))
            quiet_before = environment_photo()
            write(private / 'environment-before.json', quiet_before)
            result['pip_before'] = execute([sys.executable, '-m', 'pip', 'check'], ROOT, environment, private / 'pip-before.private.log')
            if result['pip_before'] != 0:
                raise ValueError('Dependency consistency failed before the new PG27 phase')
            pg_bin = Path(environment['METODOBASE_TEST_PG_BIN']).resolve(strict=True)
            pg_before = photo(ROOT, pg_bin)
            write(private / 'PG-before.json', pg_before)
            require_ack(args.lease_ack, contract)
            check_generation(contract, environment)  # Process identity before the first SQL/role query.
            roles_before = role_catalog(environment)
            write(private / 'roles-before.private.json', roles_before)
            lease_root = _private_evidence(temporary / ('metodobase-account37-author-pg-b13-r07-' + uuid.uuid4().hex))
            leases = lease_root / 'leases'
            leases.mkdir()
            (private / 'witnesses').mkdir()
            journal = private / 'execution-journal'
            journal.mkdir()
            environment.update(_METODOBASE_TEST_ROOT=str(temporary / ('metodobase-test-b13-r07-' + uuid.uuid4().hex)),
                METODOBASE_TEST_REDIS_URL='', ACCOUNT37_PRIVATE_LEASES=str(leases), B13_R07_PG_PRIVATE=str(private),
                B13_R07_PG_PROFILE=str(args.pg_profile.resolve()), B13_R07_PG_GENERATION=str(args.pg_generation.resolve()),
                B13_R07_PG_ACK=str(args.lease_ack.resolve()))
            argv = [sys.executable, '-B', '-X', 'utf8', 'tests/run_isolated.py', MODULE,
                '-p', 'tests.ci_web37.scope', '--web37-execution-journal', str(journal),
                '-q', '--tb=short', '--basetemp=' + str(private / 'pytest-data'), '--junitxml=' + str(private / 'pytest.xml')]
            write(private / 'command.json', argv)
            require_ack(args.lease_ack, contract)
            result['PostgreSQL_executed'] = True
            result['pytest_exit'] = execute(argv, ROOT, environment, private / 'pytest.private.log')
            expected = [[MODULE.removesuffix('.py').replace('/', '.'), node.split('::', 1)[1]] for node in value['nodeids']]
            require_exact_junit((private / 'pytest.xml').read_bytes(), expected)
            result['accepted'] = result['pytest_exit'] == 0
    except Exception as error:  # noqa: BLE001 -- rejected phase is retained privately, never a fabricated pass.
        (private / 'runner-error.private.log').write_text(traceback.format_exc(), encoding='utf8')
        result.update(accepted=False, error_class=type(error).__name__)
    finally:
        if leases is not None:
            try:
                result['normally_closed_UUIDs_fresh_absent'] = audit_leases(leases, environment)
                if result['normally_closed_UUIDs_fresh_absent'] != 1:
                    raise ValueError('The new phase missed/exceeded its single UUID')
                for path in leases.glob('lease-*.json'):
                    (private / path.name).write_bytes(path.read_bytes())
            except Exception as error:  # noqa: BLE001 -- retain own lease; no FORCE/terminate/foreign cleanup.
                (private / 'cleanup-error.private.log').write_text(traceback.format_exc(), encoding='utf8')
                result.update(accepted=False, cleanup_error_class=type(error).__name__)
        if quiet_before is not None:
            quiet_after = environment_photo()
            write(private / 'environment-after.json', quiet_after)
            result['pip_after'] = execute([sys.executable, '-m', 'pip', 'check'], ROOT, environment, private / 'pip-after.private.log')
            result['source_packages_binaries_quiet'] = quiet_before == quiet_after
            result['accepted'] = result['accepted'] and quiet_before == quiet_after and result.get('pip_before') == result['pip_after'] == 0
            if pg_before is not None and roles_before is not None:
                try:
                    check_generation(contract, environment)
                    pg_after, roles_after = photo(ROOT, pg_bin), role_catalog(environment)
                    write(private / 'PG-after.json', pg_after)
                    write(private / 'roles-after.private.json', roles_after)
                    result['PG_binaries_sources_packages_roles_quiet'] = pg_before == pg_after and roles_before == roles_after
                    result['accepted'] = result['accepted'] and result['PG_binaries_sources_packages_roles_quiet']
                except Exception as error:  # noqa: BLE001 -- uncertain generation/role/readback cannot be accepted.
                    (private / 'quiet-error.private.log').write_text(traceback.format_exc(), encoding='utf8')
                    result.update(accepted=False, quiet_error_class=type(error).__name__)
        after = source_pins()
        write(private / 'sources-after.json', after)
        result['selected_sources_quiet'] = before == after
        result['accepted'] = result['accepted'] and before == after
    print(json.dumps(seal(private, args.output, result, acl)))
    return int(not result['accepted'])


if __name__ == '__main__':
    raise SystemExit(main())
