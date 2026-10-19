import ctypes, hashlib, importlib, importlib.metadata as md, importlib.util
import json, os, pathlib, platform, re, ssl, stat, struct, subprocess, sys

ROOTS = ['/usr', '/app', '/opt']
errors = []

def elf(data):
    assert data[:4] == b'\x7fELF'
    cls, endian = data[4], data[5]
    assert cls == 2 and endian == 1, (cls, endian)
    h = struct.unpack_from('<16sHHIQQQIHHHHHH', data)
    kind, machine, phoff, phentsize, phnum = h[1], h[2], h[5], h[9], h[10]
    assert phentsize in (0, 56) and phoff + phnum * phentsize <= len(data)
    loads, dynamics, notes, interp = [], [], [], None
    for n in range(phnum):
        p = struct.unpack_from('<IIQQQQQQ', data, phoff + n * phentsize)
        typ, offset, vaddr, filesz = p[0], p[2], p[3], p[5]
        assert offset + filesz <= len(data)
        if typ == 1:
            loads.append((vaddr, offset, filesz))
        if typ == 2:
            dynamics.extend(struct.iter_unpack('<qQ', data[offset:offset+filesz]))
        if typ == 3:
            interp = data[offset:offset+filesz].rstrip(b'\0').decode()
        if typ == 4:
            notes.append(data[offset:offset+filesz])
    table = dict(dynamics)
    strings = b''
    if 5 in table:
        for vaddr, offset, size in loads:
            if vaddr <= table[5] < vaddr + size:
                off = offset + table[5] - vaddr
                strings = data[off:off+table.get(10, 0)]
                break
        assert strings
    def string(off):
        assert off < len(strings)
        return strings[off:strings.index(b'\0', off)].decode('utf-8')
    build_ids = []
    for note in notes:
        offset = 0
        while offset + 12 <= len(note):
            namesz, descsz, typ = struct.unpack_from('<III', note, offset)
            offset += 12
            name = note[offset:offset+namesz].rstrip(b'\0')
            offset += (namesz + 3) & ~3
            desc = note[offset:offset+descsz]
            offset += (descsz + 3) & ~3
            if name == b'GNU' and typ == 3:
                build_ids.append(desc.hex())
    return {'class_bits': 64, 'endian': 'little', 'machine': machine, 'elf_type': kind,
            'interpreter': interp, 'needed': [string(v) for k, v in dynamics if k == 1],
            'soname': [string(v) for k, v in dynamics if k == 14],
            'rpath': [string(v) for k, v in dynamics if k == 15],
            'runpath': [string(v) for k, v in dynamics if k == 29], 'gnu_build_ids': build_ids}

dpkg_raw = subprocess.check_output(['dpkg-query', '-W', '-f=${binary:Package}\t${Version}\t${source:Package}\t${source:Version}\n'], text=True)
packages = []
for line in dpkg_raw.splitlines():
    name, version, source, source_version = line.split('\t')
    packages.append({'name': name, 'version': version, 'source_package': source, 'source_version': source_version})
owner = {}
for listing in pathlib.Path('/var/lib/dpkg/info').glob('*.list'):
    for name in listing.read_text(errors='replace').splitlines():
        if name.startswith('/'):
            owner.setdefault(str(pathlib.Path(name).resolve()), []).append(listing.name[:-5])
wheel_owner = {}
for dist in md.distributions():
    for item in dist.files or []:
        path = str(pathlib.Path(dist.locate_file(item)).resolve())
        wheel_owner.setdefault(path, []).append({'name': dist.metadata['Name'], 'version': dist.version})

native = []
aliases = []
visited = set()
for root in ROOTS:
    for current, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = [d for d in dirs if not (pathlib.Path(current) / d).is_symlink()]
        for name in files:
            path = pathlib.Path(current) / name
            try:
                if path.is_symlink():
                    aliases.append({'path': str(path), 'target': str(path.resolve())})
                    continue
                mode = path.stat().st_mode
                if not stat.S_ISREG(mode):
                    continue
                with path.open('rb') as stream:
                    if stream.read(4) != b'\x7fELF':
                        continue
                    stream.seek(0)
                    data = stream.read()
                key = str(path.resolve())
                if key in visited:
                    continue
                visited.add(key)
                parsed = elf(data)
                assert parsed['machine'] == 62, str(path)
                native.append({'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                               'mode': oct(mode & 0o7777), 'dpkg_owners': owner.get(key, []),
                               'python_distributions': wheel_owner.get(key, []), **parsed})
            except Exception as exc:
                errors.append({'path': str(path), 'error_type': type(exc).__name__, 'error': str(exc)})
assert not errors, errors

