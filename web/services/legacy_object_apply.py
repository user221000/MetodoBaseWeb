"""Bounded operator migration, never an HTTP authority or provenance detector.

The operator supplies reviewed ownership and a real writer-maintenance window.
Hashes and this program cannot establish either fact. Originals are read only;
only the private journal, pending metadata and explicit references are written.
"""
import hashlib
import json
import os
import subprocess
import time
from contextlib import contextmanager
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from web.database.tenant_context import current_tenant
from web.services import legacy_object_inventory as inventory
from web.services.legacy_object_apply_boundary import verify as _private
from web.storage.objects import ObjectDescriptor, authorize, describe

MAX_ENTRIES = 100
MAX_DOCUMENT = 2 * 1024 * 1024
MAX_TOTAL_BYTES = 128 * 1024 * 1024
MAX_DATABASE_ROWS = 100_000
SOURCE_PATHS = (
    'scripts/apply_legacy_objects.py', 'web/services/legacy_object_apply.py',
    'web/services/legacy_object_apply_boundary.py',
    'web/services/legacy_object_inventory.py', 'web/services/gym_logos.py',
    'web/database/models.py', 'web/database/tenant_context.py',
    'web/storage/objects.py', 'web/storage/local.py', 'web/storage/s3.py',
    'web/storage/configuration.py',
)


class ApplyError(RuntimeError):
    def __init__(self, code='legacy_apply_unavailable'):
        self.code = code
        super().__init__(code)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf8')


def source_binding():
    root = inventory.REPO_ROOT
    head = subprocess.check_output(['git', '--no-replace-objects', 'rev-parse', 'HEAD'], cwd=root).decode().strip()
    return {'commit': head, 'files_sha256': digest(canonical({name: digest((root / name).read_bytes())
        for name in SOURCE_PATHS}))}


def destination_binding(configuration):
    configuration.validate()
    values = asdict(configuration)
    if values['local_root'] is not None:
        values['local_root'] = str(Path(values['local_root']).resolve())
    # Bind credentials without storing them in the operator artifacts/journal.
    for key in ('access_key', 'secret_key', 'session_token'):
        values[key] = digest((values[key] or '').encode())
    return digest(canonical(values))


def _read(path):
    _private(path)
    return _bounded(path)


def _bounded(path):
    with Path(path).open('rb') as source:
        raw = source.read(MAX_DOCUMENT + 1)
    if len(raw) > MAX_DOCUMENT:
        raise ApplyError('artifact_budget_exceeded')
    return raw


def _json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ApplyError('duplicate_json_key')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda _: (_ for _ in ()).throw(ApplyError()))


def entry_key(entry):
    return digest(canonical(entry))


def _stamp(value):
    stamp = datetime.fromisoformat(value)
    if stamp.tzinfo is None:
        raise ApplyError('finite_window_required')
    return stamp.astimezone(UTC)


