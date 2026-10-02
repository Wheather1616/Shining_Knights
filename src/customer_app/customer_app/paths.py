from __future__ import annotations

import os
import sys
from pathlib import Path


APP_NAME = "ShiningKnights"


def app_support_dir() -> Path:
    """Return the OS-appropriate ShiningKnights data directory."""

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
    return app_support_dir() / "data" / "customers.db"



def default_backup_dir() -> Path:
    """Return the local folder used for automatic database snapshots."""
    return app_support_dir() / "backups"

def default_import_folder() -> Path:
    downloads = Path.home() / "Downloads"

    if downloads.exists():
        return downloads

    return Path.home()


def legacy_settings_paths() -> list[Path]:
    """Locations used by older ShiningKnights versions."""

    if sys.platform == "win32":
        return [
            Path.home() / ".shiningknights" / "settings.json"
        ]

    return []