from __future__ import annotations

from datetime import date, datetime
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLineEdit, QWidget


class CurrencyLineEdit(QLineEdit):
    """A typable money field that formats values like ``$10.00``."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setPlaceholderText("$0.00")
        self.editingFinished.connect(self.format_as_currency)

    def value(self) -> float:
        text = self.text().strip()
        if not text:
            return 0.0

        cleaned = text.replace("$", "").replace(",", "").strip()
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

    INPUT_FORMATS = (
        "%d/%m/%Y",
        "%d/%m/%y",
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d-%m-%y",
    )

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setPlaceholderText("dd/mm/yyyy")
        self.setText(date.today().strftime("%d/%m/%Y"))
        self.editingFinished.connect(self.format_date)

    def value(self) -> str:
        text = self.text().strip()
        if not text:
            return ""

        for fmt in self.INPUT_FORMATS:
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

        for fmt in self.INPUT_FORMATS:
            try:
                parsed = datetime.strptime(text, fmt).date()
                self.setText(parsed.strftime("%d/%m/%Y"))
                return
            except ValueError:
                continue

        self.setText(text)


class CenteredCheckBox(QWidget):
    """Centre a checkbox inside table cells while exposing checkbox-like helpers."""

    def __init__(self, checked: bool = False, parent: QWidget | None = None):
        super().__init__(parent)
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(checked)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.checkbox)

    def isChecked(self) -> bool:
        return self.checkbox.isChecked()

    def setChecked(self, checked: bool) -> None:
        self.checkbox.setChecked(checked)