class Bundle:
    """Immutable reviewed mapping, with separately renewable operator approval."""
    def __init__(self, manifest, inventory_path, roots, configuration, *, storage_path=None):
        self.paths = (Path(manifest), Path(inventory_path), *([Path(storage_path)] if storage_path else []))
        self.raw = tuple(_read(path) for path in self.paths)
        self.roots = roots.validate()
        self.configuration = configuration
        self.manifest = _json(self.raw[0])
        records = [_json(line) for line in self.raw[1].splitlines()]
        if not 2 <= len(records) <= MAX_ENTRIES + 2:
            raise ApplyError('entry_budget_exceeded')
        self.header, self.footer = records[0], records[-1]
        self.entries = records[1:-1]
        if (self.header.get('record') != 'header' or self.header.get('format') != 1
                or self.footer.get('record') != 'footer' or self.footer.get('complete') is not True
                or self.footer.get('legacy_entries') != len(self.entries)
                or any(entry.get('record') != 'entry' for entry in self.entries)):
            raise ApplyError('complete_inventory_required')
        mapping = self.manifest
        root_pins = {name: inventory._hash(os.path.normcase(str(path)))
            for name, path in (('pdf', self.roots.pdf), ('logo', self.roots.logo))}
        if (set(mapping) != {'format', 'inventory_sha256', 'source', 'destination_sha256', 'entries'}
                or type(mapping['format']) is not int or mapping['format'] != 1
                or mapping['inventory_sha256'] != digest(self.raw[1])
                or mapping['source'] != source_binding()
                or mapping['destination_sha256'] != destination_binding(configuration)
                or self.header.get('root_fingerprints') != root_pins
                or self.header.get('source_revision') != '20261020_account_security'):
            raise ApplyError('artifact_binding_changed')
        decisions = mapping['entries']
        if (not isinstance(decisions, list) or len(decisions) != len(self.entries)
                or len({(entry['kind'], entry['row_id']) for entry in self.entries}) != len(self.entries)):
            raise ApplyError('complete_mapping_required')
        self.selected = []
        for entry, decision in zip(self.entries, decisions):
            if (set(decision) != {'entry_sha256', 'apply', 'provenance_reference'}
                    or decision['entry_sha256'] != entry_key(entry) or type(decision['apply']) is not bool):
                raise ApplyError('complete_mapping_required')
            if decision['apply']:
                reference = decision['provenance_reference']
                if (not isinstance(reference, str) or not 1 <= len(reference) <= 256
                        or entry.get('issues') != ['historical_provenance_unverified']
                        or entry.get('path_reference_count') != 1):
                    raise ApplyError('reviewed_provenance_required')
                self.selected.append(entry)
        if (not self.selected or len(self.selected) > MAX_ENTRIES
                or any(type(entry.get('byte_size')) is not int or entry['byte_size'] <= 0 for entry in self.selected)
                or sum(entry['byte_size'] for entry in self.selected) > MAX_TOTAL_BYTES):
            raise ApplyError('entry_budget_exceeded')
        self.binding = {'manifest_sha256': digest(self.raw[0]), 'inventory_sha256': digest(self.raw[1]),
            'source': mapping['source'], 'destination_sha256': mapping['destination_sha256']}

    def unchanged(self):
        if (any(_bounded(path) != raw for path, raw in zip(self.paths, self.raw))
                or self.manifest['source'] != source_binding()
                or self.manifest['destination_sha256'] != destination_binding(self.configuration)):
            raise ApplyError('artifact_binding_changed')


class Admission:
    def __init__(self, bundle, approval, *, seconds=120, clock=None):
        if type(seconds) is not int or not 1 <= seconds <= 600:
            raise ApplyError('deadline_required')
        self.bundle, self.path = bundle, Path(approval)
        self.raw = _read(self.path)
        self.value = _json(self.raw)
        self.clock = clock or (lambda: datetime.now(UTC))
        self.deadline = time.monotonic() + seconds
        self.check()

    def check(self):
        self.bundle.unchanged()
        value = self.value
        if (_bounded(self.path) != self.raw or time.monotonic() >= self.deadline
                or set(value) != {'approved', 'binding', 'entries', 'issued_at', 'expires_at', 'quiescence_reference'}
                or value['approved'] is not True or value['binding'] != self.bundle.binding
                or value['entries'] != [entry_key(entry) for entry in self.bundle.selected]
                or not isinstance(value['quiescence_reference'], str) or not 1 <= len(value['quiescence_reference']) <= 256):
            raise ApplyError('operator_admission_required')
        issued, expiry, now = _stamp(value['issued_at']), _stamp(value['expires_at']), self.clock()
        if not issued <= now < expiry or not 0 < (expiry - issued).total_seconds() <= 4 * 3600:
            raise ApplyError('finite_window_required')


