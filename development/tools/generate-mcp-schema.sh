#!/bin/bash

set -xe

if [ ! -f ./graphql.config.yaml ]; then
  echo "graphql.config.yaml not found found in the current directory ($PWD)"
  exit 1
fi

if [ -d src/mcp_server ]; then
  mcp_server_path=src/mcp_server
else
  mcp_server_path=mcp_server
fi

PYTHONPATH="$(pwd)/src:$(pwd):$PYTHONPATH"
export PYTHONPATH

echo "Exporting schema..."
python manage.py export_schema aplans.schema > schema.graphql
echo "Generating Turms code..."
uvx turms gen

echo "Cleaning up generated code..."
ruff check --ignore I002,E501 --unsafe-fixes --fix "$mcp_server_path/__generated__/schema.py"

echo "Formatting generated code..."
ruff format "$mcp_server_path/__generated__/schema.py"

echo "Done!"
