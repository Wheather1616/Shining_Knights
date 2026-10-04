#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
test_python="$project_dir/.venv/bin/python"
if [[ ! -x "$test_python" ]]; then
    echo 'Create the project virtual environment and install the test requirements first.' >&2
    exit 2
fi
exec "$test_python" "$project_dir/scripts/run_tests.py" "$@"
