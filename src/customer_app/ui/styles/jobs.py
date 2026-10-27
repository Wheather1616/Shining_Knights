"""Phase 7: a clear, compact Jobs workspace with robust light popup menus."""
from .tokens import themed

JOBS_QSS = themed(r'''
QWidget#JobsPage { background: @canvas@; }
QLabel#JobsKicker {
    color: #C86467; font-family: @font_body@;
    font-size: 11px; font-weight: 700;
}
QLabel#JobsPageTitle {
    color: @bordeaux@; font-family: @font_regular@; font-size: 37px;
}
QPushButton#JobsAddButton {
    background: @bordeaux_mid@; color: @white@; border: 1px solid @bordeaux_mid@;
    border-radius: 10px; padding: 9px 16px; font-family: @font_body@; font-weight: 700;
}
QPushButton#JobsAddButton:hover { background: @bordeaux@; }
QPushButton#JobsExportButton {
    color: #176478; background: #EAF7F9; border: 1px solid #C7E4E9;
    border-radius: 10px; padding: 9px 13px; font-family: @font_body@;
}
QPushButton#JobsExportButton:hover { background: #DFF1F5; border-color: @cyan@; }
QLineEdit#JobsSearch {
    background: @white@; border: 1px solid @border_strong@;
    border-radius: 11px; padding: 8px 12px; min-height: 30px;
    color: @text@; font-family: @font_body@; font-size: 13px;
}
QLineEdit#JobsSearch:focus { border-color: @cyan@; }
QWidget#JobsQuickFilters {
    background: #F7F3F0; border: 1px solid #E8DDD6;
    border-radius: 12px;
}
QPushButton#JobsQuickButton {
    background: transparent; color: #544E55; border: 1px solid transparent;
    border-radius: 9px; min-height: 29px; padding: 6px 9px;
    font-family: @font_body@; font-size: 12px; font-weight: 600;
}
QPushButton#JobsQuickButton:hover { background: #F3E8E4; color: @bordeaux@; }
QPushButton#JobsQuickButton:checked {
    background: #F9E9E8; color: @bordeaux@; border-color: #E5C4C0;
}
QPushButton#JobsQuickButton[kind="upcoming"]:checked {
    background: #E6F4F7; color: #176478; border-color: #BBDEE5;
}
QPushButton#JobsQuickButton[kind="overdue"]:checked {
    background: #FFF0EB; color: #A84237; border-color: #F2C7C0;
}
QPushButton#JobsQuickButton[kind="completed"]:checked {
    background: #E9F7ED; color: #287449; border-color: #C6E7CF;
}
QLabel#JobsFilterLabel {
    color: @text_muted@; background: transparent;
    font-family: @font_body@; font-size: 11px; font-weight: 700;
}
/* Override the earlier global burgundy-on-burgundy popup issue.
   The closed control is light, as is the explicit QListView popup. */
QComboBox[role="jobFilter"] {
    background: #FFFFFF; color: #302A30;
    border: 1px solid #DCCDC5; border-radius: 9px;
    padding: 8px 28px 8px 11px; min-height: 28px;
    font-family: @font_body@; font-size: 12px;
    selection-background-color: #DFF1F5; selection-color: #176478;
}
QComboBox[role="jobFilter"]:hover { background: #FAFCFD; border-color: @cyan@; }
QComboBox[role="jobFilter"]:focus { border: 2px solid @cyan@; padding: 7px 27px 7px 10px; }
QComboBox[role="jobFilter"]:disabled { background: #F0EAE5; color: #71656D; }
QComboBox[role="jobFilter"]::drop-down {
    subcontrol-origin: padding; subcontrol-position: top right;
    width: 27px; border: none; background: transparent;
}
QComboBox[role="jobFilter"]::down-arrow {
    image: @icon_down@; width: 13px; height: 13px;
}
QComboBox[role="jobFilter"] QAbstractItemView, QListView#JobsComboPopup {
    background: #FFFFFF; color: #302A30; border: 1px solid #DCCDC5;
    selection-background-color: #DFF1F5; selection-color: #176478;
    padding: 4px; outline: none;
}
QComboBox[role="jobFilter"] QAbstractItemView::item, QListView#JobsComboPopup::item {
    color: #302A30; min-height: 25px; padding: 8px 11px;
}
QComboBox[role="jobFilter"] QAbstractItemView::item:selected,
QListView#JobsComboPopup::item:selected {
    color: #176478; background: #DFF1F5;
}
QMenu#JobsMenu {
    background: @white@; color: @text@; border: 1px solid @border_strong@; padding: 6px;
}
QMenu#JobsMenu::item {
    background: transparent; color: @text@; padding: 9px 17px; border-radius: 5px;
}
QMenu#JobsMenu::item:selected { background: #DFF1F5; color: #176478; }
QMenu#JobsMenu::item:disabled { color: #71656D; }
QWidget#JobsListCard, QWidget#JobDetailCard {
    background: @surface@; border: 1px solid @border@; border-radius: 17px;
}
QLabel#JobsPanelTitle {
    color: @bordeaux@; font-family: @font_regular@; font-size: 23px;
}
QLabel#JobsCount { color: @text_muted@; font-size: 12px; }
QLabel#JobsError { color: #8D332C; font-size: 13px; }
QTreeWidget#JobsTree {
    background: @surface@; border: none; border-radius: 0; outline: none;
    alternate-background-color: @surface@; color: @text@;
    selection-background-color: #EAF7F9; selection-color: @text@;
}
QTreeWidget#JobsTree::item {
    border: none; border-bottom: 1px solid #EBE1DA;
    padding: 6px 8px; min-height: 33px;
}
QTreeWidget#JobsTree::item:selected,
QTreeWidget#JobsTree::item:selected:!active {
    background: #E6F4F7; color: #302A30;
}
QTreeWidget#JobsTree::item:hover:!selected { background: #F8F3F0; }

QTreeWidget#JobsTree QHeaderView::section {
    background: #F9F3EF; color: @bordeaux@; border: none;
    border-bottom: 1px solid @border@; padding: 9px 8px;
    font-size: 12px; font-family: @font_body@; font-weight: 700;
}
QLabel#JobsSelection { color: @text_muted@; font-size: 11px; }
QScrollArea#JobDetailScroll, QWidget#JobDetailContent {
    background: @surface@; border: none;
}
QLabel#JobIdentifier {
    color: #777078; font-family: @font_body@; font-size: 11px; font-weight: 700;
}
QLabel#JobCustomerName {
    color: @bordeaux@; font-family: @font_regular@; font-size: 29px;
    min-height: 39px;
}
QLabel#JobStatus {
    background: #EAF7F9; color: #176478; border: 1px solid #B9DDE5;
    border-radius: 9px; padding: 6px 11px; font-weight: 700; font-size: 12px;
}
QLabel#JobStatus[status="completed"] {
    background: #E8F7EC; border-color: #C3E9CD; color: #287449;
}
QLabel#JobStatus[status="cancelled"], QLabel#JobStatus[status="in-trash"] {
    background: #F3F0EE; border-color: #E5DAD3; color: #6B6267;
}
QLabel#JobStatus[status="in-progress"] {
    background: #FAF1FA; border-color: #EBD9EC; color: #793572;
}
QWidget#JobContactFact, QWidget#JobDetailSection,
QWidget#JobDetailValueRow, QWidget#JobChipHost {
    background: transparent; border: none;
}
QWidget#JobLineIcon { background: transparent; border: none; }
QLabel#JobFactCaption { color: #746C73; background: transparent;
    font-family: @font_body@; font-size: 10px; font-weight: 700; }
QFrame#JobDetailDivider { background: @border@; border: none; }
QLabel#JobSectionTitle {
    color: @bordeaux@; font-family: @font_regular@;
    font-size: 21px; font-weight: 700; background: transparent;
    padding: 0; margin: 0; min-height: 34px;
}
QLabel#JobFieldCaption {
    color: #746C73; font-size: 11px; font-family: @font_body@;
    font-weight: 700; background: transparent; padding: 0;
}
QLabel#JobInfoValue {
    color: #302A30; font-size: 13px; font-family: @font_body@;
    background: transparent;
}
QLabel#JobFeeValue {
    color: @bordeaux@; font-family: @font_regular@; font-size: 20px;
}
QLabel#JobPaymentValue { color: #302A30; font-size: 13px; font-weight: 700; }
QLabel#JobPaymentValue[state="paid"] { color: #287449; }
QLabel#JobPaymentValue[state="unpaid"] { color: #A84237; }
QLabel#JobDetailChip {
    color: #176478; background: #EAF7F9; border: 1px solid #C6E3EA;
    border-radius: 8px; padding: 6px 10px; font-size: 12px;
}
QLabel#JobDetailChip[tone="maroon"] {
    background: #F9F0EF; color: @bordeaux@; border-color: #EDD7D4;
}
QTextEdit#JobDetailNotes {
    background: #FAF8F6; color: @text@; border: 1px solid @border@;
    border-radius: 8px; padding: 8px 10px;
}
QPushButton#JobEditAction {
    color: @bordeaux@; background: @white@; border: 1px solid #E2BDB8;
    border-radius: 10px; font-family: @font_body@; font-weight: 700;
}
QPushButton#JobEditAction:hover { background: #FFF5F2; border-color: @bordeaux_mid@; }
QPushButton[role="jobMenu"] {
    color: @bordeaux@; background: #F9F0EF; border: 1px solid #ECD8D5;
    border-radius: 9px; padding: 7px 30px 7px 12px; font-family: @font_body@;
}
QPushButton[role="jobMenu"]::menu-indicator {
    image: @icon_down@; width: 13px; height: 13px;
    subcontrol-origin: padding; subcontrol-position: right center; right: 8px;
}
QPushButton[role="jobMenu"]:hover { background: #F6E5E2; }
''')

JOBS_QSS += themed(r'''
QMenu#JobsFilterPopup { background: #FFFFFF; color: #302A30; border: 1px solid #DCCDC5; padding: 5px; }
QMenu#JobsFilterPopup::item { background: #FFFFFF; color: #302A30; padding: 9px 20px 9px 26px; margin: 2px; }
QMenu#JobsFilterPopup::item:selected { color: #176478; background: #DFF1F5; }
QMenu#JobsFilterPopup::item:checked { color: #52050A; font-weight: 700; }
QWidget#JobDetailSection { background: transparent; border: none; }
QWidget#JobDetailValueRow { background: transparent; border: none; }
QLabel#JobInfoValue { font-size: 13px; color: #302A30; }
QLabel#JobDetailChip { min-height: 30px; }
''')
