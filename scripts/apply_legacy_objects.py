"""Plan by default. Apply only reviewed operator mappings in maintenance.

This CLI does not prove historical ownership or stop other writers. Real-data
use needs external provenance, an actual maintenance window and durable private
journal/storage chosen by the operator. It never reads application DB settings.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from contextlib import suppress
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

from scripts.inventory_legacy_objects import create_inventory_engine
from web.services import legacy_object_apply as apply
from web.services.legacy_object_inventory import InventoryRoots
from web.storage.configuration import ObjectStoreConfiguration, build_object_store

GIT_EXECUTABLE = Path(shutil.which('git') or '').resolve()


def source_check():
    if not GIT_EXECUTABLE.is_file():
        raise apply.ApplyError('source_tool_unavailable')
    environment = {key: value for key, value in os.environ.items() if not key.upper().startswith('GIT_')}
    environment.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
        GIT_NO_LAZY_FETCH='1', GIT_TERMINAL_PROMPT='0', GIT_OPTIONAL_LOCKS='0')
    head = subprocess.check_output([str(GIT_EXECUTABLE), '--no-replace-objects', 'rev-parse', 'HEAD'],
        cwd=ROOT, timeout=5, stderr=subprocess.DEVNULL, shell=False, env=environment).decode().strip()
    if not re.fullmatch('[a-f0-9]{40}', head):
        raise apply.ApplyError('source_tool_unavailable')
    return apply.source_binding(head)


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise apply.ApplyError('invalid_apply_arguments')


def create_target(raw_url, expected, *, readonly):
    # Reuse the existing explicit authority/query validation before any connect.
    validation = create_inventory_engine(raw_url, expected)
    if readonly:
        return validation
    validation.dispose()
    if raw_url.startswith('postgres://'):
        raw_url = 'postgresql+psycopg2://' + raw_url[len('postgres://'):]
    elif raw_url.startswith('postgresql://'):
        raw_url = 'postgresql+psycopg2://' + raw_url[len('postgresql://'):]
    url = make_url(raw_url)
    if url.drivername.startswith('sqlite'):
        if apply.inventory._links(Path(url.database)):
            raise apply.ApplyError('database_binding_changed')
        engine = create_engine(url, poolclass=NullPool, hide_parameters=True, connect_args={'timeout': 5})
        @event.listens_for(engine, 'connect')
        def foreign_keys(connection, _record):
            connection.execute('PRAGMA foreign_keys=ON')
        return engine
    return create_engine(url, poolclass=NullPool, hide_parameters=True,
        connect_args={'connect_timeout': 5, 'options': '-c statement_timeout=10000 -c lock_timeout=5000'})


def main(argv=None):
    engine = None
    try:
        parser = Parser(description=__doc__)
        parser.add_argument('--manifest', required=True, type=Path)
        parser.add_argument('--inventory', required=True, type=Path)
        parser.add_argument('--storage', required=True, type=Path)
        parser.add_argument('--pdf-root', required=True, type=Path)
        parser.add_argument('--logo-root', required=True, type=Path)
        parser.add_argument('--expected-database', required=True)
        parser.add_argument('--url-env', default='LEGACY_APPLY_DATABASE_URL')
        parser.add_argument('--apply', action='store_true')
        parser.add_argument('--approval', type=Path)
        parser.add_argument('--journal', type=Path)
        parser.add_argument('--deadline-seconds', type=int, default=120)
        args = parser.parse_args(argv)
        if (args.apply and (args.approval is None or args.journal is None)
                or not args.apply and (args.approval is not None or args.journal is not None)):
            raise apply.ApplyError('operator_admission_required')
        values = apply._json(apply._read(args.storage))
        if values.get('local_root') is not None:
            values['local_root'] = Path(values['local_root'])
        configuration = ObjectStoreConfiguration(**values)
        bundle = apply.Bundle(args.manifest, args.inventory, InventoryRoots(args.pdf_root, args.logo_root),
            configuration, storage_path=args.storage, source_check=source_check)
        admission = apply.Admission(bundle, args.approval, seconds=args.deadline_seconds) if args.apply else None
        raw_url = os.environ.get(args.url_env, '')
        if not raw_url:
            raise apply.ApplyError('explicit_database_required')
        engine = create_target(raw_url, args.expected_database, readonly=not args.apply)
        if admission is not None:
            admission.check()
        store = build_object_store(configuration) if args.apply else None
        result = apply.run(engine, bundle, approval=args.approval if args.apply else None,
            journal=args.journal, store=store, seconds=args.deadline_seconds)
        engine.dispose()
        engine = None
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception:  # noqa: BLE001 -- CLI privacy boundary returns only a fixed failure.
        # No traceback, argv, paths, candidate data, SDK detail or URL reflection.
        print(json.dumps({'complete': False, 'status': 503, 'code': 'legacy_apply_unavailable'}), file=sys.stderr)
        return 2
    finally:
        if engine is not None:
            # Success already required dispose above; this is failure cleanup.
            with suppress(Exception):
                engine.dispose()


if __name__ == '__main__':
    raise SystemExit(main())
