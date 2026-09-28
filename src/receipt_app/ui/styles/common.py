"""Shared ReceiptFlow component styles.

This is the design-system layer. Component styles should only contain the visual
rules that are genuinely unique to that screen/widget.
"""

from .tokens import themed

COMMON_QSS = themed(r'''
/* ------------------------------------------------------------------
   Common canvases
   ------------------------------------------------------------------ */
QWidget#AppShell,
QWidget#HomePage,
QWidget#BrowsePage,
QWidget#SettingsPage,
QWidget#SettingsContent,
QScrollArea#SettingsScroll,
QScrollArea#SettingsScroll > QWidget > QWidget,
QDialog#ReceiptFormDialog {
    background: @canvas@;
}

/* ------------------------------------------------------------------
   Common type hierarchy
   ------------------------------------------------------------------ */
QLabel#HomeEyebrow,
QLabel#BrowseEyebrow,
QLabel#SettingsEyebrow,
QLabel#ReceiptDialogEyebrow {
    color: #7a3e42;
    font-family: @font_regular@;
    font-size: 12px;
    letter-spacing: 2px;
}

QLabel#HomeDisplayTitle,
QLabel#BrowseDisplayTitle,
QLabel#SettingsDisplayTitle,
QLabel#ReceiptDialogTitle {
    color: @bordeaux@;
    font-family: @font_regular@;
    font-size: 40px;
}

QLabel#HomeLead,
QLabel#BrowseLead,
QLabel#SettingsLead,
QLabel#ReceiptDialogSubtitle {
    color: #615960;
    font-family: @font_body@;
    font-size: 15px;
}

QLabel#HomeHeroTitle,
QLabel#HomeFeatureTitle,
QLabel#ReceiptDialogHelperTitle,
QLabel#DesktopPanelTitle,
QLabel#DesktopSubheading {
    color: @bordeaux@;
    font-family: @font_regular@;
}

QLabel#SettingsCardTitle {
    color: @bordeaux@;
    font-family: @font_regular@;
    font-size: 18px;
}

QLabel#SettingsHelper,
QLabel#HomeHeroBody,
QLabel#HomeFeatureBody,
QLabel#ReceiptDialogHelperBody,
QLabel#ReceiptDialogTipText {
    color: @text_muted@;
    font-family: @font_body@;
}

/* ------------------------------------------------------------------
   Common surfaces
   ------------------------------------------------------------------ */
QFrame#HomeHeroCard,
QFrame#HomeFeatureCard,
QFrame#BrowseFilterCard,
QFrame#BrowseResultsCard,
QFrame#SettingsCard,
QFrame#ReceiptDialogFormCard,
QFrame#ReceiptDialogHelperCard,
QFrame#DesktopFormCard {
    background: @surface@;
    border: 1px solid @border@;
    border-radius: @radius_card@;
}

/* ------------------------------------------------------------------
   Common form controls
   ------------------------------------------------------------------ */
QLineEdit,
QTextEdit,
QComboBox,
QDateEdit,
QDoubleSpinBox,
QSpinBox {
    background: @white@;
    color: @text@;
    border: 1px solid @border_strong@;
    border-radius: @radius_control@;
    padding: 8px 10px;
    min-height: 24px;
    font-family: @font_body@;
    font-size: 14px;
    selection-background-color: #dff1f5;
    selection-color: @text@;
}

QLineEdit:focus,
QTextEdit:focus,
QComboBox:focus,
QDateEdit:focus,
QDoubleSpinBox:focus,
QSpinBox:focus {
    border: 1px solid @cyan@;
}

QComboBox::drop-down {
    border: none;
    width: 28px;
}

QComboBox QAbstractItemView {
    background: @surface@;
    color: @text@;
    border: 1px solid @border_strong@;
    selection-background-color: #e5f3f6;
    selection-color: @text@;
    outline: 0;
    font-family: @font_body@;
}

QCheckBox {
    color: #3e383d;
    spacing: 8px;
    font-family: @font_body@;
    font-size: 13px;
}

/* ------------------------------------------------------------------
   Button roles
   ------------------------------------------------------------------ */
QPushButton {
    font-family: @font_regular@;
    font-size: 14px;
}

QPushButton#PrimaryButton,
QPushButton#SettingsSaveButton,
QPushButton#ReceiptDialogSaveButton,
QPushButton#DesktopPrimaryButton {
    background: @bordeaux_mid@;
    color: @white@;
    border: 1px solid @bordeaux_mid@;
    border-radius: @radius_control@;
    padding: 10px 16px;
    min-height: 24px;
}

QPushButton#PrimaryButton:hover,
QPushButton#SettingsSaveButton:hover,
QPushButton#ReceiptDialogSaveButton:hover,
QPushButton#DesktopPrimaryButton:hover {
    background: @bordeaux@;
    border-color: @bordeaux@;
}

QPushButton#PrimaryButton:pressed,
QPushButton#SettingsSaveButton:pressed,
QPushButton#ReceiptDialogSaveButton:pressed,
QPushButton#DesktopPrimaryButton:pressed {
    background: @bordeaux_dark@;
    border-color: @bordeaux_dark@;
}

QPushButton#SecondaryButton,
QPushButton#ReceiptDialogCancelButton,
QPushButton#DesktopSecondaryButton,
QPushButton#BrowseRefreshButton,
QPushButton#BrowsePreviousButton {
    background: @surface_alt@;
    color: @bordeaux_mid@;
    border: 1px solid #d9c8c1;
    border-radius: @radius_control@;
    padding: 9px 14px;
    min-height: 22px;
}

QPushButton#SecondaryButton:hover,
QPushButton#ReceiptDialogCancelButton:hover,
QPushButton#DesktopSecondaryButton:hover,
QPushButton#BrowseRefreshButton:hover,
QPushButton#BrowsePreviousButton:hover {
    background: #f7ebe6;
    color: @bordeaux@;
    border-color: #c8afa6;
}

QPushButton#BrowseExportButton,
QPushButton#SettingsAddButton {
    background: @cyan_soft@;
    color: #187d94;
    border: 1px solid @cyan_border@;
    border-radius: @radius_control@;
    padding: 9px 14px;
    min-height: 22px;
}

QPushButton#BrowseExportButton:hover,
QPushButton#SettingsAddButton:hover {
    background: #e2f3f6;
    color: #12677a;
    border-color: @cyan@;
}

QPushButton#DangerButton,
QPushButton#SettingsDangerButton,
QPushButton#BrowseTrashButton,
QPushButton#MiniDeleteButton {
    background: @coral_soft@;
    color: #c8574c;
    border: 1px solid @coral_border@;
    border-radius: @radius_control@;
}

QPushButton#DangerButton:hover,
QPushButton#SettingsDangerButton:hover,
QPushButton#BrowseTrashButton:hover,
QPushButton#MiniDeleteButton:hover {
    background: @coral@;
    color: @white@;
    border-color: @coral@;
}

QPushButton:disabled {
    background: #f5f1ee;
    color: #aaa09b;
    border-color: #e4dcd7;
}

/* ------------------------------------------------------------------
   Shared table language
   ------------------------------------------------------------------ */
QTableView#BrowseTableView,
QTableWidget#SettingsFieldsTable,
QTableWidget#ProductCatalogTable {
    background: @surface@;
    alternate-background-color: #fcfaf8;
    color: @text@;
    border: 1px solid @border@;
    gridline-color: #eee4de;
    selection-background-color: #e5f3f6;
    selection-color: @text@;
    outline: 0;
    font-family: @font_body@;
    font-size: 13px;
}

QHeaderView#BrowseHeader::section,
QHeaderView#SettingsFieldsHeader::section,
QHeaderView#SettingsCatalogHeader::section {
    background: #f8efeb;
    color: #6e3337;
    border: none;
    border-right: 1px solid #eee2dc;
    border-bottom: 1px solid #eadfd9;
    padding: 8px 8px;
    font-family: @font_regular@;
    font-size: 11px;
}

/* ------------------------------------------------------------------
   Shared scrollbar treatment
   ------------------------------------------------------------------ */
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 4px 1px 4px 1px;
}

QScrollBar::handle:vertical {
    background: rgba(37, 142, 166, 0.30);
    border-radius: 4px;
    min-height: 26px;
}

QScrollBar::handle:vertical:hover {
    background: rgba(37, 142, 166, 0.48);
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
}
''')
