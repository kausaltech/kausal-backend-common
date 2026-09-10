#!/bin/bash
#
# Nightly database re-initialisation for the staging and testing environments.
#
#   refresh-db.sh staging   Trim the staging database down to test content, dump it
#                           into the testing backup repository, then re-initialise
#                           staging from the latest production dump.
#   refresh-db.sh testing   Re-initialise the testing database from the pruned dump
#                           that staging produced.
#
# Both modes end with `migrate`, so the restored dump is brought up to the schema
# of the image that runs this script, and with a cache flush.
#
# Environment:
#   DB_REFRESH_ENABLED           Must be "1". Set only by the refresh CronJob.
#   DEPLOYMENT_TYPE              Must match the mode (staging or testing).
#   DB_BACKUP_SECRET_PATH        Restic repository to restore from. For staging this is
#                                the read-only production repository, for testing the
#                                testing repository. Default /run/secrets/db-backup.
#   DB_REFRESH_TESTING_SECRET_PATH  (staging) Restic repository the pruned dump is
#                                written to. Default /run/secrets/testing-db-backup.
#   DB_REFRESH_TESTING_TAG       (staging) Tag for the pruned dump, e.g. watch-testing-fi.
#                                Defaults to DB_BACKUP_TAG with -staging- -> -testing-.
#   DB_TRIM_ARGS                 (staging) Extra arguments for destructively_trim_db,
#                                e.g. "--exclude-plan sunnydale".
#   DB_REFRESH_MAX_AGE_HOURS     (testing) Refuse dumps older than this. Default 12.
#   DB_REFRESH_EXTENSIONS        Extensions re-created after dropping the schema.
#                                Default "postgis".

set -eo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
BACKUP_SCRIPT="$SCRIPT_DIR/manage-db-backup.sh"

mode="$1"
if [ "$mode" != "staging" ] && [ "$mode" != "testing" ] ; then
    echo "Usage: $0 {staging|testing}"
    exit 2
fi
if [ "$DB_REFRESH_ENABLED" != "1" ] ; then
    echo "ERROR: DB_REFRESH_ENABLED is not set to 1; refusing to touch the database."
    exit 1
fi
if [ "$DEPLOYMENT_TYPE" != "$mode" ] ; then
    echo "ERROR: DEPLOYMENT_TYPE is '${DEPLOYMENT_TYPE}', but this is a ${mode} refresh; refusing."
    exit 1
fi
if [ -z "$DB_BACKUP_TAG" ] ; then
    echo "ERROR: DB_BACKUP_TAG must be set."
    exit 1
fi

extensions="${DB_REFRESH_EXTENSIONS-postgis}"

log() {
    echo "[$(date -u +%FT%TZ)] $*"
}

sql() {
    python manage.py dbshell -- -qAX -v ON_ERROR_STOP=1 "$@"
}

terminate_other_sessions() {
    # The app pods keep connections open, which would block DROP SCHEMA.
    echo "SELECT count(pg_terminate_backend(pid)) FROM pg_stat_activity
          WHERE datname = current_database() AND pid <> pg_backend_pid();" | sql -t
}

reset_schema() {
    log "Dropping schema public..."
    terminate_other_sessions
    {
        echo 'DROP SCHEMA public CASCADE;'
        echo 'CREATE SCHEMA public;'
        for ext in $extensions ; do
            echo "CREATE EXTENSION IF NOT EXISTS ${ext};"
        done
    } | sql
}

restore_and_migrate() {
    log "Restoring database from ${DB_BACKUP_SECRET_PATH:-/run/secrets/db-backup}${DB_RESTORE_TAG:+ (tag ${DB_RESTORE_TAG})}..."
    FORCE_ALLOW_RESTORE=1 "$BACKUP_SCRIPT" restore
    log "Running migrations..."
    python manage.py migrate --no-input
    log "Clearing cache..."
    python manage.py shell -c 'from django.core.cache import cache; cache.clear()'
}

refresh_staging() {
    testing_secret_path="${DB_REFRESH_TESTING_SECRET_PATH:-/run/secrets/testing-db-backup}"
    testing_tag="${DB_REFRESH_TESTING_TAG:-${DB_BACKUP_TAG/-staging-/-testing-}}"
    if [ "$testing_tag" == "$DB_BACKUP_TAG" ] ; then
        echo "ERROR: could not derive a testing tag from DB_BACKUP_TAG=${DB_BACKUP_TAG}; set DB_REFRESH_TESTING_TAG."
        exit 1
    fi
    if [ ! -d "$testing_secret_path" ] ; then
        echo "ERROR: testing backup secrets not mounted at ${testing_secret_path}."
        exit 1
    fi

    log "Trimming staging database to test content (destructively_trim_db ${DB_TRIM_ARGS})..."
    # shellcheck disable=SC2086
    python manage.py destructively_trim_db --no-confirm $DB_TRIM_ARGS

    log "Dumping pruned database to the testing repository (tag ${testing_tag})..."
    if ! DB_BACKUP_SECRET_PATH="$testing_secret_path" "$BACKUP_SCRIPT" snapshots > /dev/null 2>&1 ; then
        log "Testing repository not initialised yet; initialising."
        DB_BACKUP_SECRET_PATH="$testing_secret_path" "$BACKUP_SCRIPT" init
    fi
    DB_BACKUP_SECRET_PATH="$testing_secret_path" DB_BACKUP_TAG="$testing_tag" "$BACKUP_SCRIPT" backup

    log "Re-initialising staging from the latest production dump..."
    reset_schema
    restore_and_migrate
    log "Staging refresh done."
}

check_dump_freshness() {
    max_age_hours="${DB_REFRESH_MAX_AGE_HOURS:-12}"
    eval "$("$BACKUP_SCRIPT" export-config)"
    restic snapshots --json --no-lock --host '' --tag "$DB_BACKUP_TAG" latest | python3 - "$max_age_hours" "$DB_BACKUP_TAG" <<'PY'
import json, re, sys
from datetime import datetime, timedelta, timezone

max_age_hours, tag = float(sys.argv[1]), sys.argv[2]
snapshots = json.load(sys.stdin)
if not snapshots:
    sys.exit(f"ERROR: no snapshot tagged {tag} found")
# restic emits RFC 3339 with nanoseconds; Python parses at most microseconds.
ts = re.sub(r'(\.\d{6})\d+', r'\1', snapshots[-1]['time'])
taken = datetime.fromisoformat(ts)
age = datetime.now(timezone.utc) - taken
print(f"Latest {tag} snapshot {snapshots[-1]['short_id']} taken {taken.isoformat()} ({age} ago)")
if age > timedelta(hours=max_age_hours):
    sys.exit(f"ERROR: snapshot is older than {max_age_hours:g} hours; the staging refresh probably failed. Refusing to restore stale data.")
PY
}

refresh_testing() {
    log "Checking that a fresh pruned dump exists..."
    check_dump_freshness
    log "Re-initialising testing from the pruned dump..."
    reset_schema
    DB_RESTORE_TAG="$DB_BACKUP_TAG" restore_and_migrate
    log "Testing refresh done."
}

case "$mode" in
    staging) refresh_staging ;;
    testing) refresh_testing ;;
esac
