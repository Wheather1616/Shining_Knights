"""Regression checks for readable control states with a dark initial OS palette."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtGui import QColor, QFont, QFontDatabase, QFontMetrics, QPalette, QPixmap
from PySide6.QtWidgets import QApplication, QComboBox, QLineEdit, QPushButton, QTableWidget
import pytest

from customer_app.ui.theme import apply_application_theme, load_application_fonts
from customer_app.ui import theme
from customer_app.ui.styles.tokens import TOKENS

def contrast(first, second):
    def luminance(colour):
        values = [component / 12.92 if component <= 0.04045 else ((component + 0.055) / 1.055) ** 2.4
                  for component in (colour.redF(), colour.greenF(), colour.blueF())]
        return sum(value * weight for value, weight in zip(values, (0.2126, 0.7152, 0.0722)))
    lighter, darker = sorted((luminance(first), luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)

@pytest.fixture
def themed_app(qapp):
    app = qapp
    dark = QPalette()
    dark.setColor(QPalette.ColorRole.Base, QColor('#202020'))
    dark.setColor(QPalette.ColorRole.Window, QColor('#202020'))
    dark.setColor(QPalette.ColorRole.Text, QColor('#eeeeee'))
    app.setPalette(dark)
    apply_application_theme(app)
    return app

def test_theme_replaces_dark_palette_for_all_colour_groups(themed_app):
    palette = themed_app.palette()
    for group in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive, QPalette.ColorGroup.Disabled):
        for text, background in ((QPalette.ColorRole.Text,QPalette.ColorRole.Base),
                                 (QPalette.ColorRole.WindowText,QPalette.ColorRole.Window),
                                 (QPalette.ColorRole.HighlightedText,QPalette.ColorRole.Highlight)):
            assert contrast(palette.color(group,text),palette.color(group,background)) >= 4.5

def test_effective_input_button_and_selection_colours_are_readable(themed_app):
    controls = [QLineEdit('Customer name'),QLineEdit('Every 8 weeks'),QPushButton('Save'),QTableWidget(1,1),QComboBox()]
    controls[1].setEnabled(False)
    controls[2].setProperty('role','primary')
    controls[4].addItems(['Scheduled','Completed'])
    try:
        for widget in controls:
            widget.ensurePolished()
            palette = widget.palette()
            group = QPalette.ColorGroup.Active if widget.isEnabled() else QPalette.ColorGroup.Disabled
            roles = (QPalette.ColorRole.ButtonText,QPalette.ColorRole.Button) if isinstance(widget,QPushButton) else (QPalette.ColorRole.Text,QPalette.ColorRole.Base)
            assert contrast(palette.color(group,roles[0]),palette.color(group,roles[1])) >= 4.5
        assert contrast(controls[3].palette().color(QPalette.ColorRole.HighlightedText),controls[3].palette().color(QPalette.ColorRole.Highlight)) >= 4.5
        assert contrast(controls[4].view().palette().color(QPalette.ColorRole.Text),controls[4].view().palette().color(QPalette.ColorRole.Base)) >= 4.5
    finally:
        for widget in controls: widget.close()

def test_bundled_fonts_and_indicator_images_load(themed_app):
    assert 'Idiqlat' in load_application_fonts()
    for key in ('icon_tick','icon_partial','icon_down','icon_right'):
        path = TOKENS[key][5:-2]
        pixmap = QPixmap(path)
        assert not pixmap.isNull(), path


@pytest.mark.parametrize('system,available,private,expected', [
    ('Sans Serif', ['Sans Serif', 'Helvetica Neue', 'Arial'], [], 'Helvetica Neue'),
    ('Sans Serif', ['Segoe UI', 'Arial'], [], 'Segoe UI'),
    ('Sans Serif', ['DejaVu Sans', 'Sans Serif'], [], 'DejaVu Sans'),
    ('System UI', ['System UI', 'Arial'], [], 'System UI'),
    ('.AppleSystemUIFont', ['.AppleSystemUIFont', 'Arial'], ['.AppleSystemUIFont'], 'Arial'),
    ('Missing font', ['Other installed font', 'Serif'], [], 'Other installed font'),
    ('Sans Serif', ['helvetica neue', 'Arial'], [], 'helvetica neue'),
])
def test_body_font_resolves_generic_missing_and_private_defaults(
        qapp, monkeypatch, system, available, private, expected):
    # Simulate platform inventories without rendering a font absent on this host.
    monkeypatch.setattr(QFontDatabase, 'families', lambda: available)
    monkeypatch.setattr(QFontDatabase, 'systemFont', lambda kind: QFont(system))
    monkeypatch.setattr(QFontDatabase, 'isPrivateFamily', lambda family: family in private)
    assert theme._body_font_family() == expected


def test_body_font_requires_a_usable_family(qapp, monkeypatch):
    monkeypatch.setattr(QFontDatabase, 'families', lambda: ['Sans Serif', 'Serif', 'Monospace'])
    monkeypatch.setattr(QFontDatabase, 'systemFont', lambda kind: QFont('Sans Serif'))
    with pytest.raises(RuntimeError, match='No usable font family'):
        theme._body_font_family()


def test_theme_reapplication_renders_with_an_available_body_font(qapp, qtbot):
    control = QLineEdit('Customer name')
    qtbot.addWidget(control)
    control.show()
    for _ in range(2):
        apply_application_theme(qapp)
        font = qapp.font()
        assert font.family() in QFontDatabase.families()
        assert font.family().casefold() not in {'sans serif', 'sans-serif', 'serif', 'monospace'}
        assert not QFontDatabase.isPrivateFamily(font.family())
        assert font.pixelSize() == 14
        assert font.weight() == QFont.Weight.Normal
        # Force font resolution rather than only inspecting the requested name.
        assert QFontMetrics(font).horizontalAdvance('Customer name') > 0
        control.grab()
