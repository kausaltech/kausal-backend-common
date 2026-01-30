#!/bin/bash

set -xe

if [ ! -f ./graphql.config.yaml ]; then
  echo "graphql.config.yaml not found found in the current directory ($PWD)"
  exit 1
fi

echo "Exporting schema..."
python manage.py export_schema aplans.schema > schema.graphql
echo "Generating Turms code..."
uvx turms gen

echo "Cleaning up generated code..."
ruff check --ignore I002,E501 --unsafe-fixes --fix mcp_server/__generated__/schema.py

echo "Formatting generated code..."
ruff format mcp_server/__generated__/schema.py

echo "Done!"
