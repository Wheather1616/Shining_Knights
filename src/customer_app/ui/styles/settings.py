"""Business settings cards, clear navigation and maroon selection controls."""
from .tokens import themed

SETTINGS_QSS = themed(r'''
QWidget#SettingsContent { background: transparent; }
QScrollArea#SettingsScroll { background: transparent; border: none; }
QScrollArea#SettingsScroll > QWidget > QWidget { background: transparent; }
QWidget#SettingsCard {
    background: @surface@; border: 1px solid @border@; border-radius: @radius_card@;
}
QWidget#SettingsCard QLabel, QWidget#SettingsCard QCheckBox { background: transparent; border: none; }
QListWidget#SettingsNavigation {
    background: @surface@; border: 1px solid @border@; border-radius: @radius_card@;
    padding: 8px; outline: none; font-size: 14px;
}
QListWidget#SettingsNavigation::item {
    color: @text_muted@; padding: 15px 8px; margin: 3px 0; border-radius: 9px;
}
QListWidget#SettingsNavigation::item:selected {
    background: @bordeaux_mid@; color: @white@;
}
QListWidget#SettingsNavigation::item:hover:!selected { background: @surface_soft@; }
QLabel#SettingsRowName { color: @text@; font-size: 14px; }
QLabel#SettingsPreview {
    background: @surface_soft@; color: @text_muted@; border: 1px solid @border@;
    border-radius: 9px; padding: 12px; font-size: 13px;
}
QLabel#SettingsSaveStatus { color: @text_muted@; font-size: 14px; }
QLabel#SettingsError { color: #8d332c; font-size: 14px; }
QWidget#RestoreWarning { background: #fff7e8; border: 1px solid #ecd3a1; border-radius: 12px; }
QWidget#RestoreWarning QLabel { background: transparent; border: none; }
QComboBox[role="settingsChoice"] {
    background: @bordeaux_mid@; color: @white@; border-color: @bordeaux_mid@;
    min-height: 26px; border-radius: @radius_control@; padding: 8px 34px 8px 12px;
}
QComboBox[role="settingsChoice"]:hover { background: @bordeaux@; }
QComboBox[role="settingsChoice"]:focus { border: 2px solid @cyan@; }
QComboBox[role="settingsChoice"]::down-arrow { image: @icon_down_white@; width: 14px; height: 14px; }
QComboBox[role="settingsChoice"] QAbstractItemView {
    background: @surface@; color: @text@;
    selection-background-color: @bordeaux_mid@; selection-color: @white@;
}
QComboBox[role="settingsChoice"]:disabled { background: #f0eae5; color: #71656d; border-color: @border@; }
QComboBox[role="settingsChoice"]:disabled::down-arrow { image: @icon_down@; }
QPushButton[role="link"] {
    background: transparent; color: #176478; border: none; font-family: @font_body@;
    padding: 5px 8px; min-height: 20px;
}
QPushButton[role="link"]:hover { background: @cyan_soft@; }
''')
