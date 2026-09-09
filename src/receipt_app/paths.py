from __future__ import annotations

import os
import sys
from pathlib import Path


APP_NAME = "ReceiptFlow"


def app_support_dir() -> Path:
    """Return the OS-appropriate ReceiptFlow data directory."""

    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")

        if local_app_data:
            return Path(local_app_data) / APP_NAME

        return Path.home() / "AppData" / "Local" / APP_NAME

    if sys.platform == "darwin":
        return (
            Path.home()
            / "Library"
            / "Application Support"
            / APP_NAME
        )

    # Linux / other Unix fallback.
    xdg_data_home = os.environ.get("XDG_DATA_HOME")

    if xdg_data_home:
        return Path(xdg_data_home) / APP_NAME

    return Path.home() / ".local" / "share" / APP_NAME


def default_db_path() -> Path:
    return app_support_dir() / "data" / "receipts.db"


def default_import_folder() -> Path:
    downloads = Path.home() / "Downloads"

    if downloads.exists():
        return downloads

    return Path.home()


def legacy_settings_paths() -> list[Path]:
    """Locations used by older ReceiptFlow versions."""

    if sys.platform == "win32":
        return [
            Path.home() / ".receiptflow" / "settings.json"
        ]

    return []