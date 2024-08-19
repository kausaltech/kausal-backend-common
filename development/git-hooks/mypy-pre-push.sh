#!/bin/bash

set -euo pipefail

mypy . | mypy-baseline filter --allow-unsynced
