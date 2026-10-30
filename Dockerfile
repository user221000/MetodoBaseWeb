# ══════════════════════════════════════════════════════════════════════════════
# MetodoBase Web — Dockerfile de producción
# Candidato local 2026-10-19: locks con hashes y base Linux/amd64 fijada por digest.
#
# Multi-stage build:
#   1. Instala dependencias web-only (sin PySide6, sin GUI)
#   2. Copia solo lo necesario para el servidor
#   3. Ejecuta con uvicorn como non-root user
#
# Build:   docker build -t metodobase-web .
# Run:     docker run -p 8000:8000 --env-file .env metodobase-web
# ══════════════════════════════════════════════════════════════════════════════

# CPython 3.12.15 includes the September 2026 security fixes for the container target.
FROM python:3.12.15-slim@sha256:2b4f19dae3a777dfc3b76730bda1e82e1f66ab2a2686fa93ca78edbfb4f04ffe AS base

# Debian's liblzma security backport fixes GHSA-5qpq-xqfv-j9pg in both stages.
# Resolve only signed stable/security metadata and upgrade the exact binary version.
RUN printf '%s\n' \
        'deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] https://snapshot.debian.org/archive/debian/20261029T082808Z trixie main' \
        'deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] https://snapshot.debian.org/archive/debian/20261029T082808Z trixie-updates main' \
        'deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] https://snapshot.debian.org/archive/debian-security/20261029T131250Z trixie-security main' \
        > /tmp/metodobase-security.list \
    && apt-get -o Dir::Etc::sourcelist=/tmp/metodobase-security.list \
        -o Dir::Etc::sourceparts=- -o APT::Update::Error-Mode=any \
        -o Acquire::AllowInsecureRepositories=false update \
    && cd /tmp \
    && apt-get -o Dir::Etc::sourcelist=/tmp/metodobase-security.list \
        -o Dir::Etc::sourceparts=- -o APT::Get::AllowUnauthenticated=false \
        download liblzma5=5.8.1-1+deb13u2 \
    && test "$(stat -c %s /tmp/liblzma5_5.8.1-1+deb13u2_amd64.deb)" = '309696' \
    && printf '%s  %s\n' \
        'b38acab30f295bf1066a6632e31cbd0a1980f2924b38040cda131d5dea5384ec' \
        '/tmp/liblzma5_5.8.1-1+deb13u2_amd64.deb' | sha256sum --check - \
    && apt-get -o Dir::Etc::sourcelist=/tmp/metodobase-security.list \
        -o Dir::Etc::sourceparts=- -o APT::Get::AllowUnauthenticated=false \
        install -y --only-upgrade --no-install-recommends /tmp/liblzma5_5.8.1-1+deb13u2_amd64.deb \
    && test "$(dpkg-query -W -f='${Version}' liblzma5)" = '5.8.1-1+deb13u2' \
    && rm -f /tmp/metodobase-security.list /tmp/liblzma5_5.8.1-1+deb13u2_amd64.deb \
    && rm -rf /var/lib/apt/lists/*

# METODOBASE_CA_G3_20261029_BEGIN
RUN set -eu; \
    printf '%s\n' \
        '"""Stdlib-only exact OS truststore transition for the immutable Python base."""' \
        'import hashlib' \
        'import json' \
        'from pathlib import Path' \
        'import re' \
        'import ssl' \
        'import sys' \
        'import os' \
        '' \
        'TARGET_DER = "86a1ecba089c4a8d3bbe2734c612ba341d813e043cf9e8a862cd5c57a36bbe6b"' \
        'TARGET_SPKI = "8d417db2dd8bf5e3084d1e3f196d583849d81bdd4c00c70b9d39369e96b8c782"' \
        'BUNDLE_SHA = "714d457d580922dbf1d0be8bd35ba236a842b50b0072ae791582a19adef772a5"' \
        'SET_SHA = "ffb9164a1ec4a8d8c1cc2f1449a647d18ffbd986b5939fd5b07dd32321147302"' \
        'CONF_BEFORE_SHA = "ab7339d40969fb1084cb23011fbdae7cc8edb46ac7e410897bb6b7016f07ed7f"' \
        'CONF_AFTER_SHA = "1e1de7c638c2ea3fa5fa19f4cb342227391d3c3c2869825b39a5a0705f3782c5"' \
        'SOURCE_SHA = "36e68e205b53c67c7a013894e0d5c8583063468118d1ce78ecbc2200d1dd185c"' \
        'ENTRY = b"mozilla/emSign_ECC_Root_CA_-_G3.crt\n"' \
        'BUNDLE = Path("/etc/ssl/certs/ca-certificates.crt")' \
        'CONF = Path("/etc/ca-certificates.conf")' \
        'SOURCE = Path("/usr/share/ca-certificates/mozilla/emSign_ECC_Root_CA_-_G3.crt")' \
        'CAPATH = Path("/etc/ssl/certs")' \
        'STATE = Path("/tmp/metodobase-ca-g3-before.json")' \
        'PROVENANCE = Path("/usr/local/share/metodobase/ca-root-g3-20261029.json")' \
        'PEM = re.compile(br"-----BEGIN CERTIFICATE-----\s+.*?-----END CERTIFICATE-----", re.S)' \
        '' \
        '' \
        'def require(condition, message):' \
        '    if not condition:' \
        '        raise ValueError(message)' \
        '' \
        '' \
        'def sha(raw):' \
        '    return hashlib.sha256(raw).hexdigest()' \
        '' \
        '' \
        'def der_hashes(raw):' \
        '    blocks = PEM.findall(raw)' \
        '    require(blocks and not PEM.sub(b"", raw).strip(), "Unexpected CA bundle framing")' \
        '    return [sha(ssl.PEM_cert_to_DER_cert(block.decode("ascii"))) for block in blocks]' \
        '' \
        '' \
        'def set_sha(values):' \
        '    return sha(("\n".join(sorted(values)) + "\n").encode("ascii"))' \
        '' \
        '' \
        'def before_state(bundle, conf, source, capath):' \
        '    require(sha(bundle) == BUNDLE_SHA and sha(conf) == CONF_BEFORE_SHA and sha(source) == SOURCE_SHA,' \
        '            "Immutable base CA inputs differ")' \
        '    values = der_hashes(bundle)' \
        '    require(len(values) == len(set(values)) == 150 and set_sha(values) == SET_SHA,' \
        '            "The exact150 base CA set differs")' \
        '    require(der_hashes(source) == [TARGET_DER] and TARGET_DER in values,' \
        '            "The exact affected G3 certificate differs")' \
        '    require(set(capath) == set(values), "The base CApath differs from its exact bundle")' \
        '    require(conf.splitlines().count(ENTRY.rstrip(b"\n")) == 1 and conf.count(ENTRY) == 1,' \
        '            "Exactly one active G3 configuration entry is required")' \
        '    changed = conf.replace(ENTRY, b"!" + ENTRY, 1)' \
        '    require(sha(changed) == CONF_AFTER_SHA, "The single-line G3 disable transition differs")' \
        '    return {"bundle_sha256": BUNDLE_SHA, "before_der_sha256": sorted(values)}, changed' \
        '' \
        '' \
        'def after_state(state, bundle, conf, source, capath, defaults):' \
        '    require(set(state) == {"bundle_sha256", "before_der_sha256"} and state["bundle_sha256"] == BUNDLE_SHA,' \
        '            "The exact before-state authority differs")' \
        '    before = state["before_der_sha256"]' \
        '    require(type(before) is list and len(before) == len(set(before)) == 150' \
        '            and set_sha(before) == SET_SHA and TARGET_DER in before,' \
        '            "The immutable before CA set differs")' \
        '    require(sha(conf) == CONF_AFTER_SHA and sha(source) == SOURCE_SHA,' \
        '            "The exact disabled configuration or retained source certificate differs")' \
        '    require(conf.splitlines().count(b"!" + ENTRY.rstrip(b"\n")) == 1' \
        '            and conf.splitlines().count(ENTRY.rstrip(b"\n")) == 0,' \
        '            "G3 must be disabled exactly once")' \
        '    values = der_hashes(bundle)' \
        '    expected = set(before) - {TARGET_DER}' \
        '    require(len(values) == len(set(values)) == 149 and set(values) == expected,' \
        '            "The regenerated bundle must retain exactly the other149 certificates")' \
        '    require(set(capath) == expected and set(defaults) == expected,' \
        '            "CApath and the default SSLContext must contain exactly the same149 CAs")' \
        '    return {"schema": "metodobase-exact-os-ca-root-removal-v1", "scope": "OS truststore only; vendored bundles are separate",' \
        '            "target_DER_sha256": TARGET_DER, "target_SPKI_sha256": TARGET_SPKI,' \
        '            "disabled_configuration_entry": ENTRY.decode().strip(),' \
        '            "before_bundle_sha256": BUNDLE_SHA, "after_bundle_sha256": sha(bundle),' \
        '            "before_count": 150, "after_count": 149,' \
        '            "before_der_sha256": before, "after_der_sha256": sorted(values),' \
        '            "removed_der_sha256": [TARGET_DER], "other149_preserved": True,' \
        '            "configuration_sha256": CONF_AFTER_SHA, "disabled_source_PEM_sha256": SOURCE_SHA,' \
        '            "disabled_source_retained": True, "CApath_and_default_SSLContext_match": True}' \
        '' \
        '' \
        'def capath_hashes():' \
        '    values = set()' \
        '    for path in CAPATH.iterdir():' \
        '        require(not path.is_symlink() or path.exists(), "Dangling CApath alias")' \
        '        if path.is_dir():' \
        '            continue' \
        '        require(path.is_file() and path.stat().st_size <= 2 * 1024**2, "Unexpected CApath entry")' \
        '        values.update(der_hashes(path.read_bytes()))' \
        '    return values' \
        '' \
        '' \
        'def main():' \
        '    require(sys.platform == "linux" and len(sys.argv) == 2 and sys.argv[1] in {"before", "after"},' \
        '            "Explicit Linux build-only CA transition phase required")' \
        '    require(not os.environ.get("SSL_CERT_FILE") and not os.environ.get("SSL_CERT_DIR"), "Ambient SSL overrides rejected")' \
        '    for path in (BUNDLE, CONF, SOURCE):' \
        '        require(path.is_file() and not path.is_symlink(), "Expected regular base CA input")' \
        '    if sys.argv[1] == "before":' \
        '        state, changed = before_state(BUNDLE.read_bytes(), CONF.read_bytes(), SOURCE.read_bytes(), capath_hashes())' \
        '        with STATE.open("x", encoding="utf8") as output:' \
        '            json.dump(state, output)' \
        '        CONF.write_bytes(changed)' \
        '    else:' \
        '        paths = ssl.get_default_verify_paths()' \
        '        require(paths.cafile and Path(paths.cafile).resolve() == BUNDLE' \
        '                and paths.capath and Path(paths.capath).resolve() == CAPATH, "Default SSL trust paths differ")' \
        '        defaults = {sha(der) for der in ssl.create_default_context().get_ca_certs(binary_form=True)}' \
        '        result = after_state(json.loads(STATE.read_bytes()), BUNDLE.read_bytes(), CONF.read_bytes(),' \
        '                             SOURCE.read_bytes(), capath_hashes(), defaults)' \
        '        PROVENANCE.parent.mkdir(parents=True, exist_ok=True)' \
        '        with PROVENANCE.open("x", encoding="utf8") as output:' \
        '            json.dump(result, output, sort_keys=True, indent=2)' \
        '            output.write("\n")' \
        '        require(json.loads(PROVENANCE.read_bytes()) == result, "CA provenance readback differs")' \
        '        STATE.unlink()' \
        '' \
        '' \
        'if __name__ == "__main__":' \
        '    main()' \
        > /tmp/metodobase-ca-g3.py; \
    python -I -B /tmp/metodobase-ca-g3.py before; \
    update-ca-certificates --fresh; \
    python -I -B /tmp/metodobase-ca-g3.py after; \
    rm -f -- /tmp/metodobase-ca-g3.py
# METODOBASE_CA_G3_20261029_END
# Both dependency and runtime stages inherit the verified installer upgrade.
# Pin its wheel independently; application locks and Windows environments stay separate.
COPY requirements-container-bootstrap.lock /usr/local/share/metodobase/requirements-container-bootstrap.lock
RUN python -m pip --isolated install --no-cache-dir --require-hashes --only-binary=:all: \
    --index-url https://pypi.org/simple -r /usr/local/share/metodobase/requirements-container-bootstrap.lock

# Prevenir bytecode + buffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# ── Stage 1: dependencias ────────────────────────────────────────────────────
FROM base AS native-runtime

# Pin the complete signed APT index inputs used to resolve libpq and its dependencies.
# A changed or expired index fails closed; refreshing these pins requires review.
COPY requirements-container-apt-metadata.lock /usr/local/share/metodobase/requirements-container-apt-metadata.lock
RUN set -eu; \
    printf '%s\n' \
        'deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] https://snapshot.debian.org/archive/debian/20261029T082808Z trixie main' \
        'deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] https://snapshot.debian.org/archive/debian/20261029T082808Z trixie-updates main' \
        'deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] https://snapshot.debian.org/archive/debian-security/20261029T131250Z trixie-security main' \
        > /tmp/metodobase-native.list; \
    mkdir -p /usr/local/share/metodobase/native-runtime; \
    dpkg-query -W -f='${binary:Package}\t${Version}\n' > /usr/local/share/metodobase/native-runtime/before.tsv; \
    apt-get -o Dir::Etc::sourcelist=/tmp/metodobase-native.list -o Dir::Etc::sourceparts=- \
        -o APT::Update::Error-Mode=any -o Acquire::AllowInsecureRepositories=false update; \
    sha256sum --check /usr/local/share/metodobase/requirements-container-apt-metadata.lock; \
    apt-get -o Dir::Etc::sourcelist=/tmp/metodobase-native.list -o Dir::Etc::sourceparts=- \
        -o APT::Get::AllowUnauthenticated=false install -y --no-remove --no-install-recommends libpq5=17.11-0+deb13u1; \
    test "$(dpkg-query -W -f='${Version}' libpq5)" = '17.11-0+deb13u1'; \
    test "$(dpkg-query -W -f='${Version}' libssl3t64)" = '3.5.7-1~deb13u3'; \
    dpkg-query -W -f='${binary:Package}\t${Version}\n' > /usr/local/share/metodobase/native-runtime/after.tsv; \
    python -c "from pathlib import Path; p=Path('/usr/local/share/metodobase/native-runtime'); rows=lambda n:dict(line.split('\t') for line in (p/n).read_text().splitlines()); before=rows('before.tsv'); after=rows('after.tsv'); assert all(after.get(k)==v for k,v in before.items()), 'Existing base packages changed'"; \
    rm -f /tmp/metodobase-native.list; \
    rm -rf /var/lib/apt/lists/*

# Compiler and PEP 517 backend exist only in this stage, outside copied site-packages.
FROM native-runtime AS psycopg-build
COPY requirements-container-build.lock requirements-container-psycopg.lock /tmp/
RUN set -eu; \
    printf '%s\n' \
        'deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] https://snapshot.debian.org/archive/debian/20261029T082808Z trixie main' \
        'deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] https://snapshot.debian.org/archive/debian/20261029T082808Z trixie-updates main' \
        'deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] https://snapshot.debian.org/archive/debian-security/20261029T131250Z trixie-security main' \
        > /tmp/metodobase-native.list; \
    dpkg-query -W -f='${binary:Package}\t${Version}\n' > /tmp/native-before.tsv; \
    apt-get -o Dir::Etc::sourcelist=/tmp/metodobase-native.list -o Dir::Etc::sourceparts=- \
        -o APT::Update::Error-Mode=any -o Acquire::AllowInsecureRepositories=false update; \
    sha256sum --check /usr/local/share/metodobase/requirements-container-apt-metadata.lock; \
    apt-get -o Dir::Etc::sourcelist=/tmp/metodobase-native.list -o Dir::Etc::sourceparts=- \
        -o APT::Get::AllowUnauthenticated=false install -y --no-remove --no-install-recommends \
        gcc=4:14.2.0-1 libc6-dev=2.41-12+deb13u4 libpq-dev=17.11-0+deb13u1 libssl-dev=3.5.7-1~deb13u3; \
    test "$(dpkg-query -W -f='${Version}' libpq-dev)" = "$(dpkg-query -W -f='${Version}' libpq5)"; \
    mkdir -p /wheelhouse /tmp/metodobase-native-build; \
    dpkg-query -W -f='${binary:Package}\t${Version}\n' > /wheelhouse/builder-dpkg.tsv; \
    python -c "from pathlib import Path; rows=lambda p:dict(line.split('\t') for line in Path(p).read_text().splitlines()); before=rows('/tmp/native-before.tsv'); after=rows('/wheelhouse/builder-dpkg.tsv'); assert all(after.get(k)==v for k,v in before.items()), 'Existing native runtime packages changed'"; \
    python -m venv /opt/psycopg-build-tools; \
    /opt/psycopg-build-tools/bin/python -m pip --isolated install --no-cache-dir --require-hashes --only-binary=:all: \
        --index-url https://pypi.org/simple -r /usr/local/share/metodobase/requirements-container-bootstrap.lock; \
    /opt/psycopg-build-tools/bin/python -m pip --isolated install --no-cache-dir --require-hashes --no-deps --only-binary=:all: \
        --index-url https://pypi.org/simple -r /tmp/requirements-container-build.lock; \
    mkdir -p /tmp/metodobase-native-source; \
    python -c "from pathlib import Path; import hashlib,urllib.request; raw=urllib.request.urlopen('https://files.pythonhosted.org/packages/91/81/6ea19b8b28feb9405c8c87a307776614d6e404bdb98467d1ce10a39d2c1d/psycopg2-2.9.13.tar.gz',timeout=60).read(); assert len(raw)==378068 and hashlib.sha256(raw).hexdigest()=='d36784fc2dae69523ba4b79c7d1d1b4d6e83e87836874f111262f4db940b16a6'; Path('/tmp/metodobase-native-source/psycopg2-2.9.13.tar.gz').write_bytes(raw)"; \
    TMPDIR=/tmp/metodobase-native-build SOURCE_DATE_EPOCH=1792414502 PYTHONHASHSEED=0 \
        CFLAGS='-g0 -ffile-prefix-map=/tmp/metodobase-native-build=.' \
        /opt/psycopg-build-tools/bin/python -m pip --isolated wheel --no-cache-dir --require-hashes --no-deps \
        --no-build-isolation --no-binary=:all: --no-index --find-links=/tmp/metodobase-native-source \
        --wheel-dir /wheelhouse -r /tmp/requirements-container-psycopg.lock; \
    python -c "from pathlib import Path; import hashlib,zipfile; root=Path('/wheelhouse'); wheels=list(root.glob('*.whl')); assert len(wheels)==1; wheel=wheels[0]; assert wheel.name.startswith('psycopg2-2.9.13-'); z=zipfile.ZipFile(wheel); assert z.testzip() is None; assert not any('.libs/' in n or n.startswith('/') or '..' in Path(n).parts for n in z.namelist()); digest=hashlib.sha256(wheel.read_bytes()).hexdigest(); (root/'built-wheel.lock').write_text('psycopg2==2.9.13 --hash=sha256:'+digest+'\n')"; \
    /usr/bin/pg_config --version > /wheelhouse/pg-config-version.txt; \
    /opt/psycopg-build-tools/bin/python -m pip --isolated freeze --all > /wheelhouse/build-tools.txt; \
    cp /tmp/requirements-container-build.lock /tmp/requirements-container-psycopg.lock /wheelhouse/; \
    cp /usr/local/share/metodobase/requirements-container-apt-metadata.lock /wheelhouse/; \
    rm -f /tmp/native-before.tsv /tmp/metodobase-native.list; \
    rm -rf /var/lib/apt/lists/* /tmp/metodobase-native-build /tmp/metodobase-native-source

# Rebuild only pyexpat with the pinned upstream Expat capacity backport.
# _elementtree keeps its original ELF and identical pyexpat C API/version contract.
FROM psycopg-build AS expat-build
COPY runtime-source/expat-sec10 /tmp/metodobase-expat-sec10
RUN /opt/psycopg-build-tools/bin/python -I /tmp/metodobase-expat-sec10/rebuild_pyexpat.py --build --output /expat-output

FROM native-runtime AS deps
COPY requirements-container.lock .
RUN python -m pip --isolated install --no-cache-dir --require-hashes --only-binary=:all: \
    --index-url https://pypi.org/simple -r requirements-container.lock
COPY --from=psycopg-build /wheelhouse /tmp/psycopg-wheelhouse
RUN set -eu; \
    python -m pip --isolated install --no-cache-dir --no-index --no-deps --require-hashes --only-binary=:all: \
        --find-links=/tmp/psycopg-wheelhouse -r /tmp/psycopg-wheelhouse/built-wheel.lock; \
    python -m pip check; \
    mkdir -p /usr/local/share/metodobase/psycopg2-build; \
    cp /tmp/psycopg-wheelhouse/*.lock /tmp/psycopg-wheelhouse/*.tsv /tmp/psycopg-wheelhouse/*.txt /usr/local/share/metodobase/psycopg2-build/; \
    rm -rf /tmp/psycopg-wheelhouse

# ── Stage 2: app final ───────────────────────────────────────────────────────
FROM native-runtime AS runtime

# Copiar dependencias instaladas del stage anterior
COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin
COPY --from=deps /usr/local/share/metodobase/psycopg2-build /usr/local/share/metodobase/psycopg2-build
COPY --from=expat-build /expat-output/pyexpat.cpython-312-x86_64-linux-gnu.so /usr/local/lib/python3.12/lib-dynload/pyexpat.cpython-312-x86_64-linux-gnu.so
COPY --from=expat-build /expat-output/build-provenance.json /expat-output/sbom.json /expat-output/source-pins.json /expat-output/13c5f63.patch /expat-output/COPYING.expat /expat-output/small-binding-tests.log /usr/local/share/metodobase/expat-sec10/

# Asset version used by existing templates.
COPY web/.build_version /tmp/web_build_version

# Copiar solo los módulos necesarios para el web server
COPY config/ config/
COPY core/ core/
COPY src/ src/
COPY api/ api/
COPY web/ web/
COPY utils/ utils/
COPY static/ static/
COPY fonts/ fonts/

# Crear directorio para datos persistentes (incluye config y planes para evitar PermissionError)
RUN mkdir -p /data/registros /data/output /data/config /data/planes && \
    useradd --system --no-create-home appuser && \
    chown -R appuser:appuser /app /data

# Variables de entorno por defecto (overrideables en deploy)
ENV METODOBASE_ENV=production \
    METODOBASE_DATA_DIR=/data \
    PYTHONPATH=/app \
    PORT=8000

# Copiar entrypoint y asignar permisos
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Copiar Alembic config, migraciones y DB bootstrap
COPY alembic.ini /app/alembic.ini
COPY db_bootstrap.py /app/db_bootstrap.py

COPY runtime-source/container37-contract.json /usr/local/share/metodobase/container37-contract.json

# Runtime does not install packages or create virtual environments. Keep installers
# in build stages for hash verification and SCA, and remove their bundled wheels too.
# Expected current37 runtime inventory: 57 application distributions, checked by exact names and versions.
RUN set -eu; \
    python -c "from pathlib import Path; import importlib.metadata as m,sysconfig; root=Path('/usr/local/lib/python3.12'); site=root/'site-packages'; scripts=Path('/usr/local/bin'); assert Path(sysconfig.get_path('stdlib'))==root and Path(sysconfig.get_path('purelib'))==site and Path(sysconfig.get_path('scripts'))==scripts; assert root.resolve()==root and site.resolve()==site; assert scripts.is_dir() and not scripts.is_symlink() and scripts.resolve()==scripts; assert m.version('pip')=='26.2.1'; assert all(p.is_dir() and not p.is_symlink() for p in (site/'pip',site/'pip-26.2.1.dist-info',root/'ensurepip')); assert (root/'ensurepip'/'_bundled').is_dir()"; \
    rm -rf -- /usr/local/lib/python3.12/site-packages/pip \
        /usr/local/lib/python3.12/site-packages/pip-26.2.1.dist-info \
        /usr/local/lib/python3.12/ensurepip; \
    rm -f -- /usr/local/bin/pip /usr/local/bin/pip3 /usr/local/bin/pip3.12; \
    python -c "from pathlib import Path; import importlib.util as u,importlib.metadata as m,json,re; root=Path('/usr/local'); assert all(u.find_spec(n) is None for n in ('pip','ensurepip')); assert not any(root.rglob('*.whl')); assert not any(p.name.lower().startswith(('pip-','pip.')) for p in (root/'lib/python3.12/site-packages').iterdir()); assert not any(p.exists() or p.is_symlink() for p in (root/'bin/pip',root/'bin/pip3',root/'bin/pip3.12')); rows=sorted((d.metadata['Name'],d.version) for d in m.distributions()); expected=json.loads(Path('/usr/local/share/metodobase/container37-contract.json').read_text()); normalize=lambda n:re.sub('[-_.]+','-',n).lower(); actual={normalize(n):v for n,v in rows}; assert type(expected['runtime_distribution_count']) is int and expected['runtime_distribution_count']==57 and len(rows)==57 and actual==expected['distributions'] and all(n.lower() not in ('pip','setuptools','wheel') for n,v in rows); Path('/usr/local/share/metodobase/runtime-python-metadata.json').write_text(json.dumps(rows,indent=2)+'\n')"

# Non-root user
USER appuser

# Health check para Docker / Railway
# Readiness returns non-success when the database cannot serve requests.
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8000') + '/health/ready', timeout=5)" || exit 1

EXPOSE ${PORT}

# Railway uses preDeployCommand; standalone Docker migrates via entrypoint.
CMD ["/app/entrypoint.sh"]

# Publish the verified merged filesystem as a fresh root layer. The assembler
# above remains independently checked; deleted installer files have no lower
# image layer to reappear from in the production artifact.
FROM scratch AS production
COPY --from=runtime / /
ENV PATH=/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    LANG=C.UTF-8 \
    GPG_KEY=7169605F62C751356D054A26A821E680E5FA6305 \
    PYTHON_VERSION=3.12.15 \
    PYTHON_SHA256=c2c4321961fab0fb999d66e0cecf521c2ab3994c7992873ea99e306c1094fd5a \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    METODOBASE_ENV=production \
    METODOBASE_DATA_DIR=/data \
    PYTHONPATH=/app \
    PORT=8000
WORKDIR /app
RUN chown -R appuser:appuser /app /data \
    && python -c "from pathlib import Path; import importlib.util as u,importlib.metadata as m,json,re; root=Path('/usr/local'); assert all(u.find_spec(n) is None for n in ('pip','ensurepip')); assert not any(root.rglob('*.whl')); assert not any(p.name.lower().startswith(('pip-','pip.')) for p in (root/'lib/python3.12/site-packages').iterdir()); assert not any(p.exists() or p.is_symlink() for p in (root/'bin/pip',root/'bin/pip3',root/'bin/pip3.12')); rows=sorted((d.metadata['Name'],d.version) for d in m.distributions()); expected=json.loads(Path('/usr/local/share/metodobase/container37-contract.json').read_text()); normalize=lambda n:re.sub('[-_.]+','-',n).lower(); actual={normalize(n):v for n,v in rows}; assert type(expected['runtime_distribution_count']) is int and expected['runtime_distribution_count']==57 and len(rows)==57 and actual==expected['distributions'] and all(n.lower() not in ('pip','setuptools','wheel') for n,v in rows); assert json.loads(Path('/usr/local/share/metodobase/runtime-python-metadata.json').read_text())==[list(row) for row in rows]"
USER appuser
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8000') + '/health/ready', timeout=5)" || exit 1
EXPOSE ${PORT}
CMD ["/app/entrypoint.sh"]
