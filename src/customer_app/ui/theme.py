"""Bundled font loading and a consistent light Qt palette on Mac and Windows."""
from __future__ import annotations
from pathlib import Path

from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette
from PySide6.QtWidgets import QApplication

from .styles import APP_QSS
from .styles.tokens import TOKENS

ASSETS_DIR = Path(__file__).resolve().parent.parent / 'assets'
FONT_DIR = ASSETS_DIR / 'fonts'
_loaded_fonts: dict[Path, tuple[str, ...]] = {}


def load_application_fonts() -> tuple[str, ...]:
    """Load the same Idiqlat assets as ReceiptFlow, with readable system fallbacks."""
    families = []
    for name in ('Idiqlat-Regular.ttf','Idiqlat-Light.ttf','Idiqlat-ExtraLight.ttf'):
        path = FONT_DIR / name
        if not path.exists(): continue
        if path not in _loaded_fonts:
            font_id = QFontDatabase.addApplicationFont(str(path))
            _loaded_fonts[path] = tuple(QFontDatabase.applicationFontFamilies(font_id)) if font_id >= 0 else ()
        for family in _loaded_fonts[path]:
            if family not in families: families.append(family)
    app = QApplication.instance()
    if app is not None:
        family = 'Idiqlat' if 'Idiqlat' in families else app.font().family()
        font = QFont(family)
        font.setPixelSize(14)
        app.setFont(font)
    return tuple(families)


def apply_application_theme(app: QApplication | None = None) -> None:
    """Pair full QSS control states with a light palette, independent of OS Dark Mode."""
    app = app or QApplication.instance()
    if app is None: raise RuntimeError('Create QApplication before applying the theme.')
    app.setStyle('Fusion')
    palette = QPalette()
    roles = {
        QPalette.ColorRole.Window:TOKENS['canvas'],
        QPalette.ColorRole.WindowText:TOKENS['text'],
        QPalette.ColorRole.Base:TOKENS['surface'],
        QPalette.ColorRole.AlternateBase:TOKENS['surface_soft'],
        QPalette.ColorRole.Text:TOKENS['text'],
        QPalette.ColorRole.Button:TOKENS['surface_alt'],
        QPalette.ColorRole.ButtonText:TOKENS['bordeaux_mid'],
        QPalette.ColorRole.Highlight:'#dff1f5',
        QPalette.ColorRole.HighlightedText:TOKENS['text'],
        QPalette.ColorRole.ToolTipBase:TOKENS['surface'],
        QPalette.ColorRole.ToolTipText:TOKENS['text'],
        QPalette.ColorRole.PlaceholderText:TOKENS['text_muted'],
        QPalette.ColorRole.Link:'#176478',
        QPalette.ColorRole.LinkVisited:'#803578',
        QPalette.ColorRole.Light:TOKENS['white'],
        QPalette.ColorRole.Midlight:TOKENS['surface_soft'],
        QPalette.ColorRole.Mid:TOKENS['border_strong'],
        QPalette.ColorRole.Dark:'#9d8c89',
        QPalette.ColorRole.Shadow:'#71656d',
        QPalette.ColorRole.BrightText:TOKENS['white'],
    }
    for group in (QPalette.ColorGroup.Active,QPalette.ColorGroup.Inactive,QPalette.ColorGroup.Disabled):
        for role,value in roles.items(): palette.setColor(group,role,QColor(value))
    for role in (QPalette.ColorRole.WindowText,QPalette.ColorRole.Text,QPalette.ColorRole.ButtonText):
        palette.setColor(QPalette.ColorGroup.Disabled,role,QColor('#71656d'))
    palette.setColor(QPalette.ColorGroup.Disabled,QPalette.ColorRole.Base,QColor('#f0eae5'))
    app.setPalette(palette)
    load_application_fonts()
    app.setStyleSheet(APP_QSS)
