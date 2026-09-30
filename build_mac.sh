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
  --name ReceiptFlow \
  --icon "src/receipt_app/assets/Logo.icns" \
  --paths src \
  --collect-all keyring \
  --collect-all sqlcipher3 \
  --add-data "src/receipt_app/assets:receipt_app/assets" \
  main.py
printf '\nBuilt app should appear at: dist/ReceiptFlow.app\n'
