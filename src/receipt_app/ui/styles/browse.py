"""Browse-page component styles."""

from .tokens import themed

BROWSE_QSS = themed(r'''
QFrame#BrowseFilterCard {
    border-radius: @radius_card@;
}

QLineEdit#BrowseSearchInput {
    font-size: 14px;
}

QCheckBox#BrowseGroupCheck {
    font-family: @font_regular@;
    font-size: 13px;
}

QPushButton#BrowseExportButton,
QPushButton#BrowseRefreshButton,
QPushButton#BrowseTrashButton {
    font-size: 13px;
}

QFrame#BrowseResultsCard {
    border-radius: @radius_card@;
}

QTableView#BrowseTableView {
    border: none;
    border-top-left-radius: 17px;
    border-top-right-radius: 17px;
}

QTableView#BrowseTableView::item {
    padding: 8px 10px;
    border: none;
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
