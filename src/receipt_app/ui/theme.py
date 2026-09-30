"""ReceiptFlow runtime theme helpers.

The design system references the bundled Idiqlat family by name. Qt still needs
those font files registered before the application stylesheet is applied.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
FONT_DIR = ASSETS_DIR / "fonts"

IDIQLAT_FILES = (
    "Idiqlat-Regular.ttf",
    "Idiqlat-Light.ttf",
    "Idiqlat-ExtraLight.ttf",
)


def load_application_fonts() -> tuple[str, ...]:
    """Register the bundled Idiqlat fonts and set the default UI font.

    Missing files are ignored so development builds remain launchable. The QSS
    includes sensible system fallbacks when Idiqlat has not been copied into
    ``receipt_app/assets/fonts`` yet.
    """

    families: list[str] = []
    for filename in IDIQLAT_FILES:
        path = FONT_DIR / filename
        if not path.exists():
            continue
        font_id = QFontDatabase.addApplicationFont(str(path))
        if font_id < 0:
            continue
        for family in QFontDatabase.applicationFontFamilies(font_id):
            if family not in families:
                families.append(family)

    app = QApplication.instance()
    if app is not None:
        preferred = "Idiqlat Light" if "Idiqlat Light" in families else "Idiqlat"
        if preferred in families:
            app.setFont(QFont(preferred, 10))

    return tuple(families)
