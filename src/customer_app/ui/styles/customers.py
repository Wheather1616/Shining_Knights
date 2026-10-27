"""Refined customer workspace styles with stronger colour, icons and hierarchy."""
from .tokens import themed

CUSTOMERS_QSS = themed(r'''
QWidget#CustomersPage { background: @canvas@; }
QWidget#CustomerWorkspace { background: transparent; }

QLabel#CustomersKicker {
    color: #c86467; font-family: @font_body@; font-size: 12px;
    font-weight: 700; letter-spacing: 1px;
}
QLabel#CustomersTitle {
    color: @bordeaux@; font-family: @font_regular@; font-size: 40px;
}
QLabel#CustomersSubtitle {
    color: @text_muted@; font-family: @font_body@; font-size: 14px;
}
QWidget#CustomersPage QPushButton { font-family: @font_body@; }
QPushButton#CustomerAddButton, QPushButton#CustomerAddJobButton {
    background: @bordeaux_mid@; color: @white@; border: 1px solid @bordeaux_mid@;
    padding: 10px 16px; font-weight: 600; border-radius: 11px;
}
QPushButton#CustomerAddButton:hover, QPushButton#CustomerAddJobButton:hover {
    background: @bordeaux@; border-color: @bordeaux@;
}
QPushButton#CustomerExportButton {
    background: @cyan_soft@; border: 1px solid @cyan_border@;
    color: #176478; border-radius: 11px; padding: 10px 15px;
}
QPushButton#CustomerExportButton:hover {
    background: #dff1f5; border-color: @cyan@;
}
QPushButton#CustomerEditButton, QPushButton#CustomerEditJobButton {
    background: @surface@; color: @bordeaux@; border: 1px solid #e9c9c2;
    border-radius: 11px; padding: 9px 14px;
}
QPushButton#CustomerEditButton:hover, QPushButton#CustomerEditJobButton:hover {
    background: #fff3ef; border-color: #d9aaa0;
}
QPushButton#CustomerEditJobButton:disabled {
    background: @surface_soft@; color: #71656d; border-color: @border@;
}

QWidget#CustomerDirectory, QWidget#CustomerProfileCard, QWidget#CustomerDetailsCard {
    background: @surface@; border: 1px solid @border@;
    border-radius: 18px;
}
QLineEdit#CustomerSearch {
    background: @white@; border: 1px solid @border_strong@;
    border-radius: 12px; padding: 9px 12px; min-height: 28px;
    color: @text@; font-size: 14px;
}
QLineEdit#CustomerSearch:focus { border: 1px solid @cyan@; }
QLabel#CustomerSearchHint {
    color: @text_subtle@; font-size: 12px; margin-top: -6px; margin-bottom: 2px;
}
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
    color: @bordeaux@; font-family: @font_regular@; font-size: 31px;
}
QLabel#CustomerStatus {
    background: @green_soft@; color: @green@; border: 1px solid @green_border@;
    border-radius: 12px; padding: 6px 13px; font-size: 12px;
    font-weight: 700;
}
QLabel#CustomerStatus[active="false"] {
    background: @surface_soft@; color: @text_muted@; border-color: @border@;
}
QLabel#CustomerInfoCaption {
    font-size: 10px; font-weight: 700; color: @text_subtle@;
    background: transparent;
}
QLabel#CustomerValue {
    font-family: @font_body@; font-size: 14px;
    color: @text@; border: none; background: transparent;
}
QWidget#CustomerQuickInfo, QWidget#CustomerMetrics { background: transparent; border: none; }
QWidget#CustomerInfoTile {
    background: #fbfaf8; border: 1px solid #f0eae5; border-radius: 13px;
}
QLabel#CustomerTileCaption {
    color: @text_subtle@; background: transparent; border: none;
    font-size: 10px; font-weight: 700;
}
QLabel#CustomerTileValue {
    color: @text@; background: transparent; border: none;
    font-size: 14px; font-weight: 500;
}
QFrame#CustomerDivider { background: @border@; border: none; }
QWidget#CustomerMetricTile {
    background: @surface@; border: 1px solid @border@; border-radius: 13px;
}
QWidget#CustomerMetricTile[tone="coral"] { border-color: #f0ddd7; }
QLabel#CustomerMetricCaption {
    color: @text_muted@; font-size: 11px; font-weight: 700;
    background: transparent;
}
QLabel#CustomerMetricValue {
    color: @bordeaux@; font-family: @font_regular@;
    font-size: 19px; background: transparent;
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
    background: transparent; font-weight: 700;
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
''')

