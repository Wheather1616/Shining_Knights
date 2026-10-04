#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -x .venv/bin/python ]]; then
    python3 -m venv .venv
fi
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install --only-binary=:all: -r requirements.txt
.venv/bin/python -c "from sqlcipher3 import dbapi2; c=dbapi2.connect(':memory:'); assert c.execute('PRAGMA cipher_version').fetchone(), 'SQLCipher unavailable'; c.close()"
echo 'Setup complete. Run: bash run_mac.sh'
