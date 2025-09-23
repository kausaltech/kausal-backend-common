#!/bin/bash

set -eo pipefail

DB_ENDPOINT=${DB_ENDPOINT:-db:5432}
APP_ENDPOINT=${APP_ENDPOINT:-app:8000}

wait_for_it=/scripts/wait-for-it.sh

function wait_for_db {
    # Wait for the database to get ready when not running in Kubernetes.
    # In Kube, the migrations will be handled through a job.
    if [ "$KUBERNETES_MODE" == "1" ] ; then
        return
    fi
    echo "Waiting for database to get ready..."
    $wait_for_it "$DB_ENDPOINT"
}

function populate_paths_test_instances() {
  echo "Populating Kausal Paths database with test data..."
  if [ -z "$TEST_INSTANCE_IDENTIFIERS" ] ; then
    echo "You must set TEST_INSTANCE_IDENTIFIERS."
    exit 1
  fi

  for instance in $(echo $TEST_INSTANCE_IDENTIFIERS | sed -e 's/,/ /g') ; do
    echo "Populating instance ${instance}..."
    python load_nodes.py --config configs/${instance}.yaml --update-instance
  done
}

function populate_watch_test_data() {
  for var in TEST_DB_FILE TEST_DB_S3_BUCKET TEST_DB_S3_ENDPOINT AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY ; do
      [ -z "${!var}" ] && { echo "$var is not set" >&2; exit 1; }
  done

  echo "Downloading test database dump from S3..."
  s3cmd get "s3://${TEST_DB_S3_BUCKET}/${TEST_DB_FILE}" /tmp/test-db.sql.gz \
    --host "${TEST_DB_S3_ENDPOINT}" \
    --host-bucket "${TEST_DB_S3_ENDPOINT}"

  echo "Deleting and recreating database..."
  DB_HOST=${DB_ENDPOINT%:*}
  DB_PORT=${DB_ENDPOINT##*:}
  dropdb -h $DB_HOST -p $DB_PORT -U $DB_USER --if-exists $DB_NAME -f
  createdb -h $DB_HOST -p $DB_PORT -U $DB_USER -T template0 -l fi_FI.UTF-8 $DB_NAME
  psql -h $DB_HOST -p $DB_PORT -U $DB_USER -c "CREATE EXTENSION postgis" $DB_NAME
  echo "Populating Kausal Watch database with test data..."
  gunzip -c /tmp/test-db.sql.gz | psql -h $DB_HOST -p $DB_PORT -U $DB_USER -v ON_ERROR_STOP=1 $DB_NAME > /dev/null
}

needs_app=0
needs_migrations=0
needs_db=0

case "$1" in
    uwsgi|gunicorn|runserver|"")
        needs_db=1
        needs_migrations=1
        ;;
    celery)
        needs_db=1
        needs_app=1
        ;;
esac

if [ $needs_db -eq 1 ]; then
    wait_for_db
    if [ $needs_migrations -eq 1 ] && [ "$KUBERNETES_MODE" != "1" ]; then
        echo "Running database migrations..."
        python manage.py migrate --no-input
        if [ "$TEST_MODE" == "1" ]; then
          if [ -f '/code/paths/settings.py' ]; then
            populate_paths_test_instances
          elif [ -f '/code/aplans/settings.py' ]; then
            populate_watch_test_data
          else
            echo "No Django settings file recognized for Kausal Paths or Watch." >& 2
            exit 2
          fi
        fi
    fi
    if [ -d '/docker-entrypoint.d' ]; then
        for scr in /docker-entrypoint.d/*.sh ; do
            echo "Running $scr"
            /bin/bash "$scr"
        done
    fi
fi

if [ $needs_app -eq 1 ]; then
    if ! $wait_for_it -t 60 "$APP_ENDPOINT" ; then
        echo "App container didn't start, but we don't care"
    fi
fi

case "$1" in
    uwsgi)
        exec uwsgi --ini /uwsgi.ini
        ;;
    gunicorn|"")
        exec gunicorn -c /code/kausal_common/docker/gunicorn.conf.py
        ;;
    celery)
        CELERY_ARGS=""
        if [ "$2" = "worker" ] && [ "$KUBERNETES_MODE" = "1" ] ; then
            CELERY_ARGS="--concurrency=2"
        fi
        exec celery -A "${CELERY_APPLICATION}" "$2" -l INFO $CELERY_ARGS
        ;;
    runserver)
        cd /code
        exec python manage.py runserver 0.0.0.0:8000
        ;;
    *) exec "$@"
esac