# Supporting forms, customer service previews and structured service setup.
# These styles are composed here so an existing styles/__init__.py does not
# need to be replaced simply to activate the new section design.
CUSTOMERS_QSS += themed(r'''
QDialog#RecordDialog { background: @canvas@; }
QWidget#RecordForm { background: transparent; border: none; border-radius: 0; }
QFrame#FormSectionCard {
    background: @surface@; border: 1px solid @border@;
    border-radius: 16px;
}
QWidget#FormCardContent, QWidget#FormField, QWidget#FormFieldRow,
QWidget#ChoiceGrid, QWidget#ChoiceChipEntry { background: transparent; border: none; }
QLabel#FormSectionSymbol {
    background: #F9EAE8; color: @bordeaux_mid@; border: none;
    border-radius: 18px; font-size: 19px; font-weight: 700;
}
QLabel#FormCardTitle {
    color: @bordeaux@; font-family: @font_regular@; font-size: 20px;
    font-weight: 700; background: transparent;
}
QLabel#FormCardSubtitle, QLabel#FormFieldHint {
    color: @text_muted@; font-family: @font_body@;
    font-size: 12px; background: transparent;
}
QLabel#FormFieldLabel {
    color: @text@; font-family: @font_body@; font-size: 12px;
    font-weight: 600; background: transparent;
}
QToolButton#FormDisclosureButton {
    color: #176478; font-size: 12px; font-family: @font_body@;
    border: 1px solid @cyan_border@; background: @cyan_soft@;
    padding: 6px 10px; border-radius: 9px; min-width: 57px;
}
QToolButton#FormDisclosureButton:hover { border-color: @cyan@; background: #e0f3f6; }
QFrame#FormSelectionDisclosure {
    background: #FAF8F6; border: 1px solid @border@;
    border-radius: 12px;
}
QLabel#FormSelectionTitle {
    color: @text@; font-size: 13px; font-weight: 700;
}
QLabel#FormSelectionSummary {
    color: #176478; font-size: 12px;
}
QCheckBox#ChoiceChip {
    background: #FFFFFF; color: @text@;
    border: 1px solid @border_strong@; border-radius: 9px;
    padding: 9px 11px; font-family: @font_body@; font-size: 12px;
    min-height: 19px;
}
QCheckBox#ChoiceChip::indicator { width: 0px; height: 0px; }
QCheckBox#ChoiceChip:hover { background: @cyan_soft@; border-color: @cyan@; }
QCheckBox#ChoiceChip:checked {
    background: #16798A; border: 1px solid #16798A;
    color: #FFFFFF; font-weight: 700;
}
QCheckBox#ChoiceChip:focus { border: 2px solid @cyan@; }
QFrame#WorkSideSelector {
    background: @cyan_soft@; border: 1px solid @cyan_border@;
    border-radius: 9px;
}
QPushButton[role="workSide"] {
    background: transparent; color: #176478; font-family: @font_body@;
    font-size: 12px; border: 1px solid transparent; border-radius: 6px;
    padding: 5px 1px; min-height: 19px;
}
QPushButton[role="workSide"]:checked {
    background: #16798A; color: #FFFFFF; border-color: #16798A;
}
QComboBox#CustomerLookup {
    color: @text@; background: @white@; border-color: @cyan_border@;
    border-radius: 11px; padding: 9px 31px 9px 12px;
}
QLabel#FormLookupPreview {
    color: #176478; background: @cyan_soft@;
    border: 1px solid @cyan_border@; border-radius: 10px;
    padding: 11px 13px; font-size: 12px;
}
QScrollArea#RecordScroll { background: @canvas@; border: none; }
QScrollArea#RecordScroll > QWidget > QWidget { background: transparent; }
QDialog#RecordDialog QDialogButtonBox {
    background: @canvas@; border-top: 1px solid @border@;
    padding: 12px 0 2px 0;
}

QLabel#CustomerDetailHelper { color: @text_muted@; font-size: 13px; }
QWidget#CustomerServiceSummaryContent,
QWidget#CustomerServiceSummary { background: @surface@; border: none; }
QFrame#CustomerSummaryFact {
    background: #F9F7F5; border: 1px solid @border@; border-radius: 10px;
}
QLabel#CustomerSummaryCaption { color: @text_muted@; font-size: 11px; font-weight: 600; }
QLabel#CustomerSummaryValue { color: @text@; font-size: 14px; }
QFrame#CustomerNotesCard {
    background: #FAF8F6; border: 1px solid @border@; border-radius: 13px;
}
QTextEdit#CustomerNotes {
    background: transparent; border: none; color: @text@; padding: 3px;
    font-size: 14px;
}
QTableWidget#CustomerServicesTable {
    background: @surface@; border: none; gridline-color: transparent;
    selection-background-color: @cyan_soft@; selection-color: @text@;
}
QTableWidget#CustomerServicesTable::item {
    border: none; border-bottom: 1px solid @border@; padding: 10px;
}
QTableWidget#CustomerServicesTable::item:selected { background: @cyan_soft@; color: @text@; }
QTableWidget#CustomerServicesTable QHeaderView::section {
    background: @surface@; border: none;
    border-bottom: 1px solid @border_strong@; color: @text_muted@;
    padding: 10px; font-size: 12px;
}
QFrame#CustomerServicePreview {
    background: @cyan_soft@; border: 1px solid @cyan_border@;
    border-radius: 14px;
}
QLabel#ServicePreviewTitle {
    color: @bordeaux@; font-family: @font_regular@; font-size: 19px; font-weight: 700;
}
QLabel#ServicePreviewLine { color: @text@; font-size: 12px; }
QLabel#ServicePreviewNotes { color: #176478; font-size: 12px; }
''')
CUSTOMERS_QSS += themed(r'''
QWidget#GroupedWorkTypes { background: transparent; border: none; }
QFrame#WorkCategoryCard {
    background: #F0F8F8; border: 1px solid @cyan_border@;
    border-radius: 12px;
}
QLabel#WorkCategoryTitle {
    color: #176478; font-size: 13px; font-weight: 700;
    background: transparent;
}
''')

