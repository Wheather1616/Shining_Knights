from __future__ import annotations

from dataclasses import fields
import json
import sys
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import QDate, QEvent, QPoint, QSize, Qt, QTimer
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
    QInputDialog,
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
    QTableView,
    QTableWidget,
    QTableWidgetItem,
    QAbstractItemView,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QSystemTrayIcon,
)

from .backup import DatabaseBackupManager
from .browse_model import BrowseTableModel, ReceiptActionsDelegate
from .config import (
    CATALOG_EXPANDABLE_CATEGORIES,
    CORE_FIELD_KEYS,
    DEFAULT_TRANSACTION_CATALOG,
    FieldDefinition,
    PAYMENT_TYPE_OPTIONS,
    SettingsStore,
    TRANSACTION_CATEGORY_OPTIONS,
    clone_catalog,
    description_for_selection,
    infer_category_from_description,
    normalise_surcharge_percentage,
    normalise_surcharge_rates,
    surcharge_percentage_for_payment,
    product_from_description,
    product_options,
    product_price,
)
from .database import ReceiptDatabase, ReceiptRecord, SORT_OPTIONS
from .db_crypto import DatabaseEncryptionError
from .paths import default_backup_dir
from .security import SecureKeyStoreError
from .single_instance import SingleInstanceManager
from .styles import APP_QSS

DROPDOWN_OPTIONS_BY_KEY = {
    "payment_type": list(PAYMENT_TYPE_OPTIONS),
}

WORKFLOW_FIELD_LABELS = {
    "receipt_category": "Category",
    "description": "Product / term",
    "quantity": "Quantity",
    "event_number": "Event number",
}
ASSETS_DIR = Path(__file__).resolve().parent / "assets"
APP_LOGO_PATH = ASSETS_DIR / "logo.jpg"


def _money(value: float | int | str | Decimal) -> float:
    """Round a currency value to cents using normal half-up rounding."""
    return float(
        Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    )


