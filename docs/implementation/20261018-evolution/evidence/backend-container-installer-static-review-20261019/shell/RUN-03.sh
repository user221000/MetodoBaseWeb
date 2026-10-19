set -eu; \
    printf '%s\n' \
        'deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] https://deb.debian.org/debian trixie main' \
        'deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] https://deb.debian.org/debian trixie-updates main' \
        'deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] https://security.debian.org/debian-security trixie-security main' \
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
