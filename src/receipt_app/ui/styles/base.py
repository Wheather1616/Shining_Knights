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
''')
