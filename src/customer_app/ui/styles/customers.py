"""Phase 2 Shining Knights customer directory and profile styles.

All selectors are scoped to customer widgets to avoid changing the Home,
Jobs, Settings, customer-edit forms or backend behaviour.
"""
from .tokens import themed

CUSTOMERS_QSS = themed(r'''
QWidget#CustomersPage { background: @canvas@; }
QWidget#CustomerWorkspace { background: transparent; }

QLabel#CustomersKicker {
    color: #b65b63; font-family: @font_body@; font-size: 11px;
    font-weight: 600; letter-spacing: 1px;
}
QLabel#CustomersTitle {
    color: @bordeaux@; font-family: @font_regular@; font-size: 39px;
}
QLabel#CustomersSubtitle {
    color: @text_muted@; font-family: @font_body@; font-size: 13px;
}
QWidget#CustomersPage QPushButton { font-family: @font_body@; }
QPushButton#CustomerAddButton, QPushButton#CustomerAddJobButton {
    background: @bordeaux_mid@; color: @white@; border: 1px solid @bordeaux_mid@;
    padding: 9px 16px; font-weight: 600; border-radius: 10px;
}
QPushButton#CustomerAddButton:hover, QPushButton#CustomerAddJobButton:hover {
    background: @bordeaux@; border-color: @bordeaux@;
}
QPushButton#CustomerExportButton {
    background: @cyan_soft@; border: 1px solid @cyan_border@;
    color: #176478; border-radius: 10px; padding: 9px 15px;
}
QPushButton#CustomerExportButton:hover {
    background: #dff1f5; border-color: @cyan@;
}
QPushButton#CustomerEditButton, QPushButton#CustomerEditJobButton {
    background: @surface@; color: @bordeaux@; border: 1px solid #e8cfc8;
    border-radius: 10px; padding: 8px 13px;
}
QPushButton#CustomerEditButton:hover, QPushButton#CustomerEditJobButton:hover {
    background: #fff2ef; border-color: #d9aaa0;
}
QPushButton#CustomerEditJobButton:disabled {
    background: @surface_soft@; color: #71656d; border-color: @border@;
}

QWidget#CustomerDirectory, QWidget#CustomerProfileCard, QWidget#CustomerDetailsCard {
    background: @surface@; border: 1px solid @border@;
    border-radius: @radius_card@;
}
QWidget#CustomerDirectory { background: @surface@; }
QLineEdit#CustomerSearch {
    background: @white@; border: 1px solid @border_strong@;
    border-radius: 10px; padding: 9px 12px; min-height: 27px;
    color: @text@; font-size: 13px;
}
QLineEdit#CustomerSearch:focus { border: 1px solid @cyan@; }
QLabel#CustomerDirectoryCount {
    color: @text_muted@; font-size: 12px; background: transparent;
}
QPushButton#CustomerDirectoryDetailsButton {
    background: transparent; border: none; color: #176478;
    padding: 0 3px 2px 3px; min-height: 18px; font-size: 12px;
}
QPushButton#CustomerDirectoryDetailsButton:hover {
    color: @cyan@; text-decoration: underline;
}
QTableWidget#CustomerDirectoryTable {
    background: @surface@; alternate-background-color: @surface@;
    border: none; border-radius: 0; gridline-color: transparent;
    selection-background-color: @cyan_soft@;
}
QTableWidget#CustomerDirectoryTable::item {
    background: transparent; border: none; padding: 0;
}

QScrollArea#CustomerOverviewScroll, QScrollArea#CustomerServiceScroll {
    background: transparent; border: none;
}
QScrollArea#CustomerOverviewScroll > QWidget > QWidget,
QScrollArea#CustomerServiceScroll > QWidget > QWidget { background: @surface@; }
QLabel#CustomerName {
    color: @bordeaux@; font-family: @font_regular@; font-size: 30px;
}
QLabel#CustomerStatus {
    background: @green_soft@; color: @green@; border: 1px solid @green_border@;
    border-radius: 10px; padding: 4px 12px; font-size: 12px;
    font-weight: 600;
}
QLabel#CustomerStatus[active="false"] {
    background: @surface_soft@; color: @text_muted@; border-color: @border@;
}
QLabel#CustomerInfoCaption {
    font-size: 10px; font-weight: 600; color: @text_subtle@;
    background: transparent;
}
QLabel#CustomerValue {
    font-family: @font_body@; font-size: 14px;
    color: @text@; border: none; background: transparent;
}
QWidget#CustomerQuickInfo { background: transparent; border: none; }
QWidget#CustomerInfoChip {
    background: #f8f6f3; border: 1px solid #f0eae5;
    border-radius: 10px;
}
QLabel#CustomerChipCaption {
    color: @text_subtle@; background: transparent; border: none;
    font-size: 10px; font-weight: 600;
}
QLabel#CustomerChipValue {
    color: @text@; background: transparent; border: none;
    font-size: 13px; font-weight: 500;
}
QFrame#CustomerDivider { background: @border@; border: none; }
QWidget#CustomerMetrics { background: transparent; border: none; }
QLabel#CustomerMetricCaption {
    color: @text_muted@; font-size: 11px; font-weight: 600;
    background: transparent;
}
QLabel#CustomerMetric {
    color: @bordeaux@; font-family: @font_regular@;
    font-size: 20px; background: transparent;
}
QLabel#CustomerEmpty {
    color: @text_muted@; font-size: 13px; padding: 13px;
    border: none; background: transparent;
}

QTabWidget#CustomerDetailTabs::pane { background: @surface@; border: none; }
QTabWidget#CustomerDetailTabs QTabBar::tab {
    background: transparent; color: @text_muted@;
    font-family: @font_body@; font-size: 14px;
    border: none; border-bottom: 2px solid transparent;
    padding: 11px 14px; margin-right: 8px; border-radius: 0;
}
QTabWidget#CustomerDetailTabs QTabBar::tab:selected {
    color: @bordeaux@; border-bottom: 2px solid @bordeaux_mid@;
    background: transparent; font-weight: 600;
}
QTabWidget#CustomerDetailTabs QTabBar::tab:hover:!selected {
    background: @surface_soft@; color: @bordeaux@;
}
QWidget#CustomerDetailPage { background: @surface@; }
QLabel#CustomerJobHeading {
    color: @bordeaux@; font-family: @font_regular@; font-size: 23px;
}
QLabel#CustomerJobCount { color: @text_muted@; font-size: 12px; }
QLabel#CustomerCaption {
    font-size: 12px; color: @text_muted@; border: none;
    background: transparent;
}
QTextEdit#CustomerNotes {
    background: @surface@; color: @text@; border: none;
    padding: 16px; font-family: @font_body@; font-size: 14px;
}
QTableWidget#CustomerJobHistory {
    background: @surface@; border: none; border-radius: 0;
    alternate-background-color: @surface@;
    selection-background-color: @cyan_soft@;
    selection-color: @text@;
    gridline-color: transparent;
}
QTableWidget#CustomerJobHistory QHeaderView::section {
    background: @surface@; color: @text_muted@;
    border: none; border-bottom: 1px solid @border_strong@;
    padding: 10px 9px; font-family: @font_body@; font-size: 12px;
}
QTableWidget#CustomerJobHistory::item {
    padding: 8px; border: none; border-bottom: 1px solid @border@;
}
QTableWidget#CustomerJobHistory::item:selected {
    background: @cyan_soft@; color: @text@;
}
QSplitter#CustomerSplitter::handle { background: @canvas@; }
QSplitter#CustomerSplitter::handle:hover { background: @cyan_border@; }

/* Existing service forms and calendar retain their documented behaviour. */
QLabel#FormSectionTitle {
    color: @bordeaux@; font-family: @font_regular@;
    font-size: 20px; padding-top: 10px;
}
QFrame#FormCalendarPopup {
    background: @surface@; border: 1px solid @border_strong@; border-radius: 10px;
}
QCalendarWidget#FormCalendar QWidget { background: @surface@; color: @text@; }
QCalendarWidget#FormCalendar QToolButton {
    background: @surface_soft@; color: @bordeaux_mid@;
    padding: 6px; border: none;
}
QCalendarWidget#FormCalendar QAbstractItemView {
    border: none; border-radius: 0;
    selection-background-color: @bordeaux_mid@; selection-color: @white@;
}
QCalendarWidget#FormCalendar QAbstractItemView::item { padding: 0; border: none; }
QCalendarWidget#FormCalendar QAbstractItemView::item:selected {
    background: @bordeaux_mid@; color: @white@;
}
''')
