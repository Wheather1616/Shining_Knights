"""Floating desktop receipt-panel component styles."""

from .tokens import themed

DESKTOP_QSS = themed(r'''
QFrame#DesktopPanel {
    background: @canvas@;
    border: 1px solid #e2d8d1;
    border-radius: 24px;
}

QWidget#DesktopDragHeader {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 @bordeaux@,
        stop:0.58 @bordeaux_mid@,
        stop:1 #861a36);
    border: 1px solid #78101f;
    border-radius: @radius_large@;
}

QLabel#DesktopDragHandle {
    color: rgba(255, 247, 244, 0.66);
    min-width: 18px;
}

QLabel#DesktopPanelTitle {
    color: #fffaf7;
    font-size: 28px;
}

QPushButton#DesktopOpenAppButton {
    background: rgba(255, 255, 255, 0.10);
    color: #fffaf7;
    border: 1px solid rgba(255, 255, 255, 0.24);
    border-radius: @radius_control@;
    padding: 7px 11px;
    min-height: 24px;
    font-size: 12px;
}

QPushButton#DesktopOpenAppButton:hover {
    background: rgba(255, 255, 255, 0.18);
    border-color: rgba(255, 255, 255, 0.36);
}

QPushButton#DesktopIconButton {
    background: rgba(255, 255, 255, 0.10);
    color: #fffaf7;
    border: 1px solid rgba(255, 255, 255, 0.24);
    border-radius: 16px;
    min-width: 32px;
    max-width: 32px;
    min-height: 32px;
    max-height: 32px;
    padding: 0;
}

QPushButton#DesktopIconButton:hover {
    background: rgba(248, 118, 102, 0.28);
    border-color: rgba(255, 255, 255, 0.38);
}

QFrame#DesktopFormCard { border-radius: @radius_large@; }
QWidget#DesktopEntryForm { background: transparent; }

QLabel#DesktopFieldLabel {
    color: @text@;
    font-family: @font_regular@;
    font-size: 12px;
    min-width: 112px;
}

QWidget#DesktopEntryForm QLineEdit,
QWidget#DesktopEntryForm QTextEdit,
QWidget#DesktopEntryForm QComboBox,
QWidget#DesktopEntryForm QDateEdit,
QWidget#DesktopEntryForm QDoubleSpinBox,
QWidget#DesktopEntryForm QSpinBox {
    padding: 5px 9px;
    min-height: 18px;
    font-size: 13px;
    border-radius: 11px;
}

QFrame#DesktopDivider { background: #eadfd9; border: none; }

QLabel#DesktopStatus {
    color: #187d94;
    font-family: @font_regular@;
    font-size: 11px;
}

QFrame#DesktopTodayCard {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #fff7f5,
        stop:1 #fbf0ef);
    border: 1px solid #ead9d4;
    border-radius: @radius_card@;
}

QLabel#DesktopTodayAccent {
    background: @amethyst@;
    border-radius: 5px;
}

QLabel#DesktopSubheading { font-size: 18px; }

QLabel#DesktopTodayCount {
    color: #7d7276;
    font-family: @font_regular@;
    font-size: 11px;
}

QPushButton#DesktopDropdownButton {
    background: @surface@;
    color: #5d555a;
    border: 1px solid #d9cec8;
    border-radius: 11px;
    padding: 7px 10px;
    min-height: 24px;
    text-align: left;
    font-size: 12px;
}

QPushButton#DesktopDropdownButton:hover {
    background: @white@;
    color: @bordeaux@;
    border-color: #c9b8b0;
}

QPushButton#DesktopDropdownButton:checked { border-color: @amethyst@; }

QFrame#DesktopDropdownPanel {
    background: @surface@;
    border: 1px solid #ddd1ca;
    border-radius: 13px;
}

QListWidget#DesktopReceiptList {
    background: @surface@;
    border: none;
    color: @text@;
    padding: 4px;
    outline: 0;
}

QListWidget#DesktopReceiptList::item { background: transparent; border: none; margin: 0; padding: 0; }
QListWidget#DesktopReceiptList::item:selected { background: #e5f3f6; color: @text@; }

QWidget#DesktopReceiptRow {
    background: @white@;
    border: 1px solid #e3d8d1;
    border-radius: 11px;
}

QLabel#DesktopReceiptRowLabel {
    color: #3a3338;
    font-family: @font_regular@;
    font-size: 11px;
}

QPushButton#MiniDeleteButton {
    padding: 5px 9px;
    min-height: 22px;
    font-size: 11px;
}

QPushButton#MiniEditButton {
    background: @amethyst_soft@;
    color: #94378e;
    border: 1px solid @amethyst_border@;
    border-radius: 9px;
    padding: 5px 9px;
    min-height: 22px;
    font-size: 11px;
}

QPushButton#MiniEditButton:hover {
    background: @amethyst@;
    color: @white@;
    border-color: @amethyst@;
}

QWidget#BrowseReceiptRow {
    background: @surface@;
    border: 1px solid @border@;
    border-radius: 11px;
}

QLabel#BrowseReceiptRowLabel {
    color: @text@;
    font-family: @font_regular@;
    font-size: 11px;
}

QWidget#ReceiptActionsWidget,
QWidget#DesktopFooter { background: transparent; }

QLabel#DesktopFooterHandle {
    color: #a99799;
}

QLabel#DesktopHint {
    color: #80777b;
    font-family: @font_body@;
    font-size: 10px;
}
''')
