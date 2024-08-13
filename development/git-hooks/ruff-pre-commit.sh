#!/bin/bash

# Check against the changed files
exec ruff check --output-format concise "$@" | ondivi --baseline HEAD
