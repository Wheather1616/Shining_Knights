#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
export PYTHONPATH="$PWD/src"

# Help Qt/PySide6 find the native macOS platform plugin when running from source.
QT_PLUGIN_DIR=$(python - <<'PY'
from pathlib import Path
import PySide6
root = Path(PySide6.__file__).resolve().parent
for candidate in (root / "Qt" / "plugins", root / "plugins"):
    if (candidate / "platforms").exists():
        print(candidate)
        raise SystemExit(0)
raise SystemExit("Could not locate the PySide6 Qt plugins directory")
PY
)
export QT_PLUGIN_PATH="$QT_PLUGIN_DIR"
export QT_QPA_PLATFORM_PLUGIN_PATH="$QT_PLUGIN_DIR/platforms"

python -m receipt_app
