"""Global ReceiptFlow reset and typography defaults."""

from .tokens import themed

BASE_QSS = themed(r'''
QMainWindow {
    background: @canvas@;
}

QWidget {
    color: @text@;
    font-family: @font_body@;
    font-size: 14px;
}

QLabel {
    background: transparent;
}

QToolTip {
    background: @surface@;
    color: @text@;
    border: 1px solid @border@;
    border-radius: 8px;
    padding: 6px 8px;
    font-family: @font_body@;
    font-size: 12px;
}

/* ------------------------------------------------------------------
   Global modal dialogs

   macOS can keep its dark system palette for QMessageBox/QInputDialog
   even while the rest of ReceiptFlow uses a light custom stylesheet.
   Explicitly styling the modal surface prevents dark-on-dark text.
   ------------------------------------------------------------------ */
QMessageBox,
QInputDialog {
    background: @canvas@;
    color: @text@;
}

QMessageBox QLabel,
QInputDialog QLabel {
    background: transparent;
    color: @text@;
    font-family: @font_body@;
    font-size: 14px;
}

QMessageBox QLabel#qt_msgbox_label {
    color: @text@;
    min-width: 320px;
    padding: 4px 0;
}

QMessageBox QLabel#qt_msgbox_informativelabel {
    color: @text_muted@;
    font-size: 13px;
}

QMessageBox QPushButton,
QInputDialog QPushButton {
    background: @surface_alt@;
    color: @bordeaux_mid@;
    border: 1px solid #d9c8c1;
    border-radius: @radius_control@;
    padding: 8px 16px;
    min-width: 82px;
    min-height: 28px;
    font-family: @font_regular@;
    font-size: 13px;
}

QMessageBox QPushButton:hover,
QInputDialog QPushButton:hover {
    background: #f7ebe6;
    color: @bordeaux@;
    border-color: #c8afa6;
}

QMessageBox QPushButton:default,
QInputDialog QPushButton:default {
    background: @bordeaux_mid@;
    color: @white@;
    border-color: @bordeaux_mid@;
}

QMessageBox QPushButton:default:hover,
QInputDialog QPushButton:default:hover {
    background: @bordeaux@;
    border-color: @bordeaux@;
}

QInputDialog QLineEdit,
QInputDialog QDoubleSpinBox,
QInputDialog QSpinBox,
QInputDialog QComboBox {
    background: @white@;
    color: @text@;
    border: 1px solid @border_strong@;
    border-radius: @radius_control@;
    padding: 8px 10px;
    min-height: 26px;
    font-family: @font_body@;
    font-size: 14px;
}

QInputDialog QLineEdit:focus,
QInputDialog QDoubleSpinBox:focus,
QInputDialog QSpinBox:focus,
QInputDialog QComboBox:focus {
    border-color: @cyan@;
}
''')
