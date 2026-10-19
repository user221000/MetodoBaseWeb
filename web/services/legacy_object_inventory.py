"""Read-only, globally scoped legacy reference inventory; never a migration.

Even unique, readable files require historical provenance review. File names
could have been overwritten before this tool existed. The private JSONL report
contains source identifiers/relative names; loggers receive only stable codes.
"""
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import stat

from sqlalchemy import select, text

MAX_INDEX_PATHS = 100_000
MAX_PDF_BYTES = 64 * 1024 * 1024
MAX_LOGO_BYTES = 2 * 1024 * 1024
REPO_ROOT = Path(__file__).resolve().parents[2]


class InventoryError(RuntimeError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _hash(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), default=str)


def _links(path):
    return any(part.is_symlink() or getattr(part, 'is_junction', lambda: False)()
        for part in (path, *path.parents))


@dataclass(frozen=True)
class InventoryRoots:
    pdf: Path
    logo: Path

    def validate(self):
        for path in (self.pdf, self.logo):
            if (not path.is_absolute() or _links(path) or not path.is_dir()
                    or path.resolve() == Path(path.resolve().anchor)):
                raise InventoryError('invalid_source_root')
        pdf, logo = self.pdf.resolve(), self.logo.resolve()
        if tuple(map(os.path.normcase,logo.parts[-4:])) != ('web', 'static', 'uploads', 'logos'):
            raise InventoryError('invalid_legacy_logo_root')
        if (pdf.is_relative_to(logo) or logo.is_relative_to(pdf)
                or any(pdf.is_relative_to(root.resolve()) for root in (REPO_ROOT/'static',REPO_ROOT/'web/static'))):
            raise InventoryError('pdf_root_must_be_private')
        return InventoryRoots(pdf, logo)


def validate_manifest_destination(path, roots):
    """Reject overwrite, source/public/repository placement before connecting."""
    path = Path(path)
    if not path.is_absolute() or _links(path) or path.exists() or not path.parent.is_dir():
        raise InventoryError('invalid_private_manifest_destination')
    parent = path.parent.resolve()
    if any(parent.is_relative_to(root) for root in (roots.pdf,roots.logo,REPO_ROOT.resolve())):
        raise InventoryError('manifest_destination_is_not_separate')
    if os.name != 'nt' and stat.S_IMODE(parent.stat().st_mode) & 0o077:
        raise InventoryError('manifest_directory_requires_private_permissions')
    return parent / path.name


@contextmanager
def readonly_inventory_connection(engine):
    """One snapshot for both passes, with explicit global visibility on PG."""
    with engine.connect() as connection:
        if connection.dialect.name == 'postgresql':
            connection = connection.execution_options(isolation_level='REPEATABLE READ')
            transaction = connection.begin()
            try:
                connection.execute(text('SET TRANSACTION READ ONLY'))
                role = connection.execute(text('SELECT rolsuper,rolbypassrls FROM pg_catalog.pg_roles WHERE rolname=current_user')).one()
                if not any(role):
                    raise InventoryError('global_visibility_required')
                if connection.scalar(text('SELECT pg_catalog.current_schema()')) != 'public':
                    raise InventoryError('unexpected_source_schema')
                yield connection
            finally:
                transaction.rollback()
        elif connection.dialect.name == 'sqlite':
            previous = connection.exec_driver_sql('PRAGMA query_only').scalar_one()
            connection.exec_driver_sql('PRAGMA query_only=ON')
            connection.commit()
            connection.exec_driver_sql('BEGIN')
            try:
                yield connection
            finally:
                connection.rollback()
                connection.exec_driver_sql('PRAGMA query_only=' + ('ON' if previous else 'OFF'))
                connection.commit()
        else:
            raise InventoryError('unsupported_inventory_database')


