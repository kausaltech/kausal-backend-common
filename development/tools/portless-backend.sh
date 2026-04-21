#!/bin/bash

if [ -z "$PORT" ]; then
  echo "PORT is not set"
  exit 1
fi

if [ -z "$PORTLESS_URL" ]; then
  echo "PORTLESS_URL is not set"
  exit 1
fi

export ADMIN_BASE_URL=$PORTLESS_URL
ALLOWED_HOSTS="$(echo "$PORTLESS_URL" | sed -e 's|^https://||' -e 's|^http://||' -e 's|:.*||')"
export ALLOWED_HOSTS

exec .venv/bin/python manage.py runserver "$@" 127.0.0.1:"$PORT"