def _surcharge_totals(base_amount: float, percentage: float) -> tuple[float, float]:
    """Return (final total, surcharge amount), rounded independently to cents."""
    base = Decimal(str(base_amount or 0)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    rate = Decimal(str(normalise_surcharge_percentage(percentage))) / Decimal("100")
    surcharge = (base * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    total = (base + surcharge).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return float(total), float(surcharge)


class CurrencyLineEdit(QLineEdit):
    """A normal typable money field that formats values like $10.00."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setPlaceholderText("$0.00")
        self.editingFinished.connect(self.format_as_currency)

    def value(self) -> float:
        text = self.text().strip()
        if not text:
            return 0.0

        cleaned = (
            text.replace("$", "")
            .replace(",", "")
            .strip()
        )

        if not cleaned:
            return 0.0

        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    def format_as_currency(self) -> None:
        text = self.text().strip()
        if not text:
            return

        self.setText(f"${self.value():,.2f}")

    def set_value(self, value: Any) -> None:
        if value in {None, ""}:
            self.clear()
            return
        try:
            self.setText(f"${float(value):,.2f}")
        except (TypeError, ValueError):
            self.setText(str(value))

class DateLineEdit(QLineEdit):
    """A typable date field that defaults to today and saves as yyyy-mm-dd."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setPlaceholderText("dd/mm/yyyy")
        self.setText(date.today().strftime("%d/%m/%Y"))
        self.editingFinished.connect(self.format_date)

    def value(self) -> str:
        text = self.text().strip()
        if not text:
            return ""

        formats = [
            "%d/%m/%Y",
            "%d/%m/%y",
            "%Y-%m-%d",
            "%d-%m-%Y",
            "%d-%m-%y",
        ]

        for fmt in formats:
            try:
                parsed = datetime.strptime(text, fmt).date()
                return parsed.isoformat()
            except ValueError:
                continue

        return text

    def format_date(self) -> None:
        value = self.value()
        if not value:
            return

        try:
            parsed = datetime.strptime(value, "%Y-%m-%d").date()
            self.setText(parsed.strftime("%d/%m/%Y"))
        except ValueError:
            pass

    def set_value(self, value: Any) -> None:
        text = str(value or "").strip()
        if not text:
            self.setText(date.today().strftime("%d/%m/%Y"))
            return

        for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y", "%d-%m-%y"]:
            try:
                parsed = datetime.strptime(text, fmt).date()
                self.setText(parsed.strftime("%d/%m/%Y"))
                return
            except ValueError:
                continue

        self.setText(text)
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
    def __init__(
        self,
        fields: list[FieldDefinition],
        parent: QWidget | None = None,
        title: str = "New Receipt",
        heading: str = "Add a receipt",
        subtitle: str = "Capture the transaction as soon as it is completed.",
        initial_values: dict[str, Any] | None = None,
        quick_only: bool = True,
        catalog: dict[str, dict[str, float]] | None = None,
        surcharge_rates: dict[str, float] | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(500)
        self.fields = [field for field in fields if field.quick_entry] if quick_only else list(fields)
        self.catalog = clone_catalog(catalog)
        self.surcharge_rates = normalise_surcharge_rates(surcharge_rates)
        self._base_amount: float | None = None
        self._surcharge_amount = 0.0
        self._applied_surcharge_percentage = 0.0
        self._amount_user_dirty = False
        self._loading_values = False
        self.widgets: dict[str, QWidget] = {}
        self.labels: dict[str, QLabel] = {}

        layout = QVBoxLayout(self)
        title_label = QLabel(heading)
        title_label.setObjectName("SectionTitle")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("Subtitle")
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)

        self.form = QFormLayout()
        self.form.setLabelAlignment(Qt.AlignLeft)
        for field_def in self.fields:
            widget = self._make_widget(field_def)
            self.widgets[field_def.key] = widget
            label = QLabel(self._label_text(field_def))
            self.labels[field_def.key] = label
            self.form.addRow(label, widget)

        self.surcharge_hint = QLabel("")
        self.surcharge_hint.setObjectName("SurchargeHint")
        self.surcharge_hint.setWordWrap(True)
        self.surcharge_hint.hide()
        self.form.addRow("", self.surcharge_hint)
        layout.addLayout(self.form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._wire_product_workflow()
        self._reset_product_workflow()
        if initial_values:
            self.set_values(initial_values)

    def _display_label(self, field_def: FieldDefinition) -> str:
        return WORKFLOW_FIELD_LABELS.get(field_def.key, field_def.label)

    def _label_text(self, field_def: FieldDefinition) -> str:
        required = " *" if field_def.required else ""
        return f"{self._display_label(field_def)}{required}"

    def _make_widget(self, field_def: FieldDefinition) -> QWidget:
        if field_def.key == "receipt_category":
            widget = QComboBox()
            widget.setEditable(False)
            widget.addItems(TRANSACTION_CATEGORY_OPTIONS)
            widget.setCurrentIndex(-1)
            return widget
        if field_def.key == "description":
            widget = QComboBox()
            widget.setEditable(False)
            widget.setCurrentIndex(-1)
            return widget
        if field_def.key == "quantity":
            widget = QSpinBox()
            widget.setRange(1, 999)
            widget.setValue(1)
            return widget
        if field_def.field_type == "date":
            return DateLineEdit()
        if field_def.field_type == "currency":
            return CurrencyLineEdit()
        if field_def.field_type == "number":
            widget = QDoubleSpinBox()
            widget.setMaximum(999999999.99)
            widget.setDecimals(2)
            return widget
        if field_def.field_type == "textarea":
            widget = QTextEdit()
            widget.setFixedHeight(90)
            return widget
        if field_def.field_type == "dropdown":
            widget = QComboBox()
            widget.setEditable(False)
            options = DROPDOWN_OPTIONS_BY_KEY.get(field_def.key, field_def.options)
            widget.addItems(options)
            return widget
        return QLineEdit()

    def _wire_product_workflow(self) -> None:
        category = self.widgets.get("receipt_category")
        product = self.widgets.get("description")
        quantity = self.widgets.get("quantity")
        payment = self.widgets.get("payment_type")
        amount = self.widgets.get("amount")

        if isinstance(category, QComboBox):
            category.currentTextChanged.connect(self._on_category_changed)
        if isinstance(product, QComboBox):
            product.currentTextChanged.connect(self._on_product_changed)
        if isinstance(quantity, QSpinBox):
            quantity.valueChanged.connect(self._on_quantity_changed)
        if isinstance(payment, QComboBox):
            payment.currentTextChanged.connect(self._on_payment_changed)
        if isinstance(amount, CurrencyLineEdit):
            amount.textEdited.connect(self._on_amount_text_edited)
            amount.editingFinished.connect(self._commit_manual_amount_if_dirty)

    def _set_row_visible(self, key: str, visible: bool) -> None:
        widget = self.widgets.get(key)
        label = self.labels.get(key)
        if widget is not None:
            widget.setVisible(visible)
        if label is not None:
            label.setVisible(visible)

    def _set_amount(self, amount: float | None) -> None:
        """Update the displayed final charged amount without changing its base."""
        widget = self.widgets.get("amount")
        if isinstance(widget, CurrencyLineEdit):
            if amount is None:
                widget.clear()
            else:
                widget.set_value(_money(amount))
        elif isinstance(widget, QDoubleSpinBox):
            widget.setValue(float(_money(amount or 0)))

    def _current_payment_type(self) -> str:
        widget = self.widgets.get("payment_type")
        if isinstance(widget, QComboBox):
            return widget.currentText().strip()
        return ""

    def _set_base_amount(self, amount: float | None) -> None:
        """Set the pre-surcharge price and recalculate the amount shown to the user."""
        self._base_amount = None if amount is None else _money(amount)
        self._amount_user_dirty = False
        self._apply_surcharge()

    def _apply_surcharge(self) -> None:
        if self._loading_values:
            return

        if self._base_amount is None:
            self._surcharge_amount = 0.0
            self._applied_surcharge_percentage = 0.0
            self._set_amount(None)
            self._update_surcharge_hint()
            return

        percentage = surcharge_percentage_for_payment(
            self._current_payment_type(),
            self.surcharge_rates,
        )
        if percentage > 0:
            total, surcharge = _surcharge_totals(
                self._base_amount,
                percentage,
            )
            self._surcharge_amount = surcharge
            self._applied_surcharge_percentage = percentage
            self._set_amount(total)
        else:
            self._surcharge_amount = 0.0
            self._applied_surcharge_percentage = 0.0
            self._set_amount(self._base_amount)

        self._update_surcharge_hint()

    def _update_surcharge_hint(self) -> None:
        if (
            self._base_amount is not None
            and self._surcharge_amount > 0
            and self._applied_surcharge_percentage > 0
        ):
            payment = self._current_payment_type() or "payment"
            self.surcharge_hint.setText(
                f"Includes {self._applied_surcharge_percentage:.2f}% {payment} surcharge: "
                f"+${self._surcharge_amount:,.2f} "
                f"(base ${self._base_amount:,.2f})"
            )
            self.surcharge_hint.show()
        else:
            self.surcharge_hint.clear()
            self.surcharge_hint.hide()

    def _on_payment_changed(self, _payment: str) -> None:
        self._apply_surcharge()

    def _on_amount_text_edited(self, _text: str) -> None:
        if not self._loading_values:
            self._amount_user_dirty = True

    def _commit_manual_amount_if_dirty(self) -> None:
        if self._loading_values or not self._amount_user_dirty:
            return
        self._amount_user_dirty = False
        widget = self.widgets.get("amount")
        if isinstance(widget, CurrencyLineEdit):
            # A manually typed amount is always interpreted as the pre-surcharge
            # amount. This is especially important for Function receipts.
            self._base_amount = _money(widget.value())
            self._apply_surcharge()

    def _ticket_quantity(self) -> int:
        quantity = self.widgets.get("quantity")
        if isinstance(quantity, QSpinBox):
            return max(1, quantity.value())
        return 1

    def _update_ticketed_event_amount(self) -> None:
        category_widget = self.widgets.get("receipt_category")
        product_widget = self.widgets.get("description")
        category = (
            category_widget.currentText().strip()
            if isinstance(category_widget, QComboBox)
            else ""
        )
        if category != "Ticketed Event":
            return

        product = (
            product_widget.currentText().strip()
            if isinstance(product_widget, QComboBox)
            else ""
        )
        unit_price = product_price(category, product, self.catalog)
        if unit_price is None or not product:
            self._set_base_amount(None)
            return

        self._set_base_amount(unit_price * self._ticket_quantity())

    def _reset_product_workflow(self) -> None:
        category = self.widgets.get("receipt_category")
        if isinstance(category, QComboBox):
            category.setCurrentIndex(-1)
        self._on_category_changed("")

    def _on_category_changed(self, category: str) -> None:
        category = str(category or "").strip()
        product = self.widgets.get("description")
        event = self.widgets.get("event_number")
        quantity = self.widgets.get("quantity")

        options = product_options(category, self.catalog)
        ticketed_event_selected = category == "Ticketed Event"
        # Ticketed events always show the event selector, even when only one event
        # is configured, so adding future ticket types does not change the workflow.
        needs_product_choice = len(options) > 1 or ticketed_event_selected

        if isinstance(product, QComboBox):
            product.blockSignals(True)
            product.clear()
            if needs_product_choice:
                product.addItems(options)
                product.setCurrentIndex(-1)
            elif options:
                product.addItem(options[0])
                product.setCurrentIndex(0)
            product.blockSignals(False)

        self._set_row_visible("description", needs_product_choice)
        if needs_product_choice and self.labels.get("description") is not None:
            if category in {"New Member", "Renewal"}:
                self.labels["description"].setText("Membership term *")
            elif ticketed_event_selected:
                self.labels["description"].setText("Event *")
            else:
                self.labels["description"].setText("Product *")

        self._set_row_visible("quantity", ticketed_event_selected)
        if isinstance(quantity, QSpinBox):
            quantity.blockSignals(True)
            quantity.setValue(1)
            quantity.blockSignals(False)

        function_selected = category == "Function"
        self._set_row_visible("event_number", function_selected)
        if function_selected and self.labels.get("event_number") is not None:
            self.labels["event_number"].setText("Event number *")
        if not function_selected and isinstance(event, QLineEdit):
            event.clear()

        if not category or function_selected or needs_product_choice:
            self._set_base_amount(None)
        else:
            product_name = options[0] if options else ""
            self._set_base_amount(product_price(category, product_name, self.catalog))

    def _on_product_changed(self, product: str) -> None:
        category_widget = self.widgets.get("receipt_category")
        category = category_widget.currentText().strip() if isinstance(category_widget, QComboBox) else ""
        if not category or category == "Function":
            return
        if category == "Ticketed Event":
            self._update_ticketed_event_amount()
            return
        price = product_price(category, str(product or "").strip(), self.catalog)
        self._set_base_amount(price)

    def _on_quantity_changed(self, _quantity: int) -> None:
        self._update_ticketed_event_amount()

    def set_values(self, values: dict[str, Any]) -> None:
        self._loading_values = True
        try:
            description = str(values.get("description", "") or "").strip()
            category = str(values.get("receipt_category", "") or "").strip()
            if not category:
                category = infer_category_from_description(description)

            category_widget = self.widgets.get("receipt_category")
            if isinstance(category_widget, QComboBox):
                if category and category_widget.findText(category) >= 0:
                    category_widget.setCurrentText(category)
                else:
                    category_widget.setCurrentIndex(-1)
                self._on_category_changed(category)

            product_widget = self.widgets.get("description")
            product = product_from_description(category, description, self.catalog)
            if isinstance(product_widget, QComboBox) and product:
                if product_widget.findText(product) < 0:
                    # Preserve historical custom products that may have since been
                    # removed from the current catalogue.
                    product_widget.addItem(product)
                product_widget.setCurrentText(product)
                self._on_product_changed(product)

            quantity_widget = self.widgets.get("quantity")
            if isinstance(quantity_widget, QSpinBox):
                quantity_value = values.get("quantity", 1)
                try:
                    quantity_value = max(1, int(float(quantity_value or 1)))
                except (TypeError, ValueError):
                    quantity_value = 1
                quantity_widget.setValue(quantity_value)

            event_widget = self.widgets.get("event_number")
            if isinstance(event_widget, QLineEdit):
                event_widget.setText(str(values.get("event_number", "") or ""))

            for field_def in self.fields:
                if field_def.key in {"receipt_category", "description", "quantity", "event_number"}:
                    continue
                widget = self.widgets.get(field_def.key)
                value = values.get(field_def.key, "")
                if widget is None:
                    continue
                if isinstance(widget, DateLineEdit):
                    widget.set_value(value)
                elif isinstance(widget, CurrencyLineEdit):
                    widget.set_value(value)
                elif isinstance(widget, QDoubleSpinBox):
                    try:
                        widget.setValue(float(value or 0))
                    except (TypeError, ValueError):
                        widget.setValue(0)
                elif isinstance(widget, QTextEdit):
                    widget.setPlainText(str(value or ""))
                elif isinstance(widget, QComboBox):
                    text = str(value or "")
                    if text and widget.findText(text) == -1:
                        widget.addItem(text)
                    if text:
                        widget.setCurrentText(text)
                    else:
                        widget.setCurrentIndex(-1)
                elif isinstance(widget, QLineEdit):
                    widget.setText(str(value or ""))
        finally:
            self._loading_values = False

        # Existing receipts keep their exact saved total. When surcharge metadata
        # exists, retain the original base/rate so changing today's setting does not
        # rewrite history merely by opening and saving an old receipt.
        if "amount" in values:
            saved_total = _money(values.get("amount", 0) or 0)
            if values.get("surcharge_base_amount") not in {None, ""}:
                self._base_amount = _money(values.get("surcharge_base_amount", saved_total))
                self._surcharge_amount = _money(values.get("surcharge_amount", 0) or 0)
                self._applied_surcharge_percentage = normalise_surcharge_percentage(
                    values.get("surcharge_percentage", 0),
                    0,
                )
            else:
                self._base_amount = saved_total
                self._surcharge_amount = 0.0
                self._applied_surcharge_percentage = 0.0
            self._set_amount(saved_total)
            self._update_surcharge_hint()
        self._amount_user_dirty = False

    def values(self) -> dict[str, Any]:
        self._commit_manual_amount_if_dirty()

        values: dict[str, Any] = {}
        category_widget = self.widgets.get("receipt_category")
        category = category_widget.currentText().strip() if isinstance(category_widget, QComboBox) else ""

        for field_def in self.fields:
            widget = self.widgets[field_def.key]
            if field_def.key == "receipt_category":
                values[field_def.key] = category
            elif field_def.key == "description":
                product = widget.currentText().strip() if isinstance(widget, QComboBox) else ""
                values[field_def.key] = description_for_selection(category, product)
            elif field_def.key == "quantity":
                values[field_def.key] = (
                    widget.value()
                    if category == "Ticketed Event" and isinstance(widget, QSpinBox)
                    else ""
                )
            elif isinstance(widget, DateLineEdit):
                values[field_def.key] = widget.value()
            elif isinstance(widget, QDateEdit):
                values[field_def.key] = widget.date().toString("yyyy-MM-dd")
            elif isinstance(widget, QDoubleSpinBox):
                values[field_def.key] = widget.value()
            elif isinstance(widget, CurrencyLineEdit):
                values[field_def.key] = widget.value()
            elif isinstance(widget, QTextEdit):
                values[field_def.key] = widget.toPlainText().strip()
            elif isinstance(widget, QComboBox):
                values[field_def.key] = widget.currentText().strip()
            elif isinstance(widget, QLineEdit):
                values[field_def.key] = widget.text().strip()

        if (
            self._base_amount is not None
            and self._surcharge_amount > 0
            and self._applied_surcharge_percentage > 0
        ):
            values["surcharge_base_amount"] = _money(self._base_amount)
            values["surcharge_percentage"] = self._applied_surcharge_percentage
            values["surcharge_amount"] = _money(self._surcharge_amount)

        return values

    def accept(self) -> None:
        values = self.values()
        missing: list[str] = []
        for field in self.fields:
            if field.required and not str(values.get(field.key, "")).strip():
                missing.append(self._display_label(field))
        if missing:
            QMessageBox.warning(self, "Missing required fields", "Please complete: " + ", ".join(missing))
            return
        if values.get("receipt_category") == "Function":
            if not str(values.get("event_number", "")).strip():
                QMessageBox.warning(self, "Event number required", "Please enter the Event number for this function purchase.")
                return
            if float(values.get("amount", 0) or 0) <= 0:
                QMessageBox.warning(self, "Amount required", "Please enter the amount for this function purchase.")
                return
        if values.get("receipt_category") == "Ticketed Event":
            if int(values.get("quantity", 0) or 0) < 1:
                QMessageBox.warning(self, "Quantity required", "Please select at least one ticket.")
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
        on_delete_receipt=None,
        width: int = 430,
        height: int = 640,
        parent: QWidget | None = None,
        catalog: dict[str, dict[str, float]] | None = None,
        surcharge_rates: dict[str, float] | None = None,
    ):
        super().__init__(parent)
        self.db = db
        self.fields = [field for field in fields if field.quick_entry]
        self.catalog = clone_catalog(catalog)
        self.surcharge_rates = normalise_surcharge_rates(surcharge_rates)
        self._base_amount: float | None = None
        self._surcharge_amount = 0.0
        self._applied_surcharge_percentage = 0.0
        self._amount_user_dirty = False
        self._loading_values = False
        self.on_receipt_saved = on_receipt_saved
        self.on_open_app = on_open_app
        self.on_position_changed = on_position_changed
        self.on_delete_receipt = on_delete_receipt
        self.widgets: dict[str, QWidget] = {}
        self.labels: dict[str, QLabel] = {}
        self._drag_offset: QPoint | None = None
        self._suggested_receipt_no: str | None = None

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
        header_widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        header_widget.setCursor(Qt.CursorShape.OpenHandCursor)
        header_widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        header_widget.setMinimumHeight(58)
        header_widget.installEventFilter(self)
        header = QHBoxLayout(header_widget)
        header.setContentsMargins(14, 10, 10, 10)
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
        self.today_list.setMinimumHeight(170)
        self.today_list.setMaximumHeight(320)
        self.today_list.setSpacing(8)
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

    def update_context(
        self,
        db: ReceiptDatabase,
        fields: list[FieldDefinition],
        catalog: dict[str, dict[str, float]] | None = None,
        surcharge_rates: dict[str, float] | None = None,
    ) -> None:
        self.db = db
        catalog_changed = False
        if catalog is not None:
            updated_catalog = clone_catalog(catalog)
            catalog_changed = updated_catalog != self.catalog
            self.catalog = updated_catalog

        surcharge_changed = False
        if surcharge_rates is not None:
            updated_rates = normalise_surcharge_rates(surcharge_rates)
            surcharge_changed = updated_rates != self.surcharge_rates
            self.surcharge_rates = updated_rates

        quick_keys = [field.key for field in fields if field.quick_entry]
        current_keys = [field.key for field in self.fields]
        if quick_keys != current_keys or catalog_changed or surcharge_changed:
            self.fields = [field for field in fields if field.quick_entry]
            self.rebuild_form()
        else:
            self.fields = [field for field in fields if field.quick_entry]
        self.refresh()

    def _display_label(self, field_def: FieldDefinition) -> str:
        return WORKFLOW_FIELD_LABELS.get(field_def.key, field_def.label)

    def rebuild_form(self) -> None:
        while self.form.rowCount():
            self.form.removeRow(0)
        self.widgets.clear()
        self.labels.clear()
        for field_def in self.fields:
            widget = self._make_widget(field_def)
            self.widgets[field_def.key] = widget
            required = " *" if field_def.required else ""
            label = QLabel(f"{self._display_label(field_def)}{required}")
            label.setObjectName("DesktopFieldLabel")
            self.labels[field_def.key] = label
            self.form.addRow(label, widget)

        self.surcharge_hint = QLabel("")
        self.surcharge_hint.setObjectName("SurchargeHint")
        self.surcharge_hint.setWordWrap(True)
        self.surcharge_hint.hide()
        self.form.addRow("", self.surcharge_hint)

        self._wire_product_workflow()
        self._reset_product_workflow()
        self.load_next_receipt_number()

    def load_next_receipt_number(self) -> None:
        """Pre-fill the desktop receipt form with the next sequential number."""
        widget = self.widgets.get("receipt_no")
        if isinstance(widget, QLineEdit):
            self._suggested_receipt_no = self.db.next_receipt_number()
            widget.setText(self._suggested_receipt_no)

    def _make_widget(self, field_def: FieldDefinition) -> QWidget:
        if field_def.key == "receipt_category":
            widget = QComboBox()
            widget.setEditable(False)
            widget.addItems(TRANSACTION_CATEGORY_OPTIONS)
            widget.setCurrentIndex(-1)
        elif field_def.key == "description":
            widget = QComboBox()
            widget.setEditable(False)
            widget.setCurrentIndex(-1)
        elif field_def.key == "quantity":
            widget = QSpinBox()
            widget.setRange(1, 999)
            widget.setValue(1)
        elif field_def.field_type == "date":
            widget = DateLineEdit()
        elif field_def.field_type == "currency":
            widget = CurrencyLineEdit()
        elif field_def.field_type == "number":
            widget = QDoubleSpinBox()
            widget.setMaximum(999999999.99)
            widget.setDecimals(2)
        elif field_def.field_type == "textarea":
            widget = QTextEdit()
            widget.setFixedHeight(58)
        elif field_def.field_type == "dropdown":
            widget = QComboBox()
            widget.setEditable(False)
            options = DROPDOWN_OPTIONS_BY_KEY.get(field_def.key, field_def.options)
            widget.addItems(options)
        else:
            widget = QLineEdit()

        widget.installEventFilter(self)
        return widget

    def _wire_product_workflow(self) -> None:
        category = self.widgets.get("receipt_category")
        product = self.widgets.get("description")
        quantity = self.widgets.get("quantity")
        payment = self.widgets.get("payment_type")
        amount = self.widgets.get("amount")

        if isinstance(category, QComboBox):
            category.currentTextChanged.connect(self._on_category_changed)
        if isinstance(product, QComboBox):
            product.currentTextChanged.connect(self._on_product_changed)
        if isinstance(quantity, QSpinBox):
            quantity.valueChanged.connect(self._on_quantity_changed)
        if isinstance(payment, QComboBox):
            payment.currentTextChanged.connect(self._on_payment_changed)
        if isinstance(amount, CurrencyLineEdit):
            amount.textEdited.connect(self._on_amount_text_edited)
            amount.editingFinished.connect(self._commit_manual_amount_if_dirty)

    def _set_row_visible(self, key: str, visible: bool) -> None:
        widget = self.widgets.get(key)
        label = self.labels.get(key)
        if widget is not None:
            widget.setVisible(visible)
        if label is not None:
            label.setVisible(visible)

    def _set_amount(self, amount: float | None) -> None:
        """Update the displayed final charged amount without changing its base."""
        widget = self.widgets.get("amount")
        if isinstance(widget, CurrencyLineEdit):
            if amount is None:
                widget.clear()
            else:
                widget.set_value(_money(amount))
        elif isinstance(widget, QDoubleSpinBox):
            widget.setValue(float(_money(amount or 0)))

    def _current_payment_type(self) -> str:
        widget = self.widgets.get("payment_type")
        if isinstance(widget, QComboBox):
            return widget.currentText().strip()
        return ""

    def _set_base_amount(self, amount: float | None) -> None:
        self._base_amount = None if amount is None else _money(amount)
        self._amount_user_dirty = False
        self._apply_surcharge()

    def _apply_surcharge(self) -> None:
        if self._loading_values:
            return

        if self._base_amount is None:
            self._surcharge_amount = 0.0
            self._applied_surcharge_percentage = 0.0
            self._set_amount(None)
            self._update_surcharge_hint()
            return

        percentage = surcharge_percentage_for_payment(
            self._current_payment_type(),
            self.surcharge_rates,
        )
        if percentage > 0:
            total, surcharge = _surcharge_totals(
                self._base_amount,
                percentage,
            )
            self._surcharge_amount = surcharge
            self._applied_surcharge_percentage = percentage
            self._set_amount(total)
        else:
            self._surcharge_amount = 0.0
            self._applied_surcharge_percentage = 0.0
            self._set_amount(self._base_amount)

        self._update_surcharge_hint()

    def _update_surcharge_hint(self) -> None:
        if (
            self._base_amount is not None
            and self._surcharge_amount > 0
            and self._applied_surcharge_percentage > 0
        ):
            payment = self._current_payment_type() or "payment"
            self.surcharge_hint.setText(
                f"Includes {self._applied_surcharge_percentage:.2f}% {payment} surcharge: "
                f"+${self._surcharge_amount:,.2f} "
                f"(base ${self._base_amount:,.2f})"
            )
            self.surcharge_hint.show()
        else:
            self.surcharge_hint.clear()
            self.surcharge_hint.hide()

    def _on_payment_changed(self, _payment: str) -> None:
        self._apply_surcharge()

    def _on_amount_text_edited(self, _text: str) -> None:
        if not self._loading_values:
            self._amount_user_dirty = True

    def _commit_manual_amount_if_dirty(self) -> None:
        if self._loading_values or not self._amount_user_dirty:
            return
        self._amount_user_dirty = False
        widget = self.widgets.get("amount")
        if isinstance(widget, CurrencyLineEdit):
            self._base_amount = _money(widget.value())
            self._apply_surcharge()

    def _ticket_quantity(self) -> int:
        quantity = self.widgets.get("quantity")
        if isinstance(quantity, QSpinBox):
            return max(1, quantity.value())
        return 1

    def _update_ticketed_event_amount(self) -> None:
        category_widget = self.widgets.get("receipt_category")
        product_widget = self.widgets.get("description")
        category = (
            category_widget.currentText().strip()
            if isinstance(category_widget, QComboBox)
            else ""
        )
        if category != "Ticketed Event":
            return

        product = (
            product_widget.currentText().strip()
            if isinstance(product_widget, QComboBox)
            else ""
        )
        unit_price = product_price(category, product, self.catalog)
        if unit_price is None or not product:
            self._set_base_amount(None)
            return

        self._set_base_amount(unit_price * self._ticket_quantity())

    def _reset_product_workflow(self) -> None:
        category = self.widgets.get("receipt_category")
        if isinstance(category, QComboBox):
            category.setCurrentIndex(-1)
        self._on_category_changed("")

    def _on_category_changed(self, category: str) -> None:
        category = str(category or "").strip()
        product = self.widgets.get("description")
        event = self.widgets.get("event_number")
        quantity = self.widgets.get("quantity")
        options = product_options(category, self.catalog)
        ticketed_event_selected = category == "Ticketed Event"
        needs_product_choice = len(options) > 1 or ticketed_event_selected

        if isinstance(product, QComboBox):
            product.blockSignals(True)
            product.clear()
            if needs_product_choice:
                product.addItems(options)
                product.setCurrentIndex(-1)
            elif options:
                product.addItem(options[0])
                product.setCurrentIndex(0)
            product.blockSignals(False)

        self._set_row_visible("description", needs_product_choice)
        if needs_product_choice and self.labels.get("description") is not None:
            if category in {"New Member", "Renewal"}:
                self.labels["description"].setText("Membership term *")
            elif ticketed_event_selected:
                self.labels["description"].setText("Event *")
            else:
                self.labels["description"].setText("Product *")

        self._set_row_visible("quantity", ticketed_event_selected)
        if isinstance(quantity, QSpinBox):
            quantity.blockSignals(True)
            quantity.setValue(1)
            quantity.blockSignals(False)

        function_selected = category == "Function"
        self._set_row_visible("event_number", function_selected)
        if function_selected and self.labels.get("event_number") is not None:
            self.labels["event_number"].setText("Event number *")
        if not function_selected and isinstance(event, QLineEdit):
            event.clear()

        if not category or function_selected or needs_product_choice:
            self._set_base_amount(None)
        else:
            product_name = options[0] if options else ""
            self._set_base_amount(product_price(category, product_name, self.catalog))

    def _on_product_changed(self, product: str) -> None:
        category_widget = self.widgets.get("receipt_category")
        category = category_widget.currentText().strip() if isinstance(category_widget, QComboBox) else ""
        if not category or category == "Function":
            return
        if category == "Ticketed Event":
            self._update_ticketed_event_amount()
            return
        self._set_base_amount(product_price(category, str(product or "").strip(), self.catalog))

    def _on_quantity_changed(self, _quantity: int) -> None:
        self._update_ticketed_event_amount()

    def values(self) -> dict[str, Any]:
        self._commit_manual_amount_if_dirty()

        values: dict[str, Any] = {}
        category_widget = self.widgets.get("receipt_category")
        category = category_widget.currentText().strip() if isinstance(category_widget, QComboBox) else ""

        for field_def in self.fields:
            widget = self.widgets[field_def.key]
            if field_def.key == "receipt_category":
                values[field_def.key] = category
            elif field_def.key == "description":
                product = widget.currentText().strip() if isinstance(widget, QComboBox) else ""
                values[field_def.key] = description_for_selection(category, product)
            elif field_def.key == "quantity":
                values[field_def.key] = (
                    widget.value()
                    if category == "Ticketed Event" and isinstance(widget, QSpinBox)
                    else ""
                )
            elif isinstance(widget, DateLineEdit):
                values[field_def.key] = widget.value()
            elif isinstance(widget, QDoubleSpinBox):
                values[field_def.key] = widget.value()
            elif isinstance(widget, CurrencyLineEdit):
                values[field_def.key] = widget.value()
            elif isinstance(widget, QTextEdit):
                values[field_def.key] = widget.toPlainText().strip()
            elif isinstance(widget, QComboBox):
                values[field_def.key] = widget.currentText().strip()
            elif isinstance(widget, QLineEdit):
                values[field_def.key] = widget.text().strip()

        if (
            self._base_amount is not None
            and self._surcharge_amount > 0
            and self._applied_surcharge_percentage > 0
        ):
            values["surcharge_base_amount"] = _money(self._base_amount)
            values["surcharge_percentage"] = self._applied_surcharge_percentage
            values["surcharge_amount"] = _money(self._surcharge_amount)

        return values

    def save_receipt(self) -> None:
        values = self.values()

        if str(values.get("receipt_no", "")) == str(self._suggested_receipt_no or ""):
            fresh_receipt_no = self.db.next_receipt_number()
            values["receipt_no"] = fresh_receipt_no
            receipt_widget = self.widgets.get("receipt_no")
            if isinstance(receipt_widget, QLineEdit):
                receipt_widget.setText(fresh_receipt_no)

        missing: list[str] = []
        for field in self.fields:
            if field.required and not str(values.get(field.key, "")).strip():
                missing.append(self._display_label(field))
        if missing:
            self.status_label.setText("Complete required fields: " + ", ".join(missing))
            return

        if values.get("receipt_category") == "Function":
            if not str(values.get("event_number", "")).strip():
                self.status_label.setText("Enter the Event number for this function purchase.")
                return
            if float(values.get("amount", 0) or 0) <= 0:
                self.status_label.setText("Enter the amount for this function purchase.")
                return
        if values.get("receipt_category") == "Ticketed Event":
            if int(values.get("quantity", 0) or 0) < 1:
                self.status_label.setText("Select at least one ticket.")
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
            if isinstance(widget, DateLineEdit):
                widget.setText(date.today().strftime("%d/%m/%Y"))
            elif isinstance(widget, QSpinBox):
                widget.setValue(1)
            elif isinstance(widget, QDoubleSpinBox):
                widget.setValue(0)
            elif isinstance(widget, CurrencyLineEdit):
                widget.clear()
            elif isinstance(widget, QTextEdit):
                widget.clear()
            elif isinstance(widget, QComboBox):
                widget.setCurrentIndex(-1)
            elif isinstance(widget, QLineEdit):
                widget.clear()
        self._reset_product_workflow()
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
            delete_btn.clicked.connect(lambda checked=False, receipt_id=int(row["id"]): self.delete_receipt(receipt_id))
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


class ReceiptMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.store = SettingsStore()
        self.settings = self.store.load()
        self.db = ReceiptDatabase(self.settings.db_path)
        self.backup_manager = DatabaseBackupManager(
            self.settings.db_path,
            default_backup_dir(),
            self.db.key_hex,
        )
        self.last_rows: list[Any] = []
        self.tray: QSystemTrayIcon | None = None
        self.tray_menu: QMenu | None = None
        self.desktop_panel: DesktopReceiptPanel | None = None
        self.current_page = 0
        self.page_size = 100
        self.total_results = 0
        self.active_receipt_count: int | None = None

        self.setWindowTitle("ReceiptFlow")
        if APP_LOGO_PATH.exists():
            self.setWindowIcon(QIcon(str(APP_LOGO_PATH)))
        self.resize(1120, 760)
        self.setStyleSheet(APP_QSS)

        self.stack = QStackedWidget()
        self.setCentralWidget(self._build_shell())
        self._build_pages()
        self._setup_tray()

        # Debounce live search so typing does not rebuild the result widgets and
        # hit SQLCipher once for every keystroke.
        self.search_debounce_timer = QTimer(self)
        self.search_debounce_timer.setSingleShot(True)
        self.search_debounce_timer.setInterval(250)
        self.search_debounce_timer.timeout.connect(self.refresh_results)

        # Let the first window paint before doing backup work. The recurring timer
        # only checks whether the next hourly snapshot is due.
        QTimer.singleShot(1500, self.run_automatic_backup)
        self.backup_timer = QTimer(self)
        self.backup_timer.setInterval(15 * 60 * 1000)
        self.backup_timer.timeout.connect(self.run_automatic_backup)
        self.backup_timer.start()

        self._quitting = False
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
        if APP_LOGO_PATH.exists():
            self.desktop_btn.setIcon(QIcon(str(APP_LOGO_PATH)))
            self.desktop_btn.setIconSize(QSize(22, 22))
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
        subtitle = QLabel("Capture receipts quickly, search transactions, and keep the desktop entry panel ready when you need it.")
        subtitle.setObjectName("Subtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        grid = QGridLayout()
        grid.setSpacing(16)
        grid.addWidget(self._action_card("Quick receipt entry", "Record a transaction immediately with guided product and pricing selection.", "Add receipt", self.open_quick_receipt, primary=True), 0, 0)
        grid.addWidget(self._action_card("Browse transactions", "Search across receipt number, member, event number, amount, date and notes.", "Browse", lambda: self.stack.setCurrentIndex(1)), 0, 1)
        grid.addWidget(self._action_card("Desktop tab", "Keep a small draggable receipt-entry panel open while you work.", "Show desktop tab", self.show_desktop_tab), 1, 0)
        grid.addWidget(self._action_card("Settings", "Manage app behaviour, desktop panel options and receipt fields.", "Open settings", lambda: self.stack.setCurrentIndex(2)), 1, 1)
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
        subtitle = QLabel(
            "Search the database using receipt numbers, names, member numbers, "
            "notes, dates or amounts."
        )
        subtitle.setObjectName("Subtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        controls = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Search anything, e.g. Smith, 2026-05-16, 45.00, card, receipt number"
        )
        self.search_input.textChanged.connect(self.schedule_refresh_results)
        controls.addWidget(self.search_input, 2)

        self.sort_combo = QComboBox()
        self.sort_combo.addItems(list(SORT_OPTIONS.keys()))
        self.sort_combo.setCurrentText(self.settings.default_sort)
        self.sort_combo.currentTextChanged.connect(self._browse_filters_changed)
        controls.addWidget(self.sort_combo)

        self.group_by_date = QCheckBox("Group by date")
        self.group_by_date.stateChanged.connect(self._browse_filters_changed)
        controls.addWidget(self.group_by_date)
        layout.addLayout(controls)

        action_row = QHBoxLayout()
        export_btn = QPushButton("Export current page")
        export_btn.setToolTip(
            "Export only the rows currently loaded on this Browse page."
        )
        export_btn.clicked.connect(self.export_current_results)
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_results)
        trash_btn = QPushButton("Trash")
        trash_btn.clicked.connect(self.open_trash)
        action_row.addWidget(export_btn)
        action_row.addWidget(refresh_btn)
        action_row.addWidget(trash_btn)
        action_row.addStretch()
        layout.addLayout(action_row)

        self.browse_model = BrowseTableModel(self.settings.fields, self)
        self.results_view = QTableView()
        self.results_view.setObjectName("BrowseTableView")
        self.results_view.setModel(self.browse_model)
        self.results_view.setAlternatingRowColors(True)
        self.results_view.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.results_view.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.results_view.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.results_view.setVerticalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )
        self.results_view.setHorizontalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )
        self.results_view.setWordWrap(False)
        self.results_view.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.results_view.verticalHeader().setVisible(False)
        self.results_view.verticalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Fixed
        )
        self.results_view.verticalHeader().setDefaultSectionSize(46)
        self.results_view.horizontalHeader().setSectionsMovable(False)
        self.results_view.doubleClicked.connect(self._edit_browse_index)

        self.actions_delegate = ReceiptActionsDelegate(self.results_view)
        self.actions_delegate.edit_requested.connect(self.edit_receipt)
        self.actions_delegate.delete_requested.connect(self.delete_receipt)
        self.results_view.setItemDelegateForColumn(
            self.browse_model.actions_column,
            self.actions_delegate,
        )
        self._configure_browse_columns()
        layout.addWidget(self.results_view, 1)

        pagination = QHBoxLayout()
        pagination.setSpacing(8)

        self.previous_page_btn = QPushButton("Previous")
        self.previous_page_btn.setObjectName("PaginationButton")
        self.previous_page_btn.clicked.connect(
            lambda: self._change_browse_page(-1)
        )
        pagination.addWidget(self.previous_page_btn)

        self.next_page_btn = QPushButton("Next")
        self.next_page_btn.setObjectName("PaginationButton")
        self.next_page_btn.clicked.connect(
            lambda: self._change_browse_page(1)
        )
        pagination.addWidget(self.next_page_btn)

        self.page_label = QLabel("")
        self.page_label.setObjectName("PaginationStatus")
        pagination.addWidget(self.page_label)
        pagination.addStretch()

        rows_label = QLabel("Rows per page")
        rows_label.setObjectName("PaginationStatus")
        pagination.addWidget(rows_label)

        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems(["50", "100", "200"])
        self.page_size_combo.setCurrentText(str(self.page_size))
        self.page_size_combo.currentTextChanged.connect(
            self._page_size_changed
        )
        pagination.addWidget(self.page_size_combo)
        layout.addLayout(pagination)

        self.result_count_label = QLabel("")
        self.result_count_label.setObjectName("Subtitle")
        layout.addWidget(self.result_count_label)
        return page

    def _settings_page(self) -> QWidget:
        # Work on a settings-only copy until the user explicitly clicks Save.
        self.catalog_draft = clone_catalog(self.settings.catalog)
        self._catalog_current_category = ""

        page = QWidget()
        page.setObjectName("SettingsPage")
        outer = QVBoxLayout(page)
        outer.setContentsMargins(28, 28, 28, 28)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setObjectName("SettingsScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content.setObjectName("SettingsContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(4, 4, 12, 20)
        layout.setSpacing(18)

        title = QLabel("Settings")
        title.setObjectName("Title")
        subtitle = QLabel(
            "Manage how ReceiptFlow behaves. Database storage and encryption are managed automatically for safety."
        )
        subtitle.setObjectName("Subtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        # Data and security -------------------------------------------------
        data_card = QFrame()
        data_card.setObjectName("SettingsCard")
        data_layout = QVBoxLayout(data_card)
        data_layout.setContentsMargins(20, 18, 20, 20)
        data_layout.setSpacing(12)

        data_title = QLabel("Data & security")
        data_title.setObjectName("SettingsCardTitle")
        data_help = QLabel(
            "ReceiptFlow manages the live database location so it cannot be accidentally moved into a sync folder or removable drive."
        )
        data_help.setObjectName("SettingsHelper")
        data_help.setWordWrap(True)
        data_layout.addWidget(data_title)
        data_layout.addWidget(data_help)

        data_form = QFormLayout()
        data_form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        data_form.setHorizontalSpacing(18)
        data_form.setVerticalSpacing(12)

        self.db_path_display = QLineEdit(str(self.settings.db_path))
        self.db_path_display.setReadOnly(True)
        self.db_path_display.setObjectName("ReadOnlySetting")
        self.db_path_display.setToolTip(str(self.settings.db_path))
        data_form.addRow("Database location", self.db_path_display)

        self.database_security_label = QLabel(
            f"SQLCipher {self.db.cipher_version()} · encryption key stored in the OS credential store"
        )
        self.database_security_label.setObjectName("SecurityStatus")
        self.database_security_label.setWordWrap(True)
        data_form.addRow("Encryption", self.database_security_label)
        data_layout.addLayout(data_form)
        layout.addWidget(data_card)

        # Behaviour and desktop panel --------------------------------------
        cards_row = QHBoxLayout()
        cards_row.setSpacing(18)

        behaviour_card = QFrame()
        behaviour_card.setObjectName("SettingsCard")
        behaviour_layout = QVBoxLayout(behaviour_card)
        behaviour_layout.setContentsMargins(20, 18, 20, 20)
        behaviour_layout.setSpacing(12)
        behaviour_title = QLabel("App behaviour")
        behaviour_title.setObjectName("SettingsCardTitle")
        behaviour_help = QLabel("Choose how ReceiptFlow behaves when it starts and while it is running.")
        behaviour_help.setObjectName("SettingsHelper")
        behaviour_help.setWordWrap(True)
        behaviour_layout.addWidget(behaviour_title)
        behaviour_layout.addWidget(behaviour_help)

        self.tray_checkbox = QCheckBox("Show menu bar / tray quick access")
        self.tray_checkbox.setChecked(self.settings.enable_tray)
        self.start_minimised_checkbox = QCheckBox("Start minimised")
        self.start_minimised_checkbox.setChecked(self.settings.start_minimised)
        behaviour_layout.addWidget(self.tray_checkbox)
        behaviour_layout.addWidget(self.start_minimised_checkbox)
        behaviour_layout.addStretch()
        cards_row.addWidget(behaviour_card, 1)

        desktop_card = QFrame()
        desktop_card.setObjectName("SettingsCard")
        desktop_layout = QVBoxLayout(desktop_card)
        desktop_layout.setContentsMargins(20, 18, 20, 20)
        desktop_layout.setSpacing(12)
        desktop_title = QLabel("Desktop receipt panel")
        desktop_title.setObjectName("SettingsCardTitle")
        desktop_help = QLabel("Control whether the quick-entry panel opens automatically and how large it appears.")
        desktop_help.setObjectName("SettingsHelper")
        desktop_help.setWordWrap(True)
        desktop_layout.addWidget(desktop_title)
        desktop_layout.addWidget(desktop_help)

        self.desktop_tab_launch_checkbox = QCheckBox("Show desktop tab on launch")
        self.desktop_tab_launch_checkbox.setChecked(self.settings.show_desktop_tab_on_launch)
        desktop_layout.addWidget(self.desktop_tab_launch_checkbox)

        size_row = QHBoxLayout()
        size_row.setSpacing(10)
        width_label = QLabel("Width")
        width_label.setObjectName("SettingsMiniLabel")
        self.desktop_width_spin = QSpinBox()
        self.desktop_width_spin.setRange(360, 900)
        self.desktop_width_spin.setSuffix(" px")
        self.desktop_width_spin.setValue(self.settings.desktop_tab_width)
        height_label = QLabel("Height")
        height_label.setObjectName("SettingsMiniLabel")
        self.desktop_height_spin = QSpinBox()
        self.desktop_height_spin.setRange(520, 1000)
        self.desktop_height_spin.setSuffix(" px")
        self.desktop_height_spin.setValue(self.settings.desktop_tab_height)
        size_row.addWidget(width_label)
        size_row.addWidget(self.desktop_width_spin)
        size_row.addSpacing(8)
        size_row.addWidget(height_label)
        size_row.addWidget(self.desktop_height_spin)
        size_row.addStretch()
        desktop_layout.addLayout(size_row)
        desktop_layout.addStretch()
        cards_row.addWidget(desktop_card, 1)

        layout.addLayout(cards_row)

        # Payment surcharges ------------------------------------------------
        surcharge_card = QFrame()
        surcharge_card.setObjectName("SettingsCard")
        surcharge_layout = QVBoxLayout(surcharge_card)
        surcharge_layout.setContentsMargins(20, 18, 20, 20)
        surcharge_layout.setSpacing(12)

        surcharge_title = QLabel("Payment surcharges")
        surcharge_title.setObjectName("SettingsCardTitle")
        surcharge_help = QLabel(
            "Set a separate surcharge percentage for each payment method. "
            "Use 0.00% when a payment type should have no surcharge. Cash is "
            "configurable in exactly the same way as the other payment methods."
        )
        surcharge_help.setObjectName("SettingsHelper")
        surcharge_help.setWordWrap(True)
        surcharge_layout.addWidget(surcharge_title)
        surcharge_layout.addWidget(surcharge_help)

        rates_grid = QGridLayout()
        rates_grid.setHorizontalSpacing(18)
        rates_grid.setVerticalSpacing(10)

        payment_heading = QLabel("Payment type")
        payment_heading.setObjectName("SettingsMiniLabel")
        rate_heading = QLabel("Surcharge")
        rate_heading.setObjectName("SettingsMiniLabel")
        rates_grid.addWidget(payment_heading, 0, 0)
        rates_grid.addWidget(rate_heading, 0, 1)

        self.surcharge_rate_spins: dict[str, QDoubleSpinBox] = {}
        for row, payment_type in enumerate(PAYMENT_TYPE_OPTIONS, start=1):
            payment_label = QLabel(payment_type)
            payment_label.setObjectName("PaymentSurchargeLabel")
            rates_grid.addWidget(payment_label, row, 0)

            rate_spin = QDoubleSpinBox()
            rate_spin.setRange(0.0, 100.0)
            rate_spin.setDecimals(2)
            rate_spin.setSingleStep(0.1)
            rate_spin.setSuffix(" %")
            rate_spin.setMinimumWidth(130)
            rate_spin.setValue(
                float(self.settings.payment_surcharges.get(payment_type, 0.0))
            )
            rate_spin.valueChanged.connect(self._update_surcharge_settings_preview)
            self.surcharge_rate_spins[payment_type] = rate_spin
            rates_grid.addWidget(rate_spin, row, 1)

        rates_grid.setColumnStretch(2, 1)
        surcharge_layout.addLayout(rates_grid)

        self.surcharge_preview_label = QLabel("")
        self.surcharge_preview_label.setObjectName("SurchargePreview")
        self.surcharge_preview_label.setWordWrap(True)
        surcharge_layout.addWidget(self.surcharge_preview_label)

        self._update_surcharge_settings_preview()
        layout.addWidget(surcharge_card)

        # Products and pricing ----------------------------------------------
        catalog_card = QFrame()
        catalog_card.setObjectName("SettingsCard")
        catalog_layout = QVBoxLayout(catalog_card)
        catalog_layout.setContentsMargins(20, 18, 20, 20)
        catalog_layout.setSpacing(12)

        catalog_title = QLabel("Products & pricing")
        catalog_title.setObjectName("SettingsCardTitle")
        catalog_help = QLabel(
            "Manage the products and current default prices used when creating new receipts. "
            "Price changes apply to future receipts only; existing receipts keep the amount saved at the time of sale."
        )
        catalog_help.setObjectName("SettingsHelper")
        catalog_help.setWordWrap(True)
        catalog_layout.addWidget(catalog_title)
        catalog_layout.addWidget(catalog_help)

        category_row = QHBoxLayout()
        category_label = QLabel("Category")
        category_label.setObjectName("SettingsMiniLabel")
        self.catalog_category_combo = QComboBox()
        self.catalog_category_combo.addItems(TRANSACTION_CATEGORY_OPTIONS)
        self.catalog_category_combo.setMinimumWidth(220)
        category_row.addWidget(category_label)
        category_row.addWidget(self.catalog_category_combo)
        category_row.addStretch()
        catalog_layout.addLayout(category_row)

        self.catalog_table = QTableWidget()
        self.catalog_table.setObjectName("ProductCatalogTable")
        self.catalog_table.setColumnCount(2)
        self.catalog_table.setHorizontalHeaderLabels(["Product / option", "Price"])
        self.catalog_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.catalog_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self.catalog_table.verticalHeader().setVisible(False)
        self.catalog_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.catalog_table.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )
        self.catalog_table.setMinimumHeight(250)
        self.catalog_table.setMaximumHeight(420)
        catalog_layout.addWidget(self.catalog_table)

        self.catalog_note = QLabel("")
        self.catalog_note.setObjectName("SettingsHelper")
        self.catalog_note.setWordWrap(True)
        catalog_layout.addWidget(self.catalog_note)

        catalog_buttons = QHBoxLayout()
        self.add_catalog_product_btn = QPushButton("Add product")
        self.add_catalog_product_btn.clicked.connect(self.add_catalog_product)
        self.remove_catalog_product_btn = QPushButton("Remove selected")
        self.remove_catalog_product_btn.setObjectName("DangerButton")
        self.remove_catalog_product_btn.clicked.connect(self.remove_catalog_product)
        catalog_buttons.addWidget(self.add_catalog_product_btn)
        catalog_buttons.addWidget(self.remove_catalog_product_btn)
        catalog_buttons.addStretch()
        catalog_layout.addLayout(catalog_buttons)

        self.catalog_category_combo.currentTextChanged.connect(
            self._catalog_category_changed
        )
        self._catalog_category_changed(self.catalog_category_combo.currentText())
        layout.addWidget(catalog_card)

        # Receipt fields ----------------------------------------------------
        fields_card = QFrame()
        fields_card.setObjectName("SettingsCard")
        fields_layout = QVBoxLayout(fields_card)
        fields_layout.setContentsMargins(20, 18, 20, 20)
        fields_layout.setSpacing(12)

        fields_title = QLabel("Receipt fields")
        fields_title.setObjectName("SettingsCardTitle")
        fields_help = QLabel(
            "Built-in fields protect the guided receipt workflow. You can choose what optional fields appear in quick entry and Browse, or add your own custom fields."
        )
        fields_help.setObjectName("SettingsHelper")
        fields_help.setWordWrap(True)
        fields_layout.addWidget(fields_title)
        fields_layout.addWidget(fields_help)

        self.fields_table = QTableWidget()
        self.fields_table.setObjectName("SettingsFieldsTable")
        self.fields_table.setColumnCount(5)
        self.fields_table.setHorizontalHeaderLabels(["Field", "Type", "Required", "Quick entry", "Browse"])
        self.fields_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.fields_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        for col in (2, 3, 4):
            self.fields_table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        self.fields_table.verticalHeader().setVisible(False)
        self.fields_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.fields_table.setAlternatingRowColors(False)
        self.fields_table.setMinimumHeight(470)
        self.fields_table.setMaximumHeight(620)
        fields_layout.addWidget(self.fields_table)

        field_buttons = QHBoxLayout()
        add_field_btn = QPushButton("Add custom field")
        add_field_btn.clicked.connect(self.add_field_row)
        remove_field_btn = QPushButton("Remove selected custom field")
        remove_field_btn.setObjectName("DangerButton")
        remove_field_btn.clicked.connect(self.remove_field_row)
        field_buttons.addWidget(add_field_btn)
        field_buttons.addWidget(remove_field_btn)
        field_buttons.addStretch()
        fields_layout.addLayout(field_buttons)
        layout.addWidget(fields_card)

        save_row = QHBoxLayout()
        save_row.addStretch()
        save_btn = QPushButton("Save settings")
        save_btn.setObjectName("PrimaryButton")
        save_btn.setMinimumWidth(190)
        save_btn.clicked.connect(self.save_settings_from_ui)
        save_row.addWidget(save_btn)
        layout.addLayout(save_row)
        layout.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll)
        self.populate_fields_table()
        return page

    def _update_surcharge_settings_preview(self, *_args: object) -> None:
        if not hasattr(self, "surcharge_rate_spins"):
            return

        rates = normalise_surcharge_rates(
            {
                payment_type: spin.value()
                for payment_type, spin in self.surcharge_rate_spins.items()
            }
        )

        examples: list[str] = []
        for payment_type in PAYMENT_TYPE_OPTIONS:
            percentage = rates.get(payment_type, 0.0)
            total, _surcharge = _surcharge_totals(20.0, percentage)
            examples.append(
                f"{payment_type}: {percentage:.2f}% → ${total:,.2f}"
            )

        self.surcharge_preview_label.setText(
            "Example on a $20.00 base amount: " + "   |   ".join(examples)
        )

    def _save_catalog_table_to_draft(self) -> None:
        """Capture the prices currently visible in the catalogue table."""
        category = str(getattr(self, "_catalog_current_category", "") or "").strip()
        if not category or not hasattr(self, "catalog_table"):
            return

        products: dict[str, float] = {}
        for row in range(self.catalog_table.rowCount()):
            item = self.catalog_table.item(row, 0)
            if item is None:
                continue
            product = item.text().strip()
            if not product:
                continue
            price_widget = self.catalog_table.cellWidget(row, 1)
            price = (
                float(price_widget.value())
                if isinstance(price_widget, QDoubleSpinBox)
                else 0.0
            )
            products[product] = max(0.0, price)

        self.catalog_draft[category] = products

    def _catalog_category_changed(self, category: str) -> None:
        """Persist the previous category draft, then show the selected category."""
        if getattr(self, "_catalog_current_category", ""):
            self._save_catalog_table_to_draft()

        category = str(category or "").strip()
        self._catalog_current_category = category
        self._populate_catalog_table(category)

    def _populate_catalog_table(self, category: str) -> None:
        category = str(category or "").strip()
        products = self.catalog_draft.get(category, {})
        self.catalog_table.setRowCount(len(products))

        default_products = DEFAULT_TRANSACTION_CATALOG.get(category, {})
        for row, (product, price) in enumerate(products.items()):
            name_item = QTableWidgetItem(product)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if product in default_products:
                name_item.setToolTip(
                    "Built-in ReceiptFlow option. Its price can be changed, but the option itself is protected."
                )
            else:
                name_item.setToolTip(
                    "Custom product. Remove and re-add it if you need to rename it."
                )
            self.catalog_table.setItem(row, 0, name_item)

            price_spin = QDoubleSpinBox()
            price_spin.setDecimals(2)
            price_spin.setRange(0.0, 999999.99)
            price_spin.setPrefix("$")
            price_spin.setSingleStep(1.0)
            price_spin.setValue(float(price or 0))
            price_spin.setMinimumWidth(130)
            self.catalog_table.setCellWidget(row, 1, price_spin)
            self.catalog_table.setRowHeight(row, 46)

        expandable = category in CATALOG_EXPANDABLE_CATEGORIES
        self.add_catalog_product_btn.setEnabled(expandable)
        self.remove_catalog_product_btn.setEnabled(expandable and bool(products))

        if category == "Function":
            self.catalog_note.setText(
                "Function receipts use an Event number and a manually entered amount, so they do not use preset products."
            )
        elif expandable:
            self.catalog_note.setText(
                "You can add products to this category. Built-in options are protected, while custom products can be removed."
            )
        else:
            self.catalog_note.setText(
                "This is a fixed ReceiptFlow category. You can change its current price, but its built-in product cannot be removed."
            )

    def add_catalog_product(self) -> None:
        category = self.catalog_category_combo.currentText().strip()
        if category not in CATALOG_EXPANDABLE_CATEGORIES:
            QMessageBox.information(
                self,
                "Fixed category",
                "This category has a fixed ReceiptFlow workflow and does not accept additional products.",
            )
            return

        self._save_catalog_table_to_draft()
        existing = self.catalog_draft.get(category, {})

        name, ok = QInputDialog.getText(
            self,
            "Add product",
            f"Product / option name for {category}:",
        )
        if not ok:
            return
        name = name.strip()
        if not name:
            QMessageBox.warning(self, "Product name required", "Enter a product name.")
            return
        if any(existing_name.lower() == name.lower() for existing_name in existing):
            QMessageBox.warning(
                self,
                "Product already exists",
                f"{name} already exists under {category}.",
            )
            return

        price, ok = QInputDialog.getDouble(
            self,
            "Product price",
            f"Current price for {name}:",
            0.0,
            0.0,
            999999.99,
            2,
        )
        if not ok:
            return

        self.catalog_draft.setdefault(category, {})[name] = float(price)
        self._populate_catalog_table(category)

        # Select the new row so it is easy to review/remove immediately.
        for row in range(self.catalog_table.rowCount()):
            item = self.catalog_table.item(row, 0)
            if item is not None and item.text() == name:
                self.catalog_table.selectRow(row)
                self.catalog_table.scrollToItem(item)
                break

    def remove_catalog_product(self) -> None:
        category = self.catalog_category_combo.currentText().strip()
        row = self.catalog_table.currentRow()
        if row < 0:
            QMessageBox.information(
                self,
                "Select a product",
                "Select the custom product you want to remove first.",
            )
            return

        item = self.catalog_table.item(row, 0)
        if item is None:
            return
        product = item.text().strip()
        if not product:
            return

        if product in DEFAULT_TRANSACTION_CATALOG.get(category, {}):
            QMessageBox.information(
                self,
                "Built-in product",
                "Built-in ReceiptFlow products cannot be removed. You can change the price instead.",
            )
            return

        self._save_catalog_table_to_draft()
        confirm = QMessageBox.question(
            self,
            "Remove product",
            f"Remove {product} from {category}? Existing receipts will not be changed.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        self.catalog_draft.get(category, {}).pop(product, None)
        self._populate_catalog_table(category)

    def _field_key_for_row(self, row: int) -> str:
        item = self.fields_table.item(row, 0)
        if item is None:
            return ""
        return str(item.data(Qt.ItemDataRole.UserRole) or "").strip()

    def _set_field_row(self, row: int, field_def: FieldDefinition, *, is_new: bool = False) -> None:
        built_in_keys = {
            "receipt_no", "transaction_date", "receipt_category", "description",
            "quantity", "event_number", "name", "amount", "payment_type", "member_no", "notes",
        }
        required_locked = {"receipt_no", "transaction_date", "receipt_category", "description", "amount", "payment_type"}
        quick_locked = {"receipt_no", "transaction_date", "receipt_category", "description", "quantity", "event_number", "amount", "payment_type"}
        is_built_in = field_def.key in built_in_keys

        label_item = QTableWidgetItem(field_def.label)
        label_item.setData(Qt.ItemDataRole.UserRole, field_def.key)
        if is_built_in:
            label_item.setFlags(label_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            label_item.setToolTip("Built-in ReceiptFlow field")
        elif is_new:
            label_item.setToolTip("Rename this field to something meaningful before saving")
        self.fields_table.setItem(row, 0, label_item)

        if is_built_in:
            type_item = QTableWidgetItem(field_def.field_type.title())
            type_item.setFlags(type_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.fields_table.setItem(row, 1, type_item)
        else:
            type_combo = QComboBox()
            type_combo.addItems(["text", "number", "currency", "date", "textarea", "dropdown"])
            type_combo.setCurrentText(field_def.field_type)
            self.fields_table.setCellWidget(row, 1, type_combo)

        required = CenteredCheckBox(field_def.required)
        if field_def.key in required_locked or field_def.key in {"event_number", "quantity"}:
            required.checkbox.setEnabled(False)
            if field_def.key == "event_number":
                required.checkbox.setToolTip("Required automatically for Function receipts only")
            elif field_def.key == "quantity":
                required.checkbox.setToolTip("Required automatically for Ticketed Event receipts only")
        self.fields_table.setCellWidget(row, 2, required)

        quick = CenteredCheckBox(field_def.quick_entry)
        if field_def.key in quick_locked:
            quick.checkbox.setChecked(True)
            quick.checkbox.setEnabled(False)
            quick.checkbox.setToolTip("Required for the guided receipt-entry workflow")
        self.fields_table.setCellWidget(row, 3, quick)

        browse = CenteredCheckBox(field_def.browse_column)
        self.fields_table.setCellWidget(row, 4, browse)
        self.fields_table.setRowHeight(row, 46)

    def populate_fields_table(self) -> None:
        self.fields_table.setRowCount(len(self.settings.fields))
        for row, field_def in enumerate(self.settings.fields):
            self._set_field_row(row, field_def)

    def add_field_row(self) -> None:
        existing = {self._field_key_for_row(row) for row in range(self.fields_table.rowCount())}
        base = "custom_field"
        key = base
        counter = 2
        while key in existing:
            key = f"{base}_{counter}"
            counter += 1

        row = self.fields_table.rowCount()
        self.fields_table.insertRow(row)
        self._set_field_row(
            row,
            FieldDefinition(key, "New custom field", "text", False, True, True, []),
            is_new=True,
        )
        self.fields_table.selectRow(row)
        self.fields_table.scrollToItem(self.fields_table.item(row, 0))
        self.fields_table.editItem(self.fields_table.item(row, 0))

    def remove_field_row(self) -> None:
        row = self.fields_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Select a field", "Select the custom field you want to remove first.")
            return

        built_in_keys = {
            "receipt_no", "transaction_date", "receipt_category", "description",
            "quantity", "event_number", "name", "amount", "payment_type", "member_no", "notes",
        }
        key = self._field_key_for_row(row)
        if key in built_in_keys:
            QMessageBox.information(
                self,
                "Built-in field",
                "Built-in receipt fields cannot be removed. You can change whether optional fields appear in Quick entry or Browse instead.",
            )
            return
        self.fields_table.removeRow(row)

    def save_settings_from_ui(self) -> None:
        fields: list[FieldDefinition] = []
        seen: set[str] = set()
        built_in_keys = {
            "receipt_no", "transaction_date", "receipt_category", "description",
            "quantity", "event_number", "name", "amount", "payment_type", "member_no", "notes",
        }
        required_locked = {"receipt_no", "transaction_date", "receipt_category", "description", "amount", "payment_type"}
        quick_locked = {"receipt_no", "transaction_date", "receipt_category", "description", "quantity", "event_number", "amount", "payment_type"}

        for row in range(self.fields_table.rowCount()):
            key = self._field_key_for_row(row)
            label_item = self.fields_table.item(row, 0)
            label = (label_item.text() if label_item else "").strip()
            if not key or not label:
                QMessageBox.warning(self, "Invalid field", "Each receipt field needs a name.")
                return
            if key in seen:
                QMessageBox.warning(self, "Duplicate field", f"ReceiptFlow found a duplicate internal field: {key}")
                return
            seen.add(key)

            if key in built_in_keys:
                current = next((f for f in self.settings.fields if f.key == key), None)
                if current is None:
                    continue
                field_type = current.field_type
                options = list(current.options)
            else:
                type_combo = self.fields_table.cellWidget(row, 1)
                field_type = type_combo.currentText() if isinstance(type_combo, QComboBox) else "text"
                options = []

            required_widget = self.fields_table.cellWidget(row, 2)
            quick_widget = self.fields_table.cellWidget(row, 3)
            browse_widget = self.fields_table.cellWidget(row, 4)
            required = required_widget.isChecked() if hasattr(required_widget, "isChecked") else False
            quick = quick_widget.isChecked() if hasattr(quick_widget, "isChecked") else True
            browse = browse_widget.isChecked() if hasattr(browse_widget, "isChecked") else True

            if key in required_locked:
                required = True
            elif key in {"event_number", "quantity"}:
                required = False
            if key in quick_locked:
                quick = True

            if key == "receipt_category":
                label = "Category"
                field_type = "dropdown"
                options = list(TRANSACTION_CATEGORY_OPTIONS)
            elif key == "description":
                label = "Product / term"
                field_type = "dropdown"
                options = []
            elif key == "quantity":
                label = "Quantity"
                field_type = "number"
                options = []
            elif key == "event_number":
                label = "Event number"
                field_type = "text"
                options = []

            fields.append(FieldDefinition(key, label, field_type, required, quick, browse, options))

        self._save_catalog_table_to_draft()
        self.settings.catalog = clone_catalog(self.catalog_draft)
        self.settings.payment_surcharges = normalise_surcharge_rates(
            {
                payment_type: spin.value()
                for payment_type, spin in self.surcharge_rate_spins.items()
            }
        )

        self.settings.enable_tray = self.tray_checkbox.isChecked()
        self.settings.start_minimised = self.start_minimised_checkbox.isChecked()
        self.settings.show_desktop_tab_on_launch = self.desktop_tab_launch_checkbox.isChecked()
        self.settings.desktop_tab_width = self.desktop_width_spin.value()
        self.settings.desktop_tab_height = self.desktop_height_spin.value()
        self.settings.default_sort = self.sort_combo.currentText() if hasattr(self, "sort_combo") else self.settings.default_sort
        self.settings.fields = fields
        self.store.save(self.settings)

        if hasattr(self, "browse_model"):
            self.browse_model.set_fields(self.settings.fields)
            self._configure_browse_columns()

        self._setup_tray()
        if self.desktop_panel is not None:
            self.desktop_panel.set_panel_size(self.settings.desktop_tab_width, self.settings.desktop_tab_height)
            self.desktop_panel.update_context(
                self.db,
                self.settings.fields,
                self.settings.catalog,
                self.settings.payment_surcharges,
            )
        self.refresh_results()
        QMessageBox.information(self, "Settings saved", "Your ReceiptFlow settings have been saved.")

    def open_quick_receipt(self) -> None:
        suggested_receipt_no = self.db.next_receipt_number()
        dialog = ReceiptFormDialog(
            self.settings.fields,
            self,
            initial_values={"receipt_no": suggested_receipt_no},
            catalog=self.settings.catalog,
            surcharge_rates=self.settings.payment_surcharges,
        )
        if dialog.exec() != QDialog.Accepted:
            return
        values = dialog.values()

        # Refresh an untouched auto-suggestion in case another receipt was saved
        # while this dialog was open. Manual receipt-number changes are preserved.
        if str(values.get("receipt_no", "")) == suggested_receipt_no:
            values["receipt_no"] = self.db.next_receipt_number()
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
        self.active_receipt_count = None
        self.refresh_results()
        self.refresh_desktop_tab()
        QMessageBox.information(self, "Receipt saved", "The receipt was added to the database.")

    def _row_values_for_edit(self, row: Any) -> dict[str, Any]:
        custom = json.loads(row["custom_fields"] or "{}")
        values: dict[str, Any] = {}
        for field_def in self.settings.fields:
            if field_def.key in CORE_FIELD_KEYS:
                values[field_def.key] = row[field_def.key]
            else:
                values[field_def.key] = custom.get(field_def.key, "")

        for key in (
            "surcharge_base_amount",
            "surcharge_percentage",
            "surcharge_amount",
        ):
            if key in custom:
                values[key] = custom[key]
        return values

    def _record_from_values(self, values: dict[str, Any], source: str) -> ReceiptRecord:
        custom = {key: value for key, value in values.items() if key not in CORE_FIELD_KEYS}
        return ReceiptRecord(
            receipt_no=str(values.get("receipt_no", "") or ""),
            transaction_date=str(values.get("transaction_date", "") or ""),
            name=str(values.get("name", "") or ""),
            amount=float(values.get("amount", 0) or 0),
            payment_type=str(values.get("payment_type", "") or ""),
            member_no=str(values.get("member_no", "") or ""),
            notes=str(values.get("notes", "") or ""),
            custom_fields=custom,
            source=source,
        )

    def edit_receipt(self, receipt_id: int) -> None:
        row = self.db.get_receipt(receipt_id)
        if row is None:
            QMessageBox.warning(self, "Receipt not found", "This receipt could not be found. It may have already been deleted.")
            self.refresh_results()
            self.refresh_desktop_tab()
            return

        dialog = ReceiptFormDialog(
            self.settings.fields,
            self,
            title="Edit Receipt",
            heading="Edit receipt",
            subtitle="Update the receipt details and save the corrected data back to the database.",
            initial_values=self._row_values_for_edit(row),
            quick_only=False,
            catalog=self.settings.catalog,
            surcharge_rates=self.settings.payment_surcharges,
        )
        if dialog.exec() != QDialog.Accepted:
            return

        record = self._record_from_values(dialog.values(), str(row["source"] or "manual"))
        self.db.update_receipt(receipt_id, record)
        self.refresh_results()
        self.refresh_desktop_tab()
        QMessageBox.information(self, "Receipt updated", "The receipt was updated successfully.")

    def delete_receipt(self, receipt_id: int) -> None:
        row = self.db.get_receipt(receipt_id)
        if row is None:
            QMessageBox.warning(self, "Receipt not found", "This receipt could not be found. It may have already been deleted.")
            self.refresh_results()
            self.refresh_desktop_tab()
            return

        amount = f"${float(row['amount']):,.2f}" if row["amount"] not in {None, ""} else ""
        description = row["name"] or row["receipt_no"] or "this receipt"
        confirm = QMessageBox.question(
            self,
            "Move receipt to Trash",
            f"Move {description} {amount} to Trash? You can restore it later.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        self.db.delete_receipt(receipt_id)
        self.active_receipt_count = None
        self.refresh_results()
        self.refresh_desktop_tab()
        QMessageBox.information(self, "Moved to Trash", "The receipt was moved to Trash and can be restored.")

    def schedule_refresh_results(self, *_args: object) -> None:
        """Coalesce rapid search edits into a single paged database/UI refresh."""
        self.current_page = 0
        if hasattr(self, "search_debounce_timer"):
            self.search_debounce_timer.start()
        else:
            self.refresh_results()

    def run_automatic_backup(self) -> None:
        """Create an hourly recovery point without interrupting normal use."""
        try:
            self.backup_manager.create_backup_if_due()
        except Exception as exc:
            # Backups should never crash the receipt-entry workflow.
            print(f"ReceiptFlow automatic backup failed: {exc}", file=sys.stderr)

    def open_trash(self) -> None:
        """Show soft-deleted receipts and allow the user to restore them."""
        dialog = QDialog(self)
        dialog.setWindowTitle("ReceiptFlow Trash")
        dialog.resize(720, 460)

        layout = QVBoxLayout(dialog)

        heading = QLabel("Trash")
        heading.setObjectName("SectionTitle")
        helper = QLabel(
            "Deleted receipts remain in the database and can be restored here."
        )
        helper.setObjectName("Subtitle")
        helper.setWordWrap(True)

        layout.addWidget(heading)
        layout.addWidget(helper)

        trash_list = QListWidget()
        layout.addWidget(trash_list, 1)

        def populate() -> None:
            trash_list.clear()
            rows = self.db.trashed_receipts()

            if not rows:
                item = QListWidgetItem("Trash is empty")
                item.setFlags(Qt.ItemFlag.NoItemFlags)
                trash_list.addItem(item)
                return

            for row in rows:
                amount = (
                    f"${float(row['amount']):,.2f}"
                    if row["amount"] not in {None, ""}
                    else ""
                )
                name = row["name"] or row["receipt_no"] or "Unnamed receipt"
                deleted_at = row["deleted_at"] or ""
                text = (
                    f"{name} | {row['receipt_no'] or 'No receipt no'} | {amount}"
                    f"\nDeleted: {deleted_at}"
                )
                item = QListWidgetItem(text)
                item.setData(Qt.ItemDataRole.UserRole, int(row["id"]))
                trash_list.addItem(item)

        def restore_selected() -> None:
            item = trash_list.currentItem()
            if item is None:
                return

            receipt_id = item.data(Qt.ItemDataRole.UserRole)
            if receipt_id is None:
                return

            if self.db.restore_receipt(int(receipt_id)):
                self.active_receipt_count = None
                populate()
                self.refresh_results()
                self.refresh_desktop_tab()

        populate()

        buttons = QHBoxLayout()
        restore_btn = QPushButton("Restore selected")
        restore_btn.setObjectName("PrimaryButton")
        restore_btn.clicked.connect(restore_selected)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)

        buttons.addWidget(restore_btn)
        buttons.addStretch()
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)

        dialog.exec()

    def _browse_filters_changed(self, *_args: object) -> None:
        """Reset paging when search presentation or sort order changes."""
        self.current_page = 0
        self.refresh_results()

    def _page_size_changed(self, value: str) -> None:
        try:
            page_size = int(value)
        except (TypeError, ValueError):
            page_size = 100
        self.page_size = max(25, min(page_size, 500))
        self.current_page = 0
        self.refresh_results()

    def _change_browse_page(self, delta: int) -> None:
        page_count = max(
            1,
            (self.total_results + self.page_size - 1) // self.page_size,
        )
        target = max(0, min(self.current_page + int(delta), page_count - 1))
        if target == self.current_page:
            return
        self.current_page = target
        self.refresh_results()

    def _configure_browse_columns(self) -> None:
        if not hasattr(self, "results_view") or not hasattr(self, "browse_model"):
            return

        header = self.results_view.horizontalHeader()
        actions_column = self.browse_model.actions_column

        for column in range(self.browse_model.columnCount()):
            if column == actions_column:
                header.setSectionResizeMode(
                    column,
                    QHeaderView.ResizeMode.Fixed,
                )
                self.results_view.setColumnWidth(column, 160)
            else:
                header.setSectionResizeMode(
                    column,
                    QHeaderView.ResizeMode.Stretch,
                )

        self.results_view.setItemDelegateForColumn(
            actions_column,
            self.actions_delegate,
        )

    def _edit_browse_index(self, index) -> None:
        if not hasattr(self, "browse_model"):
            return
        if index.column() == self.browse_model.actions_column:
            return
        receipt_id = self.browse_model.receipt_id_at(index)
        if receipt_id is not None:
            self.edit_receipt(receipt_id)

    def refresh_results(self, *_args: object) -> None:
        if not hasattr(self, "results_view"):
            return

        query = self.search_input.text() if hasattr(self, "search_input") else ""
        sort = (
            self.sort_combo.currentText()
            if hasattr(self, "sort_combo")
            else self.settings.default_sort
        )

        # Clamp the requested page after database mutations or filter changes.
        offset = self.current_page * self.page_size
        rows, total = self.db.browse_page(
            query=query,
            sort=sort,
            limit=self.page_size,
            offset=offset,
        )
        self.total_results = total

        page_count = max(
            1,
            (self.total_results + self.page_size - 1) // self.page_size,
        )
        if self.current_page >= page_count:
            self.current_page = page_count - 1
            offset = self.current_page * self.page_size
            rows, total = self.db.browse_page(
                query=query,
                sort=sort,
                limit=self.page_size,
                offset=offset,
            )
            self.total_results = total

        self.last_rows = list(rows)
        self.browse_model.set_rows(
            self.last_rows,
            grouped=self.group_by_date.isChecked(),
        )
        self._configure_browse_columns()

        if self.total_results:
            first = (self.current_page * self.page_size) + 1
            last = first + len(self.last_rows) - 1
            self.result_count_label.setText(
                f"Showing {first:,}–{last:,} of {self.total_results:,} transaction(s)."
            )
        else:
            self.result_count_label.setText("No matching transactions.")

        self.page_label.setText(
            f"Page {self.current_page + 1:,} of {page_count:,}"
        )
        self.previous_page_btn.setEnabled(self.current_page > 0)
        self.next_page_btn.setEnabled(self.current_page + 1 < page_count)

        if not query:
            self.active_receipt_count = self.total_results
        elif self.active_receipt_count is None:
            self.active_receipt_count = self.db.count_active_receipts()

        if hasattr(self, "summary_label") and self.active_receipt_count is not None:
            self.summary_label.setText(
                f"Current database: {self.active_receipt_count:,} receipt(s)."
            )

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
                self.delete_receipt,
                self.settings.desktop_tab_width,
                self.settings.desktop_tab_height,
                catalog=self.settings.catalog,
                surcharge_rates=self.settings.payment_surcharges,
            )
            if self.settings.desktop_tab_x is not None and self.settings.desktop_tab_y is not None:
                self.desktop_panel.move(self.settings.desktop_tab_x, self.settings.desktop_tab_y)
            else:
                self.desktop_panel.move(18, 44)
        else:
            self.desktop_panel.set_panel_size(self.settings.desktop_tab_width, self.settings.desktop_tab_height)
            self.desktop_panel.update_context(
                self.db,
                self.settings.fields,
                self.settings.catalog,
                self.settings.payment_surcharges,
            )
        self.desktop_panel.show()
        self.desktop_panel.raise_()
        self.desktop_panel.activateWindow()

    def save_desktop_tab_position(self, position: QPoint) -> None:
        self.settings.desktop_tab_x = position.x()
        self.settings.desktop_tab_y = position.y()
        self.store.save(self.settings)

    def _desktop_receipt_saved(self) -> None:
        self.active_receipt_count = None
        self.refresh_results()
        self.refresh_desktop_tab()

    def refresh_desktop_tab(self) -> None:
        if self.desktop_panel is not None:
            self.desktop_panel.update_context(
                self.db,
                self.settings.fields,
                self.settings.catalog,
                self.settings.payment_surcharges,
            )
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
            self.tray.setContextMenu(None)
            self.tray.deleteLater()
            self.tray = None
        if self.tray_menu is not None:
            self.tray_menu.deleteLater()
            self.tray_menu = None
        if not self.settings.enable_tray or not QSystemTrayIcon.isSystemTrayAvailable():
            app = QApplication.instance()
            if app is not None:
                app.setQuitOnLastWindowClosed(True)
            return
        self.tray = QSystemTrayIcon(self._app_icon(), self)
        menu = QMenu(self)
        self.tray_menu = menu
        show_action = QAction("Show ReceiptFlow", self)
        show_action.triggered.connect(self.show_normal)
        new_action = QAction("New receipt", self)
        new_action.triggered.connect(self.open_quick_receipt)
        browse_action = QAction("Browse transactions", self)
        browse_action.triggered.connect(lambda: (self.show_normal(), self.stack.setCurrentIndex(1)))
        desktop_action = QAction("Show desktop tab", self)
        desktop_action.triggered.connect(self.show_desktop_tab)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_application)
        menu.addAction(show_action)
        menu.addAction(new_action)
        menu.addAction(browse_action)
        menu.addAction(desktop_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda reason: self.open_quick_receipt() if reason == QSystemTrayIcon.Trigger else None)
        self.tray.show()
        app = QApplication.instance()
        if app is not None:
            app.setQuitOnLastWindowClosed(False)

    def show_normal(self) -> None:
        if self.isMinimized():
            self.showNormal()
        else:
            self.show()
        self.raise_()
        self.activateWindow()

    def quit_application(self) -> None:
        """Perform deterministic tray/timer cleanup, then quit the event loop."""
        self.prepare_shutdown()
        app = QApplication.instance()
        if app is not None:
            app.quit()

    def prepare_shutdown(self) -> None:
        if self._quitting:
            return
        self._quitting = True

        if hasattr(self, "search_debounce_timer"):
            self.search_debounce_timer.stop()
        if hasattr(self, "backup_timer"):
            self.backup_timer.stop()

        if self.desktop_panel is not None:
            self.desktop_panel.hide()
            self.desktop_panel.deleteLater()
            self.desktop_panel = None

        if self.tray is not None:
            self.tray.hide()
            self.tray.setContextMenu(None)
            self.tray.deleteLater()
            self.tray = None
        if self.tray_menu is not None:
            self.tray_menu.deleteLater()
            self.tray_menu = None

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._quitting:
            event.accept()
        elif self.tray and self.tray.isVisible():
            self.hide()
            event.ignore()
        else:
            event.accept()


