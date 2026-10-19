printf '%s\n' \
        'deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] https://deb.debian.org/debian trixie main' \
        'deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] https://deb.debian.org/debian trixie-updates main' \
        'deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] https://security.debian.org/debian-security trixie-security main' \
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