class Journal:
    """One cooperating operator, append/fsync, bounded chain; never DB authority."""
    def __init__(self, path, binding):
        self.path, self.binding = Path(path), binding
        self.stream = None

    def __enter__(self):
        _private(self.path.parent, directory=True)
        if any(self.path.parent.resolve().is_relative_to(root.resolve())
                for root in (inventory.REPO_ROOT,)) or inventory._links(self.path):
            raise ApplyError('separate_journal_required')
        flags = os.O_RDWR | os.O_CREAT | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_BINARY', 0)
        self.stream = os.fdopen(os.open(self.path, flags, 0o600), 'r+b')
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            _private(self.path)
            raw = self.stream.read(MAX_DOCUMENT + 1)
            if len(raw) > MAX_DOCUMENT or raw and not raw.endswith(b'\n'):
                raise ApplyError('journal_incomplete_or_changed')
            self.rows, self.chain, self.planned = [], '0' * 64, {}
            for line in raw.splitlines():
                row = _json(line)
                if (set(row) != {'previous', 'data', 'sha256'} or row['previous'] != self.chain
                        or row['sha256'] != digest(canonical({'previous': row['previous'], 'data': row['data']}))):
                    raise ApplyError('journal_incomplete_or_changed')
                self.rows.append(row['data'])
                self.chain = row['sha256']
                if row['data'].get('event') == 'planned':
                    key = row['data']['entry_sha256']
                    if key in self.planned:
                        raise ApplyError('journal_incomplete_or_changed')
                    self.planned[key] = ObjectDescriptor(**row['data']['descriptor'])
            if not self.rows:
                self.append({'event': 'header', 'binding': self.binding})
            if self.rows[0] != {'event': 'header', 'binding': self.binding}:
                raise ApplyError('journal_binding_changed')
            return self
        except BaseException:
            self.stream.close()
            raise

    def append(self, data):
        row = {'previous': self.chain, 'data': data}
        row['sha256'] = digest(canonical(row))
        raw = canonical(row) + b'\n'
        self.stream.seek(0, os.SEEK_END)
        if self.stream.tell() + len(raw) > MAX_DOCUMENT or len(self.rows) >= 2000:
            raise ApplyError('journal_budget_exceeded')
        self.stream.write(raw)
        self.stream.flush()
        os.fsync(self.stream.fileno())
        self.rows.append(data)
        self.chain = row['sha256']

    def descriptor(self, entry, data, content_type):
        key = entry_key(entry)
        value = self.planned.get(key)
        if value is None:
            value = describe(entry['tenant_id'], entry['kind'], data, content_type)
            self.append({'event': 'planned', 'entry_sha256': key, 'descriptor': asdict(value)})
            self.planned[key] = value
        authorize(value, entry['tenant_id'])
        if (value.kind != entry['kind'] or value.sha256 != digest(data)
                or value.byte_size != len(data) or value.content_type != content_type):
            raise ApplyError('journal_descriptor_changed')
        return value

    def __exit__(self, *_args):
        self.stream.close()


def _row(db, entry, *, lock=False):
    from web.database.models import Cliente, GymProfile, PlanGenerado
    if entry['kind'] == 'plan_pdf':
        query = select(PlanGenerado.id.label('row_id'), PlanGenerado.gym_id.label('tenant_id'),
            PlanGenerado.id_cliente.label('client_id'), PlanGenerado.ruta_pdf.label('legacy_path'),
            PlanGenerado.pdf_object_id.label('new_reference'), PlanGenerado.deleted_at.label('deleted_at'),
            PlanGenerado.fecha_generacion.label('source_date'), Cliente.gym_id.label('client_tenant'),
            Cliente.id_cliente.label('client_present'), Cliente.deleted_at.label('client_deleted')).outerjoin(
                Cliente, Cliente.id_cliente == PlanGenerado.id_cliente).where(PlanGenerado.id == entry['row_id'])
    elif entry['kind'] == 'gym_logo':
        query = select(GymProfile.id.label('row_id'), GymProfile.gym_id.label('tenant_id'),
            GymProfile.logo_url.label('legacy_path'), GymProfile.logo_object_id.label('new_reference'),
            GymProfile.updated_at.label('source_date')).where(GymProfile.id == entry['row_id'])
    else:
        raise ApplyError()
    model = PlanGenerado if entry['kind'] == 'plan_pdf' else GymProfile
    row = db.execute(query.with_for_update(of=model) if lock else query).mappings().one_or_none()
    return dict(row) if row is not None else None


def _owner(db, entry):
    from web.database.models import UserRole, Usuario
    def live(user):
        return (user is not None and user.activo is True and user.deleted_at is None
            and user.invitation_token is None and user.role in tuple(UserRole)
            and type(user.session_version) is int and 0 <= user.session_version <= 2147483647)
    def owner(user):
        return live(user) and user.tipo == 'gym' and user.role == UserRole.OWNER and user.team_gym_id is None
    user = db.get(Usuario, entry['tenant_id'])
    valid = owner(user)
    if entry['kind'] == 'plan_pdf' and live(user) and user.role != UserRole.OWNER:
        valid = ((user.tipo == 'usuario' and user.team_gym_id is None) or (
            user.role in (UserRole.ADMIN, UserRole.NUTRIOLOGO, UserRole.VIEWER)
            and user.team_gym_id is not None and owner(db.get(Usuario, user.team_gym_id))))
    if not valid:
        raise ApplyError('persisted_owner_unavailable')


