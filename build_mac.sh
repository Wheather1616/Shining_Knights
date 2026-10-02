#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
source .venv/bin/activate 2>/dev/null || true
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
pyinstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name ShiningKnights \
  --icon "src/customer_app/assets/Logo.icns" \
  --paths src \
  --collect-all keyring \
  --collect-all sqlcipher3 \
  --add-data "src/customer_app/assets:customer_app/assets" \
  main.py
printf '\nBuilt app should appear at: dist/ShiningKnights.app\n'
