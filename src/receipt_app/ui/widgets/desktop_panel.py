from __future__ import annotations

from datetime import date

from PySide6.QtCore import QEvent, QPoint, QSize, Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ...config import CORE_FIELD_KEYS, FieldDefinition
from ...database import ReceiptDatabase, ReceiptRecord
from ...styles import APP_QSS
from ..assets import app_icon
from .receipt_entry_form import ReceiptEntryForm


class DesktopReceiptPanel(QWidget):
    """Floating desktop tab for fast receipt capture.

    The panel supplies the desktop-specific shell and persistence behaviour while
    ``ReceiptEntryForm`` owns the actual receipt-entry workflow.
    """

    def __init__(
        self,
        db: ReceiptDatabase,
        fields: list[FieldDefinition],
        on_receipt_saved,
        on_open_app,
        on_position_changed=None,
        on_delete_receipt=None,
        width: int = 430,
        height: int = 640,
        parent: QWidget | None = None,
        catalog: dict[str, dict[str, float]] | None = None,
        surcharge_rates: dict[str, float] | None = None,
    ):
        super().__init__(parent)
        self.db = db
        self.on_receipt_saved = on_receipt_saved
        self.on_open_app = on_open_app
        self.on_position_changed = on_position_changed
        self.on_delete_receipt = on_delete_receipt
        self._drag_offset: QPoint | None = None
        self._suggested_receipt_no: str | None = None

        self.setWindowTitle("ReceiptFlow quick add")
        self.setWindowIcon(app_icon())
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
        layout.setContentsMargins(12, 12, 12, 10)
        layout.setSpacing(10)

        # Branded draggable header -------------------------------------------------
        header_widget = QWidget()
        header_widget.setObjectName("DesktopDragHeader")
        header_widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        header_widget.setCursor(Qt.CursorShape.OpenHandCursor)
        header_widget.setMinimumHeight(58)
        header_widget.installEventFilter(self)

        header = QHBoxLayout(header_widget)
        header.setContentsMargins(14, 8, 10, 8)
        header.setSpacing(9)

        drag_handle = QLabel("⠿")
        drag_handle.setObjectName("DesktopDragHandle")
        drag_handle.setCursor(Qt.CursorShape.OpenHandCursor)
        drag_handle.installEventFilter(self)
        header.addWidget(drag_handle)

        title = QLabel("Quick receipt")
        title.setObjectName("DesktopPanelTitle")
        title.installEventFilter(self)
        title.setCursor(Qt.CursorShape.OpenHandCursor)
        header.addWidget(title)
        header.addStretch()

        open_btn = QPushButton("Open app  ↗")
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

        # Receipt-entry card -------------------------------------------------------
        form_wrap = QFrame()
        form_wrap.setObjectName("DesktopFormCard")
        form_wrap.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        form_layout = QVBoxLayout(form_wrap)
        form_layout.setContentsMargins(12, 12, 12, 12)
        form_layout.setSpacing(8)

        self.entry_form = ReceiptEntryForm(
            fields,
            form_wrap,
            quick_only=True,
            catalog=catalog,
            surcharge_rates=surcharge_rates,
            compact=True,
            field_label_object_name="DesktopFieldLabel",
            event_filter_target=self,
        )
        self.entry_form.setObjectName("DesktopEntryForm")
        form_layout.addWidget(self.entry_form)

        form_divider = QFrame()
        form_divider.setObjectName("DesktopDivider")
        form_divider.setFixedHeight(1)
        form_layout.addWidget(form_divider)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        self.save_btn = QPushButton("Save receipt")
        self.save_btn.setObjectName("DesktopPrimaryButton")
        self.save_btn.setDefault(True)
        self.save_btn.clicked.connect(self.save_receipt)
        actions.addWidget(self.save_btn, 2)

        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("DesktopSecondaryButton")
        clear_btn.clicked.connect(self.clear_form)
        actions.addWidget(clear_btn, 1)
        form_layout.addLayout(actions)

        self.status_label = QLabel("")
        self.status_label.setObjectName("DesktopStatus")
        self.status_label.setWordWrap(True)
        form_layout.addWidget(self.status_label)
        layout.addWidget(form_wrap)

        # Today's receipts card ----------------------------------------------------
        today_card = QFrame()
        today_card.setObjectName("DesktopTodayCard")
        today_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        today_layout = QVBoxLayout(today_card)
        today_layout.setContentsMargins(12, 10, 12, 10)
        today_layout.setSpacing(8)

        today_header = QHBoxLayout()
        today_header.setSpacing(8)

        today_accent = QLabel("")
        today_accent.setObjectName("DesktopTodayAccent")
        today_accent.setFixedSize(11, 11)
        today_header.addWidget(today_accent)

        today_label = QLabel("Today's receipts")
        today_label.setObjectName("DesktopSubheading")
        self.today_count_label = QLabel("0 today")
        self.today_count_label.setObjectName("DesktopTodayCount")
        today_header.addWidget(today_label)
        today_header.addStretch()
        today_header.addWidget(self.today_count_label)
        today_layout.addLayout(today_header)

        self.today_toggle = QPushButton("Show today’s receipts ▾")
        self.today_toggle.setObjectName("DesktopDropdownButton")
        self.today_toggle.setCheckable(True)
        self.today_toggle.clicked.connect(self.toggle_today_receipts)
        today_layout.addWidget(self.today_toggle)

        self.today_dropdown = QFrame()
        self.today_dropdown.setObjectName("DesktopDropdownPanel")
        self.today_dropdown.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        dropdown_layout = QVBoxLayout(self.today_dropdown)
        dropdown_layout.setContentsMargins(6, 6, 6, 6)
        dropdown_layout.setSpacing(6)

        self.today_list = QListWidget()
        self.today_list.setObjectName("DesktopReceiptList")
        self.today_list.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.today_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.today_list.setMinimumHeight(150)
        self.today_list.setMaximumHeight(280)
        self.today_list.setSpacing(6)
        dropdown_layout.addWidget(self.today_list)
        self.today_dropdown.hide()
        today_layout.addWidget(self.today_dropdown)
        layout.addWidget(today_card)

        # Quiet drag hint -----------------------------------------------------------
        footer_wrap = QWidget()
        footer_wrap.setObjectName("DesktopFooter")
        footer_layout = QHBoxLayout(footer_wrap)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.setSpacing(7)
        footer_layout.addStretch()

        footer_handle = QLabel("⠿")
        footer_handle.setObjectName("DesktopFooterHandle")
        footer_layout.addWidget(footer_handle)

        footer = QLabel("Drag the title area to move this desktop tab")
        footer.setObjectName("DesktopHint")
        footer_layout.addWidget(footer)
        footer_layout.addStretch()
        layout.addWidget(footer_wrap)

        self.load_next_receipt_number()
        self.refresh()

    def set_panel_size(self, width: int, height: int) -> None:
        safe_width = max(360, min(int(width or 430), 900))
        safe_height = max(520, min(int(height or 640), 1000))
        self.setFixedSize(safe_width, safe_height)

    def update_context(
        self,
        db: ReceiptDatabase,
        fields: list[FieldDefinition],
        catalog: dict[str, dict[str, float]] | None = None,
        surcharge_rates: dict[str, float] | None = None,
    ) -> None:
        self.db = db
        rebuilt = self.entry_form.update_context(
            fields,
            catalog,
            surcharge_rates,
            quick_only=True,
        )
        if rebuilt:
            self.load_next_receipt_number()
        self.refresh()

    def load_next_receipt_number(self) -> None:
        """Pre-fill the desktop receipt form with the next sequential number."""
        widget = self.entry_form.widget("receipt_no")
        if isinstance(widget, QLineEdit):
            self._suggested_receipt_no = self.db.next_receipt_number()
            widget.setText(self._suggested_receipt_no)

    def save_receipt(self) -> None:
        values = self.entry_form.values()

        if str(values.get("receipt_no", "")) == str(self._suggested_receipt_no or ""):
            fresh_receipt_no = self.db.next_receipt_number()
            values["receipt_no"] = fresh_receipt_no
            receipt_widget = self.entry_form.widget("receipt_no")
            if isinstance(receipt_widget, QLineEdit):
                receipt_widget.setText(fresh_receipt_no)

        issue = self.entry_form.validation_issue(values)
        if issue is not None:
            self.status_label.setText(issue.inline_message)
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
        self.entry_form.clear_values()
        self.load_next_receipt_number()
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

            item = QListWidgetItem()
            row_widget = QWidget()
            row_widget.setObjectName("DesktopReceiptRow")
            row_widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            row_widget.setMinimumHeight(70)
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(10, 8, 10, 8)
            row_layout.setSpacing(10)

            label = QLabel(f"{prefix}{name}\n{receipt_no} | {amount}")
            label.setObjectName("DesktopReceiptRowLabel")
            label.setWordWrap(True)
            label.setMinimumHeight(44)
            label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            row_layout.addWidget(label, 1)

            delete_btn = QPushButton("Delete")
            delete_btn.setObjectName("MiniDeleteButton")
            delete_btn.setMinimumSize(74, 34)
            delete_btn.clicked.connect(
                lambda checked=False, receipt_id=int(row["id"]): self.delete_receipt(receipt_id)
            )
            row_layout.addWidget(delete_btn)

            item.setSizeHint(QSize(0, 76))
            self.today_list.addItem(item)
            self.today_list.setItemWidget(item, row_widget)

    def delete_receipt(self, receipt_id: int) -> None:
        confirm = QMessageBox.question(
            self,
            "Move receipt to Trash",
            "Move this receipt to Trash? You can restore it later.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        self.db.delete_receipt(receipt_id)
        self.status_label.setText("Receipt moved to Trash.")
        self.refresh()
        self.on_receipt_saved()

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
