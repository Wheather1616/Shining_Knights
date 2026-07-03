from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

from PySide6.QtCore import QDate, QEvent, QPoint, QSize, Qt
from PySide6.QtGui import QAction, QCloseEvent, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QSystemTrayIcon,
)

from .config import CORE_FIELD_KEYS, FieldDefinition, SettingsStore
from .database import ReceiptDatabase, ReceiptRecord, SORT_OPTIONS
from .importer import import_file, mapping_preview
from .styles import APP_QSS

class CenteredCheckBox(QWidget):
    """Small wrapper that centres a checkbox inside a table cell.

    QCheckBox itself does not expose a setAlignment method in PySide6,
    so this widget keeps the table layout tidy while still presenting an
    isChecked()/setChecked() interface to the settings save logic.
    """

    def __init__(self, checked: bool = False, parent: QWidget | None = None):
        super().__init__(parent)
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(checked)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.checkbox)

    def isChecked(self) -> bool:
        return self.checkbox.isChecked()

    def setChecked(self, checked: bool) -> None:
        self.checkbox.setChecked(checked)


class ReceiptFormDialog(QDialog):
    def __init__(self, fields: list[FieldDefinition], parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("New Receipt")
        self.setMinimumWidth(480)
        self.fields = [field for field in fields if field.quick_entry]
        self.widgets: dict[str, QWidget] = {}

        layout = QVBoxLayout(self)
        title = QLabel("Add a receipt")
        title.setObjectName("SectionTitle")
        subtitle = QLabel("Capture the transaction as soon as it is completed.")
        subtitle.setObjectName("Subtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        for field_def in self.fields:
            widget = self._make_widget(field_def)
            self.widgets[field_def.key] = widget
            required = " *" if field_def.required else ""
            form.addRow(f"{field_def.label}{required}", widget)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _make_widget(self, field_def: FieldDefinition) -> QWidget:
        if field_def.field_type == "date":
            widget = QDateEdit()
            widget.setCalendarPopup(True)
            widget.setDisplayFormat("dd/MM/yyyy")
            widget.setDate(QDate.currentDate())
            return widget
        if field_def.field_type in {"number", "currency"}:
            widget = QDoubleSpinBox()
            widget.setMaximum(999999999.99)
            widget.setDecimals(2)
            widget.setPrefix("$" if field_def.field_type == "currency" else "")
            return widget
        if field_def.field_type == "textarea":
            widget = QTextEdit()
            widget.setFixedHeight(90)
            return widget
        if field_def.field_type == "dropdown":
            widget = QComboBox()
            widget.setEditable(True)
            widget.addItems(field_def.options)
            return widget
        return QLineEdit()

    def values(self) -> dict[str, Any]:
        values: dict[str, Any] = {}
        for field_def in self.fields:
            widget = self.widgets[field_def.key]
            if isinstance(widget, QDateEdit):
                values[field_def.key] = widget.date().toString("yyyy-MM-dd")
            elif isinstance(widget, QDoubleSpinBox):
                values[field_def.key] = widget.value()
            elif isinstance(widget, QTextEdit):
                values[field_def.key] = widget.toPlainText().strip()
            elif isinstance(widget, QComboBox):
                values[field_def.key] = widget.currentText().strip()
            elif isinstance(widget, QLineEdit):
                values[field_def.key] = widget.text().strip()
        return values

    def accept(self) -> None:
        values = self.values()
        missing = [field.label for field in self.fields if field.required and not str(values.get(field.key, "")).strip()]
        if missing:
            QMessageBox.warning(self, "Missing required fields", "Please complete: " + ", ".join(missing))
            return
        super().accept()


class DesktopReceiptPanel(QWidget):
    """Floating desktop tab for fast receipt capture.

    The panel is intentionally form-first. It behaves like a small desktop
    widget, but the main interaction is the same as the app's Add Receipt
    workflow: enter the transaction, save it, then keep working.
    """

    def __init__(
        self,
        db: ReceiptDatabase,
        fields: list[FieldDefinition],
        on_receipt_saved,
        on_open_app,
        on_position_changed=None,
        width: int = 430,
        height: int = 640,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.db = db
        self.fields = [field for field in fields if field.quick_entry]
        self.on_receipt_saved = on_receipt_saved
        self.on_open_app = on_open_app
        self.on_position_changed = on_position_changed
        self.widgets: dict[str, QWidget] = {}
        self._drag_offset: QPoint | None = None

        self.setWindowTitle("ReceiptFlow quick add")
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet(APP_QSS)
        self.set_panel_size(width, height)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)

        panel = QFrame()
        panel.setObjectName("DesktopPanel")
        panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        outer.addWidget(panel)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        header_widget = QWidget()
        header_widget.setObjectName("DesktopDragHeader")
        header_widget.setCursor(Qt.CursorShape.OpenHandCursor)
        header_widget.installEventFilter(self)
        header = QHBoxLayout(header_widget)
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)

        title_area = QVBoxLayout()
        title_area.setSpacing(2)
        title = QLabel("Quick receipt")
        title.setObjectName("DesktopPanelTitle")
        title.installEventFilter(self)
        title.setCursor(Qt.CursorShape.OpenHandCursor)
        title_area.addWidget(title)
        header.addLayout(title_area)
        header.addStretch()

        open_btn = QPushButton("Open app")
        open_btn.setObjectName("DesktopOpenAppButton")
        open_btn.setToolTip("Open ReceiptFlow")
        open_btn.clicked.connect(self._open_app)
        header.addWidget(open_btn)

        close_btn = QPushButton("×")
        close_btn.setObjectName("DesktopIconButton")
        close_btn.setToolTip("Hide desktop tab")
        close_btn.clicked.connect(self.hide)
        header.addWidget(close_btn)
        layout.addWidget(header_widget)

        form_wrap = QFrame()
        form_wrap.setObjectName("DesktopFormCard")
        form_wrap.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        form_layout = QVBoxLayout(form_wrap)
        form_layout.setContentsMargins(12, 12, 12, 12)
        form_layout.setSpacing(8)

        self.form_container = QWidget()
        self.form = QFormLayout(self.form_container)
        self.form.setContentsMargins(0, 0, 0, 0)
        self.form.setSpacing(8)
        self.form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form_layout.addWidget(self.form_container)
        layout.addWidget(form_wrap)

        actions = QHBoxLayout()
        self.save_btn = QPushButton("Save receipt")
        self.save_btn.setObjectName("DesktopPrimaryButton")
        self.save_btn.setDefault(True)
        self.save_btn.clicked.connect(self.save_receipt)
        actions.addWidget(self.save_btn, 2)

        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("DesktopSecondaryButton")
        clear_btn.clicked.connect(self.clear_form)
        actions.addWidget(clear_btn, 1)
        layout.addLayout(actions)

        self.status_label = QLabel("")
        self.status_label.setObjectName("DesktopStatus")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        today_header = QHBoxLayout()
        today_label = QLabel("Today's receipts")
        today_label.setObjectName("DesktopSubheading")
        self.today_count_label = QLabel("0 today")
        self.today_count_label.setObjectName("DesktopHint")
        today_header.addWidget(today_label)
        today_header.addStretch()
        today_header.addWidget(self.today_count_label)
        layout.addLayout(today_header)

        self.today_toggle = QPushButton("Show today’s receipts ▾")
        self.today_toggle.setObjectName("DesktopDropdownButton")
        self.today_toggle.setCheckable(True)
        self.today_toggle.clicked.connect(self.toggle_today_receipts)
        layout.addWidget(self.today_toggle)

        self.today_dropdown = QFrame()
        self.today_dropdown.setObjectName("DesktopDropdownPanel")
        self.today_dropdown.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        dropdown_layout = QVBoxLayout(self.today_dropdown)
        dropdown_layout.setContentsMargins(8, 8, 8, 8)
        dropdown_layout.setSpacing(6)

        self.today_list = QListWidget()
        self.today_list.setObjectName("DesktopReceiptList")
        self.today_list.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.today_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.today_list.setMinimumHeight(96)
        self.today_list.setMaximumHeight(190)
        dropdown_layout.addWidget(self.today_list)
        self.today_dropdown.hide()
        layout.addWidget(self.today_dropdown)

        footer = QLabel("Drag the title area to move this desktop tab")
        footer.setObjectName("DesktopHint")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(footer)

        self.rebuild_form()
        self.refresh()

    def set_panel_size(self, width: int, height: int) -> None:
        safe_width = max(360, min(int(width or 430), 900))
        safe_height = max(520, min(int(height or 640), 1000))
        self.setFixedSize(safe_width, safe_height)

    def update_context(self, db: ReceiptDatabase, fields: list[FieldDefinition]) -> None:
        self.db = db
        quick_keys = [field.key for field in fields if field.quick_entry]
        current_keys = [field.key for field in self.fields]
        if quick_keys != current_keys:
            self.fields = [field for field in fields if field.quick_entry]
            self.rebuild_form()
        else:
            self.fields = [field for field in fields if field.quick_entry]
        self.refresh()

    def rebuild_form(self) -> None:
        while self.form.rowCount():
            self.form.removeRow(0)
        self.widgets.clear()
        for field_def in self.fields:
            widget = self._make_widget(field_def)
            self.widgets[field_def.key] = widget
            required = " *" if field_def.required else ""
            label = QLabel(f"{field_def.label}{required}")
            label.setObjectName("DesktopFieldLabel")
            self.form.addRow(label, widget)

    def _make_widget(self, field_def: FieldDefinition) -> QWidget:
        if field_def.field_type == "date":
            widget = QDateEdit()
            widget.setCalendarPopup(True)
            widget.setDisplayFormat("dd/MM/yyyy")
            widget.setDate(QDate.currentDate())
        elif field_def.field_type in {"number", "currency"}:
            widget = QDoubleSpinBox()
            widget.setMaximum(999999999.99)
            widget.setDecimals(2)
            widget.setPrefix("$" if field_def.field_type == "currency" else "")
        elif field_def.field_type == "textarea":
            widget = QTextEdit()
            widget.setFixedHeight(58)
        elif field_def.field_type == "dropdown":
            widget = QComboBox()
            widget.setEditable(True)
            widget.addItems(field_def.options)
        else:
            widget = QLineEdit()

        # Let Return/Enter save the form from any field in the desktop tab.
        # Shift+Enter still creates a new line in textarea fields.
        widget.installEventFilter(self)
        return widget

    def values(self) -> dict[str, Any]:
        values: dict[str, Any] = {}
        for field_def in self.fields:
            widget = self.widgets[field_def.key]
            if isinstance(widget, QDateEdit):
                values[field_def.key] = widget.date().toString("yyyy-MM-dd")
            elif isinstance(widget, QDoubleSpinBox):
                values[field_def.key] = widget.value()
            elif isinstance(widget, QTextEdit):
                values[field_def.key] = widget.toPlainText().strip()
            elif isinstance(widget, QComboBox):
                values[field_def.key] = widget.currentText().strip()
            elif isinstance(widget, QLineEdit):
                values[field_def.key] = widget.text().strip()
        return values

    def save_receipt(self) -> None:
        values = self.values()
        missing = [field.label for field in self.fields if field.required and not str(values.get(field.key, "")).strip()]
        if missing:
            self.status_label.setText("Complete required fields: " + ", ".join(missing))
            return

        custom = {key: value for key, value in values.items() if key not in CORE_FIELD_KEYS}
        record = ReceiptRecord(
            receipt_no=str(values.get("receipt_no", "") or ""),
            transaction_date=str(values.get("transaction_date", "") or ""),
            name=str(values.get("name", "") or ""),
            amount=float(values.get("amount", 0) or 0),
            payment_type=str(values.get("payment_type", "") or ""),
            member_no=str(values.get("member_no", "") or ""),
            notes=str(values.get("notes", "") or ""),
            custom_fields=custom,
            source="desktop-tab",
        )
        self.db.upsert_receipt(record)
        self.status_label.setText("Receipt saved.")
        self.clear_form(keep_status=True)
        self.refresh()
        self.on_receipt_saved()

    def clear_form(self, keep_status: bool = False) -> None:
        for field_def in self.fields:
            widget = self.widgets.get(field_def.key)
            if isinstance(widget, QDateEdit):
                widget.setDate(QDate.currentDate())
            elif isinstance(widget, QDoubleSpinBox):
                widget.setValue(0)
            elif isinstance(widget, QTextEdit):
                widget.clear()
            elif isinstance(widget, QComboBox):
                widget.setCurrentText("")
            elif isinstance(widget, QLineEdit):
                widget.clear()
        if not keep_status:
            self.status_label.setText("")

    def refresh(self) -> None:
        today = date.today().isoformat()
        rows = self.db.receipts_for_date(today, limit=50)
        self.today_list.clear()
        self.today_count_label.setText(f"{len(rows)} today")

        if not rows:
            empty_item = QListWidgetItem("No receipts today")
            empty_item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.today_list.addItem(empty_item)
            self.today_toggle.setText("No receipts today ▾")
            self.today_toggle.setEnabled(False)
            self.today_dropdown.hide()
            self.today_toggle.setChecked(False)
            return

        self.today_toggle.setEnabled(True)
        self.today_toggle.setText(f"Show today’s receipts ({len(rows)}) ▾")
        for row in rows:
            amount = f"${float(row['amount']):,.2f}" if row["amount"] not in {None, ""} else ""
            name = row["name"] or row["receipt_no"] or "Unnamed receipt"
            receipt_no = row["receipt_no"] or "No receipt no"
            created = (row["created_at"] or "")[11:16] if "created_at" in row.keys() else ""
            prefix = f"{created} · " if created else ""
            self.today_list.addItem(f"{prefix}{name} | {receipt_no} | {amount}")

    def toggle_today_receipts(self) -> None:
        open_now = self.today_toggle.isChecked()
        self.today_dropdown.setVisible(open_now)
        if open_now:
            self.today_toggle.setText(self.today_toggle.text().replace("▾", "▴"))
        else:
            self.today_toggle.setText(self.today_toggle.text().replace("▴", "▾"))

    def _open_app(self) -> None:
        self.on_open_app()
        self.refresh()

    def eventFilter(self, watched, event) -> bool:
        if event.type() == QEvent.Type.KeyPress and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if isinstance(watched, QTextEdit) and event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                return False
            self.save_receipt()
            event.accept()
            return True
        if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            watched.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return True
        if event.type() == QEvent.Type.MouseMove and self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
            return True
        if event.type() == QEvent.Type.MouseButtonRelease and self._drag_offset is not None:
            self._drag_offset = None
            watched.setCursor(Qt.CursorShape.OpenHandCursor)
            if self.on_position_changed:
                self.on_position_changed(self.pos())
            event.accept()
            return True
        return super().eventFilter(watched, event)


class ReceiptMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.store = SettingsStore()
        self.settings = self.store.load()
        self.db = ReceiptDatabase(self.settings.db_path)
        self.last_rows: list[Any] = []
        self.tray: QSystemTrayIcon | None = None
        self.desktop_panel: DesktopReceiptPanel | None = None

        self.setWindowTitle("ReceiptFlow")
        self.resize(1120, 760)
        self.setStyleSheet(APP_QSS)

        self.stack = QStackedWidget()
        self.setCentralWidget(self._build_shell())
        self._build_pages()
        self._setup_tray()
        self.refresh_results()

    def _build_shell(self) -> QWidget:
        shell = QWidget()
        root = QHBoxLayout(shell)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(230)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(18, 22, 18, 18)
        side_layout.setSpacing(12)

        app_title = QLabel("ReceiptFlow")
        app_title.setObjectName("SectionTitle")
        app_tagline = QLabel("Local receipt capture and search")
        app_tagline.setObjectName("Subtitle")
        app_tagline.setWordWrap(True)
        side_layout.addWidget(app_title)
        side_layout.addWidget(app_tagline)
        side_layout.addSpacing(12)

        self.home_btn = self._side_button("Home", lambda: self.stack.setCurrentIndex(0))
        self.browse_btn = self._side_button("Browse transactions", lambda: self.stack.setCurrentIndex(1))
        self.quick_btn = self._side_button("Quick receipt", self.open_quick_receipt)
        self.desktop_btn = self._side_button("Desktop tab", self.show_desktop_tab)
        self.settings_btn = self._side_button("Settings", lambda: self.stack.setCurrentIndex(2))
        for button in [self.home_btn, self.browse_btn, self.quick_btn, self.desktop_btn, self.settings_btn]:
            side_layout.addWidget(button)
        side_layout.addStretch()

        db_label = QLabel(f"Database:\n{self.settings.db_path}")
        db_label.setObjectName("Subtitle")
        db_label.setWordWrap(True)
        self.db_path_sidebar_label = db_label
        side_layout.addWidget(db_label)

        root.addWidget(sidebar)
        root.addWidget(self.stack, 1)
        return shell

    def _side_button(self, text: str, slot) -> QPushButton:
        button = QPushButton(text)
        button.setMinimumHeight(44)
        button.clicked.connect(slot)
        return button

    def _build_pages(self) -> None:
        self.stack.addWidget(self._home_page())
        self.stack.addWidget(self._browse_page())
        self.stack.addWidget(self._settings_page())

    def _home_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(18)

        title = QLabel("Receipt database")
        title.setObjectName("Title")
        subtitle = QLabel("Capture receipts manually, import existing files, then search and sort transactions from one local database.")
        subtitle.setObjectName("Subtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        grid = QGridLayout()
        grid.setSpacing(16)
        grid.addWidget(self._action_card("Quick receipt entry", "Open a desktop popup and record a transaction immediately.", "Add receipt", self.open_quick_receipt, primary=True), 0, 0)
        grid.addWidget(self._action_card("Upload CSV or Excel", "Import legacy receipts and map them to your configured fields.", "Upload file", self.import_receipts), 0, 1)
        grid.addWidget(self._action_card("Browse transactions", "Search across receipt number, name, amount, date, notes and custom fields.", "Browse", lambda: self.stack.setCurrentIndex(1)), 1, 0)
        grid.addWidget(self._action_card("Desktop tab", "Keep a small, draggable desktop panel open for fast access to recent receipts.", "Show desktop tab", self.show_desktop_tab), 1, 1)
        grid.addWidget(self._action_card("Settings", "Configure fields, database path, default import folder and tray behaviour.", "Open settings", lambda: self.stack.setCurrentIndex(2)), 2, 0, 1, 2)
        layout.addLayout(grid)

        self.summary_label = QLabel("")
        self.summary_label.setObjectName("Subtitle")
        layout.addWidget(self.summary_label)
        layout.addStretch()
        return page

    def _action_card(self, heading: str, body: str, button_text: str, slot, primary: bool = False) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        card.setMinimumHeight(180)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 18, 18, 18)
        heading_label = QLabel(heading)
        heading_label.setObjectName("SectionTitle")
        body_label = QLabel(body)
        body_label.setObjectName("Subtitle")
        body_label.setWordWrap(True)
        button = QPushButton(button_text)
        if primary:
            button.setObjectName("PrimaryButton")
        button.clicked.connect(slot)
        layout.addWidget(heading_label)
        layout.addWidget(body_label)
        layout.addStretch()
        layout.addWidget(button)
        return card

    def _browse_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(12)

        title = QLabel("Welcome back")
        title.setObjectName("Title")
        subtitle = QLabel("Search the database using receipt numbers, names, member numbers, notes, dates or amounts.")
        subtitle.setObjectName("Subtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        controls = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search anything, e.g. Smith, 2026-05-16, 45.00, card, receipt number")
        self.search_input.textChanged.connect(self.refresh_results)
        controls.addWidget(self.search_input, 2)

        self.sort_combo = QComboBox()
        self.sort_combo.addItems(list(SORT_OPTIONS.keys()))
        self.sort_combo.setCurrentText(self.settings.default_sort)
        self.sort_combo.currentTextChanged.connect(self.refresh_results)
        controls.addWidget(self.sort_combo)

        self.group_by_date = QCheckBox("Group by date")
        self.group_by_date.stateChanged.connect(self.refresh_results)
        controls.addWidget(self.group_by_date)
        layout.addLayout(controls)

        action_row = QHBoxLayout()
        export_btn = QPushButton("Export current results")
        export_btn.clicked.connect(self.export_current_results)
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_results)
        action_row.addWidget(export_btn)
        action_row.addWidget(refresh_btn)
        action_row.addStretch()
        layout.addLayout(action_row)

        self.results_stack = QStackedWidget()
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.grouped_list = QListWidget()
        self.results_stack.addWidget(self.table)
        self.results_stack.addWidget(self.grouped_list)
        layout.addWidget(self.results_stack, 1)

        self.result_count_label = QLabel("")
        self.result_count_label.setObjectName("Subtitle")
        layout.addWidget(self.result_count_label)
        return page

    def _settings_page(self) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(32, 32, 32, 32)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(16)

        title = QLabel("Settings")
        title.setObjectName("Title")
        subtitle = QLabel("Configure the receipt popup, import behaviour and local database path.")
        subtitle.setObjectName("Subtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        database_box = QGroupBox("Database and import")
        database_form = QFormLayout(database_box)
        self.db_path_input = QLineEdit(str(self.settings.db_path))
        db_browse_btn = QPushButton("Choose database")
        db_browse_btn.clicked.connect(self.choose_database_path)
        db_row = QHBoxLayout()
        db_row.addWidget(self.db_path_input, 1)
        db_row.addWidget(db_browse_btn)
        database_form.addRow("Database file", db_row)

        self.import_folder_input = QLineEdit(str(self.settings.import_folder))
        import_browse_btn = QPushButton("Choose folder")
        import_browse_btn.clicked.connect(self.choose_import_folder)
        import_row = QHBoxLayout()
        import_row.addWidget(self.import_folder_input, 1)
        import_row.addWidget(import_browse_btn)
        database_form.addRow("Default import folder", import_row)

        self.tray_checkbox = QCheckBox("Show menu bar/tray quick access")
        self.tray_checkbox.setChecked(self.settings.enable_tray)
        database_form.addRow("Quick access", self.tray_checkbox)

        self.start_minimised_checkbox = QCheckBox("Start minimised")
        self.start_minimised_checkbox.setChecked(self.settings.start_minimised)
        database_form.addRow("Startup", self.start_minimised_checkbox)

        self.desktop_tab_launch_checkbox = QCheckBox("Show desktop tab on launch")
        self.desktop_tab_launch_checkbox.setChecked(self.settings.show_desktop_tab_on_launch)
        database_form.addRow("Desktop tab", self.desktop_tab_launch_checkbox)

        self.desktop_width_spin = QSpinBox()
        self.desktop_width_spin.setRange(360, 900)
        self.desktop_width_spin.setSuffix(" px wide")
        self.desktop_width_spin.setValue(self.settings.desktop_tab_width)
        self.desktop_height_spin = QSpinBox()
        self.desktop_height_spin.setRange(520, 1000)
        self.desktop_height_spin.setSuffix(" px high")
        self.desktop_height_spin.setValue(self.settings.desktop_tab_height)
        desktop_size_row = QHBoxLayout()
        desktop_size_row.addWidget(self.desktop_width_spin)
        desktop_size_row.addWidget(self.desktop_height_spin)
        database_form.addRow("Desktop size", desktop_size_row)
        layout.addWidget(database_box)

        fields_box = QGroupBox("Receipt fields")
        fields_layout = QVBoxLayout(fields_box)
        helper = QLabel("These fields drive both the quick-entry popup and the import mapping. Custom fields are stored in JSON so the database stays flexible.")
        helper.setObjectName("Subtitle")
        helper.setWordWrap(True)
        fields_layout.addWidget(helper)

        self.fields_table = QTableWidget()
        self.fields_table.setColumnCount(6)
        self.fields_table.setHorizontalHeaderLabels(["Key", "Label", "Type", "Required", "Quick", "Browse"])
        self.fields_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        fields_layout.addWidget(self.fields_table)

        field_buttons = QHBoxLayout()
        add_field_btn = QPushButton("Add custom field")
        add_field_btn.clicked.connect(self.add_field_row)
        remove_field_btn = QPushButton("Remove selected field")
        remove_field_btn.setObjectName("DangerButton")
        remove_field_btn.clicked.connect(self.remove_field_row)
        field_buttons.addWidget(add_field_btn)
        field_buttons.addWidget(remove_field_btn)
        field_buttons.addStretch()
        fields_layout.addLayout(field_buttons)
        layout.addWidget(fields_box)

        save_btn = QPushButton("Save settings")
        save_btn.setObjectName("PrimaryButton")
        save_btn.clicked.connect(self.save_settings_from_ui)
        layout.addWidget(save_btn)
        layout.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll)
        self.populate_fields_table()
        return page

    def populate_fields_table(self) -> None:
        self.fields_table.setRowCount(len(self.settings.fields))
        for row, field_def in enumerate(self.settings.fields):
            self.fields_table.setItem(row, 0, QTableWidgetItem(field_def.key))
            self.fields_table.setItem(row, 1, QTableWidgetItem(field_def.label))
            type_combo = QComboBox()
            type_combo.addItems(["text", "number", "currency", "date", "textarea", "dropdown"])
            type_combo.setCurrentText(field_def.field_type)
            self.fields_table.setCellWidget(row, 2, type_combo)
            for col, value in [(3, field_def.required), (4, field_def.quick_entry), (5, field_def.browse_column)]:
                self.fields_table.setCellWidget(row, col, CenteredCheckBox(value))

    def add_field_row(self) -> None:
        row = self.fields_table.rowCount()
        self.fields_table.insertRow(row)
        self.fields_table.setItem(row, 0, QTableWidgetItem("custom_field"))
        self.fields_table.setItem(row, 1, QTableWidgetItem("Custom Field"))
        type_combo = QComboBox()
        type_combo.addItems(["text", "number", "currency", "date", "textarea", "dropdown"])
        self.fields_table.setCellWidget(row, 2, type_combo)
        for col in [3, 4, 5]:
            self.fields_table.setCellWidget(row, col, CenteredCheckBox(col != 3))

    def remove_field_row(self) -> None:
        row = self.fields_table.currentRow()
        if row < 0:
            return
        key_item = self.fields_table.item(row, 0)
        if key_item and key_item.text() in CORE_FIELD_KEYS:
            QMessageBox.warning(self, "Core field", "Core fields cannot be removed. You can untick Quick or Browse instead.")
            return
        self.fields_table.removeRow(row)

    def choose_database_path(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Choose database file", self.db_path_input.text(), "SQLite database (*.db)")
        if path:
            self.db_path_input.setText(path)

    def choose_import_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choose import folder", self.import_folder_input.text())
        if path:
            self.import_folder_input.setText(path)

    def save_settings_from_ui(self) -> None:
        fields: list[FieldDefinition] = []
        seen: set[str] = set()
        for row in range(self.fields_table.rowCount()):
            key = (self.fields_table.item(row, 0).text() if self.fields_table.item(row, 0) else "").strip().lower().replace(" ", "_")
            label = (self.fields_table.item(row, 1).text() if self.fields_table.item(row, 1) else "").strip()
            if not key or not label:
                QMessageBox.warning(self, "Invalid field", "Each field needs a key and label.")
                return
            if key in seen:
                QMessageBox.warning(self, "Duplicate field", f"The field key '{key}' is duplicated.")
                return
            seen.add(key)
            type_combo = self.fields_table.cellWidget(row, 2)
            required = self.fields_table.cellWidget(row, 3).isChecked()
            quick = self.fields_table.cellWidget(row, 4).isChecked()
            browse = self.fields_table.cellWidget(row, 5).isChecked()
            fields.append(FieldDefinition(key, label, type_combo.currentText(), required, quick, browse))

        self.settings.db_path = Path(self.db_path_input.text()).expanduser()
        self.settings.import_folder = Path(self.import_folder_input.text()).expanduser()
        self.settings.enable_tray = self.tray_checkbox.isChecked()
        self.settings.start_minimised = self.start_minimised_checkbox.isChecked()
        self.settings.show_desktop_tab_on_launch = self.desktop_tab_launch_checkbox.isChecked()
        self.settings.desktop_tab_width = self.desktop_width_spin.value()
        self.settings.desktop_tab_height = self.desktop_height_spin.value()
        self.settings.default_sort = self.sort_combo.currentText() if hasattr(self, "sort_combo") else self.settings.default_sort
        self.settings.fields = fields
        self.store.save(self.settings)
        self.db = ReceiptDatabase(self.settings.db_path)
        self.db_path_sidebar_label.setText(f"Database:\n{self.settings.db_path}")
        self._setup_tray()
        if self.desktop_panel is not None:
            self.desktop_panel.set_panel_size(self.settings.desktop_tab_width, self.settings.desktop_tab_height)
            self.desktop_panel.update_context(self.db, self.settings.fields)
        self.refresh_results()
        QMessageBox.information(self, "Settings saved", "Settings saved successfully.")

    def open_quick_receipt(self) -> None:
        dialog = ReceiptFormDialog(self.settings.fields, self)
        if dialog.exec() != QDialog.Accepted:
            return
        values = dialog.values()
        custom = {key: value for key, value in values.items() if key not in CORE_FIELD_KEYS}
        record = ReceiptRecord(
            receipt_no=str(values.get("receipt_no", "") or ""),
            transaction_date=str(values.get("transaction_date", "") or ""),
            name=str(values.get("name", "") or ""),
            amount=float(values.get("amount", 0) or 0),
            payment_type=str(values.get("payment_type", "") or ""),
            member_no=str(values.get("member_no", "") or ""),
            notes=str(values.get("notes", "") or ""),
            custom_fields=custom,
            source="manual",
        )
        self.db.upsert_receipt(record)
        self.refresh_results()
        self.refresh_desktop_tab()
        QMessageBox.information(self, "Receipt saved", "The receipt was added to the database.")

    def import_receipts(self) -> None:
        start = str(self.settings.import_folder if self.settings.import_folder.exists() else Path.home())
        path, _ = QFileDialog.getOpenFileName(self, "Upload receipts", start, "Receipt files (*.csv *.xlsx *.xlsm *.xltx *.xltm)")
        if not path:
            return
        try:
            preview = mapping_preview(Path(path), self.settings.fields)
            mapped_labels = []
            for key, index in preview["mapping"].items():
                label = next((field.label for field in self.settings.fields if field.key == key), key)
                header = preview["headers"][index] if index < len(preview["headers"]) else ""
                mapped_labels.append(f"{label} ← {header}")
            confirm = QMessageBox.question(
                self,
                "Confirm import",
                "Detected mapping:\n\n" + "\n".join(mapped_labels or ["No mapping detected"]) + "\n\nContinue with import?",
            )
            if confirm != QMessageBox.Yes:
                return
            result = import_file(Path(path), self.db, self.settings.fields)
            self.refresh_results()
            self.refresh_desktop_tab()
            error_preview = "\n".join((result.errors or [])[:5])
            QMessageBox.information(
                self,
                "Import complete",
                f"Imported: {result.imported}\nSkipped: {result.skipped}" + (f"\n\nErrors:\n{error_preview}" if error_preview else ""),
            )
        except Exception as exc:
            QMessageBox.critical(self, "Import failed", str(exc))

    def refresh_results(self) -> None:
        if not hasattr(self, "table"):
            return
        query = self.search_input.text() if hasattr(self, "search_input") else ""
        sort = self.sort_combo.currentText() if hasattr(self, "sort_combo") else self.settings.default_sort
        self.last_rows = self.db.search(query=query, sort=sort)
        if self.group_by_date.isChecked():
            self.results_stack.setCurrentIndex(1)
            self._populate_grouped_results()
        else:
            self.results_stack.setCurrentIndex(0)
            self._populate_table()
        self.result_count_label.setText(f"Showing {len(self.last_rows)} transaction(s).")
        if hasattr(self, "summary_label"):
            self.summary_label.setText(f"Current database: {len(self.db.search(limit=999999))} receipt(s).")

    def _visible_field_keys(self) -> list[str]:
        return [field.key for field in self.settings.fields if field.browse_column]

    def _visible_field_labels(self) -> list[str]:
        return [field.label for field in self.settings.fields if field.browse_column]

    def _populate_table(self) -> None:
        keys = self._visible_field_keys()
        labels = self._visible_field_labels()
        self.table.clear()
        self.table.setColumnCount(len(keys))
        self.table.setHorizontalHeaderLabels(labels)
        self.table.setRowCount(len(self.last_rows))
        for row_index, row in enumerate(self.last_rows):
            custom = json.loads(row["custom_fields"] or "{}")
            for col_index, key in enumerate(keys):
                value = row[key] if key in CORE_FIELD_KEYS else custom.get(key, "")
                if key == "amount" and value not in {None, ""}:
                    value = f"${float(value):,.2f}"
                item = QTableWidgetItem(str(value or ""))
                self.table.setItem(row_index, col_index, item)

    def _populate_grouped_results(self) -> None:
        self.grouped_list.clear()
        grouped = self.db.grouped_by_date(self.last_rows)
        for date, rows in grouped.items():
            header = QListWidgetItem(f"{date} — {len(rows)} transaction(s)")
            header.setFlags(Qt.NoItemFlags)
            self.grouped_list.addItem(header)
            for row in rows:
                amount = f"${float(row['amount']):,.2f}" if row["amount"] not in {None, ""} else ""
                item = QListWidgetItem(f"   {row['name'] or 'Unnamed'} | {row['receipt_no'] or 'No receipt no'} | {amount} | {row['payment_type'] or ''}")
                self.grouped_list.addItem(item)

    def export_current_results(self) -> None:
        if not self.last_rows:
            QMessageBox.information(self, "Nothing to export", "There are no current results to export.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export results", str(Path.home() / "receipt-results.csv"), "CSV files (*.csv)")
        if not path:
            return
        self.db.export_rows(self.last_rows, Path(path), self.settings.fields)
        QMessageBox.information(self, "Export complete", f"Saved to {path}")

    def show_desktop_tab(self) -> None:
        if self.desktop_panel is None:
            self.desktop_panel = DesktopReceiptPanel(
                self.db,
                self.settings.fields,
                self._desktop_receipt_saved,
                self.show_normal,
                self.save_desktop_tab_position,
                self.settings.desktop_tab_width,
                self.settings.desktop_tab_height,
            )
            if self.settings.desktop_tab_x is not None and self.settings.desktop_tab_y is not None:
                self.desktop_panel.move(self.settings.desktop_tab_x, self.settings.desktop_tab_y)
            else:
                self.desktop_panel.move(18, 44)
        else:
            self.desktop_panel.set_panel_size(self.settings.desktop_tab_width, self.settings.desktop_tab_height)
            self.desktop_panel.update_context(self.db, self.settings.fields)
        self.desktop_panel.show()
        self.desktop_panel.raise_()
        self.desktop_panel.activateWindow()

    def save_desktop_tab_position(self, position: QPoint) -> None:
        self.settings.desktop_tab_x = position.x()
        self.settings.desktop_tab_y = position.y()
        self.store.save(self.settings)

    def _desktop_receipt_saved(self) -> None:
        self.refresh_results()
        self.refresh_desktop_tab()

    def refresh_desktop_tab(self) -> None:
        if self.desktop_panel is not None:
            self.desktop_panel.update_context(self.db, self.settings.fields)
            self.desktop_panel.refresh()

    def _app_icon(self) -> QIcon:
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(Qt.GlobalColor.white)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(8, 6, 48, 52, 10, 10)
        painter.setBrush(Qt.GlobalColor.blue)
        painter.drawRoundedRect(14, 14, 36, 8, 4, 4)
        painter.setBrush(Qt.GlobalColor.darkBlue)
        painter.drawRoundedRect(14, 28, 26, 5, 3, 3)
        painter.drawRoundedRect(14, 39, 32, 5, 3, 3)
        painter.end()
        return QIcon(pixmap)

    def _setup_tray(self) -> None:
        if self.tray:
            self.tray.hide()
            self.tray = None
        if not self.settings.enable_tray or not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray = QSystemTrayIcon(self._app_icon(), self)
        menu = QMenu()
        show_action = QAction("Show ReceiptFlow", self)
        show_action.triggered.connect(self.show_normal)
        new_action = QAction("New receipt", self)
        new_action.triggered.connect(self.open_quick_receipt)
        browse_action = QAction("Browse transactions", self)
        browse_action.triggered.connect(lambda: (self.show_normal(), self.stack.setCurrentIndex(1)))
        desktop_action = QAction("Show desktop tab", self)
        desktop_action.triggered.connect(self.show_desktop_tab)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.quit)
        menu.addAction(show_action)
        menu.addAction(new_action)
        menu.addAction(browse_action)
        menu.addAction(desktop_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda reason: self.open_quick_receipt() if reason == QSystemTrayIcon.Trigger else None)
        self.tray.show()

    def show_normal(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.tray and self.tray.isVisible():
            self.hide()
            event.ignore()
        else:
            event.accept()


def run() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("ReceiptFlow")
    app.setStyleSheet(APP_QSS)
    window = ReceiptMainWindow()
    if not window.settings.start_minimised:
        window.show()
    if window.settings.show_desktop_tab_on_launch:
        window.show_desktop_tab()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