def _references(connection, page_size):
    from web.database.models import Cliente, GymProfile, PlanGenerado
    plan = select(PlanGenerado.id.label('row_id'),PlanGenerado.gym_id.label('tenant_id'),
        PlanGenerado.id_cliente.label('client_id'),PlanGenerado.ruta_pdf.label('legacy_path'),
        PlanGenerado.pdf_object_id.label('new_reference'),PlanGenerado.deleted_at.label('deleted_at'),
        PlanGenerado.fecha_generacion.label('source_date'),Cliente.gym_id.label('client_tenant'),
        Cliente.id_cliente.label('client_present'),Cliente.deleted_at.label('client_deleted')).outerjoin(
            Cliente,Cliente.id_cliente==PlanGenerado.id_cliente)
    logo = select(GymProfile.id.label('row_id'),GymProfile.gym_id.label('tenant_id'),
        GymProfile.logo_url.label('legacy_path'),GymProfile.logo_object_id.label('new_reference'),
        GymProfile.updated_at.label('source_date'))
    for kind,statement,column in (('plan_pdf',plan,PlanGenerado.id),('gym_logo',logo,GymProfile.id)):
        last = None
        while True:
            query = statement.order_by(column).limit(page_size)
            if last is not None:
                query = query.where(column > last)
            with connection.execute(query) as result:
                rows = result.mappings().all()
            if not rows:
                break
            for row in rows:
                yield kind,dict(row)
            last = rows[-1]['row_id']


def _path(kind, raw, roots):
    root = roots.pdf if kind == 'plan_pdf' else roots.logo
    issues = []
    if not isinstance(raw,str) or not raw or '\x00' in raw:
        return None,None,None,['invalid_path']
    if kind == 'gym_logo':
        prefix='/static/uploads/logos/'
        if not raw.startswith(prefix):
            return None,None,None,['unsupported_logo_reference']
        raw=raw[len(prefix):]
        if any(char in raw for char in ('\\','?','#','%')) or raw.startswith('/'):
            return None,None,None,['invalid_logo_path']
    if os.name != 'nt' and (PureWindowsPath(raw).drive or '\\' in raw):
        return None,None,None,['foreign_platform_path']
    relative=Path(raw)
    if '..' in relative.parts:
        issues.append('path_traversal')
    candidate=relative if relative.is_absolute() else root/relative
    try:
        resolved=candidate.resolve(strict=False)
        key=_hash(os.path.normcase(os.path.normpath(str(resolved))))
        inside=resolved.is_relative_to(root) and resolved!=root
        path_relative=resolved.relative_to(root).as_posix() if inside else None
        if not inside:
            issues.append('outside_root')
        if _links(candidate):
            issues.append('symlink_or_junction')
        return candidate,path_relative,key,issues
    except (OSError,ValueError,RuntimeError):
        return None,None,None,['invalid_path']


def _stat_fingerprint(value):
    return (value.st_dev,value.st_ino,value.st_size,value.st_mtime_ns,value.st_ctime_ns)


def _same_open_file(fd_stat,path_stat):
    # Windows can report creation/change time differently in stat and fstat.
    # Compare their common identity/size/mtime here; retain the complete ctime
    # comparison BEFORE/AFTER within each API rather than mixing its clocks.
    return _stat_fingerprint(fd_stat)[:4]==_stat_fingerprint(path_stat)[:4]


def _opened_path(fd):
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        import msvcrt
        function=ctypes.windll.kernel32.GetFinalPathNameByHandleW
        function.argtypes=[wintypes.HANDLE,wintypes.LPWSTR,wintypes.DWORD,wintypes.DWORD]
        function.restype=wintypes.DWORD
        buffer=ctypes.create_unicode_buffer(32768)
        length=function(msvcrt.get_osfhandle(fd),buffer,len(buffer),0)
        if not length or length>=len(buffer):
            raise InventoryError('unverifiable_open_file')
        path=buffer.value
        if path.startswith('\\\\?\\UNC\\'):
            path='\\\\'+path[8:]
        elif path.startswith('\\\\?\\'):
            path=path[4:]
        return Path(path).resolve(strict=True)
    proc=Path('/proc/self/fd')/str(fd)
    return proc.resolve(strict=True) if proc.exists() else None


