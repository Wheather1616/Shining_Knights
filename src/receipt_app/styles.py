APP_QSS = """
QMainWindow, QWidget {
    background: #f6f8fb;
    color: #17202f;
    font-family: Arial, Helvetica, sans-serif;
    font-size: 14px;
}

QFrame#Sidebar {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #ffffff, stop:1 #f7f5ff);
    border-right: 1px solid #d8dee7;
}

QFrame#Card {
    background: #ffffff;
    border: 1px solid #d8dee7;
    border-radius: 16px;
}

QLabel#Title {
    font-size: 30px;
    font-weight: 800;
    color: #17202f;
}

QLabel#Subtitle {
    font-size: 14px;
    color: #5b6472;
}

QLabel#SectionTitle {
    font-size: 20px;
    font-weight: 800;
    color: #17202f;
}

QPushButton {
    border-radius: 14px;
    padding: 11px 16px;
    min-height: 20px;
    background: #f3f7ff;
    border: 1px solid #d6e0f5;
    font-weight: 700;
    color: #17202f;
}

QPushButton:hover {
    border-color: #285cd4;
    background: #eef4ff;
}

QPushButton#PrimaryButton {
    background: #285cd4;
    color: white;
    border: 1px solid #285cd4;
}

QPushButton#PrimaryButton:hover {
    background: #3652da;
}

QPushButton#DangerButton {
    background: #fff1f2;
    color: #9f1239;
    border: 1px solid #fecdd3;
}

QLineEdit,
QTextEdit,
QComboBox,
QDateEdit,
QDoubleSpinBox,
QSpinBox {
    background: #ffffff;
    border: 1px solid #d8dee7;
    border-radius: 12px;
    padding: 9px 11px;
    min-height: 24px;
}

QLineEdit:focus,
QTextEdit:focus,
QComboBox:focus,
QDateEdit:focus,
QDoubleSpinBox:focus,
QSpinBox:focus {
    border: 1px solid #285cd4;
}

QTableWidget {
    background: #ffffff;
    border: 1px solid #d8dee7;
    border-radius: 14px;
    gridline-color: #edf0f4;
    selection-background-color: #eef4ff;
    selection-color: #17202f;
}

QHeaderView::section {
    background: #edf4ff;
    color: #17202f;
    padding: 8px;
    border: none;
    font-weight: 800;
}

QListWidget {
    background: #ffffff;
    border: 1px solid #d8dee7;
    border-radius: 14px;
    padding: 8px;
}

QCheckBox {
    spacing: 8px;
}


/* Desktop tab shell */

QFrame#DesktopPanel {
    background: #f6f8fb;
    border: 1px solid #d8dee7;
    border-radius: 24px;
}

/* Keep broad desktop child backgrounds transparent, then override specific widgets below. */
QFrame#DesktopPanel QLabel,
QFrame#DesktopPanel QWidget {
    background: transparent;
}


/* Quick receipt title pill */

QWidget#DesktopDragHeader {
    background-color: #285cd4;
    border: 1px solid #1d4ed8;
    border-radius: 18px;
}

QLabel#DesktopPanelTitle {
    color: #000000;
    font-size: 22px;
    font-weight: 900;
    background: transparent;
}


/* Desktop tab form card */

QFrame#DesktopFormCard {
    background: #ffffff;
    border: 1px solid #d8dee7;
    border-radius: 18px;
}

QLabel#DesktopSubheading {
    color: #17202f;
    font-size: 13px;
    font-weight: 900;
}

QLabel#DesktopFieldLabel {
    color: #17202f;
    font-size: 12px;
    font-weight: 800;
}

QLabel#DesktopEmpty {
    color: #5b6472;
    font-size: 14px;
    font-weight: 800;
}

QLabel#DesktopHint {
    color: #5b6472;
    font-size: 11px;
    font-weight: 700;
}

QLabel#DesktopStatus {
    color: #285cd4;
    font-size: 12px;
    font-weight: 800;
}


/* Desktop tab header buttons */

QPushButton#DesktopIconButton {
    background: #ffffff;
    border: 1px solid #dbeafe;
    color: #17202f;
    min-width: 28px;
    max-width: 32px;
    min-height: 28px;
    padding: 0;
    border-radius: 14px;
    font-size: 15px;
    font-weight: 900;
}

QPushButton#DesktopIconButton:hover {
    background: #dbeafe;
    border-color: #93c5fd;
    color: #17202f;
}

QPushButton#DesktopOpenAppButton {
    background: #ffffff;
    color: #17202f;
    border: 1px solid #dbeafe;
    border-radius: 14px;
    padding: 7px 12px;
    min-height: 24px;
    font-size: 12px;
    font-weight: 900;
}

QPushButton#DesktopOpenAppButton:hover {
    background: #dbeafe;
    border-color: #93c5fd;
    color: #17202f;
}


/* Desktop tab inputs */

QFrame#DesktopPanel QLineEdit,
QFrame#DesktopPanel QTextEdit,
QFrame#DesktopPanel QComboBox,
QFrame#DesktopPanel QDateEdit,
QFrame#DesktopPanel QDoubleSpinBox,
QFrame#DesktopPanel QSpinBox {
    background: #ffffff;
    border: 1px solid #d8dee7;
    border-radius: 12px;
    padding: 8px 10px;
    min-height: 22px;
    color: #17202f;
    selection-background-color: #eef4ff;
    selection-color: #17202f;
}

QFrame#DesktopPanel QLineEdit:focus,
QFrame#DesktopPanel QTextEdit:focus,
QFrame#DesktopPanel QComboBox:focus,
QFrame#DesktopPanel QDateEdit:focus,
QFrame#DesktopPanel QDoubleSpinBox:focus,
QFrame#DesktopPanel QSpinBox:focus {
    border: 2px solid #285cd4;
}


/* Save and Clear buttons */

QPushButton#DesktopPrimaryButton {
    background: #dbeafe;
    color: #17202f;
    border: 1px solid #93c5fd;
    border-radius: 14px;
    padding: 10px 14px;
    font-weight: 900;
}

QPushButton#DesktopPrimaryButton:hover {
    background: #285cd4;
    color: #ffffff;
    border-color: #285cd4;
}

QPushButton#DesktopPrimaryButton:pressed {
    background: #1d4ed8;
    color: #ffffff;
    border-color: #1d4ed8;
}

QPushButton#DesktopSecondaryButton {
    background: #ffffff;
    color: #17202f;
    border: 1px solid #bfdbfe;
    border-radius: 14px;
    padding: 10px 14px;
    font-weight: 900;
}

QPushButton#DesktopSecondaryButton:hover {
    background: #285cd4;
    color: #ffffff;
    border-color: #285cd4;
}

QPushButton#DesktopSecondaryButton:pressed {
    background: #1d4ed8;
    color: #ffffff;
    border-color: #1d4ed8;
}


/* Today's receipts dropdown button */

QPushButton#DesktopDropdownButton {
    background: #dbeafe;
    color: #17202f;
    border: 1px solid #93c5fd;
    border-radius: 14px;
    padding: 10px 12px;
    text-align: left;
    font-size: 13px;
    font-weight: 900;
}

QPushButton#DesktopDropdownButton:hover {
    background: #bfdbfe;
    border-color: #285cd4;
    color: #17202f;
}

QPushButton#DesktopDropdownButton:disabled {
    background: #f3f6fa;
    color: #5b6472;
    border: 1px solid #d8dee7;
}


/* Today's receipts dropdown panel and list */

QFrame#DesktopDropdownPanel {
    background: #ffffff;
    border: 1px solid #d8dee7;
    border-radius: 18px;
}

QListWidget#DesktopReceiptList {
    background: #ffffff;
    border: none;
    color: #17202f;
    padding: 6px;
    outline: 0;
}

QListWidget#DesktopReceiptList::item {
    background: transparent;
    border: none;
    margin: 0;
    padding: 0;
    color: #17202f;
    font-weight: 700;
}

QListWidget#DesktopReceiptList::item:selected {
    background: #eef4ff;
    color: #17202f;
}


/* Scrollbars */

QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 6px 2px 6px 2px;
}

QScrollBar::handle:vertical {
    background: rgba(40, 92, 212, 0.42);
    border-radius: 5px;
    min-height: 26px;
}

QScrollBar::handle:vertical:hover {
    background: rgba(40, 92, 212, 0.62);
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
}


/* Small edit/delete buttons */

QPushButton#MiniEditButton {
    background: #dcfce7;
    color: #166534;
    border: 1px solid #86efac;
    border-radius: 10px;
    padding: 6px 10px;
    min-height: 24px;
    font-size: 11px;
    font-weight: 900;
}

QPushButton#MiniEditButton:hover {
    background: #22c55e;
    color: #ffffff;
    border-color: #16a34a;
}

QPushButton#MiniEditButton:pressed {
    background: #16a34a;
    color: #ffffff;
    border-color: #15803d;
}

QPushButton#MiniDeleteButton {
    background: #fee2e2;
    color: #991b1b;
    border: 1px solid #fecaca;
    border-radius: 10px;
    padding: 6px 10px;
    min-height: 24px;
    font-size: 11px;
    font-weight: 900;
}

QPushButton#MiniDeleteButton:hover {
    background: #ef4444;
    color: #ffffff;
    border-color: #dc2626;
}

QPushButton#MiniDeleteButton:pressed {
    background: #dc2626;
    color: #ffffff;
    border-color: #b91c1c;
}


/* Receipt rows */

QWidget#DesktopReceiptRow {
    background: #f8fbff;
    border: 1px solid #d8dee7;
    border-radius: 12px;
}

QWidget#BrowseReceiptRow {
    background: #f8fbff;
    border: 1px solid #d8dee7;
    border-radius: 12px;
}

QLabel#DesktopReceiptRowLabel {
    color: #17202f;
    font-size: 12px;
    font-weight: 800;
    background: transparent;
}

QLabel#BrowseReceiptRowLabel {
    color: #17202f;
    font-size: 12px;
    font-weight: 800;
    background: transparent;
}

QWidget#ReceiptActionsWidget {
    background: transparent;
}


/* Final overrides kept at the end so they win over broad QWidget rules. */

QWidget#DesktopDragHeader {
    background-color: #285cd4;
    border: 1px solid #1d4ed8;
    border-radius: 18px;
}

QLabel#DesktopPanelTitle {
    color: #000000;
    font-size: 22px;
    font-weight: 900;
    background: transparent;
}

QFrame#DesktopFormCard {
    background: #ffffff;
    border: 1px solid #d8dee7;
    border-radius: 18px;
}

QPushButton#DesktopPrimaryButton:hover,
QPushButton#DesktopSecondaryButton:hover {
    background: #285cd4;
    color: #ffffff;
    border-color: #285cd4;
}

QPushButton#MiniDeleteButton:hover {
    background: #ef4444;
    color: #ffffff;
    border-color: #dc2626;
}


/* Settings page */

QWidget#SettingsPage,
QWidget#SettingsContent,
QScrollArea#SettingsScroll,
QScrollArea#SettingsScroll > QWidget > QWidget {
    background: #f6f8fb;
}

QScrollArea#SettingsScroll {
    border: none;
}

QFrame#SettingsCard {
    background: #ffffff;
    border: 1px solid #d8dee7;
    border-radius: 18px;
}

QFrame#SettingsCard QLabel,
QFrame#SettingsCard QCheckBox {
    background: transparent;
}

QLabel#SettingsCardTitle {
    background: transparent;
    color: #17202f;
    font-size: 18px;
    font-weight: 800;
}

QLabel#SettingsHelper {
    background: transparent;
    color: #667085;
    font-size: 13px;
}

QLabel#SettingsMiniLabel {
    background: transparent;
    color: #475467;
    font-size: 12px;
    font-weight: 700;
}

QLabel#SecurityStatus {
    background: #ecfdf3;
    color: #166534;
    border: 1px solid #bbf7d0;
    border-radius: 10px;
    padding: 9px 11px;
    font-weight: 700;
}

QLineEdit#ReadOnlySetting {
    background: #f8fafc;
    color: #475467;
    border: 1px solid #e2e8f0;
}

QTableWidget#SettingsFieldsTable {
    background: #ffffff;
    alternate-background-color: #ffffff;
    border: 1px solid #d8dee7;
    border-radius: 12px;
    gridline-color: #edf0f4;
    selection-background-color: #eef4ff;
    selection-color: #17202f;
}

QTableWidget#SettingsFieldsTable::item {
    padding: 8px;
}

QTableWidget#SettingsFieldsTable QCheckBox {
    background: transparent;
}



/* Browse model/view table */

QTableView#BrowseTableView {
    background: #ffffff;
    alternate-background-color: #f8fbff;
    border: 1px solid #d8dee7;
    border-radius: 14px;
    gridline-color: #edf0f4;
    selection-background-color: #eef4ff;
    selection-color: #17202f;
    outline: 0;
}

QTableView#BrowseTableView::item {
    padding: 7px 9px;
}

QTableView#BrowseTableView::item:selected {
    background: #eef4ff;
    color: #17202f;
}

QPushButton#PaginationButton {
    min-width: 82px;
    padding: 7px 12px;
    min-height: 22px;
    border-radius: 10px;
}

QLabel#PaginationStatus {
    color: #667085;
    font-size: 12px;
    font-weight: 700;
}



/* Products & pricing settings */

QTableWidget#ProductCatalogTable {
    background: #ffffff;
    alternate-background-color: #ffffff;
    border: 1px solid #d8dee7;
    border-radius: 12px;
    gridline-color: #edf0f4;
    selection-background-color: #eef4ff;
    selection-color: #17202f;
}

QTableWidget#ProductCatalogTable::item {
    padding: 8px;
}

QTableWidget#ProductCatalogTable QDoubleSpinBox {
    min-width: 110px;
}



/* Payment surcharge */

QLabel#SurchargeHint {
    background: #eff6ff;
    color: #1d4ed8;
    border: 1px solid #bfdbfe;
    border-radius: 9px;
    padding: 7px 9px;
    font-size: 12px;
    font-weight: 700;
}

QLabel#SurchargePreview {
    background: #f8fafc;
    color: #475467;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 9px 11px;
    font-size: 12px;
}

"""