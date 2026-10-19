"""Inventory only: no PUT, association changes, DDL or deletion.

Use an explicit private output directory and a dedicated audit connection,
preferably to an isolated restored database. Never falls back to application
credentials, environment files, SDK configuration or a production connection.
"""
import argparse
import json
import os
from pathlib import Path
import sqlite3
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool
from web.services.legacy_object_inventory import (InventoryError,InventoryRoots,
    readonly_inventory_connection,validate_manifest_destination,write_inventory)

TLS_OPTIONS={'sslmode','sslrootcert','sslcert','sslkey','sslcrl','sslcrldir',
    'ssl_min_protocol_version','ssl_max_protocol_version','channel_binding'}


class InventoryArgumentParser(argparse.ArgumentParser):
    def error(self,message):
        # argparse's default error includes untrusted argv (possibly a URL or
        # private filename). Usage/help remain available without echoing values.
        raise InventoryError('invalid_inventory_arguments')


def create_inventory_engine(raw_url,expected_database):
    """Validate target authority before engine construction or network access."""
    try:
        if raw_url.startswith('postgres://'):
            raw_url='postgresql+psycopg2://'+raw_url[len('postgres://'):]
        elif raw_url.startswith('postgresql://'):
            raw_url='postgresql+psycopg2://'+raw_url[len('postgresql://'):]
        url=make_url(raw_url)
        if url.drivername in {'sqlite','sqlite+pysqlite'}:
            if url.query or url.host or url.username or url.password or not url.database:
                raise InventoryError('invalid_sqlite_source')
            source=Path(url.database)
            if (not source.is_absolute() or source.is_symlink() or not source.is_file()
                    or str(source.resolve())!=expected_database):
                raise InventoryError('database_target_mismatch')
            # URI encoding comes from as_uri, never from database URL query args.
            uri=source.resolve().as_uri()+'?mode=ro'
            def connect():
                return sqlite3.connect(uri,uri=True)
            engine=create_engine('sqlite://',creator=connect,poolclass=NullPool,hide_parameters=True)
            engine._legacy_inventory_source_identity=('sqlite',None,None,str(source.resolve()))
            return engine
        if url.drivername!='postgresql+psycopg2':
            raise InventoryError('unsupported_database_driver')
        if (not url.host or not url.host.strip() or not url.username or not url.database
                or not expected_database or url.database!=expected_database):
            raise InventoryError('database_target_mismatch')
        if set(url.query)-TLS_OPTIONS or any(not isinstance(value,str) for value in url.query.values()):
            raise InventoryError('database_query_override_rejected')
        # Resolve/validate port before create_engine; no libpq authority defaults.
        if url.port is not None and not 1<=url.port<=65535:
            raise InventoryError('invalid_database_port')
        return create_engine(url,poolclass=NullPool,hide_parameters=True,
            connect_args={'connect_timeout':10,'options':'-c default_transaction_read_only=on'})
    except InventoryError:
        raise
    except Exception:
        raise InventoryError('invalid_database_source') from None


def main(argv=None):
    parser=InventoryArgumentParser(description=__doc__)
    parser.add_argument('--url-env',default='LEGACY_INVENTORY_DATABASE_URL')
    parser.add_argument('--expected-database',required=True)
    parser.add_argument('--pdf-root',required=True,type=Path)
    parser.add_argument('--logo-root',required=True,type=Path)
    parser.add_argument('--manifest',required=True,type=Path)
    parser.add_argument('--page-size',type=int,default=250)
    parser.add_argument('--max-paths',type=int,default=100000)
    engine=None
    try:
        args=parser.parse_args(argv)
        roots=InventoryRoots(args.pdf_root,args.logo_root).validate()
        manifest=validate_manifest_destination(args.manifest,roots)
        raw_url=os.environ.get(args.url_env,'')
        if not raw_url:
            raise InventoryError('explicit_inventory_database_required')
        if not 1<=args.page_size<=1000 or not 1<=args.max_paths<=1_000_000:
            raise InventoryError('invalid_inventory_bounds')
        engine=create_inventory_engine(raw_url,args.expected_database)
        with readonly_inventory_connection(engine) as connection:
            report=write_inventory(connection,roots,manifest,page_size=args.page_size,max_paths=args.max_paths)
        print(json.dumps(report,sort_keys=True))
        return 0
    except InventoryError as error:
        print(json.dumps({'complete':False,'error_code':error.code}),file=sys.stderr)
        return 2
    except Exception as error:
        print(json.dumps({'complete':False,'error_code':'inventory_failed','error_class':type(error).__name__}),file=sys.stderr)
        return 2
    finally:
        if engine is not None:
            engine.dispose()


if __name__=='__main__':
    raise SystemExit(main())