def _database(db, bundle):
    engine = getattr(db.bind, 'engine', db.bind)
    url = engine.url
    identity = getattr(engine, '_legacy_inventory_source_identity',
        (engine.dialect.name, url.host, url.port or (5432 if engine.dialect.name == 'postgresql' else None), url.database))
    if identity[0] == 'sqlite' and identity[3]:
        identity = (*identity[:3], os.path.normcase(str(Path(identity[3]).resolve())))
    if (inventory._hash(inventory._canonical(identity)) != bundle.header['source_database_fingerprint']
            or db.execute(text('SELECT version_num FROM alembic_version')).scalars().all() != [bundle.header['source_revision']]):
        raise ApplyError('database_binding_changed')
    if db.bind.dialect.name == 'postgresql':
        flags = db.execute(text('SELECT rolsuper,rolbypassrls FROM pg_catalog.pg_roles WHERE rolname=current_user')).one()
        if not any(flags) or db.scalar(text('SELECT pg_catalog.current_schema()')) != 'public':
            raise ApplyError('operational_global_role_required')


def _check_row(db, bundle, entry, descriptor=None, *, lock=False):
    _database(db, bundle)
    _owner(db, entry)
    row = _row(db, entry, lock=lock)
    if row is None or row['tenant_id'] != entry['tenant_id']:
        raise ApplyError('source_row_changed')
    attached = descriptor is not None and row['new_reference'] == descriptor.id
    if row['new_reference'] is not None and not attached:
        raise ApplyError('source_row_changed')
    original = {**row, 'new_reference': None}
    if inventory._hash(inventory._canonical(original)) != entry['source_fingerprint']:
        raise ApplyError('source_row_changed')
    if entry['kind'] == 'plan_pdf' and (row['deleted_at'] is not None or row['client_deleted'] is not None
            or row['client_present'] is None or row['client_tenant'] != row['tenant_id']):
        raise ApplyError('source_row_changed')
    _, relative, key, issues = inventory._path(entry['kind'], row['legacy_path'], bundle.roots)
    if issues or relative != entry['relative_path']:
        raise ApplyError('source_row_changed')
    return row, key, attached


def _duplicates(db, bundle, key, budget):
    count = 0
    for total, (kind, row) in enumerate(inventory._references(db.connection(), 250), 1):
        budget()
        if total > MAX_DATABASE_ROWS:
            raise ApplyError('database_budget_exceeded')
        if row['legacy_path'] and inventory._path(kind, row['legacy_path'], bundle.roots)[2] == key:
            count += 1
    if count != 1:
        raise ApplyError('source_path_ambiguous')


def _bytes(bundle, entry):
    root = bundle.roots.pdf if entry['kind'] == 'plan_pdf' else bundle.roots.logo
    path = root / entry['relative_path']
    checked = inventory._read_file(path, root, entry['kind'])
    if (checked.get('issues') or checked.get('sha256') != entry['sha256']
            or checked.get('file_fingerprint') != entry['file_fingerprint']
            or checked.get('byte_size') != entry['byte_size']):
        raise ApplyError('source_file_changed')
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_BINARY', 0)
    fd = os.open(path, flags)
    try:
        before = os.fstat(fd)
        opened = inventory._opened_path(fd)
        if (inventory._links(path) or not inventory._same_open_file(before, path.stat())
                or opened is not None and not opened.is_relative_to(root)):
            raise ApplyError('source_file_changed')
        data = bytearray()
        while len(data) <= entry['byte_size']:
            block = os.read(fd, min(1024 * 1024, entry['byte_size'] + 1 - len(data)))
            if not block:
                break
            data.extend(block)
        if (digest(data) != entry['sha256'] or len(data) != entry['byte_size']
                or inventory._stat_fingerprint(before) != inventory._stat_fingerprint(os.fstat(fd))
                or not inventory._same_open_file(before, path.stat()) or inventory._links(path)):
            raise ApplyError('source_file_changed')
    finally:
        os.close(fd)
    if entry['kind'] == 'gym_logo':
        from web.services.gym_logos import normalize_logo
        return normalize_logo(bytes(data), path.suffix.lower())
    return bytes(data), 'application/pdf'


def _stored(db, entry, descriptor, backend, *, create=False):
    from web.database.models import StoredObject
    row = db.get(StoredObject, descriptor.id, with_for_update=True)
    if row is None and create:
        row = StoredObject(id=descriptor.id, gym_id=descriptor.owner_id, kind=descriptor.kind, key=descriptor.key,
            content_type=descriptor.content_type, byte_size=descriptor.byte_size, sha256=descriptor.sha256,
            storage_backend=backend, status='pending')
        db.add(row)
        db.flush()
    if (row is None or row.gym_id != entry['tenant_id'] or row.kind != descriptor.kind or row.key != descriptor.key
            or row.byte_size != descriptor.byte_size or row.sha256 != descriptor.sha256
            or row.content_type != descriptor.content_type or row.storage_backend != backend
            or row.status not in {'pending', 'ready'}):
        raise ApplyError('pending_descriptor_changed')
    return row


