"""Settings-page component styles."""

from .tokens import themed

SETTINGS_CORE_QSS = themed(r'''
QScrollArea#SettingsScroll { border: none; }

QLabel#SettingsAccentIcon {
    background: @amethyst_soft@;
    color: @amethyst@;
    border: 1px solid @amethyst_border@;
    border-radius: 15px;
    min-width: 30px;
    max-width: 30px;
    min-height: 30px;
    max-height: 30px;
    qproperty-alignment: AlignCenter;
}

QLabel#SettingsAccentIcon[accent="cyan"] {
    background: @cyan_soft@;
    border-color: @cyan_border@;
}

QLabel#SettingsAccentIcon[accent="coral"] {
    background: @coral_soft@;
    border-color: @coral_border@;
}

QLabel#SettingsAccentIcon[accent="amethyst"] {
    background: @amethyst_soft@;
    border-color: @amethyst_border@;
}

QLabel#SettingsHelper {
    font-size: 12px;
}

QLabel#SettingsMiniLabel,
QLabel#PaymentSurchargeLabel {
    color: #514a50;
    font-family: @font_regular@;
    font-size: 11px;
}

QFrame#SettingsVerticalDivider {
    background: #eadfd9;
    border: none;
    min-width: 1px;
    max-width: 1px;
}

QLineEdit#ReadOnlySetting {
    background: @surface_soft@;
    color: #625a60;
}

QLabel#SecurityStatus {
    background: @green_soft@;
    color: @green@;
    border: 1px solid @green_border@;
    border-radius: 10px;
    padding: 8px 10px;
    font-family: @font_regular@;
    font-size: 11px;
}

QSpinBox#SettingsCompactSpin { min-width: 95px; }
QComboBox#SettingsCategoryCombo { min-width: 165px; }

QFrame#SettingsMiniCard {
    background: @surface_alt@;
    border: 1px solid #eadfd9;
    border-radius: @radius_control@;
}

QDoubleSpinBox#SettingsRateSpin {
    min-width: 96px;
    background: @white@;
}

QTableWidget#SettingsFieldsTable {
    border-radius: @radius_control@;
}

QTableWidget#SettingsFieldsTable::item {
    padding: 6px 8px;
    border: none;
}

QPushButton#SettingsAddButton,
QPushButton#SettingsDangerButton {
    font-size: 12px;
}

QFrame#SettingsFooter {
    background: transparent;
    border-top: 1px solid #eadfd8;
}
''')

SETTINGS_CATALOG_QSS = themed(r'''
QTableWidget#ProductCatalogTable {
    border-radius: @radius_control@;
}

QTableWidget#ProductCatalogTable::item {
    padding: 6px 8px;
    border: none;
}

QTableWidget#ProductCatalogTable QDoubleSpinBox {
    min-width: 102px;
    background: @white@;
    border-radius: 9px;
    padding: 5px 8px;
}
''')

SETTINGS_SURCHARGE_QSS = themed(r'''
QLabel#SurchargePreview {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(168, 70, 160, 0.08),
        stop:0.5 rgba(215, 208, 200, 0.16),
        stop:1 rgba(37, 142, 166, 0.08));
    color: #625a60;
    border: 1px solid #e5d9df;
    border-radius: 10px;
    padding: 8px 10px;
    font-family: @font_body@;
    font-size: 11px;
}
''')