versions = {'python': sys.version, 'platform': platform.platform(), 'ssl_module': ssl.OPENSSL_VERSION}
imports = {}
for name in ['_ssl', '_hashlib', 'pyexpat', '_elementtree', 'sqlite3', '_sqlite3', 'zlib', 'lzma', '_lzma',
             'cryptography', 'cryptography.hazmat.bindings._rust', 'cryptography.hazmat.backends.openssl.backend',
             'psycopg2', 'psycopg2.extensions', 'PIL.Image', 'PIL.features', 'bcrypt', '_cffi_backend',
             'greenlet', 'markupsafe._speedups', 'yaml._yaml', 'pydantic_core', 'httptools', 'watchfiles', 'PySide6']:
    try:
        module = importlib.import_module(name)
        imports[name] = {'file': getattr(module, '__file__', None)}
        if name == 'pyexpat':
            versions['expat'] = module.EXPAT_VERSION
        elif name == 'sqlite3':
            versions['sqlite'] = module.sqlite_version
        elif name == 'zlib':
            versions['zlib_compile'] = module.ZLIB_VERSION
            versions['zlib_runtime'] = module.ZLIB_RUNTIME_VERSION
        elif name == 'cryptography.hazmat.backends.openssl.backend':
            versions['cryptography_openssl'] = module.backend.openssl_version_text()
        elif name == 'psycopg2':
            versions['psycopg2_libpq_compile'] = module.__libpq_version__
        elif name == 'psycopg2.extensions':
            versions['psycopg2_libpq_runtime'] = module.libpq_version()
        elif name == 'PIL.features':
            versions['pillow_features'] = {feature: module.version(feature) for feature in module.get_supported()}
    except ModuleNotFoundError as exc:
        imports[name] = {'not_importable': True, 'missing_module': exc.name}
    except Exception as exc:
        imports[name] = {'error_type': type(exc).__name__, 'error': str(exc)}

maps = pathlib.Path('/proc/self/maps').read_text()
mapped = sorted({line.split(None, 5)[5] for line in maps.splitlines() if len(line.split(None, 5)) == 6 and line.split(None, 5)[5].startswith('/')})
runtime_api = []
for path in mapped:
    base = pathlib.Path(path).name
    query = None
    if re.match(r'lib(?:ssl|crypto)[-.]', base):
        query = ('OpenSSL_version', ctypes.c_char_p, [ctypes.c_int], [0])
    elif base.startswith('libexpat'):
        query = ('XML_ExpatVersion', ctypes.c_char_p, [], [])
    elif base.startswith('libsqlite3'):
        query = ('sqlite3_libversion', ctypes.c_char_p, [], [])
    elif re.match(r'libz[.-]', base):
        query = ('zlibVersion', ctypes.c_char_p, [], [])
    elif base.startswith('liblzma'):
        query = ('lzma_version_string', ctypes.c_char_p, [], [])
    elif base.startswith('libpq'):
        query = ('PQlibVersion', ctypes.c_int, [], [])
    elif base == 'libc.so.6':
        query = ('gnu_get_libc_version', ctypes.c_char_p, [], [])
    if query:
        function, restype, argtypes, args = query
        try:
            library = ctypes.CDLL(path)
            api = getattr(library, function)
            api.restype, api.argtypes = restype, argtypes
            value = api(*args)
            runtime_api.append({'path': path, 'function': function, 'value': value.decode() if isinstance(value, bytes) else value})
        except Exception as exc:
            runtime_api.append({'path': path, 'function': function, 'error_type': type(exc).__name__, 'error': str(exc)})

ldd = []
selected = set()
for row in native:
    p = row['path']
    if p in mapped or ('/site-packages/' in p and ('.libs/' in p or p.endswith('.so'))) or '/lib-dynload/' in p:
        selected.add(p)
for path in sorted(selected):
    result = subprocess.run(['ldd', path], capture_output=True, text=True, timeout=15)
    ldd.append({'path': path, 'exit': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr})

components = {}
for path in ['/usr/bin/mount', '/usr/bin/nsenter', '/usr/bin/infocmp', '/usr/bin/login', '/usr/bin/chfn',
             '/usr/bin/chsh', '/usr/bin/su', '/usr/bin/tar', '/usr/sbin/rmt', '/usr/bin/apt-key',
             '/usr/bin/getfacl', '/usr/bin/setfacl', '/usr/bin/chacl', '/usr/bin/getfattr', '/usr/bin/setfattr',
             '/usr/bin/bzip2recover', '/usr/bin/newuidmap', '/usr/lib/systemd/systemd-homed',
             '/usr/lib/systemd/systemd-oomd', '/usr/lib/systemd/systemd-journald', '/usr/bin/systemd-tmpfiles', '/sbin/init']:
    p = pathlib.Path(path)
    components[path] = {'exists_at_exact_path': p.exists(), 'symlink': p.is_symlink()}
    if p.exists():
        components[path].update(resolved=str(p.resolve()), mode=oct(p.stat().st_mode & 0o7777),
                                dpkg_owners=owner.get(str(p.resolve()), []))

report = {'scope': 'Metadata and native library inspection of the exact product image with CMD overridden, network none, read-only filesystem, cap-drop ALL and NNP. No application startup or PostgreSQL connection.',
          'roots_walked_without_following_directory_symlinks': ROOTS,
          'uid': os.getuid(), 'gid': os.getgid(), 'versions': versions, 'imports': imports,
          'dpkg_packages': packages, 'elf_count': len(native), 'elf_files': native,
          'file_aliases': aliases, 'proc_self_maps': maps, 'mapped_files_after_imports': mapped,
          'runtime_native_api_versions': runtime_api, 'ldd': ldd, 'exact_component_paths': components,
          'qt_scope': 'PySide6 import result and ELF filename inventory are recorded. No generic claim of absence outside the inspected roots.',
          'errors': errors}
print(json.dumps(report, indent=2))
