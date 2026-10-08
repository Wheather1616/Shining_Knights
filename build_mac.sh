#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
if [[ ! -f src/customer_app/__main__.py ]]; then
    echo 'Expected the application package directly in src/customer_app.' >&2
    exit 1
fi
if [[ ! -x .venv/bin/python ]]; then
    bash setup_mac.sh
fi
.venv/bin/python -m pip install -r requirements-build.txt
build_args=(--noconfirm --clean --windowed --name ShiningKnights --paths src
    --collect-all keyring --collect-all sqlcipher3
    --add-data 'src/customer_app/assets:customer_app/assets')
# A native Mac icon was not supplied. Build successfully with the default icon.
if [[ -f src/customer_app/assets/Logo.icns ]]; then
    build_args+=(--icon 'src/customer_app/assets/Logo.icns')
fi
.venv/bin/python -m PyInstaller "${build_args[@]}" main.py
printf '\nBuilt app: dist/ShiningKnights.app\n'
