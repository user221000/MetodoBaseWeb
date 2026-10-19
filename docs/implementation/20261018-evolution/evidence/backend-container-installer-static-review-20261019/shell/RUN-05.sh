set -eu; \
    python -m pip --isolated install --no-cache-dir --no-index --no-deps --require-hashes --only-binary=:all: \
        --find-links=/tmp/psycopg-wheelhouse -r /tmp/psycopg-wheelhouse/built-wheel.lock; \
    python -m pip check; \
    mkdir -p /usr/local/share/metodobase/psycopg2-build; \
    cp /tmp/psycopg-wheelhouse/*.lock /tmp/psycopg-wheelhouse/*.tsv /tmp/psycopg-wheelhouse/*.txt /usr/local/share/metodobase/psycopg2-build/; \
    rm -rf /tmp/psycopg-wheelhouse
