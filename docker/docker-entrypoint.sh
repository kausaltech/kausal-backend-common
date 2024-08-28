#!/bin/bash

set -e

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
  echo "Populating test data..."
  if [ -z "$TEST_INSTANCE_IDENTIFIERS" ] ; then
    echo "You must set TEST_INSTANCE_IDENTIFIERS."
    exit 1
  fi

  for instance in $(echo $TEST_INSTANCE_IDENTIFIERS | sed -e 's/,/ /g') ; do
    echo "Populating instance ${instance}..."
    python load_nodes.py --config configs/${instance}.yaml --update-instance
  done
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
    if [ $needs_migrations -eq -1 ]; then
        echo "Running database migrations..."
        python manage.py migrate --no-input
        if [ "$TEST_MODE" == "1" ]; then
            populate_paths_test_instances
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