def run() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("ReceiptFlow")
    app.setApplicationDisplayName("ReceiptFlow")
    app.setStyleSheet(APP_QSS)

    instance = SingleInstanceManager(app)
    try:
        is_primary, notified = instance.acquire()
    except RuntimeError as exc:
        QMessageBox.critical(None, "ReceiptFlow startup error", str(exc))
        return 1

    if not is_primary:
        if not notified:
            QMessageBox.information(
                None,
                "ReceiptFlow is already running",
                "Another ReceiptFlow process already owns the application lock, "
                "but it could not be contacted. Check the system tray or Task Manager "
                "instead of opening another copy.",
            )
        return 0

    try:
        window = ReceiptMainWindow()
    except (SecureKeyStoreError, DatabaseEncryptionError) as exc:
        instance.release()
        QMessageBox.critical(
            None,
            "ReceiptFlow security error",
            str(exc)
            + "\n\nReceiptFlow has stopped rather than creating or overwriting a database.",
        )
        return 1

    instance.activation_requested.connect(window.show_normal)
    app.aboutToQuit.connect(window.prepare_shutdown)
    app.aboutToQuit.connect(instance.release)

    if not window.settings.start_minimised:
        window.show()
    if window.settings.show_desktop_tab_on_launch:
        window.show_desktop_tab()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
