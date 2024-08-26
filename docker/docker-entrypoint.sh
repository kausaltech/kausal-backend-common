#!/bin/bash

set -e

DB_ENDPOINT=${DB_ENDPOINT:-db:5432}
wait_for_it=/scripts/wait-for-it.sh

# Wait for the database to get ready when not running in Kubernetes.
# In Kube, the migrations will be handled through a job.
if [ "$KUBERNETES_MODE" != "1" ] && [ "$1" = 'uwsgi' -o "$1" = 'celery' -o "$1" = 'runserver' ]; then
    echo "Waiting for database to get ready..."
    $wait_for_it $DB_ENDPOINT

    if [ "$1" = 'celery' ]; then
        # If we're in a celery container, wait for the app container
        # to start first so that migrations are run.
        if ! $wait_for_it -t 5 app:8000 ; then
            echo "App container didn't start, but we don't care"
        fi
    else
        echo "Running database migrations..."
        python manage.py migrate --no-input
    fi
    if [ -d '/docker-entrypoint.d' ]; then
        for scr in /docker-entrypoint.d/*.sh ; do
            echo "Running $scr"
            /bin/bash $scr
        done
    fi
    EXTRA_UWSGI_ARGS="--socket :8001"
fi

if [ "$1" = 'uwsgi' ]; then
    # Log to stdout
    exec uwsgi --ini /uwsgi.ini $EXTRA_UWSGI_ARGS
elif [ "$1" = 'celery' ]; then
    CELERY_ARGS=""
    if [ "$2" = "worker" -a "$KUBERNETES_MODE" = "1" ] ; then
      CELERY_ARGS="--concurrency=2"
    fi
    exec celery -A aplans "$2" -l INFO $CELERY_ARGS
elif [ "$1" = 'runserver' ]; then
    cd /code
    exec python manage.py runserver 0.0.0.0:8000
fi

exec "$@"