# Phase 5: stronger hierarchy, colour-coded form sections and readable previews.
CUSTOMERS_QSS += themed(r'''
QFrame#FormSectionCard {
    background: #FFFDFB; border: 1px solid #E5DAD3;
    border-radius: 17px;
}
QFrame#FormSectionCard[tone="coral"] {
    background: #FFFAF8; border-color: #F0D7D1;
}
QFrame#FormSectionCard[tone="teal"] {
    background: #F8FCFC; border-color: #CFE5E8;
}
QFrame#FormSectionCard[tone="maroon"] {
    background: #FFFAF9; border-color: #E9D6D3;
}
QLabel#FormSectionSymbol[tone="coral"] {
    background: #FCE8E3; color: #AE4840; border-radius: 18px;
}
QLabel#FormSectionSymbol[tone="teal"] {
    background: #E1F3F6; color: #176478; border-radius: 18px;
}
QLabel#FormSectionSymbol[tone="maroon"] {
    background: #F7E8E7; color: @bordeaux@; border-radius: 18px;
}
QLabel#FormCardTitle {
    color: @bordeaux@; font-family: @font_regular@;
    font-size: 23px; font-weight: 700;
}
QLabel#FormCardSubtitle { font-size: 13px; color: @text_muted@; }
QLabel#FormFieldLabel {
    font-size: 13px; color: @text@; font-weight: 700;
}
QLabel#FormSelectionTitle {
    color: @bordeaux@; font-size: 14px; font-weight: 700;
}
QFrame#FormSelectionDisclosure {
    background: #FFFFFF; border: 1px solid #E6DCD6;
    border-radius: 12px;
}
QFrame#WorkCategoryCard {
    background: #F0F8F8; border: 1px solid #C6E5EB;
    border-radius: 12px;
}
QLabel#WorkCategoryTitle {
    color: #176478; font-size: 14px; font-weight: 700;
}
QWidget#JobFormScrollContent { background: transparent; border: none; }
QScrollArea#RecordScroll, QScrollArea#RecordScroll > QWidget > QWidget {
    background: transparent; border: none;
}
QDialog#RecordDialog QDialogButtonBox {
    background: @canvas@; border-top: 1px solid @border@;
    padding: 11px 0 1px 0;
}
QComboBox#CustomerLookup {
    background: @white@; border: 1px solid @cyan_border@;
    border-radius: 11px; padding: 9px 31px 9px 12px;
}
QComboBox#CustomerLookup:focus { border-color: @cyan@; }
QFrame#CustomerDirectoryPreview {
    background: #F0F8FA; border: 1px solid #BFDEE6;
    border-radius: 12px;
}
QWidget#DirectoryPreviewGroup { border: none; background: transparent; }
QLabel#DirectoryPreviewTitle {
    color: @bordeaux@; font-size: 12px; font-weight: 700;
}
QLabel#DirectoryPreviewCaption {
    color: #176478; font-size: 10px; font-weight: 700;
}
QLabel#DirectoryPreviewValue {
    color: @text@; font-size: 12px; background: transparent;
}
QPushButton#CustomerActivationButton {
    background: #FFF7F2; color: @bordeaux@;
    border: 1px solid #EECBC4; border-radius: 10px;
    font-size: 12px; padding: 8px 11px;
}
QPushButton#CustomerActivationButton:hover {
    border-color: @coral@; background: #FDE9E4;
}
QFrame#CustomerServicePreview {
    background: #F0F9FA; border: 1px solid #B9DFE7;
    border-radius: 15px;
}
QLabel#ServicePreviewTitle {
    color: @bordeaux@; font-family: @font_regular@;
    font-size: 22px; font-weight: 700;
}
QLabel#ServicePreviewBadge {
    background: #DFEFF2; color: #176478; font-size: 11px;
    font-weight: 700; border: 1px solid #C6E5EB;
    border-radius: 9px; padding: 5px 11px;
}
QLabel#ServicePreviewBadge[tone="coral"] {
    background: #FFF0EA; color: #984234; border-color: #F3C5BE;
}
QLabel#ServicePreviewCaption {
    color: @bordeaux@; font-family: @font_body@;
    font-size: 12px; font-weight: 700;
}
QWidget#ServicePreviewChips { background: transparent; border: none; }
QLabel#ServicePreviewChip {
    background: #FFFFFF; color: #176478;
    border: 1px solid #C6E5EB; border-radius: 9px;
    padding: 7px 10px; font-size: 12px; font-weight: 600;
}
QLabel#ServicePreviewChip[tone="maroon"] {
    background: #FFF8F7; color: @bordeaux@;
    border: 1px solid #EBD3CF;
}
QLabel#ServicePreviewEmpty { color: @text_muted@; font-size: 12px; }
QFrame#ServicePreviewNotesCard {
    background: #FFF8F5; border: 1px solid #EAD7D1;
    border-radius: 11px;
}
QLabel#ServicePreviewNotes { color: @text@; font-size: 13px; }
QLabel#ServicePreviewNotes[empty="true"] { color: @text_muted@; }
QLabel#CustomerInfoCaption {
    color: @bordeaux@; font-size: 11px; font-weight: 700;
}
''')

