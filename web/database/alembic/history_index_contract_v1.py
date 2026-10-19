"""Versioned physical ordering contract for the personal history index only."""
from sqlalchemy import text


INDEX_NAME = 'ix_planes_gym_cliente_history'
_COLUMNS = ['gym_id', 'id_cliente', 'fecha_generacion', 'id']


def create_history_index(connection) -> None:
    """Add the reviewed live-row index inside the migration's transaction.

    PostgreSQL needs explicit NULLS LAST on descending timestamps. SQLite's
    descending index already places NULL last and rejects NULLS LAST in DDL.
    Missing/duplicate objects fail; this is never a runtime repair fallback.
    """
    if connection.dialect.name == 'postgresql':
        order = 'fecha_generacion DESC NULLS LAST, id DESC NULLS LAST'
    elif connection.dialect.name == 'sqlite':
        order = 'fecha_generacion DESC, id DESC'
    else:
        raise RuntimeError('History ordering requires a reviewed database dialect')
    connection.exec_driver_sql(
        'CREATE INDEX ix_planes_gym_cliente_history ON planes_generados '
        '(gym_id, id_cliente, ' + order + ') WHERE deleted_at IS NULL'
    )


def _predicate(value: str | None) -> str | None:
    """Accept only the two equivalent renderings of this single predicate."""
    if value in ('deleted_at IS NULL', '(deleted_at IS NULL)'):
        return 'deleted_at IS NULL'
    return value


def history_index_signature(connection) -> dict | None:
    """Inspect physical sort direction, predicate and index validity, read-only.

    The immutable structural v1 schema format omits sort/null direction. This
    additional contract is adopted only by revision30 and later, leaving all
    historical snapshots and validators unchanged. No business rows are read.
    """
    dialect = connection.dialect.name
    if dialect == 'postgresql':
        row = connection.execute(text('''
            SELECT i.indisunique, i.indisvalid, i.indisready,
                   i.indnkeyatts, i.indnatts, i.indoption::text,
                   pg_get_expr(i.indpred,i.indrelid),am.amname,
                   ARRAY(SELECT a.attname
                         FROM unnest(i.indkey) WITH ORDINALITY AS k(attnum,position)
                         JOIN pg_attribute a ON a.attrelid=i.indrelid AND a.attnum=k.attnum
                         ORDER BY k.position),
                   ARRAY(SELECT CASE WHEN k.oid=0 THEN NULL
                                     ELSE n.nspname||'.'||c.collname END
                         FROM unnest(i.indcollation) WITH ORDINALITY AS k(oid,position)
                         LEFT JOIN pg_collation c ON c.oid=k.oid
                         LEFT JOIN pg_namespace n ON n.oid=c.collnamespace
                         ORDER BY k.position),
                   ARRAY(SELECT n.nspname||'.'||c.opcname
                         FROM unnest(i.indclass) WITH ORDINALITY AS k(oid,position)
                         JOIN pg_opclass c ON c.oid=k.oid
                         JOIN pg_namespace n ON n.oid=c.opcnamespace
                         ORDER BY k.position)
            FROM pg_index i
            JOIN pg_class idx ON idx.oid=i.indexrelid
            JOIN pg_class parent ON parent.oid=i.indrelid
            JOIN pg_namespace ns ON ns.oid=parent.relnamespace
            JOIN pg_am am ON am.oid=idx.relam
            WHERE ns.nspname=current_schema() AND parent.relname='planes_generados'
              AND idx.relname=:name
        '''), {'name': INDEX_NAME}).one_or_none()
        if row is None:
            return None
        return {
            'dialect': dialect, 'name': INDEX_NAME, 'columns': list(row[8]),
            'unique': row[0], 'valid': row[1], 'ready': row[2],
            'key_columns': row[3], 'all_columns': row[4],
            'indoption': [int(value) for value in row[5].split()],
            'predicate': _predicate(row[6]), 'method': row[7],
            'collations': list(row[9]), 'operator_classes': list(row[10]),
        }
    if dialect == 'sqlite':
        row = connection.execute(text(
            "SELECT sql FROM sqlite_master WHERE type='index' "
            "AND tbl_name='planes_generados' AND name=:name"
        ), {'name': INDEX_NAME}).one_or_none()
        if row is None:
            return None
        listed = [r for r in connection.exec_driver_sql("PRAGMA index_list('planes_generados')")
                  if r[1] == INDEX_NAME]
        if len(listed) != 1:
            raise RuntimeError('History index catalogue is ambiguous')
        keys = [r for r in connection.exec_driver_sql(
            "PRAGMA index_xinfo('ix_planes_gym_cliente_history')"
        ) if r[5]]
        return {
            'dialect': dialect, 'name': INDEX_NAME,
            'columns': [r[2] for r in keys],
            'descending': [bool(r[3]) for r in keys],
            'collations': [r[4] for r in keys],
            'unique': bool(listed[0][2]), 'partial': bool(listed[0][4]),
            'predicate': _predicate(row[0].partition(' WHERE ')[2] or None),
        }
    raise RuntimeError('History ordering requires a reviewed database dialect')


def expected_history_index(dialect: str) -> dict:
    """Return the closed ordering definition used to freeze the new target."""
    common = {'dialect': dialect, 'name': INDEX_NAME, 'columns': list(_COLUMNS),
              'unique': False, 'predicate': 'deleted_at IS NULL'}
    if dialect == 'postgresql':
        return {**common, 'valid': True, 'ready': True, 'key_columns': 4,
                'all_columns': 4, 'indoption': [0, 0, 1, 1], 'method': 'btree',
                'collations': ['pg_catalog.default', 'pg_catalog.default', None, None],
                'operator_classes': ['pg_catalog.text_ops', 'pg_catalog.text_ops',
                                     'pg_catalog.timestamp_ops', 'pg_catalog.int4_ops']}
    if dialect == 'sqlite':
        return {**common, 'descending': [False, False, True, True],
                'collations': ['BINARY'] * 4, 'partial': True}
    raise RuntimeError('History ordering requires a reviewed database dialect')
