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
  --paths src \
  --add-data "src/receipt_app/assets/logo.jpg:receipt_app/assets" \
  main.py
printf '\nBuilt app should appear at: dist/ReceiptFlow.app\n'
