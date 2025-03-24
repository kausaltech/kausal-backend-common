#!/bin/bash

REPORT_PATH=/tmp/report.html
COVERAGE_XML_PATH=/tmp/coverage.xml
COVERAGE_HTML_PATH=/tmp/htmlcov
PYTEST_ARGS="--html=$REPORT_PATH --self-contained-html --cov=. --cov-branch --cov-report=xml:$COVERAGE_XML_PATH --cov-report=html:$COVERAGE_HTML_PATH --cov-report=term-missing $@"
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


function get_previous_coverage() {
    if [ -z "$BUILD_S3_BUCKET" -o -z "$BUILD_S3_ENDPOINT" ]; then
        echo "S3 env vars not configured."
        return 1
    fi

    previous_coverage_url="https://$BUILD_S3_ENDPOINT/$BUILD_S3_BUCKET/main-branch-coverage.xml"
    echo "Attempting to download previous coverage report..."
    if curl --fail -s -o /tmp/previous_coverage.xml "$previous_coverage_url"; then
        echo "Previous coverage report downloaded successfully."
        return 0
    else
        echo "No previous coverage report found. This might be the first run."
        return 1
    fi
}


function compare_coverage() {
    if [ ! -f /tmp/previous_coverage.xml ] || [ ! -f $COVERAGE_XML_PATH ]; then
        echo "Cannot compare coverage: missing files."
        return
    fi
    echo "Comparing build coverage to previous main branch coverage..."
    previous_coverage=$(grep -oP 'line-rate="\K[0-9.]*' /tmp/previous_coverage.xml | head -n 1)
    current_coverage=$(grep -oP 'line-rate="\K[0-9.]*' $COVERAGE_XML_PATH | head -n 1)

    if [ -z "$previous_coverage" ] || [ -z "$current_coverage" ]; then
        echo "Cannot extract coverage values"
        return
    fi

    previous_percentage=$(awk "BEGIN {printf \"%.0f\", $previous_coverage * 100}")
    current_percentage=$(awk "BEGIN {printf \"%.0f\", $current_coverage * 100}")

    echo "Previous coverage: $previous_percentage%"
    echo "Current coverage: $current_percentage%"

    if [ "$current_percentage" -lt "$previous_percentage" ]; then
        echo "⚠️ Warning: Coverage decreased from $previous_percentage% to $current_percentage%" >> $GITHUB_STEP_SUMMARY
    else
        echo "✅ Coverage maintained or increased from $previous_percentage% to $current_percentage%" >> $GITHUB_STEP_SUMMARY
    fi

}

function upload_report() {
    if [ -z "$AWS_ACCESS_KEY_ID" -o -z "$AWS_SECRET_ACCESS_KEY" -o -z "$BUILD_S3_BUCKET" -o -z "$BUILD_S3_ENDPOINT" ]; then
        echo "S3 not configured; not uploading test report or coverage report."
        return
    fi
    if [ -z "$BUILD_ID" ]; then
        echo "No build ID; not uploading test report or coverage report."
        return
    fi
    report_loc=s3://$BUILD_S3_BUCKET/$BUILD_ID/pytest-report.html
    coverage_xml_loc=s3://$BUILD_S3_BUCKET/$BUILD_ID/coverage.xml
    coverage_html_loc=s3://$BUILD_S3_BUCKET/$BUILD_ID/coverage-html/

    echo "Sending pytest report to ${report_loc}..."
    s3cmd --host $BUILD_S3_ENDPOINT --host-bucket $BUILD_S3_ENDPOINT put $REPORT_PATH $report_loc

    echo "Sending coverage XML to ${coverage_xml_loc}..."
    s3cmd --host $BUILD_S3_ENDPOINT --host-bucket $BUILD_S3_ENDPOINT put $COVERAGE_XML_PATH $coverage_xml_loc

    echo "Sending coverage HTML..."
    s3cmd --host $BUILD_S3_ENDPOINT --host-bucket $BUILD_S3_ENDPOINT put $COVERAGE_HTML_PATH/* $coverage_html_loc --recursive

    if [ $? -ne 0 ] ; then
        echo "Upload failed."
        return
    fi

    if [ -z "$GITHUB_OUTPUT" -o -z "$GITHUB_STEP_SUMMARY" ] ; then
        echo "GitHub env vars not configured; not outputting summary."
        return
    fi

    export TEST_REPORT_URL="https://${BUILD_S3_ENDPOINT}/${BUILD_S3_BUCKET}/${BUILD_ID}/pytest-report.html"
    export COVERAGE_HTML_URL="https://${BUILD_S3_ENDPOINT}/${BUILD_S3_BUCKET}/${BUILD_ID}/coverage-html/index.html"
    echo "test_report_url=${TEST_REPORT_URL}" >> $GITHUB_OUTPUT
    echo "coverage_report_url=${COVERAGE_HTML_URL}" >> $GITHUB_OUTPUT
    if [ $pytest_rc -eq 0 ] ; then
        echo "✅ Unit tests succeeded." >> $GITHUB_STEP_SUMMARY
    else
        echo "❌ Unit tests failed." >> $GITHUB_STEP_SUMMARY
    fi
    echo "🔗 [Test report](${TEST_REPORT_URL})" >> $GITHUB_STEP_SUMMARY
    echo "🔗 [Coverage report](${COVERAGE_HTML_URL})" >> $GITHUB_STEP_SUMMARY
}

import_test_db

if [ $SHOULD_CREATE_DB -ne "1" ] ; then
    PYTEST_ARGS="--reuse-db $PYTEST_ARGS"
fi

set +e
echo "Running pytest with args: $PYTEST_ARGS"
python run_tests.py $PYTEST_ARGS
pytest_rc=$?

upload_report
if get_previous_coverage; then
    compare_coverage
fi

# If this is a main branch build, update the main branch coverage
if [ "$GITHUB_REF" = "refs/heads/main" ]; then
    echo "Updating main branch coverage..."
    s3cmd --host $BUILD_S3_ENDPOINT --host-bucket $BUILD_S3_ENDPOINT put $COVERAGE_XML_PATH s3://$BUILD_S3_BUCKET/main-branch-coverage.xml
fi

exit $pytest_rc