# Phase 6: service previews must never render as compressed one-pixel strips.
CUSTOMERS_QSS += themed(r'''
QScrollArea#CustomerServicesScroll {
    background: @surface@; border: none;
}
QWidget#CustomerServicesScrollContent {
    background: @surface@; border: none;
}
QFrame#CustomerServicePreview {
    background: #F0F9FA; border: 1px solid #B9DFE7;
    border-radius: 15px;
}
QLabel#ServicePreviewTitle {
    color: @bordeaux@; font-family: @font_regular@;
    font-size: 22px; font-weight: 700; min-height: 29px;
}
QLabel#ServicePreviewBadge { min-height: 24px; }
QLabel#ServicePreviewCaption {
    color: @bordeaux@; font-family: @font_body@;
    font-size: 12px; font-weight: 700; min-height: 19px;
}
QLabel#ServicePreviewChip {
    background: @white@; color: #176478;
    border: 1px solid #C6E5EB; border-radius: 9px;
    padding: 8px 10px; font-size: 13px; font-weight: 600;
    min-height: 27px;
}
QLabel#ServicePreviewChip[tone="maroon"] {
    background: #FFF8F7; color: @bordeaux@; border-color: #EBD3CF;
}
QFrame#ServicePreviewNotesCard {
    background: #FFF8F5; border: 1px solid #EAD7D1;
    border-radius: 11px;
}
QLabel#ServicePreviewNotes {
    color: @text@; font-size: 13px; min-height: 22px;
}
''')
