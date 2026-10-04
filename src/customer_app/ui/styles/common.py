"""Shared scrollbar treatment retained from the receipt application.

Customer controls and tables are defined in their own shared component layers.
"""
from .tokens import themed

COMMON_QSS = themed(r'''
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 4px 1px 4px 1px;
}

QScrollBar::handle:vertical {
    background: rgba(37, 142, 166, 0.30);
    border-radius: 4px;
    min-height: 26px;
}

QScrollBar::handle:vertical:hover {
    background: rgba(37, 142, 166, 0.48);
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
}
''')
