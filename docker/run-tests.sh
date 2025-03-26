#!/bin/bash

REPORT_PATH=/tmp/report.html
COVERAGE_XML_PATH=/tmp/coverage.xml
PYTEST_ARGS="--html=$REPORT_PATH --self-contained-html --cov=. --cov-branch --cov-report=xml:$COVERAGE_XML_PATH --cov-report=term-missing $@"
SHOULD_CREATE_DB=1

function import_test_db() {
    if [ -z "$BUILD_S3_BUCKET" -o -z "$BUILD_S3_ENDPOINT" ]; then
        echo "S3 env vars not configured."
        return
    fi
    if [ -z "$POSTGRES_DATABASE" ]; then
        echo "DB env vars not configured."
        return
    fi
    TEST_DB=test_${POSTGRES_DATABASE}
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

import_test_db

if [ $SHOULD_CREATE_DB -ne "1" ] ; then
    PYTEST_ARGS="--reuse-db $PYTEST_ARGS"
fi

set +e
echo "Running pytest with args: $PYTEST_ARGS"
python run_tests.py $PYTEST_ARGS
pytest_rc=$?

exit $pytest_rc
