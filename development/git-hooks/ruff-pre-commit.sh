#!/bin/bash

# Check against the changed files
exec ruff check --force-exclude --output-format concise "$@" | ondivi --baseline HEAD
