#!/bin/bash

TEST_RESULTS_DIR=${TEST_RESULTS_DIR:-/tmp/pytest-results}
if [ ! -d "$TEST_RESULTS_DIR" ]; then
    mkdir -p $TEST_RESULTS_DIR
fi
COVERAGE_XML_PATH=$TEST_RESULTS_DIR/pytest-coverage.xml
JUNIT_XML_PATH=$TEST_RESULTS_DIR/pytest-junit.xml

PYTEST_ARGS="--maxfail=20 --junitxml=$JUNIT_XML_PATH -o junit_family=legacy --cov=. --cov-branch --cov-report=xml:$COVERAGE_XML_PATH --cov-report=term-missing $@"
SHOULD_CREATE_DB=1

# Number of pytest-xdist workers. The default of 1 runs the suite in a single process, as
# before. See clone_worker_databases() for why this needs a database dump to restore from.
PYTEST_WORKERS=${PYTEST_WORKERS:-1}
TEST_DB=test_${POSTGRES_DATABASE}

# Insist on a literal count. We clone one database per worker up front, so we have to know how
# many there will be; xdist's own `auto` spelling would leave that to xdist and every
# `[ "$PYTEST_WORKERS" -le 1 ]` below would quietly evaluate false, running the suite in a
# single process while claiming to have set up workers.
if ! [[ $PYTEST_WORKERS =~ ^(0|[1-9][0-9]*)$ ]]; then
    echo "PYTEST_WORKERS must be a non-negative integer; got '$PYTEST_WORKERS'." >&2
    exit 1
fi

function import_test_db() {
    if [ -z "$BUILD_S3_BUCKET" -o -z "$BUILD_S3_ENDPOINT" ]; then
        echo "S3 env vars not configured."
        return
    fi
    if [ -z "$POSTGRES_DATABASE" ]; then
        echo "DB env vars not configured."
        return
    fi
    url="https://$BUILD_S3_ENDPOINT/$BUILD_S3_BUCKET/test-database.sql.gz"
    echo "Attempting to download database dump..."
    curl --fail -s -o /tmp/database.sql.gz "$url"
    if [ "$?" -ne 0 ] ; then
        echo "No database dump found"
        return
    fi
    echo "Test database dump found; restoring from dump"
    set -eo pipefail
    echo "DROP DATABASE IF EXISTS $TEST_DB ; CREATE DATABASE $TEST_DB" | psql postgres
    cat /tmp/database.sql.gz | gunzip | psql $TEST_DB > /dev/null
    SHOULD_CREATE_DB=0
}

# Each xdist worker needs its own database, named after the base one with a `_gwN` suffix.
# Left to itself, pytest-django builds every one of them by running the full migration chain,
# which takes minutes per worker and costs more than the parallelism gains back. Cloning the
# already-restored database instead takes well under a second each.
#
# That only works when there is a base database to clone, so without a dump to restore we
# fall back to a single process rather than pay for N migration runs.
function clone_worker_databases() {
    if [ "$PYTEST_WORKERS" -le 1 ]; then
        return
    fi
    if [ $SHOULD_CREATE_DB -ne 0 ]; then
        echo "No test database to clone from; running tests in a single process."
        PYTEST_WORKERS=1
        return
    fi
    echo "Cloning $TEST_DB into $PYTEST_WORKERS worker databases"
    set -eo pipefail
    for i in $(seq 0 $((PYTEST_WORKERS - 1))); do
        worker_db="${TEST_DB}_gw${i}"
        echo "DROP DATABASE IF EXISTS $worker_db ; CREATE DATABASE $worker_db TEMPLATE $TEST_DB" \
            | psql -v ON_ERROR_STOP=1 postgres > /dev/null
    done
    set +eo pipefail
}

import_test_db
clone_worker_databases

if [ $SHOULD_CREATE_DB -ne "1" ] ; then
    PYTEST_ARGS="--reuse-db $PYTEST_ARGS"
fi

# `loadfile` keeps every test from a file on one worker, so the per-module fixtures they share
# are built once instead of once per worker. It measured ~16% faster than the default `load`.
if [ "$PYTEST_WORKERS" -gt 1 ] ; then
    PYTEST_ARGS="-n $PYTEST_WORKERS --dist loadfile $PYTEST_ARGS"
fi

set +e
echo "Running pytest with args: $PYTEST_ARGS"
python run_tests.py $PYTEST_ARGS
pytest_rc=$?

exit $pytest_rc
