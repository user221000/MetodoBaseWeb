"""Native-first finite control check; never call the legacy none-cursor path."""
from contextlib import closing
import os


def native_generation(value,profile):
    from tests.billing13_legacy_apply37_pg_contract import (windows_process_identity,
        linux_process_identity,pg_binary_directory)
    expected=value['generation']
    if os.name=='nt':
        created,executable=windows_process_identity(expected['postmaster_pid'])
        if (created!=expected['master_creation_filetime_100ns']
                or executable!=pg_binary_directory(profile)/'postgres.exe'):
            raise ValueError('Root39 native PostgreSQL identity differs before control connect')
    else:
        pg_binary_directory(profile);linux_process_identity(expected)


def check_control_generation(value,profile):
    # PID/birth/executable, or Linux boot/start/executable, precedes any socket.
    native_generation(value,profile)
    import psycopg2
    from tests.billing13_legacy_apply37_pg_contract import check_generation
    url=profile['METODOBASE_TEST_MIGRATOR_URL'].replace('postgresql+psycopg2://','postgresql://',1)
    with closing(psycopg2.connect(url,connect_timeout=5)) as control:
        control.autocommit=True
        with control.cursor() as cursor:
            # Approved c6 code rechecks native identity and generation on THIS
            # exact cursor, then native identity again, with no fallback path.
            check_generation(value,profile,cursor=cursor)
