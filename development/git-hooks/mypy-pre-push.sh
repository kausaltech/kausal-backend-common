#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"

# Filter the files and store the result
filtered_files=$(printf '%s\n' "$@" | "${SCRIPT_DIR}/filter-mypy-ignores.py")

# Check if there are any files left after filtering
if [ -n "$filtered_files" ]; then
    # Run mypy on the filtered files
    echo "$filtered_files" | tr '\n' '\0' | xargs -0 mypy | exec mypy-baseline filter --allow-unsynced
else
    echo "No files to check after filtering. Skipping mypy."
fi
