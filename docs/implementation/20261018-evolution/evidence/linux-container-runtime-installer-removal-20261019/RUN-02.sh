set -eu; \
    printf '%s\n' \
        'deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] https://deb.debian.org/debian trixie main' \
        'deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] https://deb.debian.org/debian trixie-updates main' \
        'deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] https://security.debian.org/debian-security trixie-security main' \
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
