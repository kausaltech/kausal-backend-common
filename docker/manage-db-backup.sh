#!/bin/bash

set -e
set -o pipefail

secret_path="${DB_BACKUP_SECRET_PATH:-/run/secrets/db-backup}"
required_vars="AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY RESTIC_PASSWORD S3_BUCKET S3_ENDPOINT"

if [ ! -d ${secret_path} ] ; then
    echo "Secrets not mounted at ${secret_path}, backups disabled."
    exit 0
fi


for fn in ${required_vars} ; do
  if [ ! -f ${secret_path}/${fn} ] ; then
    echo "Missing secret ${secret_path}/${fn}, aborting."
    exit 1
  fi
done

function get_secret() {
  cat ${secret_path}/$1
}

export AWS_ACCESS_KEY_ID=$(get_secret AWS_ACCESS_KEY_ID)
export AWS_SECRET_ACCESS_KEY=$(get_secret AWS_SECRET_ACCESS_KEY)
export RESTIC_PASSWORD_FILE=${secret_path}/RESTIC_PASSWORD
export RESTIC_REPOSITORY="s3:https://$(get_secret S3_ENDPOINT)/$(get_secret S3_BUCKET)"

if [ -z "$1" ] ; then
    echo "Usage: $0 {init|backup|restore|save|snapshots|export-config}"
    exit 2
fi

if [ "$1" == "export-config" ] ; then
    echo "  export AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}"
    echo "  export AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}"
    echo "  export RESTIC_PASSWORD_FILE=${RESTIC_PASSWORD_FILE}"
    echo "  export RESTIC_REPOSITORY=${RESTIC_REPOSITORY}"
    exit 0
fi

if [ "$1" == "init" ] ; then
    restic init
    exit 0
fi

if [ "$1" == "snapshots" ] ; then
    restic snapshots --no-lock
    exit 0
fi

function check_database_populated() {
    # Check if we already have tables in the database
    tmpf=$(mktemp)
    echo "select count(*) from information_schema.tables where table_schema = 'public';" | python manage.py dbshell -- -qtAX -o "$tmpf"
    nr_tables=$(cat "$tmpf")
    rm "$tmpf"

    # Return the number of tables via echo so caller can capture it
    echo "$nr_tables"
}

function do_backup() {
    if [ -z "$DATABASE_URL" ] ; then
        if [ -z "$PGPASSFILE" ] || [ ! -r "$PGPASSFILE" ] ; then
            echo PGPASSFILE must be set and the file pointed by it readable. Alternatively, set DATABASE_URL.
            exit 1
        fi

        # Work around kubernetes secret mount permission limitations
        pgpasstmp=$(mktemp)
        cat "$PGPASSFILE" > "$pgpasstmp"
        export PGPASSFILE="$pgpasstmp"

        database=$(cat "$PGPASSFILE" | cut -d ':' -f 3)
    else
        database="$DATABASE_URL"
    fi
    datatmp=$(mktemp)

    echo "Generating dump..."
    pg_dump -c -O "$database" > "$datatmp"
    echo "Uploading to restic..."
    cat "$datatmp" | restic backup --no-cache --stdin-filename database.sql --stdin
    echo "Pruning old backups..."
    restic forget --prune --keep-within-hourly 48h --keep-within-daily 30d --keep-within-weekly 1y --keep-monthly unlimited
    rm "$datatmp"
    if [ -z "$DATABASE_URL" ] ; then
        rm "$pgpasstmp"
    fi
}

function do_restore() {
    echo "Checking database status..."

    nr_tables=$(check_database_populated)

    # If we have 10 or more tables, consider the database populated
    if [ "$nr_tables" -ge 10 ] ; then
        echo "ERROR: Database appears to be populated (found $nr_tables tables)."
        # Check if forcing is allowed
        if [ -n "$FORCE_ALLOW_RESTORE" ] ; then
            # Never allow restore in production, even when forced
            if [ "$DEPLOYMENT_TYPE" == "production" ] ; then
                echo "ERROR: Restore is not allowed in production environment, even with FORCE_ALLOW_RESTORE."
                exit 1
            fi
            echo "WARNING: FORCE_ALLOW_RESTORE is set. Proceeding with restore in $DEPLOYMENT_TYPE environment."
        else
            echo "ERROR: Refusing to restore to a populated database."
            echo "If you are in a staging/testing environment and want to force restore, set FORCE_ALLOW_RESTORE=1"
            echo "Note: Restore is never allowed in production environments."
            exit 1
        fi
    else
        echo "Database appears empty or minimally populated (found $nr_tables tables). Safe to restore."
    fi

    echo "Restoring from backup..."
    restic dump --no-lock latest database.sql | python manage.py dbshell
}

if [ "$1" == "backup" ] ; then
    do_backup
    exit 0
fi

if [ "$1" == "restore" ] ; then
    do_restore
    exit 0
fi

if [ "$1" == "save" ] ; then
    echo "Saving latest SQL dump to database.sql.bz2..."
    restic dump --no-lock latest database.sql | bzip2 > database.sql.bz2
    exit 0
fi
