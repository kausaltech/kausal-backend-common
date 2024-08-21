#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"

# Filter the files and store the result
mapfile -t filtered_files < <(printf '%s\n' "$@" | "${SCRIPT_DIR}/filter-mypy-ignores.py")

# Check if there are any files left after filtering
if [ ${#filtered_files[@]} -gt 0 ]; then
    # Run mypy on the filtered files
    set +e
    mypy_output=$(mypy "${filtered_files[@]}" )
    mypy_exit_code=$?
    if [ $mypy_exit_code -ne 0 ] && [ $mypy_exit_code -ne 1 ]; then
        echo "mypy crashed with exit code $mypy_exit_code. Exiting."
        echo "$mypy_output"
        exit $mypy_exit_code
    fi
    set -e
    echo "$mypy_output" | exec mypy-baseline filter --allow-unsynced --hide-stats
else
    echo "No files to check after filtering. Skipping mypy."
fi