def _attach(db, entry, row, descriptor):
    from web.database.models import Cliente, GymProfile, PlanGenerado
    model, field = (PlanGenerado, PlanGenerado.pdf_object_id) if entry['kind'] == 'plan_pdf' else (GymProfile, GymProfile.logo_object_id)
    values = {field: descriptor.id}
    if model is GymProfile:
        # Reference migration does not edit the user's branding timestamp.
        values[GymProfile.updated_at] = row['source_date']
    query = update(model).where(model.id == entry['row_id'], model.gym_id == entry['tenant_id'], field.is_(None))
    if model is PlanGenerado:
        query = query.where(model.ruta_pdf == row['legacy_path'], model.fecha_generacion == row['source_date'],
            model.id_cliente == row['client_id'], model.deleted_at.is_(None),
            select(Cliente.id_cliente).where(Cliente.id_cliente == row['client_id'],
                Cliente.gym_id == entry['tenant_id'], Cliente.deleted_at.is_(None)).exists())
    else:
        query = query.where(model.logo_url == row['legacy_path'], model.updated_at == row['source_date'])
    if db.execute(query.values(values)).rowcount != 1:
        raise ApplyError('source_row_changed')


@contextmanager
def _session(engine):
    with Session(engine) as db:
        yield db


def run(engine, bundle, *, approval=None, journal=None, store=None, seconds=120, clock=None):
    """No success before commit AND session close; uncertain effects stay resumable."""
    if current_tenant.get():
        raise ApplyError('operator_context_required')
    if approval is None:
        start = time.monotonic()
        def budget():
            if time.monotonic() - start >= 120:
                raise ApplyError('deadline_exceeded')
        bundle.unchanged()
        with inventory.readonly_inventory_connection(engine) as connection, Session(bind=connection) as db:
            for entry in bundle.selected:
                _, key, _ = _check_row(db, bundle, entry)
                _duplicates(db, bundle, key, budget)
                _bytes(bundle, entry)
        return {'complete': True, 'mode': 'plan', 'eligible': len(bundle.selected), 'applied': 0}
    admission = Admission(bundle, approval, seconds=seconds, clock=clock)
    if journal is None or store is None:
        raise ApplyError('explicit_destination_and_journal_required')
    if any(Path(journal).parent.resolve().is_relative_to(root)
            for root in (bundle.roots.pdf, bundle.roots.logo,
                *([Path(bundle.configuration.local_root).resolve()] if bundle.configuration.local_root else []))):
        raise ApplyError('separate_journal_required')
    with Journal(journal, bundle.binding) as log:
        for entry in bundle.selected:
            admission.check()  # Before the first DB connection or effect.
            with _session(engine) as db:
                _, key, _ = _check_row(db, bundle, entry, log.planned.get(entry_key(entry)))
                _duplicates(db, bundle, key, lambda: admission.check() if time.monotonic() >= admission.deadline else None)
            data, content_type = _bytes(bundle, entry)
            admission.check()
            descriptor = log.descriptor(entry, data, content_type)
            with _session(engine) as db:
                _check_row(db, bundle, entry, descriptor, lock=True)
                _stored(db, entry, descriptor, bundle.configuration.backend, create=True)
                admission.check()
                db.commit()
            admission.check()  # An expired lease may close/rollback, never start PUT.
            store.put(descriptor, data, owner_id=entry['tenant_id'])
            if store.read(descriptor, owner_id=entry['tenant_id']) != data:
                raise ApplyError('destination_bytes_changed')
            admission.check()
            with _session(engine) as db:
                row, key, attached = _check_row(db, bundle, entry, descriptor, lock=True)
                _duplicates(db, bundle, key, lambda: admission.check() if time.monotonic() >= admission.deadline else None)
                pending = _stored(db, entry, descriptor, bundle.configuration.backend)
                # A publication success does not excuse source drift during I/O.
                if _bytes(bundle, entry) != (data, content_type):
                    raise ApplyError('source_file_changed')
                if not attached:
                    admission.check()
                    _attach(db, entry, row, descriptor)
                    pending.status = 'ready'
                elif pending.status != 'ready':
                    raise ApplyError('pending_descriptor_changed')
                admission.check()
                db.commit()
            log.append({'event': 'reference_committed', 'entry_sha256': entry_key(entry), 'object_id': descriptor.id})
    return {'complete': True, 'mode': 'apply', 'eligible': len(bundle.selected), 'applied': len(bundle.selected)}
