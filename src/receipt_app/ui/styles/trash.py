"""Trash / recovery dialog component styles."""

from .tokens import themed

TRASH_QSS = themed(r'''
QDialog#TrashDialog {
    background: @canvas@;
}

QLabel#TrashEyebrow {
    color: #7a3e42;
    font-family: @font_regular@;
    font-size: 12px;
    letter-spacing: 2px;
}

QLabel#TrashDisplayTitle {
    color: @bordeaux@;
    font-family: @font_regular@;
    font-size: 40px;
}

QLabel#TrashLead {
    color: #615960;
    font-family: @font_body@;
    font-size: 15px;
}

QFrame#TrashIconTile {
    background: @coral_soft@;
    border: 1px solid @coral_border@;
    border-radius: 18px;
}

QLabel#TrashIcon {
    background: transparent;
    border: none;
}

QFrame#TrashSummaryCard,
QFrame#TrashResultsCard {
    background: @surface@;
    border: 1px solid @border@;
    border-radius: @radius_card@;
}

QLabel#TrashSummaryTitle {
    color: @bordeaux@;
    font-family: @font_regular@;
    font-size: 22px;
}

QLabel#TrashSummaryHelp {
    color: @text_muted@;
    font-family: @font_body@;
    font-size: 13px;
}

QPushButton#TrashRestoreSelectedButton {
    background: @bordeaux_mid@;
    color: @white@;
    border: 1px solid @bordeaux_mid@;
    border-radius: @radius_control@;
    padding: 10px 16px;
    min-height: 26px;
    font-family: @font_regular@;
    font-size: 13px;
}

QPushButton#TrashRestoreSelectedButton:hover {
    background: @bordeaux@;
    border-color: @bordeaux@;
}

QPushButton#TrashRestoreSelectedButton:pressed {
    background: @bordeaux_dark@;
    border-color: @bordeaux_dark@;
}

QPushButton#TrashRestoreSelectedButton:disabled {
    background: #f5f1ee;
    color: #aaa09b;
    border-color: #e4dcd7;
}

QPushButton#TrashCloseButton {
    background: @surface_alt@;
    color: @bordeaux_mid@;
    border: 1px solid #d9c8c1;
    border-radius: @radius_control@;
    padding: 9px 14px;
    min-height: 26px;
    font-family: @font_regular@;
    font-size: 13px;
}

QPushButton#TrashCloseButton:hover {
    background: #f7ebe6;
    color: @bordeaux@;
    border-color: #c8afa6;
}

QLabel#TrashSelectionStatus {
    color: @bordeaux_mid@;
    font-family: @font_regular@;
    font-size: 12px;
}

QCheckBox#TrashSelectAll {
    color: @text_muted@;
    font-family: @font_regular@;
    font-size: 12px;
}

QTableWidget#TrashTable {
    background: @surface@;
    alternate-background-color: #fcfaf8;
    color: @text@;
    border: 1px solid @border@;
    border-radius: @radius_control@;
    gridline-color: transparent;
    selection-background-color: #fff7f5;
    selection-color: @text@;
    outline: 0;
    font-family: @font_body@;
    font-size: 13px;
}

QTableWidget#TrashTable::item {
    padding: 8px 10px;
    border: none;
    border-bottom: 1px solid #efe6e0;
}

QHeaderView#TrashTableHeader::section {
    background: #f8efeb;
    color: #6e3337;
    border: none;
    border-right: 1px solid #eee2dc;
    border-bottom: 1px solid #eadfd9;
    padding: 8px 8px;
    font-family: @font_regular@;
    font-size: 11px;
}

QWidget#TrashCheckWrap,
QWidget#TrashRowActions {
    background: transparent;
}

QCheckBox#TrashReceiptCheck {
    spacing: 0;
}

QPushButton#TrashRowRestoreButton {
    background: @coral_soft@;
    color: @bordeaux_mid@;
    border: 1px solid @coral_border@;
    border-radius: 9px;
    padding: 5px 10px;
    min-height: 22px;
    font-family: @font_regular@;
    font-size: 11px;
}

QPushButton#TrashRowRestoreButton:hover {
    background: #ffe7e1;
    color: @bordeaux@;
    border-color: @coral@;
}

QFrame#TrashEmptyState {
    background: @surface_alt@;
    border: 1px dashed @border_strong@;
    border-radius: @radius_control@;
}

QLabel#TrashEmptyTitle {
    color: @bordeaux@;
    font-family: @font_regular@;
    font-size: 20px;
}

QLabel#TrashEmptyBody {
    color: @text_muted@;
    font-family: @font_body@;
    font-size: 13px;
}
''')

__all__ = ["TRASH_QSS"]
