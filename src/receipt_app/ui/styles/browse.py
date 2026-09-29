"""Browse-page component styles."""

from .tokens import themed

BROWSE_QSS = themed(r'''
QFrame#BrowseFilterCard {
    border-radius: @radius_card@;
}

QLineEdit#BrowseSearchInput {
    font-size: 14px;
}

QPushButton#BrowseExportButton,
QPushButton#BrowseDeleteSelectedButton,
QPushButton#BrowseRefreshButton,
QPushButton#BrowseTrashButton {
    font-size: 13px;
}

QPushButton#BrowseDeleteSelectedButton {
    background: @coral_soft@;
    color: #c8574c;
    border: 1px solid @coral_border@;
    border-radius: @radius_control@;
    padding: 9px 14px;
}

QPushButton#BrowseDeleteSelectedButton:hover {
    background: @coral@;
    color: @white@;
    border-color: @coral@;
}

QPushButton#BrowseSearchSelectAllButton {
    background: @surface_alt@;
    color: @bordeaux_mid@;
    border: 1px solid #d9c8c1;
    border-radius: @radius_control@;
    padding: 9px 14px;
}

QPushButton#BrowseSearchSelectAllButton:hover {
    background: #f7ebe6;
    color: @bordeaux@;
    border-color: #c8afa6;
}

QLabel#BrowseSelectionStatus {
    color: @text_muted@;
    font-family: @font_body@;
    font-size: 12px;
}

QFrame#BrowseResultsCard {
    border-radius: @radius_card@;
}

QScrollArea#BrowseGroupsScroll,
QScrollArea#BrowseGroupsScroll > QWidget > QWidget,
QWidget#BrowseGroupsContainer {
    background: @surface@;
    border: none;
}

QFrame#BrowseDateGroup {
    background: @surface@;
    border: 1px solid @border@;
    border-radius: 14px;
}

QFrame#BrowseDateHeader {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 @bordeaux@,
        stop:0.72 @bordeaux_mid@,
        stop:1 #7d1025);
    border: 1px solid @bordeaux_mid@;
    border-radius: 12px;
    min-height: 46px;
}

QPushButton#BrowseDateToggle {
    background: transparent;
    color: @white@;
    border: none;
    border-radius: 0;
    text-align: left;
    padding: 11px 10px;
    font-family: @font_regular@;
    font-size: 14px;
}

QPushButton#BrowseDateToggle:hover {
    background: rgba(255, 255, 255, 0.07);
}

QLabel#BrowseDateCount {
    color: rgba(255, 250, 247, 0.78);
    font-family: @font_body@;
    font-size: 12px;
}

QCheckBox#BrowseDateSelectAll {
    color: @white@;
    font-family: @font_regular@;
    font-size: 12px;
    spacing: 7px;
}

QFrame#BrowseDateContent {
    background: @surface@;
    border: none;
    border-bottom-left-radius: 12px;
    border-bottom-right-radius: 12px;
}

QTableWidget#BrowseDateTable,
QTableWidget#BrowseSearchTable {
    background: @surface@;
    alternate-background-color: #fcfaf8;
    color: @text@;
    border: none;
    border-top: 1px solid #eadfd9;
    border-bottom: 1px solid #eadfd9;
    border-bottom-left-radius: 11px;
    border-bottom-right-radius: 11px;
    gridline-color: transparent;
    selection-background-color: #e5f3f6;
    selection-color: @text@;
    outline: 0;
    font-family: @font_body@;
    font-size: 13px;
}

QTableWidget#BrowseDateTable::item,
QTableWidget#BrowseSearchTable::item {
    padding: 8px 10px;
    border: none;
    border-bottom: 1px solid #efe6e0;
}

QTableWidget#BrowseSearchTable {
    border: 1px solid @border@;
    border-radius: 12px;
}

QHeaderView#BrowseDateTableHeader::section {
    background: #f8efeb;
    color: #6e3337;
    border: none;
    border-right: 1px solid #eee2dc;
    border-bottom: 1px solid #eadfd9;
    padding: 8px 8px;
    font-family: @font_regular@;
    font-size: 11px;
}

QWidget#BrowseRowActions {
    background: transparent;
}

QPushButton#BrowseEditButton {
    background: @amethyst_soft@;
    color: #94378e;
    border: 1px solid @amethyst_border@;
    border-radius: 9px;
    padding: 5px 10px;
    min-height: 24px;
    font-size: 11px;
}

QPushButton#BrowseEditButton:hover {
    background: @amethyst@;
    color: @white@;
    border-color: @amethyst@;
}

QPushButton#BrowseDeleteButton {
    background: @coral_soft@;
    color: #c8574c;
    border: 1px solid @coral_border@;
    border-radius: 9px;
    padding: 5px 10px;
    min-height: 24px;
    font-size: 11px;
}

QPushButton#BrowseDeleteButton:hover {
    background: @coral@;
    color: @white@;
    border-color: @coral@;
}

QCheckBox#BrowseReceiptCheck {
    spacing: 0;
}

QFrame#BrowseEmptyState {
    background: @surface_alt@;
    border: 1px dashed @border_strong@;
    border-radius: @radius_control@;
}

QLabel#BrowseEmptyTitle {
    color: @text_muted@;
    font-family: @font_body@;
    font-size: 14px;
}

QFrame#BrowseResultsFooter {
    background: @surface@;
    border: none;
    border-top: 1px solid #eadfd9;
    border-bottom-left-radius: 17px;
    border-bottom-right-radius: 17px;
}

QPushButton#BrowsePreviousButton,
QPushButton#BrowseNextButton {
    min-width: 82px;
    font-size: 13px;
}

QPushButton#BrowseNextButton {
    background: @cyan@;
    color: @white@;
    border: 1px solid @cyan@;
    border-radius: @radius_control@;
    padding: 9px 14px;
    min-height: 22px;
}

QPushButton#BrowseNextButton:hover {
    background: #1f7d93;
    border-color: #1f7d93;
}

QLabel#PaginationStatus,
QLabel#BrowseResultCount {
    color: #6d6669;
    font-family: @font_body@;
    font-size: 12px;
}

QLabel#BrowseResultCount {
    font-size: 13px;
}
''')
