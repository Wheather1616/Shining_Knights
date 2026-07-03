from __future__ import annotations

import os
from pathlib import Path


def configure_qt_plugin_paths() -> None:
    """Ensure PySide6 can find the native Qt platform plugins on macOS.

    Some virtual environments do not expose Qt's plugin folder automatically.
    Without this path, Qt can fail on startup with: "Could not find the Qt
    platform plugin 'cocoa'". This function must run before importing
    PySide6.QtWidgets / QApplication.
    """
    if os.environ.get("QT_QPA_PLATFORM_PLUGIN_PATH"):
        return

    try:
        import PySide6  # type: ignore
    except Exception:
        return

    pyside_root = Path(PySide6.__file__).resolve().parent
    candidates = [
        pyside_root / "Qt" / "plugins",
        pyside_root / "plugins",
    ]

    for plugin_root in candidates:
        platform_root = plugin_root / "platforms"
        if platform_root.exists():
            os.environ.setdefault("QT_PLUGIN_PATH", str(plugin_root))
            os.environ.setdefault("QT_QPA_PLATFORM_PLUGIN_PATH", str(platform_root))
            return