def _read_file(path, root, kind):
    """Bounded hashing; FD identity and pathname must remain the same file."""
    limit=MAX_PDF_BYTES if kind=='plan_pdf' else MAX_LOGO_BYTES
    try:
        if _links(path) or not path.resolve(strict=True).is_relative_to(root):
            return {'issues':['symlink_or_junction']}
        before_path=path.stat(follow_symlinks=False)
        if not stat.S_ISREG(before_path.st_mode):
            return {'issues':['not_regular_file']}
        if not 0 < before_path.st_size <= limit:
            return {'issues':['invalid_size']}
        flags=os.O_RDONLY|getattr(os,'O_BINARY',0)|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_NONBLOCK',0)
        fd=os.open(path,flags)
        try:
            before=os.fstat(fd)
            opened=_opened_path(fd)
            if (opened is not None and not opened.is_relative_to(root)) or _links(path):
                return {'issues':['symlink_or_junction']}
            if not _same_open_file(before,before_path) or not stat.S_ISREG(before.st_mode):
                return {'issues':['file_changed']}
            digest=hashlib.sha256()
            size=0
            header=b''
            logo=[]
            while size<=limit:
                block=os.read(fd,min(1024*1024,limit+1-size))
                if not block:
                    break
                size+=len(block)
                digest.update(block)
                header=(header+block[:5])[:5]
                if kind=='gym_logo':
                    logo.append(block)
            after=os.fstat(fd)
            after_path=path.stat(follow_symlinks=False)
            if (_stat_fingerprint(before)!=_stat_fingerprint(after)
                    or _stat_fingerprint(before_path)!=_stat_fingerprint(after_path)
                    or not _same_open_file(after,after_path)
                    or _links(path) or not path.resolve(strict=True).is_relative_to(root)):
                return {'issues':['file_changed']}
            if size!=before.st_size or size>limit:
                return {'issues':['file_changed']}
            content_type=None
            if kind=='plan_pdf':
                if path.suffix.lower()!='.pdf' or header!=b'%PDF-':
                    return {'issues':['invalid_file_type']}
                content_type='application/pdf'
            else:
                from web.services.gym_logos import normalize_logo
                try:
                    _,content_type=normalize_logo(b''.join(logo),path.suffix.lower())
                except ValueError:
                    return {'issues':['invalid_file_type']}
            return {'issues':[],'byte_size':size,'sha256':digest.hexdigest(),
                'content_type':content_type,'file_fingerprint':_hash(_canonical(_stat_fingerprint(after)))}
        finally:
            os.close(fd)
    except FileNotFoundError:
        return {'issues':['missing_file']}
    except (OSError,ValueError,InventoryError):
        return {'issues':['file_unavailable']}


