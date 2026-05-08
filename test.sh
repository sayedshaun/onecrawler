#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

PYTHON_BIN="${PYTHON:-python3}"

"$PYTHON_BIN" -m unittest discover -s tests -p "test_*.py" -v
