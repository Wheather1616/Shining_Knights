#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ ! -f "$project_dir/src/customer_app/__main__.py" ]]; then
    echo 'Missing src/customer_app/__main__.py.' >&2
    echo 'The application package belongs directly in src/customer_app, not src/customer_app/customer_app.' >&2
    exit 1
fi
if [[ ! -x "$project_dir/.venv/bin/python" ]]; then
    bash "$project_dir/setup_mac.sh"
fi
# Starting from src makes the intended package take precedence over stray outer folders.
cd "$project_dir/src"
exec "$project_dir/.venv/bin/python" -m customer_app
