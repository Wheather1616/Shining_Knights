"""Complete light control states for the customer/job application."""
from .tokens import themed

CONTROLS_QSS = themed(r'''
QLineEdit, QPlainTextEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {
    background: @white@;
    color: @text@;
    border: 1px solid @border_strong@;
    border-radius: 8px;
    padding: 7px 10px;
    min-height: 22px;
    selection-background-color: #dff1f5;
    selection-color: @text@;
    placeholder-text-color: @text_muted@;
}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QComboBox:focus {
    border-color: @cyan@;
}
QLineEdit:read-only {
    background: @surface_soft@;
    color: @text_muted@;
}
QLineEdit:disabled, QPlainTextEdit:disabled, QTextEdit:disabled, QComboBox:disabled,
QSpinBox:disabled, QDoubleSpinBox:disabled, QDateEdit:disabled {
    background: #f0eae5;
    color: #71656d;
    border-color: @border@;
}
QComboBox { padding-right: 28px; }
QComboBox::drop-down { border: none; width: 28px; }
QComboBox::down-arrow { image: @icon_down@; width: 14px; height: 14px; }
QComboBox QAbstractItemView {
    background: @surface@;
    color: @text@;
    selection-background-color: #dff1f5;
    selection-color: @text@;
    border: 1px solid @border_strong@;
    padding: 4px;
    outline: 0;
}
QPushButton {
    background: @surface_alt@;
    color: @bordeaux_mid@;
    border: 1px solid #d9c8c1;
    border-radius: 9px;
    padding: 8px 14px;
    min-height: 22px;
    font-family: @font_regular@;
    font-size: 14px;
}
QPushButton:hover { background: #f7ebe6; border-color: #c8afa6; }
QPushButton:pressed { background: #f0dfd8; }
QPushButton:focus { border: 2px solid @cyan@; padding: 7px 13px; }
QPushButton[role="primary"], QDialogButtonBox QPushButton:default {
    background: @bordeaux_mid@; color: @white@; border-color: @bordeaux_mid@;
}
QPushButton[role="primary"]:hover, QDialogButtonBox QPushButton:default:hover {
    background: @bordeaux@; color: @white@; border-color: @bordeaux@;
}
QPushButton[role="primary"]:pressed { background: @bordeaux_dark@; }
QPushButton[role="accent"] {
    background: @cyan_soft@; color: #176478; border-color: @cyan_border@;
}
QPushButton[role="accent"]:hover { background: #dff1f5; border-color: @cyan@; }
QPushButton[role="danger"] {
    background: @coral_soft@; color: #8d332c; border-color: @coral_border@;
}
QPushButton[role="danger"]:hover { background: #fce1db; border-color: @coral@; }
QPushButton:disabled, QPushButton[role="primary"]:disabled, QPushButton[role="accent"]:disabled,
QPushButton[role="danger"]:disabled {
    background: #f0eae5; color: #71656d; border-color: @border@;
}
QCheckBox, QRadioButton { color: @text@; spacing: 8px; }
QCheckBox:disabled, QRadioButton:disabled { color: #71656d; }
QCheckBox::indicator, QAbstractItemView::indicator {
    width: 17px; height: 17px;
    background: @white@; border: 1px solid #9d8c89; border-radius: 4px;
}
QCheckBox::indicator:hover, QAbstractItemView::indicator:hover { border-color: @cyan@; }
QCheckBox::indicator:checked, QAbstractItemView::indicator:checked {
    background: @bordeaux_mid@; border-color: @bordeaux_mid@; image: @icon_tick@;
}
QCheckBox::indicator:indeterminate, QAbstractItemView::indicator:indeterminate {
    background: @bordeaux_mid@; border-color: @bordeaux_mid@; image: @icon_partial@;
}
QCheckBox::indicator:disabled, QAbstractItemView::indicator:disabled {
    background: #f0eae5; border-color: #c7b9b1;
}
QCheckBox::indicator:checked:disabled, QAbstractItemView::indicator:checked:disabled {
    background: #71656d; border-color: #71656d; image: @icon_tick@;
}
QScrollBar:horizontal { background: @surface_soft@; height: 12px; margin: 2px; }
QScrollBar::handle:horizontal { background: #a6cbd3; border-radius: 4px; min-width: 30px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
''')
