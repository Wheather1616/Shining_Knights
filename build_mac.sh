#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
source .venv/bin/activate 2>/dev/null || true
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
pyinstaller \
  --windowed \
  --name ReceiptFlow \
  --paths src \
  main.py
printf '\nBuilt app should appear at: dist/ReceiptFlow.app\n'
