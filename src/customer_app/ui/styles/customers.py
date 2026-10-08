"""Customer workspace geometry and typography layered over shared tokens."""
from .tokens import themed

CUSTOMERS_QSS = themed(r'''
QWidget#CustomerDirectory, QWidget#CustomerProfileCard, QWidget#CustomerDetailsCard {
    background: @surface@;
    border: 1px solid @border@;
    border-radius: @radius_card@;
}
QLabel#CustomersTitle { color: @bordeaux@; font-family: @font_regular@; font-size: 38px; }
QFrame#CustomerDivider { background: @border@; border: none; }
QWidget#CustomersPage QPushButton { font-family: @font_body@; font-weight: 400; }
QTableWidget#CustomerDirectoryTable {
    border: none; border-radius: 0; background: @surface@;
}
QTableWidget#CustomerDirectoryTable::item {
    padding: 10px; border-bottom: 1px solid @border@;
}
QLabel#CustomerName { font-family: @font_regular@; font-size: 28px; color: @bordeaux@; }
QLabel#CustomerCaption { font-size: 13px; color: @text_muted@; border: none; background: transparent; }
QLabel#CustomerValue { font-family: @font_body@; font-size: 14px; border: none; background: transparent; }
QLabel#CustomerMetric { font-family: @font_body@; font-size: 16px; font-weight: 500; color: @bordeaux@; border: none; background: transparent; }
QLabel#CustomerEmpty { color: @text_muted@; padding: 12px; border: none; background: transparent; }
QLabel#CustomerStatus {
    background: @green_soft@; color: @green@; border: 1px solid @green_border@;
    border-radius: 10px; padding: 3px 8px; font-size: 12px;
}
QLabel#CustomerStatus[active="false"] {
    background: @surface_soft@; color: @text_muted@; border-color: @border@;
}
QScrollArea#CustomerOverviewScroll, QScrollArea#CustomerServiceScroll {
    border: none; background: @surface@;
}
QScrollArea#CustomerOverviewScroll > QWidget > QWidget,
QScrollArea#CustomerServiceScroll > QWidget > QWidget { background: @surface@; }
QTabWidget#CustomerDetailTabs::pane {
    background: @surface@; border: none;
}
QTabWidget#CustomerDetailTabs QTabBar::tab {
    font-family: @font_body@; padding: 10px 12px; font-size: 14px;
    background: transparent; color: @text_muted@; border: none;
    border-bottom: 2px solid transparent; border-radius: 0; margin-right: 8px;
}
QTabWidget#CustomerDetailTabs QTabBar::tab:selected {
    background: transparent; color: @bordeaux_mid@; border-bottom: 2px solid @bordeaux_mid@;
}
QTabWidget#CustomerDetailTabs QTabBar::tab:hover {
    background: @surface_soft@; color: @bordeaux@;
}
QWidget#CustomerDetailPage { background: @surface@; }
QTextEdit#CustomerNotes {
    background: @surface@; color: @text@; border: none;
    padding: 14px; font-family: @font_body@; font-size: 14px;
}
QTableWidget#CustomerJobHistory { border-radius: 0; border: none; }
QTableWidget#CustomerJobHistory QHeaderView::section {
    font-family: @font_body@; padding: 7px 8px; background: @surface@;
    color: @text_muted@; border: none; border-bottom: 1px solid @border_strong@;
}
QTableWidget#CustomerJobHistory::item { padding: 8px; border-bottom: 1px solid @border@; }
QSplitter#CustomerSplitter::handle { background: @canvas@; }
QLabel#FormSectionTitle { color: @bordeaux@; font-family: @font_regular@; font-size: 20px; padding-top: 10px; }
QFrame#FormCalendarPopup { background: @surface@; border: 1px solid @border_strong@; border-radius: 10px; }
QCalendarWidget#FormCalendar QWidget { background: @surface@; color: @text@; }
QCalendarWidget#FormCalendar QToolButton { background: @surface_soft@; color: @bordeaux_mid@; padding: 6px; border: none; }
QCalendarWidget#FormCalendar QAbstractItemView { border: none; border-radius: 0; selection-background-color: @bordeaux_mid@; selection-color: @white@; }
QCalendarWidget#FormCalendar QAbstractItemView::item { padding: 0; border: none; }
QCalendarWidget#FormCalendar QAbstractItemView::item:selected { background: @bordeaux_mid@; color: @white@; }
''')