def write_inventory(connection,roots,output,*,page_size=250,max_paths=MAX_INDEX_PATHS):
    """Write JSONL with complete/incomplete footer; no entry grants migration."""
    roots=roots.validate()
    output=validate_manifest_destination(output,roots)
    if not 1<=page_size<=1000 or not 1<=max_paths<=1_000_000:
        raise InventoryError('invalid_inventory_bounds')
    if connection.dialect.name=='postgresql':
        if (connection.scalar(text('SHOW transaction_read_only'))!='on'
                or connection.scalar(text('SHOW transaction_isolation'))!='repeatable read'
                or connection.scalar(text('SELECT pg_catalog.current_schema()'))!='public'
                or not any(connection.execute(text('SELECT rolsuper,rolbypassrls FROM pg_catalog.pg_roles WHERE rolname=current_user')).one())):
            raise InventoryError('global_readonly_snapshot_required')
    elif (connection.exec_driver_sql('PRAGMA query_only').scalar_one()!=1
            or not connection.connection.driver_connection.in_transaction):
        raise InventoryError('readonly_snapshot_required')
    revisions=connection.execute(text('SELECT version_num FROM alembic_version')).scalars().all()
    if len(revisions)!=1:
        raise InventoryError('single_source_revision_required')
    revision=revisions[0]
    url=connection.engine.url
    identity=getattr(connection.engine,'_legacy_inventory_source_identity',
        (connection.dialect.name,url.host,url.port or (5432 if connection.dialect.name=='postgresql' else None),url.database))
    if identity[0]=='sqlite' and identity[3]:
        identity=(*identity[:3],os.path.normcase(str(Path(identity[3]).resolve())))
    counts={'scanned_rows':0,'legacy_entries':0,'excluded_new_references':0,'empty_legacy_references':0}
    flags=os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0)
    with os.fdopen(os.open(output,flags,0o600),'w',encoding='utf-8',newline='\n') as stream:
        def emit(record):
            stream.write(json.dumps(record,ensure_ascii=False,sort_keys=True)+'\n')
        emit({'record':'header','format':1,'status':'review_required','source_revision':revision,
            'source_database_fingerprint':_hash(_canonical(identity)),
            'created_at':datetime.now(timezone.utc).isoformat(),'dialect':connection.dialect.name,
            'root_fingerprints':{name:_hash(os.path.normcase(str(path))) for name,path in (('pdf',roots.pdf),('logo',roots.logo))},
            'coverage':{'snapshot':'repeatable read/read only or explicit SQLite read-only transaction',
                'tables':['planes_generados','gym_profiles'],'duplicates':'all legacy path values, including shadowed/deleted references',
                'new_references':'excluded from entries and file reads','historical_provenance':'unverified for every entry'},
            'technical_limits':{'page_size':page_size,'max_distinct_path_hashes':max_paths}})
        try:
            index={}
            for kind,row in _references(connection,page_size):
                counts['scanned_rows']+=1
                if row['new_reference']:
                    counts['excluded_new_references']+=1
                if not row['legacy_path']:
                    counts['empty_legacy_references']+=1
                    continue
                _,_,key,_=_path(kind,row['legacy_path'],roots)
                if key is not None:
                    if key not in index and len(index)>=max_paths:
                        raise InventoryError('path_index_limit_exceeded')
                    index[key]=index.get(key,0)+1
            for kind,row in _references(connection,page_size):
                if row['new_reference'] or not row['legacy_path']:
                    continue
                path,relative,key,issues=_path(kind,row['legacy_path'],roots)
                if key is not None and index[key]>1:
                    issues.append('ambiguous_path')
                if kind=='plan_pdf':
                    if row['client_present'] is None:
                        issues.append('missing_client')
                    elif row['client_tenant']!=row['tenant_id']:
                        issues.append('mixed_tenant_reference')
                    if row['deleted_at'] is not None:
                        issues.append('deleted_plan')
                    if row['client_deleted'] is not None:
                        issues.append('deleted_client')
                file={'byte_size':None,'sha256':None,'file_fingerprint':None}
                if not issues:
                    file.update(_read_file(path,roots.pdf if kind=='plan_pdf' else roots.logo,kind))
                    issues.extend(file.pop('issues'))
                # Ambiguous paths are never read/assigned to a winning row.
                emit({'record':'entry','status':'review_required','kind':kind,'tenant_id':row['tenant_id'],
                    'row_id':row['row_id'],'source_table':'planes_generados' if kind=='plan_pdf' else 'gym_profiles',
                    'root':'pdf' if kind=='plan_pdf' else 'logo','relative_path':relative,
                    'source_fingerprint':_hash(_canonical(row)), 'path_reference_count':index.get(key,0),
                    'issues':['historical_provenance_unverified',*sorted(set(issues))],**file})
                counts['legacy_entries']+=1
            emit({'record':'footer','complete':True,'status':'review_required',**counts})
            stream.flush()
            os.fsync(stream.fileno())
            return {'complete':True,**counts}
        except Exception as error:
            code=error.code if isinstance(error,InventoryError) else 'inventory_failed'
            emit({'record':'footer','complete':False,'status':'review_required','error_code':code,**counts})
            stream.flush()
            raise InventoryError(code) from None
