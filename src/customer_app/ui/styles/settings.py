"""Compact editors and checkboxes inside field configuration tables."""
from .tokens import themed

SETTINGS_QSS = themed(r'''
QTableWidget#SettingsFieldsTable QLineEdit {
    margin: 4px; padding: 4px 7px; min-height: 21px;
    border-radius: 5px; background: @white@; color: @text@;
}
QTableWidget#SettingsFieldsTable QLineEdit:read-only { background: @surface_soft@; color: @text_muted@; }
QTableWidget#SettingsFieldsTable QPlainTextEdit {
    margin: 4px; padding: 4px 7px; border-radius: 5px;
}
QTableWidget#SettingsFieldsTable QPlainTextEdit:disabled {
    background: #f0eae5; color: #71656d;
}
QTableWidget#SettingsFieldsTable QCheckBox { background: transparent; padding-left: 12px; }
''')
