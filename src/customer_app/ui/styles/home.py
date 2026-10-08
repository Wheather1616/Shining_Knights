"""Overview cards, visit list and booking reminders."""
from .tokens import themed

HOME_QSS = themed(r'''
QLabel#HomeTitle { color: @bordeaux@; font-family: @font_regular@; font-size: 38px; }
QPushButton#HomeSummaryCard {
    background: @surface@; border: 1px solid @border@; border-radius: @radius_card@;
    padding: 0; text-align: left;
}
QPushButton#HomeSummaryCard:hover { background: @surface_alt@; border-color: @bordeaux_mid@; }
QPushButton#HomeSummaryCard:focus { border: 2px solid @cyan@; }
QLabel#HomeSummaryTitle { color: @text@; font-family: @font_regular@; font-size: 20px; }
QLabel#HomeSummaryCount { color: @bordeaux@; font-family: @font_regular@; font-size: 40px; }
QLabel#HomeSectionTitle { color: @bordeaux@; font-family: @font_regular@; font-size: 23px; }
QWidget#HomeContentCard { background: @surface@; border: 1px solid @border@; border-radius: @radius_card@; }
QWidget#HomeFooter { border-top: 1px solid @border@; }
QWidget#HomeOverdueNotice { background: @coral_soft@; border: 1px solid @coral_border@; border-radius: 9px; }
QLabel#HomeOverdueText { color: #8d332c; }
QLabel#HomeEmpty { color: @text_muted@; padding: 16px 0; }
QTableWidget#HomeVisits { background: @surface@; border: none; selection-background-color: @cyan_soft@; selection-color: @text@; }
QTableWidget#HomeVisits::item { padding: 6px; border-bottom: 1px solid @border@; }
QTableWidget#HomeVisits::item:hover { background: @cyan_soft@; }
QTableWidget#HomeVisits QHeaderView::section { background: @surface@; color: @text_muted@; border: none; border-bottom: 1px solid @border_strong@; padding: 8px 6px; }
QScrollArea#HomeBookingsScroll { background: @surface@; border: none; }
QWidget#HomeBookingContent { background: @surface@; }
QWidget#HomeBookingEntry { border-bottom: 1px solid @border@; }
QPushButton#HomeCustomerLink { color: @text@; font-family: @font_body@; font-weight: 600; font-size: 16px; padding: 0; border: none; background: transparent; text-align: left; }
QPushButton#HomeCustomerLink:hover { color: @bordeaux_mid@; text-decoration: underline; }
QPushButton#HomeCustomerLink:focus { border: 1px solid @cyan@; }
QLabel#HomeDueBadge { background: @surface_soft@; color: @text@; border: none; border-radius: 6px; padding: 4px 7px; font-size: 12px; }
QLabel#HomeDueBadge[overdue="true"] { background: @coral_soft@; color: #8d332c; }
QLabel#CustomerProfileText { background: transparent; color: @text@; border: none; padding: 4px; font-size: 14px; }
''')
