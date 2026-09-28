from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QTextEdit,
    QWidget,
)

from ...config import (
    FieldDefinition,
    PAYMENT_TYPE_OPTIONS,
    TRANSACTION_CATEGORY_OPTIONS,
    clone_catalog,
    description_for_selection,
    infer_category_from_description,
    normalise_surcharge_percentage,
    normalise_surcharge_rates,
    product_from_description,
    product_options,
    product_price,
    surcharge_percentage_for_payment,
)
from .inputs import CurrencyLineEdit, DateLineEdit


DROPDOWN_OPTIONS_BY_KEY = {
    "payment_type": list(PAYMENT_TYPE_OPTIONS),
}

WORKFLOW_FIELD_LABELS = {
    "receipt_category": "Category",
    "description": "Product / term",
    "quantity": "Quantity",
    "event_number": "Event number",
}


def money(value: float | int | str | Decimal) -> float:
    """Round a currency value to cents using normal half-up rounding."""
    return float(
        Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    )


def surcharge_totals(base_amount: float, percentage: float) -> tuple[float, float]:
    """Return ``(final total, surcharge amount)``, rounded independently to cents."""
    base = Decimal(str(base_amount or 0)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    rate = Decimal(str(normalise_surcharge_percentage(percentage))) / Decimal("100")
    surcharge = (base * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    total = (base + surcharge).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return float(total), float(surcharge)


@dataclass(frozen=True, slots=True)
class ReceiptValidationIssue:
    title: str
    dialog_message: str
    inline_message: str


class ReceiptEntryForm(QWidget):
    """Shared receipt-entry form used by both the dialog and desktop panel.

    The component owns field creation, product/category workflow, automatic pricing,
    payment surcharges, value serialisation, edit-value loading and validation. The
    surrounding dialog/panel remains responsible for persistence and presentation.
    """

    def __init__(
        self,
        fields: list[FieldDefinition],
        parent: QWidget | None = None,
        *,
        quick_only: bool = True,
        catalog: dict[str, dict[str, float]] | None = None,
        surcharge_rates: dict[str, float] | None = None,
        compact: bool = False,
        field_label_object_name: str | None = None,
        event_filter_target: QWidget | None = None,
    ):
        super().__init__(parent)
        self.quick_only = bool(quick_only)
        self.compact = bool(compact)
        self.setObjectName(
            "DesktopReceiptEntryForm" if self.compact else "ReceiptDialogEntryForm"
        )
        self.field_label_object_name = field_label_object_name
        self.event_filter_target = event_filter_target

        self.fields = self._filtered_fields(fields, self.quick_only)
        self.catalog = clone_catalog(catalog)
        self.surcharge_rates = normalise_surcharge_rates(surcharge_rates)

        self._base_amount: float | None = None
        self._surcharge_amount = 0.0
        self._applied_surcharge_percentage = 0.0
        self._amount_user_dirty = False
        self._loading_values = False

        self.widgets: dict[str, QWidget] = {}
        self.labels: dict[str, QLabel] = {}

        self.form = QFormLayout(self)
        self.form.setContentsMargins(0, 0, 0, 0)
        self.form.setLabelAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self.form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        if self.compact:
            self.form.setHorizontalSpacing(10)
            self.form.setVerticalSpacing(8)
        else:
            self.form.setHorizontalSpacing(24)
            self.form.setVerticalSpacing(14)

        self.surcharge_hint = QLabel("")
        self.surcharge_hint.setObjectName("SurchargeHint")
        self.surcharge_hint.setWordWrap(True)
        self.surcharge_hint.hide()

        self.rebuild()

    @staticmethod
    def _filtered_fields(
        fields: list[FieldDefinition],
        quick_only: bool,
    ) -> list[FieldDefinition]:
        if quick_only:
            return [field for field in fields if field.quick_entry]
        return list(fields)

    @staticmethod
    def _display_label(field_def: FieldDefinition) -> str:
        return WORKFLOW_FIELD_LABELS.get(field_def.key, field_def.label)

    def _label_text(self, field_def: FieldDefinition) -> str:
        required = " *" if field_def.required else ""
        return f"{self._display_label(field_def)}{required}"

    def widget(self, key: str) -> QWidget | None:
        return self.widgets.get(key)

    def rebuild(self) -> None:
        while self.form.rowCount():
            self.form.removeRow(0)

        self.widgets.clear()
        self.labels.clear()

        for field_def in self.fields:
            widget = self._make_widget(field_def)
            self.widgets[field_def.key] = widget

            label = QLabel(self._label_text(field_def))
            if self.field_label_object_name:
                label.setObjectName(self.field_label_object_name)
            self.labels[field_def.key] = label
            self.form.addRow(label, widget)

        self.surcharge_hint = QLabel("")
        self.surcharge_hint.setObjectName("SurchargeHint")
        self.surcharge_hint.setWordWrap(True)
        self.surcharge_hint.hide()
        self.form.addRow("", self.surcharge_hint)

        self._wire_product_workflow()
        self._reset_product_workflow()

    def update_context(
        self,
        fields: list[FieldDefinition],
        catalog: dict[str, dict[str, float]] | None = None,
        surcharge_rates: dict[str, float] | None = None,
        *,
        quick_only: bool | None = None,
    ) -> bool:
        """Update form configuration and return ``True`` when a rebuild occurred."""
        next_quick_only = self.quick_only if quick_only is None else bool(quick_only)
        next_fields = self._filtered_fields(fields, next_quick_only)
        next_catalog = self.catalog if catalog is None else clone_catalog(catalog)
        next_rates = (
            self.surcharge_rates
            if surcharge_rates is None
            else normalise_surcharge_rates(surcharge_rates)
        )

        fields_changed = [field.key for field in next_fields] != [
            field.key for field in self.fields
        ]
        quick_mode_changed = next_quick_only != self.quick_only
        catalog_changed = next_catalog != self.catalog
        surcharge_changed = next_rates != self.surcharge_rates

        self.quick_only = next_quick_only
        self.fields = next_fields
        self.catalog = next_catalog
        self.surcharge_rates = next_rates

        if fields_changed or quick_mode_changed or catalog_changed or surcharge_changed:
            self.rebuild()
            return True
        return False

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
            widget.setFixedHeight(58 if self.compact else 90)
        elif field_def.field_type == "dropdown":
            widget = QComboBox()
            widget.setEditable(False)
            options = DROPDOWN_OPTIONS_BY_KEY.get(field_def.key, field_def.options)
            widget.addItems(options)
        else:
            widget = QLineEdit()

        widget.setProperty("receiptField", True)
        widget.setProperty("fieldKey", field_def.key)
        self._apply_placeholder(widget, field_def)

        if self.event_filter_target is not None:
            widget.installEventFilter(self.event_filter_target)
        return widget

    def _apply_placeholder(self, widget: QWidget, field_def: FieldDefinition) -> None:
        """Apply concise prompts without changing stored field values."""
        placeholders = {
            "receipt_no": "Enter receipt number",
            "receipt_category": "Select a category",
            "description": "Select an option",
            "event_number": "Enter event number",
            "name": "Enter name or customer",
            "payment_type": "Select a payment type",
            "member_no": "Enter member number",
            "notes": "Add any additional notes...",
        }
        text = placeholders.get(field_def.key, "")
        if not text:
            return

        if isinstance(widget, QLineEdit) and field_def.key not in {
            "transaction_date",
            "amount",
        }:
            widget.setPlaceholderText(text)
        elif isinstance(widget, QTextEdit):
            widget.setPlaceholderText(text)
        elif isinstance(widget, QComboBox) and hasattr(widget, "setPlaceholderText"):
            widget.setPlaceholderText(text)

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
        widget = self.widgets.get("amount")
        if isinstance(widget, CurrencyLineEdit):
            if amount is None:
                widget.clear()
            else:
                widget.set_value(money(amount))
        elif isinstance(widget, QDoubleSpinBox):
            widget.setValue(float(money(amount or 0)))

    def _current_payment_type(self) -> str:
        widget = self.widgets.get("payment_type")
        if isinstance(widget, QComboBox):
            return widget.currentText().strip()
        return ""

    def _set_base_amount(self, amount: float | None) -> None:
        self._base_amount = None if amount is None else money(amount)
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
            total, surcharge = surcharge_totals(self._base_amount, percentage)
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
            self._base_amount = money(widget.value())
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
        category = (
            category_widget.currentText().strip()
            if isinstance(category_widget, QComboBox)
            else ""
        )
        if not category or category == "Function":
            return
        if category == "Ticketed Event":
            self._update_ticketed_event_amount()
            return
        self._set_base_amount(
            product_price(category, str(product or "").strip(), self.catalog)
        )

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
                if field_def.key in {
                    "receipt_category",
                    "description",
                    "quantity",
                    "event_number",
                }:
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

        if "amount" in values:
            saved_total = money(values.get("amount", 0) or 0)
            if values.get("surcharge_base_amount") not in {None, ""}:
                self._base_amount = money(
                    values.get("surcharge_base_amount", saved_total)
                )
                self._surcharge_amount = money(values.get("surcharge_amount", 0) or 0)
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
        category = (
            category_widget.currentText().strip()
            if isinstance(category_widget, QComboBox)
            else ""
        )

        for field_def in self.fields:
            widget = self.widgets[field_def.key]
            if field_def.key == "receipt_category":
                values[field_def.key] = category
            elif field_def.key == "description":
                product = (
                    widget.currentText().strip()
                    if isinstance(widget, QComboBox)
                    else ""
                )
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
            values["surcharge_base_amount"] = money(self._base_amount)
            values["surcharge_percentage"] = self._applied_surcharge_percentage
            values["surcharge_amount"] = money(self._surcharge_amount)

        return values

    def clear_values(self) -> None:
        for field_def in self.fields:
            widget = self.widgets.get(field_def.key)
            if isinstance(widget, DateLineEdit):
                widget.set_value("")
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
        self._amount_user_dirty = False

    def validation_issue(
        self,
        values: dict[str, Any] | None = None,
    ) -> ReceiptValidationIssue | None:
        values = self.values() if values is None else values

        missing: list[str] = []
        for field in self.fields:
            if field.required and not str(values.get(field.key, "")).strip():
                missing.append(self._display_label(field))
        if missing:
            names = ", ".join(missing)
            return ReceiptValidationIssue(
                "Missing required fields",
                "Please complete: " + names,
                "Complete required fields: " + names,
            )

        if values.get("receipt_category") == "Function":
            if not str(values.get("event_number", "")).strip():
                return ReceiptValidationIssue(
                    "Event number required",
                    "Please enter the Event number for this function purchase.",
                    "Enter the Event number for this function purchase.",
                )
            if float(values.get("amount", 0) or 0) <= 0:
                return ReceiptValidationIssue(
                    "Amount required",
                    "Please enter the amount for this function purchase.",
                    "Enter the amount for this function purchase.",
                )

        if values.get("receipt_category") == "Ticketed Event":
            if int(values.get("quantity", 0) or 0) < 1:
                return ReceiptValidationIssue(
                    "Quantity required",
                    "Please select at least one ticket.",
                    "Select at least one ticket.",
                )

        return None
