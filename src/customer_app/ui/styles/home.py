"""Modern, tightly scoped QSS for the Shining Knights dashboard."""
from .tokens import themed

HOME_QSS = themed(r'''
QScrollArea#HomePageScroll, QWidget#HomeDashboardContent {
    background: @canvas@; border: none;
}
QLabel#HomeEyebrow {
    color: #AE605F; font-family: @font_body@; font-size: 11px;
    font-weight: 700;
}
QLabel#HomeTitle {
    color: @bordeaux@; font-family: @font_regular@; font-size: 40px;
}
QLabel#HomeDate { color: @text_muted@; font-size: 13px; }
QPushButton#HomeSummaryCard {
    background: #FFF6F4; border: 1px solid #F1DEDA;
    border-radius: 18px; padding: 0; text-align: left;
}
QPushButton#HomeSummaryCard[tone="teal"] {
    background: #F2FBFC; border-color: #D6EBED;
}
QPushButton#HomeSummaryCard[tone="coral"] {
    background: #FFF7F2; border-color: #F1E1D8;
}
QPushButton#HomeSummaryCard:hover { border: 1px solid @bordeaux_mid@; }
QPushButton#HomeSummaryCard[tone="teal"]:hover { border-color: @cyan@; }
QPushButton#HomeSummaryCard[tone="coral"]:hover { border-color: @coral@; }
QPushButton#HomeSummaryCard:focus { border: 2px solid @cyan@; }
QLabel#HomeSummaryTitle {
    color: @text@; font-family: @font_body@; font-size: 15px; font-weight: 600;
}
QLabel#HomeSummaryCount {
    color: @bordeaux@; font-family: @font_regular@; font-size: 36px;
}
QLabel#HomeSummaryHint { color: @text_muted@; font-size: 12px; }
QLabel#HomeMetricArrow { color: @bordeaux@; font-size: 26px; }
QWidget#HomeContentCard {
    background: @surface@; border: 1px solid @border@; border-radius: 17px;
}
QLabel#HomeSectionTitle {
    color: @bordeaux@; font-family: @font_regular@; font-size: 23px;
}
QWidget#HomeOverdueNotice {
    background: @coral_soft@; border: 1px solid @coral_border@; border-radius: 10px;
}
QLabel#HomeOverdueText { color: #8D332C; font-size: 13px; }
QLabel#HomeEmpty { color: @text_muted@; font-size: 13px; padding: 13px 0; }
QLabel#HomeFootnote { color: @text_subtle@; font-size: 12px; }
QTableWidget#HomeVisits {
    background: @surface@; border: none; border-radius: 0;
    selection-background-color: @cyan_soft@; selection-color: @text@;
    gridline-color: @border@;
}
QTableWidget#HomeVisits::item {
    padding: 10px 12px; border: none; border-bottom: 1px solid @border@;
}
QTableWidget#HomeVisits::item:hover {
    background: #F4FBFC;
}
QTableWidget#HomeVisits::item:selected, QTableWidget#HomeVisits::item:selected:!active {
    background: #E9F5F7; color: @text@;
}
QTableWidget#HomeVisits QHeaderView::section {
    background: @surface@; color: @text_muted@;
    font-family: @font_body@; font-size: 12px; font-weight: 500;
    border: none; border-bottom: 1px solid @border@; padding: 9px 12px;
}
QWidget#HomeDetailsContent { background: transparent; border: none; }
QLabel#HomeDetailName {
    color: @text@; font-family: @font_body@; font-size: 20px; font-weight: 600;
}
QLabel#HomeDetailLine { color: @text_muted@; font-size: 13px; }
QLabel#HomeDetailCaption {
    color: @text_muted@; font-size: 11px; font-weight: 600;
}
QLabel#HomeDetailNotes { color: @text@; font-size: 13px; }
QFrame#HomeDetailDivider { color: @border@; border: none; background: @border@; max-width: 1px; }
QScrollArea#HomeBookingsScroll, QWidget#HomeBookingContent {
    background: @surface@; border: none;
}
QWidget#HomeBookingEntry { background: @surface@; border: none; }
QFrame#HomeBookingDivider { background: @border@; border: none; }
QPushButton#HomeCustomerLink {
    color: @text@; font-family: @font_body@; font-weight: 600;
    font-size: 14px; min-height: 18px; padding: 0;
    background: transparent; border: none; text-align: left;
}
QPushButton#HomeCustomerLink:hover { color: @bordeaux@; text-decoration: underline; }
QPushButton#HomeCustomerLink:focus { border: 1px solid @cyan@; }
QLabel#HomeBookingSuburb { color: @text_muted@; font-size: 12px; }
QLabel#HomeDueBadge {
    background: @coral_soft@; color: #A44032; border: none;
    border-radius: 6px; padding: 4px 8px; font-size: 12px;
}
QLabel#HomeDueBadge[overdue="true"] {
    background: #F9DED9; color: #84271C;
}
QPushButton#HomeQuickAction {
    min-height: 38px; text-align: left;
    background: #F9ECE9; color: @bordeaux@;
    border: 1px solid transparent; border-radius: 9px;
    padding: 7px 15px; font-family: @font_body@; font-size: 13px;
}
QPushButton#HomeQuickAction[tone="teal"] {
    background: #EAF7F9; color: #176478;
}
QPushButton#HomeQuickAction[tone="neutral"] {
    background: @surface_soft@; color: @text@;
}
QPushButton#HomeQuickAction:hover { border-color: @cyan@; }
QPushButton#HomeQuickAction:focus { border: 2px solid @cyan@; }
''')
